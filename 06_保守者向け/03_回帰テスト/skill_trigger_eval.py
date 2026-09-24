#!/usr/bin/env python3
"""skill_trigger_eval.py — スキル description が狙いどおり発火するかを実測する（A13）。依存なし。

20 本のスキルそれぞれの description（`」` の発火語・用途）から作った発話ケース
（`skill-triggers/<skill>.jsonl`。1 行 1 発話 `{"utterance": "...", "expect": "<skill名>" | "none", "note": "..."}`）
を `claude -p "<発話>" --output-format stream-json --setting-sources project --max-turns 1` に流し、
stream-json の最初の tool_use が `name=="Skill"` かどうかで発火したスキルを判定する
（`input.skill`、無ければ `input.name`。最初の tool_use が Skill でなければ「発火なし」＝none）。

Codex は対象外（SKILL.md の読込で代替する案があるが未対応）。

使い方:
  python3 06_保守者向け/03_回帰テスト/skill_trigger_eval.py [--only SKILL] [--runs N] [--dry-run]
      [--claude PATH] [--timeout SEC] [--triggers-dir DIR] [--min-hit R] [--max-miss R]

  --only SKILL      指定した 1 スキルの jsonl だけ流す（変更したスキルだけ）
  --runs N          発話ごとに N 回実行し多数決で判定（既定 1）。判定不能な実行は多数決から除く
  --dry-run         claude を一切呼ばず、打つコマンドと件数だけ出す
  --claude PATH     claude 実行ファイル（既定 "claude"。PATH から解決）
  --timeout SEC     1 回あたりのタイムアウト秒（既定 120）
  --triggers-dir DIR  発話ケースの置き場所（既定: このスクリプトと同じ場所の skill-triggers/）
  --min-hit R       正例発火率の合格閾値（既定 0.8）
  --max-miss R      誤発火率の合格閾値（既定 0.2）

判定不能（タイムアウト・非 0 終了）は「より安全な側」＝不合格として発火率・誤発火率に数える（COMMON.md）。
exit: 0=すべて閾値内 / 1=閾値外のスキルがある / 2=判定不能あり（優先。定期実行・CI はしない。手動起動のみ）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

UNDET = "__UNDETERMINED__"
NONE_ = "none"
HERE = Path(__file__).resolve().parent
DEFAULT_TRIGGERS_DIR = HERE / "skill-triggers"


def load_cases(triggers_dir: Path, only: str | None) -> dict[str, list[dict]]:
    files = sorted(triggers_dir.glob("*.jsonl"))
    if not files:
        print(f"NG: 発話ケースが無い: {triggers_dir}", file=sys.stderr)
        sys.exit(2)
    known = {f.stem for f in files}
    cases: dict[str, list[dict]] = {}
    for f in files:
        skill = f.stem
        rows = []
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"NG: {f.name} 行{i}: JSON として読めない（{e}）", file=sys.stderr)
                sys.exit(2)
            if "utterance" not in row or "expect" not in row:
                print(f"NG: {f.name} 行{i}: utterance/expect が無い", file=sys.stderr)
                sys.exit(2)
            if row["expect"] != NONE_ and row["expect"] not in known:
                print(f"NG: {f.name} 行{i}: expect '{row['expect']}' は実在するスキル名でも none でもない", file=sys.stderr)
                sys.exit(2)
            rows.append(row)
        cases[skill] = rows
    if only:
        if only not in cases:
            print(f"NG: --only {only} の jsonl が無い", file=sys.stderr)
            sys.exit(2)
        cases = {only: cases[only]}
    return cases


def run_once(claude: str, utterance: str, timeout: float) -> str:
    cmd = [claude, "-p", utterance, "--output-format", "stream-json", "--setting-sources", "project", "--max-turns", "1"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)  # bytes で受ける（非UTF-8で例外を投げないため）
    except (subprocess.TimeoutExpired, OSError):
        return UNDET
    if proc.returncode != 0:
        return UNDET
    text = proc.stdout.decode("utf-8", errors="replace")
    tainted = False  # 置換が起きた行・JSONとして読めなかった行が一つでもあれば立てる
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "�" in line:  # デコードで置換が起きた行は内容を信用せず使わない
            tainted = True
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            tainted = True  # 途中で切れた行も黙って捨てず「判定不能」の候補にする
            continue
        if obj.get("type") != "assistant":
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        tool_use = next((b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"), None)
        if tool_use is None:
            continue
        if tool_use.get("name") == "Skill":
            inp = tool_use.get("input") or {}
            return inp.get("skill") or inp.get("name") or NONE_
        return NONE_  # 最初の tool_use が Skill でない＝発火なし（有効な行から先に確定したものを優先）
    return UNDET if tainted else NONE_  # 有効な tool_use が無く、壊れた行があった＝判定不能。無ければ発火なし


def vote(results: list[str]) -> str:
    determined = [r for r in results if r != UNDET]
    if not determined:
        return UNDET
    counts = Counter(determined)
    best = max(counts.values())
    for r in determined:  # 同数は最初に出た方を採る（決定的）
        if counts[r] == best:
            return r
    return UNDET  # pragma: no cover


def main() -> int:
    ap = argparse.ArgumentParser(description="スキル発火テスト（正例・負例）")
    ap.add_argument("--only")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--claude", default="claude")
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--triggers-dir", type=Path, default=DEFAULT_TRIGGERS_DIR)
    ap.add_argument("--min-hit", type=float, default=0.8)
    ap.add_argument("--max-miss", type=float, default=0.2)
    args = ap.parse_args()

    cases = load_cases(args.triggers_dir, args.only)
    n_skills = len(cases)
    n_utter = sum(len(rows) for rows in cases.values())

    if args.dry_run:
        print("=== スキル発火テスト（--dry-run） ===")
        print(f"triggers: {args.triggers_dir}")
        print(f"claude コマンド: {args.claude} -p <発話> --output-format stream-json --setting-sources project --max-turns 1")
        print(f"件数: {n_utter * args.runs}（{n_skills} スキル × {n_utter // n_skills if n_skills else 0} 発話 × --runs {args.runs}）")
        return 0

    print("=== スキル発火テスト（skill_trigger_eval.py） ===")
    print(f"triggers: {args.triggers_dir}")
    print(f"対象: {n_skills} スキル・{n_utter} 発話（--runs {args.runs}）")
    print()
    print("| スキル | 正例発火率 | 誤発火率 | 判定不能 | 取り違え |")
    print("|---|---|---|---|---|")

    tot_pos_hit = tot_pos_total = tot_neg_false = tot_neg_total = tot_undet = 0
    failing: list[str] = []
    for skill in sorted(cases):
        rows = cases[skill]
        finals = [(row, vote([run_once(args.claude, row["utterance"], args.timeout) for _ in range(args.runs)])) for row in rows]

        pos = [(r, f) for r, f in finals if r["expect"] == skill]
        neg = [(r, f) for r, f in finals if r["expect"] != skill]
        pos_hit = sum(1 for _, f in pos if f == skill)
        neg_false = sum(1 for _, f in neg if f == skill)
        undet = sum(1 for _, f in finals if f == UNDET)
        misattr: Counter[tuple[str, str]] = Counter()
        for r, f in finals:
            if f != UNDET and f != r["expect"]:
                misattr[(r["expect"], f)] += 1

        pos_rate = (pos_hit / len(pos)) if pos else 1.0
        neg_rate = (neg_false / len(neg)) if neg else 0.0
        tot_pos_hit += pos_hit; tot_pos_total += len(pos)
        tot_neg_false += neg_false; tot_neg_total += len(neg)
        tot_undet += undet
        if (pos and pos_rate < args.min_hit) or (neg and neg_rate > args.max_miss):
            failing.append(skill)

        misattr_str = ", ".join(f"{a}→{b}×{n}" for (a, b), n in misattr.most_common()) or "-"
        print(f"| {skill} | {pos_hit}/{len(pos)} ({pos_rate:.0%}) | {neg_false}/{len(neg)} ({neg_rate:.0%}) | {undet} | {misattr_str} |")

    print()
    print("=== 全体 ===")
    overall_pos = (tot_pos_hit / tot_pos_total) if tot_pos_total else 0.0
    overall_neg = (tot_neg_false / tot_neg_total) if tot_neg_total else 0.0
    print(f"正例発火率（全体）: {tot_pos_hit}/{tot_pos_total} ({overall_pos:.1%})")
    print(f"誤発火率（全体）: {tot_neg_false}/{tot_neg_total} ({overall_neg:.1%})")
    print(f"判定不能: {tot_undet} 件")
    print(f"閾値: 正例 ≥ {args.min_hit:.0%} / 誤発火 ≤ {args.max_miss:.0%}")
    if failing:
        print("NG（閾値外）: " + ", ".join(failing))

    if tot_undet > 0:
        print(f"⚠ 判定不能あり（{tot_undet} 件）: タイムアウト・非 0 終了。exit=2")
        return 2
    if failing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
