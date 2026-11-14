#!/usr/bin/env python3
"""憲法ゲート — 見積・中間報告・番の終わり方を、AI の判断と無関係に止める hook（PreToolUse 全ツール／Stop）。
出所: 2026-11-03、同一セッションで見積欠落 3 回・無報告 2 回（「最悪のインシデント」）。「気をつける」は
効かなかったので制御にする（設計: 06_保守者向け/02_設計判断の根拠/constitution-gate.md）。解除の環境変数は作らない。
  python3 constitution-gate.py pre     # PreToolUse（配列の先頭に置く）
  python3 constitution-gate.py stop    # Stop
  python3 constitution-gate.py report  # 停止状態・最後の報告・違反件数
テスト専用: AIDD_NOW_EPOCH（現在時刻の偽装。使うと hook-decisions.log に残す）・AIDD_TRANSCRIPT_FLUSH_SEC
限界（Bash の改ざん判定。origin/main でも素通りで、本 hook の範囲外。ロードマップ M25）:
  - 保護名の文字列を含まないコマンドは判定しない。.claude ごとの削除・glob（.cl* 等）・変数で組み立てた名前・
    サブシェルや eval／インタプリタ内で名前を作る書き方・find -delete／rsync --delete・偽の .claude での上書きは通る
  - 名前の照合は大小を区別する部分一致。ブレース展開・zsh の glob 選択・$'..' の 16 進表記で名前を割ると通る
    （APFS 既定は大小無視なので大文字表記も同じ実体を指す）"""
import hashlib, json, os, re, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HOOK, HERE = "constitution-gate", Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    import secret_patterns as sp
except Exception:  # 記録が書けなくても判定は変えない
    sp = None

READ_ONLY = frozenset({"Read", "Grep", "Glob", "LS", "NotebookRead"})
READ_FREE = 3        # 見積を出す前に許す読み取りの回数（調査してから見積る余地）
TAIL_KB = 2048
# instruction-guard.py / tool-timer.py と同じ「機械が書いた発言」の印。これではターンを区切らない
MACHINE_MARKERS = ("[instruction-guard]", "[reply-language]", "[constitution-gate]", "[Subagent hand-back]", "<agent-message",
                   "<task-notification>", "Stop hook feedback:", "hook success:", "[SYSTEM NOTIFICATION - NOT USER INPUT]")
TAG_BLOCK_RE = re.compile(r"<([a-zA-Z][\w-]*)(?:\s[^>]*)?>.*?</\1>", re.S)
# 既存 hook にコーディング判定の語彙は無い（見積の有無だけを見ている）ので、ここで定める。拡張子の .md は文書なので除く
CODING_RE = re.compile(r"(実装|修正|直して|直す|作って|作成|追加|削除して|リファクタ|テスト|hook|フック|スクリプト|コード|"
                       r"バグ|不具合|変更して|書き換え|やって|進めて|続けて|対応して)|"
                       r"\.(py|sh|js|mjs|ts|tsx|jsx|json|ya?ml|toml|html|css|go|rs|java|rb|sql|ipynb)\b", re.I)
EST_RE = re.compile(r"^[ \t]*【?見積[:：][ \t]*(\d+)[ \t]*分(?![^\n】]*実測)", re.M)
# 中間報告の上限＝このターン最初の見積の分×60÷5 秒（2026-11-14 利用者指定。5分→60秒）。見積の分が取れなければ従来の 180 秒
REPORT_FALLBACK_SEC = 180
DONE_RE = re.compile(r"【見積[:：]\s*\d+\s*分[^】]*実測[:：][^】]*】|見積[:：]\s*\d+\s*分\s*/\s*実測[:：]")
MID_RE = re.compile(r"【進捗[:：][^】]*経過時間[:：][^】]*】")
ASYNC_RE = re.compile(r"(Async agent launched|running in (the )?background|バックグラウンド)", re.I)
PROTECTED_WORDS = ("constitution-stop", "constitution-state", "constitution-violations")
# Bash の改ざん判定（2026-11-10 誤検知の是正）: 保護名を含むコマンドは、全体が「既知の読み取り専用コマンドを
# ; && || | で並べただけ」と構文的に確定できたときだけ許可する（許可リスト）。それ以外は判別不能として違反（A-14）
SAFE_READ = frozenset("cat head tail grep egrep fgrep rg ls test stat wc diff cmp echo printf true false : md5 md5sum "
                      "shasum sha256sum readlink realpath basename dirname nl od hexdump strings pwd cd find git".split())
