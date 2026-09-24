#!/usr/bin/env python3
"""e2e_history.py — Playwright の結果をテスト単位の履歴にためて、通過率・flaky 率・前回からの回帰を出す。

e2e-cycle の反復（failure-rules.md）で調べるのはその回に落ちたテストだけなので、回をまたぐ揺れと前回からの回帰が
見えない。本ツールは Playwright の JSON reporter の出力（`--reporter=json` か `reporter: [['json', { outputFile }]]`）を
読み、テスト 1 本ずつの結果を `.claude/e2e-history.jsonl` に 1 行ずつ追記する。CTRF・allure は依存にしない。
標準ライブラリのみ・Python 3.9 互換。履歴は手元の記録（コミットしない。`.gitignore` に入れる）。

使い方:
  python3 scripts/e2e_history.py add e2e/results/results.json [--history PATH] [--commit SHA]
  python3 scripts/e2e_history.py report [--last 10] [--history PATH] [--json]
終了コード: 0 = 正常 ／ 2 = 入力の誤り（JSON が壊れている・Playwright の出力でない・履歴が無い）。壊れた入力で追記はしない。

add: テスト（ファイル＋describe を含む題名＋プロジェクト名）ごとに 1 行 {run, time, commit, file, title, project, outcome,
  duration_ms, retries} を追記する。outcome は pass / fail / flaky（リトライで通った）/ skipped / other。
  run は結果ファイルの中身のハッシュで、同じ結果を 2 回 add しても重ねない。time は stats.startTime（無ければ今）。
report: テストごとに直近 N 回（既定 10）の記録で次を出す。skipped と other は「有効回数」に数えず、合格にも数えない。
  通過率     = pass の回数 / 有効回数（flaky は通過に数えない）
  flaky 率   = （pass と fail の切り替わりの回数 ＋ flaky の回数）/ 有効回数
               例: pass,fail,pass,fail → 3/4 = 75%。pass×5,fail×5（途中から壊れた）→ 1/10 = 10%。fail×10 → 0%（決定的）
  前回→今回  = 直前 2 回の有効な記録。前回 pass → 今回 fail は「回帰」、fail → pass は「修正」、fail → fail は「継続 Fail」
  判定       = 有効回数が 3 未満なら「判定不能」（合格に数えない）。それ以外は flaky 率が 30% 以上で「flaky」（今回 fail でも。
               failure-rules.md の反復手順に回す）、今回 fail で「失敗」、どちらでもなければ「合格」
  並びは 回帰 → 失敗 → flaky → 判定不能 → 合格。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_HISTORY = ".claude/e2e-history.jsonl"
MIN_RUNS = 3
FLAKY_THRESHOLD = 0.30
EFFECTIVE = ("pass", "fail", "flaky")
ORDER = {"失敗": 1, "flaky": 2, "判定不能": 3, "合格": 4}   # 回帰（前回 pass → 今回 fail）はこれより前


def outcome_of(test: dict) -> str:
    """Playwright の test.status（expected / unexpected / flaky / skipped）を pass / fail / flaky / skipped に直す。"""
    st = test.get("status")
    if st == "expected":
        return "pass"
    if st == "unexpected":
        return "fail"
    if st in ("flaky", "skipped"):
        return st
    results = [r.get("status") for r in test.get("results") or [] if isinstance(r, dict)]
    if not results:
        return "other"
    last = results[-1]
    if last == "passed":
        return "flaky" if any(r in ("failed", "timedOut", "interrupted") for r in results[:-1]) else "pass"
    if last in ("failed", "timedOut"):
        return "fail"
    if last == "skipped":
        return "skipped"
    return "other"


def walk(suite: dict, path: list[str], depth: int, out: list[dict]) -> None:
    here = path if depth == 0 else path + [str(suite.get("title", ""))]
    for spec in suite.get("specs") or []:
        title = " › ".join([*here, str(spec.get("title", ""))]).strip(" ›")
        file = spec.get("file") or suite.get("file") or ""
        for t in spec.get("tests") or []:
            results = [r for r in t.get("results") or [] if isinstance(r, dict)]
            out.append({
                "file": file, "title": title, "project": t.get("projectName") or t.get("projectId") or "",
                "outcome": outcome_of(t),
                "duration_ms": int(sum(float(r.get("duration") or 0) for r in results)),
                "retries": max(len(results) - 1, 0),
            })
    for child in suite.get("suites") or []:
        if isinstance(child, dict):
            walk(child, here, depth + 1, out)


def git_commit(root: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def read_history(path: Path) -> tuple[list[dict], int]:
    """履歴を読む。壊れた行は数えて飛ばす（落ちない）。"""
    rows, bad = [], 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(d, dict) and d.get("title") is not None and d.get("outcome"):
            rows.append(d)
        else:
            bad += 1
    return rows, bad


def cmd_add(a: argparse.Namespace) -> int:
    src = Path(a.results)
    if not src.is_file():
        print(f"❌ 結果ファイルが無い: {src}", file=sys.stderr)
        return 2
    raw = src.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError as e:
        print(f"❌ JSON として読めない（壊れている）: {src}（{e}）。履歴には追記しない", file=sys.stderr)
        return 2
    if not isinstance(data, dict) or not isinstance(data.get("suites"), list):
        print(f"❌ Playwright の JSON reporter の出力ではない（suites が無い）: {src}。履歴には追記しない", file=sys.stderr)
        return 2
    tests: list[dict] = []
    for s in data["suites"]:
        if isinstance(s, dict):
            walk(s, [], 0, tests)
    hist = Path(a.history)
    run = hashlib.sha256(raw).hexdigest()[:12]
    if hist.is_file():
        rows, _bad = read_history(hist)
        if any(r.get("run") == run for r in rows):
            print(f"↷ 同じ結果（run {run}）は追記済み。重ねない: {hist}")
            return 0
    if not tests:
        print(f"⚠ テストが 0 件（記録しない）: {src}")
        return 0
    stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
    when = stats.get("startTime") or datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit = a.commit if a.commit is not None else git_commit(Path(a.root))
    hist.parent.mkdir(parents=True, exist_ok=True)
    with hist.open("a", encoding="utf-8") as fh:
        for t in tests:
            fh.write(json.dumps({"run": run, "time": when, "commit": commit, **t}, ensure_ascii=False) + "\n")
    count = {k: sum(1 for t in tests if t["outcome"] == k) for k in ("pass", "fail", "flaky", "skipped", "other")}
    print(f"✅ 追記: {len(tests)} テスト（" + " / ".join(f"{k} {v}" for k, v in count.items()) + f"）→ {hist}（run {run}）")
    return 0


def summarize(recs: list[dict], last: int) -> dict:
    window = recs[-last:]
    eff = [r["outcome"] for r in window if r.get("outcome") in EFFECTIVE]
    m = len(eff)
    passes = sum(1 for o in eff if o == "pass")
    flips = sum(1 for x, y in zip(eff, eff[1:]) if {x, y} == {"pass", "fail"})
    flaky_n = sum(1 for o in eff if o == "flaky")
    flaky_rate = (flips + flaky_n) / m if m else 0.0
    change = ""
    if len(eff) >= 2:
        prev, cur = eff[-2], eff[-1]
        change = {("pass", "fail"): "回帰", ("fail", "pass"): "修正", ("fail", "fail"): "継続 Fail"}.get((prev, cur), "")
    elif len(eff) == 1:
        change = "新規"
    if m < MIN_RUNS:
        verdict = "判定不能"
    elif flaky_rate >= FLAKY_THRESHOLD:
        verdict = "flaky"          # 今回 fail でも揺れているなら先に反復手順で確かめる（決定的な失敗と決めつけない）
    elif eff[-1] == "fail":
        verdict = "失敗"
    else:
        verdict = "合格"
    last_rec = window[-1]
    return {"file": last_rec.get("file", ""), "title": last_rec.get("title", ""), "project": last_rec.get("project", ""),
            "records": len(window), "effective": m, "pass_rate": (passes / m) if m else None, "flaky_rate": flaky_rate if m else None,
            "last": " → ".join(eff[-2:]) if eff else "", "change": change, "verdict": verdict,
            "last_time": last_rec.get("time", ""), "last_commit": last_rec.get("commit", "")}


def pct(x: float | None) -> str:
    return "—" if x is None else f"{round(x * 100)}%"


def cmd_report(a: argparse.Namespace) -> int:
    hist = Path(a.history)
    if not hist.is_file():
        print(f"❌ 履歴が無い: {hist}（先に add で追記する）", file=sys.stderr)
        return 2
    rows, bad = read_history(hist)
    by: dict[tuple, list[dict]] = {}
    for r in rows:
        by.setdefault((r.get("file", ""), r.get("title", ""), r.get("project", "")), []).append(r)
    items = [summarize(recs, a.last) for recs in by.values()]
    items.sort(key=lambda s: (0 if s["change"] == "回帰" else ORDER[s["verdict"]], -(s["flaky_rate"] or 0), s["file"], s["title"]))
    tally = {k: sum(1 for s in items if s["verdict"] == k) for k in ("合格", "失敗", "flaky", "判定不能")}
    regress = sum(1 for s in items if s["change"] == "回帰")
    if a.json:
        print(json.dumps({"history": str(hist), "last": a.last, "min_runs": MIN_RUNS, "flaky_threshold": FLAKY_THRESHOLD,
                          "broken_lines": bad, "summary": {**tally, "回帰": regress, "tests": len(items)}, "tests": items},
                         ensure_ascii=False, indent=2))
        return 0
    runs = len({r.get("run") for r in rows})
    print(f"## E2E 履歴（直近 {a.last} 回・{len(items)} テスト・{runs} 回分の記録）")
    print("")
    print(f"合格 {tally['合格']} / 失敗 {tally['失敗']} / flaky {tally['flaky']} / 判定不能 {tally['判定不能']}（履歴 {MIN_RUNS} 回未満。合格に数えない）"
          f" / 回帰 {regress}")
    if bad:
        print(f"⚠ 履歴の壊れた行 {bad} 行は読み飛ばした: {hist}")
    print("")
    print("| テスト | 回数（有効） | 通過率 | flaky 率 | 前回→今回 | 変化 | 判定 |")
    print("|---|---|---|---|---|---|---|")
    for s in items:
        name = f"{s['file']} › {s['title']}" + (f" [{s['project']}]" if s["project"] else "")
        print(f"| {name.replace('|', '/')} | {s['records']}（{s['effective']}） | {pct(s['pass_rate'])} | {pct(s['flaky_rate'])} "
              f"| {s['last'] or '—'} | {s['change'] or '—'} | {s['verdict']} |")
    if tally["flaky"]:
        print("")
        print(f"flaky 率 {round(FLAKY_THRESHOLD * 100)}% 以上のテストは e2e-cycle の references/failure-rules.md の反復手順（単独 5 回）で確かめる。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Playwright の結果をテスト単位の履歴にためて、通過率・flaky 率・回帰を出す")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add", help="JSON reporter の出力を履歴に追記する")
    p_add.add_argument("results", help="Playwright の JSON reporter の出力（例 e2e/results/results.json）")
    p_add.add_argument("--commit", default=None, help="記録する commit（既定: git rev-parse --short HEAD）")
    p_add.add_argument("--root", default=".", help="commit を読むリポジトリ（既定: カレント）")
    p_rep = sub.add_parser("report", help="直近 N 回の通過率・flaky 率・回帰を表にする")
    p_rep.add_argument("--last", type=int, default=10, help="テストごとに見る直近の回数（既定 10）")
    p_rep.add_argument("--json", action="store_true", help="結果を JSON で出す")
    for p in (p_add, p_rep):
        p.add_argument("--history", default=DEFAULT_HISTORY, help=f"履歴ファイル（既定 {DEFAULT_HISTORY}）")
    a = ap.parse_args()
    if a.cmd == "report" and a.last < 1:
        print("❌ --last は 1 以上", file=sys.stderr)
        return 2
    return cmd_add(a) if a.cmd == "add" else cmd_report(a)


if __name__ == "__main__":
    sys.exit(main())
