#!/usr/bin/env python3
"""response_eval.py — 応答の盲検対比評価（A/B の system prompt を同じ依頼文で比べ、判定者には出所を伏せる）。

出所: i-have-adhd（ayghri）の blind paired eval。「変えた規約で応答が良くなったか」を人の印象でなく、
盲検の判定と重み付き軸で決める。使い道: rules / AGENTS.md / スキル本文の改稿前後、モデル切替（Sonnet ↔ Codex）の前後。

  A = 基準（現行）  B = 候補（改稿後）。どちらも system prompt のファイル。
  依頼文は evals/response/cases.jsonl（1 行 1 件: id / prompt / must / must_not）。
  軸と判定者への指示は evals/response/rubric.md（<!-- judge:begin --> 〜 <!-- judge:end --> が判定者の system prompt）。

盲検の仕組み:
  - 応答を作るときも判定するときも、判定者には「X」「Y」の匿名ラベルだけ渡す（条件名・ファイル名・モデル名は渡さない）
  - X/Y への割当は案件ごとに seed 付きの乱数。既定で順序を入れ替えてもう 1 回判定し、位置バイアスを平均で消す
  - 判定者の出力は JSON（軸ごとの 0〜10 と blocker）。blocker が付いた応答の合計は 0（致命傷は加点で埋まらない）

runner（応答と判定を作る実行器）:
  --runner claude      claude -p --setting-sources "" --model <--model> --output-format json --system-prompt-file <file>
                       （依頼文は stdin。--setting-sources "" で ~/.claude の hooks や rules を切り、比べる system prompt だけを効かせる）
  --runner "cmd:<コマンド> {system}"   任意コマンド。{system} は system prompt ファイルのパスに置換、依頼文は stdin、応答は stdout
  判定者は --judge-runner（省略時は --runner と同じ）

使い方:
  python3 scripts/response_eval.py validate [--root DIR]
  python3 scripts/response_eval.py run --a A.md --b B.md [--runner ...] [--judge-runner ...] [--model ID] [--seed N]
                                       [--cases FILE] [--out DIR] [--single-order] [--json]
  python3 scripts/response_eval.py score --out DIR [--json]     # 既存の出力から集計だけやり直す
  exit 0: B が A より悪くない（平均が下回らず、B に blocker が無い）/ 1: B が悪い / 2: 判定不能（実行失敗・判定 JSON が読めない）
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shlex
import subprocess
import sys
from pathlib import Path

DEFAULT_CASES = "evals/response/cases.jsonl"
DEFAULT_RUBRIC = "evals/response/rubric.md"
DEFAULT_OUT = "evals/response/out"
DEFAULT_MODEL = "claude-sonnet-5"
AXES = {"正確性": 35, "自律": 25, "行動可能性": 20, "安全": 10, "簡潔": 10}   # 合計 100
JUDGE_BEGIN, JUDGE_END = "<!-- judge:begin -->", "<!-- judge:end -->"
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.S)


class EvalError(Exception):
    def __init__(self, code: int, msg: str) -> None:
        super().__init__(msg)
        self.code = code


def load_cases(path: Path) -> list[dict]:
    if not path.is_file():
        raise EvalError(2, f"依頼文ファイルが無い: {path}")
    cases, ids = [], set()
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            c = json.loads(line)
        except ValueError as e:
            raise EvalError(1, f"{path.name}:{i} JSON でない: {e}")
        if not isinstance(c, dict) or not c.get("id") or not c.get("prompt"):
            raise EvalError(1, f"{path.name}:{i} id と prompt が必要")
        if c["id"] in ids:
            raise EvalError(1, f"{path.name}:{i} id 重複: {c['id']}")
        ids.add(c["id"])
        c.setdefault("must", [])
        c.setdefault("must_not", [])
        cases.append(c)
    if not cases:
        raise EvalError(1, f"{path.name} に依頼文が無い")
    return cases


def load_rubric(path: Path) -> str:
    if not path.is_file():
        raise EvalError(2, f"rubric が無い: {path}")
    text = path.read_text(encoding="utf-8")
    if JUDGE_BEGIN not in text or JUDGE_END not in text:
        raise EvalError(1, f"{path.name} に {JUDGE_BEGIN} 〜 {JUDGE_END} が無い")
    # 本文中の説明にも印が出るので、行頭にある最後の印を使う
    starts = [i for i in range(len(text)) if text.startswith(JUDGE_BEGIN, i) and (i == 0 or text[i - 1] == '\n')]
    if not starts:
        raise EvalError(1, f"{path.name} の {JUDGE_BEGIN} が行頭に無い")
    rest = text[starts[-1] + len(JUDGE_BEGIN):]
    if JUDGE_END not in rest:
        raise EvalError(1, f"{path.name} の {JUDGE_END} が {JUDGE_BEGIN} の後に無い")
    body = rest.split(JUDGE_END, 1)[0].strip()
    for ax in AXES:
        if ax not in body:
            raise EvalError(1, f"{path.name} の判定者指示に軸「{ax}」が無い")
    return body


def build_runner(spec: str, model: str) -> list[str]:
    """runner 指定 → argv テンプレート（{system} を含む）"""
    if spec == "claude":
        return ["claude", "-p", "--setting-sources", "", "--model", model, "--output-format", "json",
                "--system-prompt-file", "{system}"]
    if spec.startswith("cmd:"):
        argv = shlex.split(spec[4:])
        if not any("{system}" in a for a in argv):
            raise EvalError(1, "cmd: runner に {system}（system prompt ファイルのパス）が無い")
        return argv
    raise EvalError(1, f"runner が不明: {spec}（claude か cmd:<コマンド> {{system}}）")


def call_runner(argv_tpl: list[str], system_file: Path, prompt: str, timeout: int) -> str:
    argv = [a.replace("{system}", str(system_file)) for a in argv_tpl]
    try:
        proc = subprocess.run(argv, input=prompt, capture_output=True, text=True, timeout=timeout, errors="replace")
    except FileNotFoundError:
        raise EvalError(2, f"runner が見つからない: {argv[0]}")
    except subprocess.TimeoutExpired:
        raise EvalError(2, f"runner がタイムアウト（{timeout}s）: {argv[0]}")
    if proc.returncode != 0:
        raise EvalError(2, f"runner が exit {proc.returncode}: {argv[0]} — {proc.stderr.strip()[:200]}")
    out = proc.stdout
    if argv_tpl[:1] == ["claude"]:   # --output-format json → .result
        try:
            out = json.loads(out).get("result", "")
        except ValueError:
            raise EvalError(2, "claude の出力が JSON でない")
    return out.strip()


def judge_prompt(case: dict, x: str, y: str) -> str:
    must = "\n".join(f"- {m}" for m in case["must"]) or "-（指定なし）"
    must_not = "\n".join(f"- {m}" for m in case["must_not"]) or "-（指定なし）"
    return (f"## 依頼文\n{case['prompt']}\n\n## 満たすべきこと\n{must}\n\n## あってはならないこと\n{must_not}\n\n"
            f"## 応答 X\n{x}\n\n## 応答 Y\n{y}\n\n"
            "上の system prompt の指示どおり、JSON だけを出力せよ。")


def parse_judgement(text: str) -> dict:
    m = JSON_BLOCK_RE.search(text)
    if not m:
        raise EvalError(2, "判定者の出力に JSON が無い")
    try:
        d = json.loads(m.group(0))
    except ValueError as e:
        raise EvalError(2, f"判定者の JSON が読めない: {e}")
    scores = d.get("scores") or {}
    for lab in ("X", "Y"):
        s = scores.get(lab)
        if not isinstance(s, dict):
            raise EvalError(2, f"判定者の JSON に scores.{lab} が無い")
        for ax in AXES:
            if not isinstance(s.get(ax), (int, float)) or not 0 <= s[ax] <= 10:
                raise EvalError(2, f"判定者の JSON の scores.{lab}.{ax} が 0〜10 の数でない")
    d.setdefault("blocker", {})
    return d


def total(scores: dict, blocker) -> float:
    if blocker:
        return 0.0
    return round(sum(scores[ax] / 10 * w for ax, w in AXES.items()), 1)


def assign(cases: list[dict], seed: int) -> dict[str, str]:
    """案件 id → 「A を X にするか（'AX'）Y にするか（'AY'）」。seed で再現可能"""
    rnd = random.Random(seed)
    return {c["id"]: rnd.choice(["AX", "AY"]) for c in cases}


def run(a: argparse.Namespace) -> dict:
    root = Path(a.root).resolve()
    cases = load_cases(root / a.cases)
    rubric = load_rubric(root / a.rubric)
    sys_a, sys_b = Path(a.a).resolve(), Path(a.b).resolve()
    for p in (sys_a, sys_b):
        if not p.is_file():
            raise EvalError(2, f"system prompt が無い: {p}")
    runner = build_runner(a.runner, a.model)
    judge = build_runner(a.judge_runner or a.runner, a.model)
    out = (root / a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    plan = assign(cases, a.seed)
    (out / "plan.json").write_text(json.dumps({"seed": a.seed, "assign": plan, "cases": [c["id"] for c in cases],
                                               "single_order": a.single_order}, ensure_ascii=False, indent=1), encoding="utf-8")
    judge_sys = out / "judge_system.md"
    judge_sys.write_text(rubric + "\n", encoding="utf-8")
    records = []
    for c in cases:
        ra = call_runner(runner, sys_a, c["prompt"], a.timeout)
        rb = call_runner(runner, sys_b, c["prompt"], a.timeout)
        (out / f"{c['id']}.A.md").write_text(ra + "\n", encoding="utf-8")
        (out / f"{c['id']}.B.md").write_text(rb + "\n", encoding="utf-8")
        orders = [plan[c["id"]]] if a.single_order else [plan[c["id"]], "AY" if plan[c["id"]] == "AX" else "AX"]
        judgements = []
        for order in orders:
            x, y = (ra, rb) if order == "AX" else (rb, ra)
            jp = judge_prompt(c, x, y)
            raw = call_runner(judge, judge_sys, jp, a.timeout)
            (out / f"{c['id']}.judge.{order}.txt").write_text(jp + "\n\n---\n" + raw + "\n", encoding="utf-8")
            d = parse_judgement(raw)
            # 復号: X/Y → A/B
            la, lb = ("X", "Y") if order == "AX" else ("Y", "X")
            judgements.append({"order": order,
                               "A": {"scores": d["scores"][la], "blocker": d["blocker"].get(la) or None},
                               "B": {"scores": d["scores"][lb], "blocker": d["blocker"].get(lb) or None}})
        records.append({"id": c["id"], "judgements": judgements})
    (out / "records.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    return score_records(records, out)


def score_records(records: list[dict], out: Path) -> dict:
    per_case, sum_a, sum_b, wins = [], 0.0, 0.0, {"B": 0, "A": 0, "tie": 0}
    blockers = {"A": [], "B": []}
    axes_a = {ax: 0.0 for ax in AXES}
    axes_b = {ax: 0.0 for ax in AXES}
    n_j = 0
    for r in records:
        ta = tb = 0.0
        for j in r["judgements"]:
            ta += total(j["A"]["scores"], j["A"]["blocker"])
            tb += total(j["B"]["scores"], j["B"]["blocker"])
            for ax in AXES:
                axes_a[ax] += j["A"]["scores"][ax]
                axes_b[ax] += j["B"]["scores"][ax]
            n_j += 1
            for side in ("A", "B"):
                if j[side]["blocker"]:
                    blockers[side].append(f"{r['id']}: {j[side]['blocker']}")
        k = len(r["judgements"])
        ta, tb = round(ta / k, 1), round(tb / k, 1)
        verdict = "B" if tb > ta else "A" if ta > tb else "tie"
        wins[verdict] += 1
        sum_a += ta
        sum_b += tb
        per_case.append({"id": r["id"], "A": ta, "B": tb, "verdict": verdict})
    n = len(records)
    mean_a, mean_b = round(sum_a / n, 1), round(sum_b / n, 1)
    axes_mean = {ax: {"A": round(axes_a[ax] / n_j, 1), "B": round(axes_b[ax] / n_j, 1)} for ax in AXES}
    ng = []
    if blockers["B"]:
        ng.append(f"B に blocker {len(blockers['B'])} 件: " + "; ".join(blockers["B"][:3]))
    if mean_b < mean_a:
        ng.append(f"B の平均 {mean_b} < A の平均 {mean_a}")
    data = {"cases": n, "judgements": n_j, "mean": {"A": mean_a, "B": mean_b}, "wins": wins, "axes": axes_mean,
            "blockers": blockers, "per_case": per_case, "ng": ng}
    lines = ["# 応答の盲検対比評価", "", f"案件 {n} 件 / 判定 {n_j} 回（順序入替 {'あり' if n_j > n else 'なし'}）", "",
             "| | A（基準） | B（候補） |", "|---|---|---|", f"| 平均（100 点満点） | {mean_a} | {mean_b} |",
             f"| 勝ち / 引分 / 負け（B から見て） | | {wins['B']} / {wins['tie']} / {wins['A']} |"]
    for ax, w in AXES.items():
        lines.append(f"| {ax}（重み {w}） | {axes_mean[ax]['A']} | {axes_mean[ax]['B']} |")
    lines += ["", "| 案件 | A | B | 判定 |", "|---|---|---|---|"]
    lines += [f"| {c['id']} | {c['A']} | {c['B']} | {c['verdict']} |" for c in per_case]
    if blockers["A"] or blockers["B"]:
        lines += ["", "## blocker", ""] + [f"- A — {b}" for b in blockers["A"]] + [f"- B — {b}" for b in blockers["B"]]
    lines += ["", "## 判定", "", ("❌ " + " / ".join(ng)) if ng else "✅ B は A より悪くない（B に blocker 無し・平均が下回らない）"]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="応答の盲検対比評価")
    ap.add_argument("cmd", choices=["validate", "run", "score"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--cases", default=DEFAULT_CASES)
    ap.add_argument("--rubric", default=DEFAULT_RUBRIC)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--a", help="基準の system prompt ファイル")
    ap.add_argument("--b", help="候補の system prompt ファイル")
    ap.add_argument("--runner", default="claude", help='claude | "cmd:<コマンド> {system}"')
    ap.add_argument("--judge-runner", default=None, help="判定者の runner（既定: --runner と同じ）")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--single-order", action="store_true", help="順序入替の 2 回目の判定をしない（呼び出し半減。位置バイアスは残る）")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    env = {"ok": True, "exit": 0, "data": {}, "meta": {"cmd": a.cmd}}
    try:
        root = Path(a.root).resolve()
        if a.cmd == "validate":
            cases = load_cases(root / a.cases)
            load_rubric(root / a.rubric)
            env["data"] = {"cases": len(cases), "axes": AXES}
            msg = f"✅ validate: 依頼文 {len(cases)} 件・rubric OK（軸 {len(AXES)}・重み合計 {sum(AXES.values())}）"
        else:
            if a.cmd == "run":
                if not a.a or not a.b:
                    raise EvalError(1, "run には --a と --b（system prompt ファイル）が必要")
                data = run(a)
            else:
                out = (root / a.out).resolve()
                rec = out / "records.json"
                if not rec.is_file():
                    raise EvalError(2, f"records.json が無い: {rec}（先に run）")
                data = score_records(json.loads(rec.read_text(encoding="utf-8")), out)
            env["data"] = data
            if data["ng"]:
                raise EvalError(1, " / ".join(data["ng"]))
            msg = (f"✅ B は A より悪くない: 平均 A {data['mean']['A']} / B {data['mean']['B']}、"
                   f"B の勝ち {data['wins']['B']} 引分 {data['wins']['tie']} 負け {data['wins']['A']}（案件 {data['cases']} 件）"
                   f"\n詳細: {(root / a.out) / 'report.md'}")
    except EvalError as e:
        env.update(ok=False, exit=e.code)
        env["error"] = {"type": "response.worse" if e.code == 1 else "response.undetermined", "message": str(e),
                        "hint": ("B の応答を直すか、rubric の重みを変えずに判定の根拠（judge.*.txt）を読む" if e.code == 1
                                 else "runner / 依頼文 / rubric を直して再実行"),
                        "retry_argv": ["./scripts/response-eval.sh"] + sys.argv[1:]}
        msg = f"❌ {e}"
    if a.json:
        print(json.dumps(env, ensure_ascii=False))
    else:
        print(msg)
        if env["ok"] and a.cmd != "validate":
            pass
    return env["exit"]


if __name__ == "__main__":
    sys.exit(main())