GIT_READ = frozenset("grep log show diff status blame ls-files commit add".split())
# 読み取りコマンドでも書き込み・任意実行になる選択肢（前方一致）
BAD_OPTS = {"rg": ("--pre",), "git": ("--output", "-O", "--open-files-in-pager", "--ext-diff", "-c"),
            "find": ("-exec", "-ok", "-delete", "-fprint", "-fls")}
SH_SPECIAL = frozenset("<>(){}*?[]!&|;~$`\\=")   # 引用符の外に出たら判別不能（リダイレクト全種・展開・サブシェル）
SH_OPS = ("&&", "||", ";", "|", "\n")

def now() -> float:
    return float(os.environ.get("AIDD_NOW_EPOCH") or time.time())

def iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).astimezone().isoformat(timespec="seconds")

def root_of(payload: dict) -> Path:
    return next((Path(b) for b in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()) if b), Path("."))

def paths(root: Path) -> dict:
    stop = Path(os.environ.get("AIDD_STOP_FILE") or ".claude/constitution-stop")
    stop, c = (stop if stop.is_absolute() else root / stop), root / ".claude"
    return {"stop": stop, "last": stop.with_name(stop.name + ".last"), "state": c / "constitution-state.json",
            "viol": c / "constitution-violations.jsonl"}

def lessons_of(root: Path) -> Path | None:
    return next((root / r for r in ("06_保守者向け/学んだこと.md", "docs/lessons.md", ".claude/lessons.md")
                 if (root / r).is_file()), None)

def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""

def loads(s: str) -> dict:
    try:
        d = json.loads(s)
    except ValueError:
        return {}
    return d if isinstance(d, dict) else {}

def lines_of(p: Path) -> list[str]:
    return [x for x in read(p).splitlines() if x.strip()]

def stopped_at(P: dict) -> float:   # 最後の停止時刻（.last の先頭。壊れていれば mtime）
    try:
        return float((lines_of(P["last"]) or [""])[0].split("\t")[0])
    except ValueError:
        return P["last"].stat().st_mtime

def log(decision: str, reason: str, tool: str = "", summary: str = "", cwd: str | None = None) -> None:
    sp and sp.log_decision(HOOK, decision, reason, tool, summary, cwd=cwd)

def text_of(c) -> str:
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return c if isinstance(c, str) else ""

def instruction_of(e: dict) -> str | None:
    """人の発言なら可視テキスト。ツール結果・メタ・機械由来は None（instruction-guard.py と同じ判定）。"""
    t = e.get("type")
    if t == "user" and not e.get("isMeta"):
        c = (e.get("message") or {}).get("content")
        if isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return None
        raw = text_of(c)
    elif t == "attachment" and (e.get("attachment") or {}).get("type") == "queued_command":
        raw = text_of(e["attachment"].get("prompt"))
    elif t == "queue-operation" and e.get("operation") == "enqueue":
        raw = text_of(e.get("content"))
    else:
        return None
    if any(m in raw for m in MACHINE_MARKERS):
        return None
    return TAG_BLOCK_RE.sub("", raw).strip() or None

def read_entries(tp: str) -> list[tuple[str, dict]]:
    if not tp:
        raise RuntimeError("入力に transcript_path が無い")
    try:
        with open(tp, "rb") as f:
            f.seek(max(0, os.path.getsize(tp) - TAIL_KB * 1024))
            data = f.read().decode("utf-8", errors="replace")
    except OSError as ex:
        raise RuntimeError(f"transcript が読めない（{tp}: {ex.strerror or ex}）") from ex
    # 途中から読み始めた先頭行・壊れた行は loads が {} を返すので落ちる
    return [(e.get("uuid") or hashlib.sha1(line.encode()).hexdigest()[:16], e) for line in data.splitlines()
            if (e := loads(line))]

