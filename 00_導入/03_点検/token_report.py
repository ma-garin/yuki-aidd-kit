#!/usr/bin/env python3
"""token_report.py — セッション JSONL（~/.claude/projects/<proj>/<id>.jsonl）から消費構造を実測する。依存なし。

token_audit.py が「仕組みが配線されているか」を見るのに対し、こちらは「実際に何に使ったか」を数える。
同じ message.id の usage は 1 回だけ数える（ストリーミングで複数行に分かれるため）。

  input / cache_write / cache_read / output の合計と構成比、応答数、1 応答あたりの出力
  費用比: 単価の倍率（input=1, cache_write=1.25, cache_read=0.1, output=5）で重み付けした構成比。
          倍率は 5 分キャッシュの公表比。1 時間キャッシュは cache_write=2.0（--write-mult で変更）

使い方: python3 00_導入/03_点検/token_report.py [JSONL ...]   （省略時はカレントのプロジェクトの最新セッション）
        python3 00_導入/03_点検/token_report.py --by skill,agent,mcp,tool [--skills-dir DIR] [--over N] [JSONL ...]

--by（区分別。複数可）: 区分・名前・回数・トークン（4 種の合計）・費用比・平均・最大 の表を、既存の出力の後に足す。
  transcript の形式は公開されておらず変わりうる。06_保守者向け/03_回帰テスト/fixtures/transcript-sample.jsonl
  （実物と同じ構造の合成データ）で固定している。形式が変わったらこの fixture を作り直す。
  帰属（assistant 応答の tool_use を見る）:
    name=="Skill" → skill（input.skill）／ name=="Agent" または "Task" → agent（input.subagent_type、無ければ description）
    name が mcp__<server>__ で始まる → mcp（<server>）／ それ以外 → tool（name）
    利用者が /名前 で呼んだもの（user 本文の <command-name>）は skill の回数に数える（トークンは付けない）
  usage: message.usage の input / cache_creation / cache_read / output。**同じ requestId の usage は 1 回だけ数える**
    （1 応答は content ブロックごとに複数行に分かれ、各行に同じ usage が載るため。キーごとの最大を採る）。
  按分規則: 1 応答に tool_use が k 個あれば、その応答の usage（4 種の合計トークン）を k 等分して各 tool_use に配る。
    整数で割り、割り切れない端数は最初の tool_use に寄せる（按分後の合計が元の usage と一致する）。費用は実数で等分する。
    tool_use の無い応答は「帰属なし」として表の外に合計だけ出す（費用比の分母には入る）。
  サブエージェント: セッション JSONL と同じ場所の <セッション>/subagents/agent-*.jsonl も読む。
    その transcript の全 usage を、生成した Agent/Task の tool_use（agent-*.meta.json の toolUseId で対応付け）の行に足す。
    対応が取れなければ meta の agentType（無ければ attributionAgent・ファイル名）の行に 1 回として足す。
    サブエージェント内の tool_use は skill / mcp / tool の表にも出るので、区分の表どうしは重なりうる（各表は別の切り口）。
  費用比: 読んだ全応答（本体＋サブエージェント）の重み付き費用に対する割合。平均 = トークン ÷ 回数、最大 = 1 回あたりの最大。
--skills-dir DIR: DIR 直下の <名前>/SKILL.md をスキルとみなし、一度も呼ばれないスキルと、
  1 セッション（本体＋そのサブエージェント）で --over N 回（既定 10）を超えて呼ばれたスキルを出す。
  このとき一覧に無い名前（/clear などの組み込みコマンド・(不明)）は区分 command として skill の後に出し、
  「呼ばれすぎ」は一覧にあるスキルだけを対象にする。
hook での常時記録や外部（Langfuse 等）への送出はしない。事後に transcript を読むだけ。

--hooks [LOG]（B12）: hook の判定の記録 `.claude/hook-decisions.log`（JSONL。secret_patterns.log_decision が書く）を集計し、
  hook 別の deny・block・warn の回数、解除（AIDD_ALLOW_*・AIDD_*_OK）で通した回数（override。誤検知の目安）、
  上位 3 件の理由の表を出す。LOG を省くと `$CLAUDE_PROJECT_DIR/.claude/`・カレントの `.claude/`・`~/.claude/` の順に探す。
  壊れた行は数えずに件数だけ出す。このときは transcript を読まない。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
LABELS = ("input", "cache_write", "cache_read", "output")
CATS = ("skill", "agent", "mcp", "tool")
CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
UNKNOWN = "(不明)"


def latest_session() -> Path | None:
    proj = Path.home() / ".claude" / "projects" / str(Path.cwd()).replace("/", "-").replace(".", "-")
    files = sorted(proj.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def collect(path: Path) -> tuple[dict[str, int], int]:
    totals = dict.fromkeys(KEYS, 0)
    seen: set[str] = set()
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            msg = e.get("message") if isinstance(e, dict) else None
            if not isinstance(msg, dict) or e.get("type") != "assistant" or not isinstance(msg.get("usage"), dict) or not msg["usage"]:
                continue            # 壊れた行・形の違う行は飛ばす（非公開形式なので落ちないことを優先する）
            mid = msg.get("id") or e.get("uuid")
            if mid in seen:
                continue
            seen.add(mid)
            for k in KEYS:
                totals[k] += _int(msg["usage"].get(k))
    return totals, len(seen)


def _int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def report(path: Path, write_mult: float) -> str:
    t, n = collect(path)
    total = sum(t.values()) or 1
    mults = dict(zip(KEYS, (1.0, write_mult, 0.1, 5.0)))
    cost = {k: t[k] * mults[k] for k in KEYS}
    ctotal = sum(cost.values()) or 1
    rows = [f"# {path.name}  応答 {n} 件・出力 {t['output_tokens'] // max(n, 1):,} tok/応答",
            "| 区分 | トークン | 構成比 | 費用比 |", "|---|---:|---:|---:|"]
    rows += [f"| {lab} | {t[k]:,} | {t[k] / total:.2%} | {cost[k] / ctotal:.2%} |" for k, lab in zip(KEYS, LABELS)]
    rows.append(f"| 計 | {total:,} | | |")
    return "\n".join(rows)


# ---- 区分別（--by） ---------------------------------------------------------------------------

def _entries(path: Path):
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if isinstance(e, dict):
                yield e


def classify(block: dict) -> tuple[str, str]:
    """tool_use 1 個を (区分, 名前) にする。規則は docstring の「帰属」。"""
    name = block.get("name")
    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
    if not isinstance(name, str) or not name:
        return "tool", UNKNOWN
    if name == "Skill":
        return "skill", str(inp.get("skill") or UNKNOWN)
    if name in ("Agent", "Task"):
        return "agent", str(inp.get("subagent_type") or inp.get("description") or UNKNOWN)
    if name.startswith("mcp__"):
        return "mcp", name[5:].split("__", 1)[0] or UNKNOWN
    return "tool", name


def read_requests(path: Path) -> tuple[list[tuple[dict[str, int], list[dict]]], Counter, str]:
    """requestId ごとに (usage, tool_use の一覧) を返す。あわせて <command-name> の回数と最初の attributionAgent。"""
    reqs: dict[str, tuple[dict[str, int], dict[str, dict]]] = {}
    cmds: Counter = Counter()
    agent_attr = ""
    for e in _entries(path):
        msg = e.get("message") if isinstance(e.get("message"), dict) else {}
        if e.get("type") == "user" and isinstance(msg.get("content"), str):
            cmds.update(m.group(1) for m in CMD_RE.finditer(msg["content"]))
        if e.get("type") != "assistant":
            continue
        agent_attr = agent_attr or str(e.get("attributionAgent") or "")
        rid = e.get("requestId") or msg.get("id") or e.get("uuid")
        if not rid:
            continue
        usage, tools = reqs.setdefault(str(rid), (dict.fromkeys(KEYS, 0), {}))
        u = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
        for k in KEYS:
            try:
                usage[k] = max(usage[k], int(u.get(k) or 0))
            except (TypeError, ValueError):
                pass
        content = msg.get("content") if isinstance(msg.get("content"), list) else []
        for i, b in enumerate(content):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                tools[str(b.get("id") or f"{e.get('uuid')}#{i}")] = b
    return [(u, list(t.items())) for u, t in reqs.values()], cmds, agent_attr


def subagent_files(path: Path) -> list[Path]:
    d = path.with_suffix("") / "subagents"
    return sorted(d.glob("agent-*.jsonl")) if d.is_dir() else []


def attribute(path: Path, write_mult: float) -> dict:
    """1 セッション分の呼び出し（call）ごとの (区分, 名前, トークン, 費用) と、帰属なし・総費用を返す。"""
    mults = dict(zip(KEYS, (1.0, write_mult, 0.1, 5.0)))
    calls: dict[str, list] = {}            # call id → [(区分, 名前), トークン, 費用]
    state = {"cost": 0.0, "none_n": 0, "none_tok": 0.0, "none_cost": 0.0}

    def add(reqs) -> tuple[int, float]:
        tok_sum, cost_sum = 0, 0.0
        for usage, tools in reqs:
            tok = sum(usage.values())
            cost = sum(usage[k] * mults[k] for k in KEYS)
            tok_sum, cost_sum = tok_sum + tok, cost_sum + cost
            state["cost"] += cost
            if not tools:
                state["none_n"] += 1
                state["none_tok"] += tok
                state["none_cost"] += cost
                continue
            base, rest = divmod(tok, len(tools))    # 按分: k 等分。端数は最初の tool_use に寄せて合計を保つ
            for j, (tid, b) in enumerate(tools):
                calls[tid] = [classify(b), base + (rest if j == 0 else 0), cost / len(tools)]
        return tok_sum, cost_sum

    reqs, cmds, _ = read_requests(path)
    add(reqs)
    subs = []
    for f in subagent_files(path):
        sreqs, scmds, attr = read_requests(f)
        subs.append((f, attr, *add(sreqs)))
        cmds.update(scmds)
    for f, attr, tok, cost in subs:        # 全 transcript を読んでから対応付ける（入れ子の Agent もあるため）
        try:
            meta = json.loads(f.with_name(f.stem + ".meta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            meta = {}
        meta = meta if isinstance(meta, dict) else {}
        tid = meta.get("toolUseId")
        if tid in calls and calls[tid][0][0] == "agent":
            calls[tid][1] += tok
            calls[tid][2] += cost
        else:
            calls[f"sub:{f.name}"] = [("agent", str(meta.get("agentType") or attr or f.stem)), tok, cost]
    for name, n in cmds.items():
        for i in range(n):
            calls[f"cmd:{name}:{i}"] = [("skill", name), 0, 0.0]
    return {"calls": list(calls.values()), "subs": len(subs), **state}


def by_report(path: Path, cats: list[str], write_mult: float, known: set[str] | None = None) -> tuple[str, Counter]:
    """区分別の表。known（--skills-dir のスキル名）があれば、一覧に無い skill 名は区分 command にする。"""
    a = attribute(path, write_mult)
    total_cost = a["cost"] or 1
    rows: dict[tuple[str, str], list[float]] = {}
    for key, tok, cost in a["calls"]:
        if known is not None and key[0] == "skill" and key[1] not in known:
            key = ("command", key[1])
        r = rows.setdefault(key, [0, 0, 0.0, 0])
        r[0] += 1
        r[1] += tok
        r[2] += cost
        r[3] = max(r[3], tok)
    out = [f"## 区分別（--by {','.join(cats)}）", "",
           "| 区分 | 名前 | 回数 | トークン | 費用比 | 平均 | 最大 |", "|---|---|---:|---:|---:|---:|---:|"]
    shown = [x for c in cats for x in ((c, "command") if c == "skill" and known is not None else (c,))]
    for c in shown:
        for (cat, name), (n, tok, cost, mx) in sorted(rows.items(), key=lambda kv: (-kv[1][1], kv[0][1])):
            if cat == c:
                out.append(f"| {cat} | {name} | {int(n)} | {round(tok):,} | {cost / total_cost:.2%} | {round(tok / n):,} | {round(mx):,} |")
    out += ["", f"- 帰属なし（tool_use の無い応答）: {a['none_n']} 応答・{round(a['none_tok']):,} tok・費用比 {a['none_cost'] / total_cost:.2%}",
            f"- 読んだ transcript: 本体 1・サブエージェント {a['subs']}（agent の行はサブエージェントの消費を含む。区分の表どうしは重なりうる）",
            "- 按分: 1 応答に tool_use が複数あれば、その応答の usage を等分する（端数は最初の tool_use）。同じ requestId の usage は 1 回だけ数える"]
    skills = Counter()
    for (cat, name), (n, *_rest) in rows.items():
        if cat == "skill":
            skills[name] += int(n)
    return "\n".join(out), skills


def known_skills(skills_dir: Path) -> list[str]:
    return sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md"))


def skill_usage(skills_dir: Path, per_session: list[tuple[Path, Counter]], over: int) -> str:
    """per_session の Counter は一覧にあるスキルだけ（by_report が一覧外を command に分けている）。"""
    known = known_skills(skills_dir)
    used = Counter()
    for _, c in per_session:
        used.update(c)
    unused = [s for s in known if not used[s]]
    heavy = [f"{name}（{p.name}: {n} 回）" for p, c in per_session for name, n in sorted(c.items()) if n > over]
    return "\n".join([f"## スキルの利用（{skills_dir}・{len(known)} 件）", "",
                      f"- 一度も呼ばれないスキル（{len(unused)} 件）: " + (", ".join(unused) or "なし"),
                      f"- 1 セッションで {over} 回を超えて呼ばれたスキル: " + (", ".join(heavy) or "なし")])


HOOK_LOG = "hook-decisions.log"
DECISION_COLS = ("deny", "block", "warn", "override")


def default_hook_log() -> Path:
    import os
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), str(Path.cwd())):
        if base and (Path(base) / ".claude" / HOOK_LOG).is_file():
            return Path(base) / ".claude" / HOOK_LOG
    return Path.home() / ".claude" / HOOK_LOG


def hook_report(path: Path) -> str:
    counts: dict[str, Counter] = {}
    reasons: dict[str, Counter] = {}
    envs: dict[str, Counter] = {}
    broken = 0
    first = last = ""
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                broken += 1
                continue
            if not isinstance(r, dict) or not isinstance(r.get("hook"), str):
                broken += 1
                continue
            hook, dec = r["hook"], str(r.get("decision", ""))
            counts.setdefault(hook, Counter())[dec] += 1
            reasons.setdefault(hook, Counter())[str(r.get("reason", ""))] += 1
            if dec == "override" and r.get("env"):
                envs.setdefault(hook, Counter())[str(r["env"])] += 1
            t = str(r.get("time", ""))
            first = min(first, t) if first else t
            last = max(last, t)
    out = [f"## hook の判定（{path}）", ""]
    if not counts:
        out.append("記録なし" + (f"（読めない行 {broken} 件）" if broken else ""))
        return "\n".join(out)
    out += [f"期間: {first} 〜 {last}" + (f"（読めない行 {broken} 件は数えない）" if broken else ""), "",
            "| hook | deny | block | warn | 解除で通過 | 上位の理由 |", "|---|---:|---:|---:|---:|---|"]
    for hook in sorted(counts, key=lambda h: (-sum(counts[h].values()), h)):
        c = counts[hook]
        top = "／".join(f"{k}（{n}）" for k, n in reasons.get(hook, Counter()).most_common(3)).replace("|", "\\|")
        ov = str(c["override"]) + (f"（{','.join(envs[hook])}）" if hook in envs else "")
        out.append(f"| {hook} | {c['deny']} | {c['block']} | {c['warn']} | {ov} | {top or '-'} |")
    out += ["", "解除で通過 = AIDD_ALLOW_*・AIDD_*_OK で止めずに通した回数（止める判定だった操作）。"
            "deny＋block に比べて多い hook は誤検知を疑う"]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jsonl", nargs="*", type=Path)
    ap.add_argument("--write-mult", type=float, default=1.25)
    ap.add_argument("--by", default="", help="skill,agent,mcp,tool のうち出す区分（カンマ区切り）")
    ap.add_argument("--skills-dir", type=Path, help="一度も呼ばれない・呼ばれすぎのスキルを出す（<名前>/SKILL.md の並ぶ場所）")
    ap.add_argument("--over", type=int, default=10, help="1 セッションでこの回数を超えたら呼ばれすぎ（既定 10）")
    ap.add_argument("--hooks", nargs="?", const="", default=None, metavar="LOG",
                    help="hook の判定の記録（.claude/hook-decisions.log）を hook 別に集計する（B12）")
    args = ap.parse_args()
    if args.hooks is not None:
        log = Path(args.hooks) if args.hooks else default_hook_log()
        if not log.is_file():
            print(f"hook の判定の記録が無い: {log}（hook が 1 度も止めていないか、記録先が違う）", file=sys.stderr)
            return 1
        print(hook_report(log))
        return 0
    cats = [c.strip() for c in args.by.split(",") if c.strip()]
    bad = [c for c in cats if c not in CATS]
    if bad:
        print(f"--by に使えるのは {','.join(CATS)}: {','.join(bad)}", file=sys.stderr)
        return 2
    if args.skills_dir and not args.skills_dir.is_dir():
        print(f"--skills-dir が無い: {args.skills_dir}", file=sys.stderr)
        return 2
    paths = args.jsonl or [p for p in [latest_session()] if p]
    if not paths:
        print("セッション JSONL が見つからない。パスを引数で渡す", file=sys.stderr)
        return 1
    per_session: list[tuple[Path, Counter]] = []
    known = set(known_skills(args.skills_dir)) if args.skills_dir else None
    for p in paths:
        print(report(p, args.write_mult))
        if cats or args.skills_dir:
            text, skills = by_report(p, cats, args.write_mult, known)
            per_session.append((p, skills))
            if cats:
                print("\n" + text)
    if args.skills_dir:
        print("\n" + skill_usage(args.skills_dir, per_session, args.over))
    return 0


if __name__ == "__main__":
    sys.exit(main())
