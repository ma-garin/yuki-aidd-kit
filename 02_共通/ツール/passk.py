#!/usr/bin/env python3
"""passk.py — 同じコマンドを k 回実行し、pass@k と pass^k で「たまたま緑」を見分ける（確認 ③）。

pass@k = k 回のうち 1 回でも合格したか（1.00 / 0.00）。pass^k = k 回すべて合格したか（1.00 / 0.00）。成功率 = 合格回数 / k。
pass@k が 1.00 でも pass^k が 1.00 未満なら、そのテストは揺れている（AI が「通った」と言った 1 回を信じない）。
E2E の履歴をまたいだ flaky 率は e2e_history.py が見る。本ツールはその場で k 回まわすだけ。標準ライブラリのみ・Python 3.10 以上。

使い方:
  python3 02_共通/ツール/passk.py -k 5 [--junit "<glob>"] [--timeout 秒] [--verbose] -- <コマンド> [引数...]
    --junit    毎回の実行後に glob に合う JUnit XML を読み、テスト単位で合否が混ざったもの（揺れ）を一覧する
    --verbose  コマンドの stdout / stderr を捨てずに出す
終了コード: 0 = pass^k が 1.00 ／ 1 = 1 回でも不合格 ／ 2 = コマンドが無い・引数の誤り
"""
from __future__ import annotations

import argparse
import glob
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def junit_results(pattern: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted(glob.glob(pattern, recursive=True)):
        try:
            root = ET.parse(f).getroot()
        except (ET.ParseError, OSError):
            continue
        for tc in root.iter("testcase"):
            if tc.find("skipped") is not None:
                continue
            name = f"{tc.get('classname', '')}::{tc.get('name', '')}"
            bad = tc.find("failure") is not None or tc.find("error") is not None
            out[name] = "fail" if bad or out.get(name) == "fail" else "pass"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="同じコマンドを k 回実行して pass@k / pass^k を出す")
    ap.add_argument("-k", type=int, default=5, help="実行回数（既定 5）")
    ap.add_argument("--junit", help="回ごとに読む JUnit XML の glob")
    ap.add_argument("--timeout", type=int, default=600, help="1 回の上限秒（既定 600。超えたら不合格）")
    ap.add_argument("--verbose", action="store_true", help="コマンドの出力を表示する")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- の後ろに実行するコマンド")
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd or a.k < 1:
        print("-- の後ろにコマンドを書く（-k は 1 以上）", file=sys.stderr)
        return 2
    sink = None if a.verbose else subprocess.DEVNULL
    passed = 0
    per_test: dict[str, list[str]] = {}
    for n in range(1, a.k + 1):
        t0 = time.monotonic()
        try:
            rc = subprocess.run(cmd, stdout=sink, stderr=sink, timeout=a.timeout).returncode
        except subprocess.TimeoutExpired:
            rc = "timeout"
        except FileNotFoundError:
            print(f"コマンドが無い: {cmd[0]}", file=sys.stderr)
            return 2
        sec = time.monotonic() - t0
        ok = rc == 0
        passed += ok
        print(f"#{n}: exit={rc} {sec:.2f}s {'合格' if ok else '不合格'}")
        if a.junit:
            for name, st in junit_results(a.junit).items():
                per_test.setdefault(name, []).append(st)
    print(f"pass@{a.k}: {1.0 if passed else 0.0:.2f}")
    print(f"pass^{a.k}: {1.0 if passed == a.k else 0.0:.2f}")
    print(f"成功率: {passed}/{a.k}")
    if a.junit:
        flaky = {k: v for k, v in per_test.items() if len(set(v)) > 1}
        print(f"揺れたテスト: {len(flaky)} 件")
        for name, v in sorted(flaky.items()):
            print(f"  {name}: 合格 {v.count('pass')} / 不合格 {v.count('fail')}")
    return 0 if passed == a.k else 1


if __name__ == "__main__":
    sys.exit(main())