def scan(entries: list) -> dict:
    """このターン（最後の人の発言以降）の報告行・委譲の状況。発言が tail に無ければ turn=None。"""
    start, inst, turn = 0, "", None
    for i, (k, e) in enumerate(entries):
        s = instruction_of(e)
        if s is not None and not e.get("isSidechain"):
            start, inst, turn = i + 1, s, k
    events, agents, results, notes, est_min = [], [], {}, [], None
    for k, e in entries[start:]:
        c = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant":
            t = text_of(c)
            hits = sorted((m.start(), kd) for kd, rx in (("done", DONE_RE), ("est", EST_RE), ("mid", MID_RE))
                          for m in rx.finditer(t))
            events += [(k, kind) for _, kind in hits]
            m0 = EST_RE.search(t) if est_min is None else None
            est_min = int(m0.group(1)) if m0 else est_min
            for b in c if isinstance(c, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Agent", "Task"):
                    agents.append((b.get("id", ""), bool((b.get("input") or {}).get("run_in_background"))))
        elif e.get("type") == "user":
            for b in c if isinstance(c, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id", "")] = text_of(b.get("content"))
            if "<task-notification>" in text_of(c):
                notes.append(text_of(c))
    return {"turn": turn, "inst": inst, "events": events, "agents": agents, "results": results, "notes": notes,
            "est_min": est_min}

def section(sc: dict, st: dict) -> tuple[bool, bool]:   # (見積あり, 完了行で閉じた)。ターンが tail に無ければ状態 file を引き継ぐ
    marks = [kind for _, kind in sc["events"] if kind != "mid"]
    est = any(kind == "est" for kind in marks) or (sc["turn"] is None and st.get("est", False))
    closed = (marks[-1] == "done") if marks else (sc["turn"] is None and st.get("closed", False))
    return est, closed

def running_agents(sc: dict) -> list[str]:
    out, spare = [], len(sc["notes"])
    inflight = loads(read(Path(os.environ.get("AIDD_TOOL_TIME") or HERE.parent / "tool-time.json"))).get("inflight") or {}
    for aid, bg in sc["agents"]:
        res = sc["results"].get(aid)
        if res is None or aid in inflight:
            out.append(aid)
        elif bg or ASYNC_RE.search(res):
            m = re.search(r"agentId:\s*([\w-]+)", res)
            if any((m.group(1) if m else aid) in n for n in sc["notes"]) or (not m and spare > 0):
                spare -= 1   # 完了通知が届いている（id が取れなければ通知の数で突き合わせる）
            else:
                out.append(aid)
    return out

def evaluate(sc: dict, st: dict, tool: str, t: float) -> tuple[tuple[str, str] | None, dict]:
    st = dict(st)
    if sc["turn"] is not None and sc["turn"] != st.get("turn"):
        st = {"turn": sc["turn"], "coding": bool(CODING_RE.search(sc["inst"])), "ro": 0, "last": None, "rkey": None}
    st["est"], st["closed"] = section(sc, st)
    if sc["events"] and sc["events"][-1][0] != st.get("rkey"):
        st["last"], st["rkey"] = t, sc["events"][-1][0]   # 新しい見積行・中間行・完了行を確認した壁時計時刻
    if st.get("coding") and not st["est"]:
        if tool in READ_ONLY and st.get("ro", 0) < READ_FREE:
            st["ro"] = st.get("ro", 0) + 1
            return None, st
        return ("見積欠落", f"コーディングを含む指示に `見積：N分` 行が無いまま {tool} を呼んだ"
                f"（読み取りは {READ_FREE} 回まで）"), st
    if sc.get("est_min"):
        st["est_min"] = sc["est_min"]   # ターンが tail から外れても最初の見積の分を引き継ぐ
    est_min = st.get("est_min") or 0
    interval = int(os.environ.get("AIDD_REPORT_INTERVAL_SEC") or (est_min * 60 // 5 if est_min else REPORT_FALLBACK_SEC))
    if st["est"] and not st["closed"] and isinstance(st.get("last"), (int, float)) and t - st["last"] > interval:
        return ("無報告", f"最後の見積行／中間行から {int(t - st['last'])} 秒（上限 {interval} 秒）。"
                "中間行【進捗:… | 経過時間：M分 | 終了:HH:MM | タスク数:k/n】を出してから再実行"), st
    return None, st

def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": f"[{HOOK}] {reason}"}}, ensure_ascii=False))
    return 0

def violate(P: dict, kind: str, detail: str, tool: str, t: float, cwd: str) -> int:
    """違反＝即停止。猶予・回数の閾値は設けない。"""
    P["stop"].parent.mkdir(parents=True, exist_ok=True)
    P["stop"].write_text(f"{iso(t)}\t{kind}\t{tool}\n", encoding="utf-8")
    P["last"].write_text(f"{t}\t{iso(t)}\t{kind}\n", encoding="utf-8")
    with P["viol"].open("a", encoding="utf-8") as f:
        f.write(json.dumps({"time": iso(t), "epoch": t, "kind": kind, "tool": tool, "detail": detail},
                           ensure_ascii=False) + "\n")
    log("stop", f"{kind}: {detail}", tool, cwd=cwd)
    return deny(f"憲法違反（{kind}）: {detail}。停止 file {P['stop']} を書いた。保守者が自分の端末で停止 file を消し、"
                "停止時刻より新しいインシデント記録を書くまで再開不可。作業を止め、何を破ったかを保守者に報告する")

def squash(s: str) -> str:   # 引用符・バックスラッシュで名前を分断する書き方も「名前あり」と数える
    return s.replace("\\", "").replace("'", "").replace('"', "")

def simple_commands(cmd: str) -> list[list[str]] | None:
    """; && || | 改行で区切った単純コマンドの語の列。引用符の外に記号（リダイレクト・展開・サブシェル・
    背景実行等）が 1 つでもあれば None（判別不能）。語頭の # から改行まではコメントとして捨てる。"""
    segs, words, cur, i = [], [], None, 0
    while i < len(cmd):
        c = cmd[i]
        if c in "'\"":
            j = cmd.find(c, i + 1)
            if j < 0:
                return None
            cur, i = (cur or "") + cmd[i + 1:j], j + 1
            continue
        op = next((o for o in SH_OPS if cmd.startswith(o, i)), None)
        if c in " \t\r" or op:
            if cur is not None:
                words.append(cur)
            cur, i = None, i + (len(op) if op else 1)
            if op and words:
                segs.append(words)
                words = []
            elif op and op != "\n":
                return None   # 空の単純コマンド（;; や先頭の |）
            continue
        if c == "#" and cur is None:
            j = cmd.find("\n", i)
            i = len(cmd) if j < 0 else j
            continue
        if c in SH_SPECIAL:
            return None
        cur, i = (cur or "") + c, i + 1
    if cur is not None:
        words.append(cur)
    return segs + ([words] if words else [])

def read_only(words: list[str]) -> bool:
    cmd, args = words[0], words[1:]
    if cmd not in SAFE_READ or any(a.startswith(BAD_OPTS.get(cmd, ())) for a in args):
        return False
    return cmd != "git" or (bool(args) and args[0] in GIT_READ)

def bash_tampers(cmd: str, P: dict) -> bool:
    """保護名を含み、かつ読み取り専用と確定できないコマンドを改ざんとみなす。名前を含まないコマンドは判定しない
    （origin/main と同じ範囲。限界はモジュール docstring）。"""
    if not any(n in squash(cmd) for n in PROTECTED_WORDS + (P["stop"].name,)):
        return False
    segs = simple_commands(cmd)
    return segs is None or not all(read_only(w) for w in segs)

def tampers(tool: str, ti: dict, P: dict, root: Path) -> bool:
    if tool == "Bash":
        return bash_tampers(str(ti.get("command") or ""), P)
    target = ti.get("file_path") or ti.get("notebook_path")
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit") and target:
        p = Path(target) if Path(target).is_absolute() else root / target
        return p.resolve() in {P[k].resolve() for k in ("stop", "last", "state", "viol")}
    return False

def pre(payload: dict) -> int:
    tool, ti = str(payload.get("tool_name") or ""), payload.get("tool_input") or {}
    P, t, cwd = paths(root := root_of(payload)), now(), payload.get("cwd")
    if P["stop"].exists():
        head = read(P["stop"]).strip().replace("\t", " ")
        log("deny", "停止中", tool, cwd=cwd)
        return deny(f"憲法違反で停止中（{head}）。保守者が自分の端末で停止 file（{P['stop']}）を消し、"
                    "停止時刻より新しいインシデント記録を書くまで再開不可")
    if tampers(tool, ti if isinstance(ti, dict) else {}, P, root):
        return violate(P, "停止 file の改ざん", f"{tool} で停止 file／状態 file を変更しようとした（解除は保守者の端末のみ）",
                       tool, t, cwd)
    if P["last"].exists():
        stopped, les = stopped_at(P), lessons_of(root)
        if les is None or les.stat().st_mtime <= stopped:
            log("deny", "事後分析なし", tool, cwd=cwd)
            return deny(f"停止後のインシデント記録が無い（最後の停止 {iso(stopped)}）。保守者が 06_保守者向け/学んだこと.md"
                        "（無ければ docs/lessons.md・.claude/lessons.md）に記録するまで再開不可")
    if payload.get("agent_id"):
        return 0   # 委譲先の中。見積・報告の義務は親が負う（親の次のツール呼び出しで判定される）
    st = loads(read(P["state"]))
    deadline = time.time() + float(os.environ.get("AIDD_TRANSCRIPT_FLUSH_SEC") or 1.0)
    while True:   # 直前に書いた行が transcript に未反映の可能性があるので、deny の前だけ読み直して待つ
        verdict, new = evaluate(scan(read_entries(payload.get("transcript_path", ""))), st, tool, t)
        if verdict is None or time.time() >= deadline:
            break
        time.sleep(0.25)
    P["state"].parent.mkdir(parents=True, exist_ok=True)
    P["state"].write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
    return 0 if verdict is None else violate(P, verdict[0], verdict[1], tool, t, cwd)

def block(reason: str) -> int:
    print(json.dumps({"decision": "block", "reason": f"[{HOOK}] {reason}"}, ensure_ascii=False))
    return 0

def stop(payload: dict) -> int:
    if payload.get("stop_hook_active"):
        return 0
    P = paths(root_of(payload))
    if P["stop"].exists():
        return 0   # 停止中は番を終えて保守者に渡すのが正しい
    sc = scan(read_entries(payload.get("transcript_path", "")))
    est, closed = section(sc, loads(read(P["state"])))
    why = ([f"委譲先が走行中（{n} 本）"] if (n := len(running_agents(sc))) else []) + (
        ["計測区間が未了（見積行の後に完了行【見積:…|実測:…】が無い）"] if est and not closed else [])
    if not why:
        return 0
    log("block", " / ".join(why), "Stop", cwd=payload.get("cwd"))
    return block(" / ".join(why) + "。委譲先の走行中／区間未了のまま番を終えない。定期報告を併設し、完了行で閉じる")

def report() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    P, t = paths(root), now()
    st, rows = loads(read(P["state"])), [("停止中", read(P["stop"]).strip().replace("\t", " ") or "いいえ")]
    if P["last"].exists():
        les, last = lessons_of(root), stopped_at(P)
        rows.append(("最後の停止", f"{iso(last)}（事後記録: {'済' if les and les.stat().st_mtime > last else '未'}）"))
    last = st.get("last")
    rows.append(("最後の報告", f"{iso(last)}（{int(t - last)} 秒前）" if isinstance(last, (int, float)) else "未記録"))
    rows.append(("計測区間", "なし" if not st.get("est") else ("閉" if st.get("closed") else "開")))
    counts = Counter(re.findall(r'"hook": "%s", "decision": "([^"]+)"' % HOOK,
                                read(sp.decision_log_path(str(root))) if sp is not None else ""))
    rows.append(("hook-decisions.log", " / ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "0 件"))
    rows.append(("違反記録（constitution-violations.jsonl）", f"{len(lines_of(P['viol']))} 件"))
    print("| 項目 | 値 |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows))
    return 0

def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if mode == "report":
        return report()
    fail = block if mode == "stop" else deny
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("object ではない")
    except (ValueError, OSError) as ex:
        return fail(f"hook 内部エラー（入力 JSON が読めない: {ex}）。素通りさせない")
    if os.environ.get("AIDD_NOW_EPOCH"):
        log("test-clock", f"AIDD_NOW_EPOCH={os.environ['AIDD_NOW_EPOCH']}", cwd=payload.get("cwd"))
    try:
        return stop(payload) if mode == "stop" else pre(payload)
    except Exception as ex:   # fail-closed。読み取り系でも止めるので原因を理由に載せる
        tool = str(payload.get("tool_name") or "")
        hint = "（読み取り系も止まる。原因を保守者に伝える）" * (tool in READ_ONLY)
        log("deny" if mode != "stop" else "block", f"内部エラー {type(ex).__name__}", tool, cwd=payload.get("cwd"))
        return fail(f"hook 内部エラー（{type(ex).__name__}: {ex}）{hint}。素通りさせない")

if __name__ == "__main__":
    sys.exit(main())
