#!/usr/bin/env python3
"""mutate-quick.py — 簡易ミューテーション。対象をわざと 1 か所ずつ壊し、テストが落ちるか確かめる（確認 ②）。

壊しても緑のままの変異（見逃し）は、テストがその境目・条件を確かめていない印。
変異は 1 つずつファイルを書き換え → テストコマンドを実行 → 必ず元に戻す（例外・Ctrl-C でも finally で mktemp のバックアップから復元）。
標準ライブラリのみ・Python 3.10 以上。

使い方:
  python3 02_共通/ツール/mutate-quick.py <対象ファイル> --test "<テストコマンド>" [--max N] [--only 演算子]... [--timeout 秒]
    --max      試す変異の上限（既定 20。行の先頭から順）
    --only     boundary（< ↔ <=, > ↔ >=）／ eq（== ↔ !=）／ const（整数定数 ±1）／ cond（if の真偽反転）。省略時は全部
    --timeout  1 回のテスト実行の上限秒（既定 60。超えたら「検出」に数える）
終了コード: 0 = 見逃しなし ／ 1 = 見逃しあり ／ 2 = 変異前のテストが既に落ちる・対象が無い（判定不能）
出力: 変異ごとに `行:変異内容 → 検出|見逃し`、末尾に `ミューテーションスコア: 検出 m / 全 n`
文字列リテラルとコメントの中は変異しない（引用符の内側を伏せて探す）。return 値の定数化は扱わない。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PATTERNS = {
    "boundary": re.compile(r"(?<![<>=!\-])(<=|>=|<|>)(?![<>=])"),
    "eq": re.compile(r"(?<![=!<>])(==|!=)(?!=)"),
    "const": re.compile(r"(?<![\w.])\d+(?![\w.])"),
    "cond": re.compile(r"^(\s*(?:el)?if\s*)(\(?)(.+?)(\)?)(\s*[:{]\s*)$"),
}
SWAP = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "=="}


def mask(line: str, py: bool) -> str:
    s = re.sub(r"(\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`[^`]*`)", lambda m: " " * len(m.group(0)), line)
    cut = s.find("#") if py else s.find("//")
    return s if cut < 0 else s[:cut] + " " * (len(s) - cut)


def mutants(lines: list[str], ops: list[str], py: bool):
    for i, ln in enumerate(lines):
        m = mask(ln, py)
        if re.match(r"\s*(import|from|#!|//)", m):
            continue
        for op in ("boundary", "eq", "const"):
            if op not in ops:
                continue
            for x in PATTERNS[op].finditer(m):
                a, b = x.start(), x.end()
                if op == "boundary" and (m[a - 1:a + 1] == "->" or m[a:a + 2] == "=>" or m[max(0, a - 1):a] == "=" and m[a] == ">"):
                    continue
                old = ln[a:b]
                for nv in ([str(int(old) + 1), str(int(old) - 1)] if op == "const" else [SWAP[old]]):
                    yield i, f"{old} → {nv}", ln[:a] + nv + ln[b:]
        if "cond" in ops:
            c = PATTERNS["cond"].match(ln)
            if c and not m.lstrip().startswith(("#", "//")):
                inner = c.group(3)
                if py:
                    yield i, f"if {inner} → if not ({inner})", f"{c.group(1)}not ({c.group(2)}{inner}{c.group(4)}){c.group(5)}"
                elif c.group(2):
                    yield i, f"if ({inner}) → if (!({inner}))", f"{c.group(1)}(!({inner})){c.group(5)}"


def run(cmd: str, timeout: int, target: Path) -> str:
    for pyc in target.parent.glob(f"__pycache__/{target.stem}.*.pyc"):
        pyc.unlink(missing_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return "timeout"
    return "pass" if r.returncode == 0 else "fail"


def main() -> int:
    ap = argparse.ArgumentParser(description="対象を 1 か所ずつ壊してテストが落ちるか確かめる（簡易ミューテーション）")
    ap.add_argument("target", help="変異させる実装ファイル")
    ap.add_argument("--test", required=True, help="テストコマンド（exit 0 = 合格）")
    ap.add_argument("--max", type=int, default=20, help="試す変異の上限（既定 20）")
    ap.add_argument("--only", action="append", choices=list(PATTERNS), help="使う演算子（複数可）")
    ap.add_argument("--timeout", type=int, default=60, help="1 回の実行の上限秒（既定 60）")
    a = ap.parse_args()
    target = Path(a.target)
    if not target.is_file():
        print(f"対象が無い: {target}", file=sys.stderr)
        return 2
    if run(a.test, a.timeout, target) != "pass":
        print("変異前のテストが合格しない（判定不能）", file=sys.stderr)
        return 2
    original = target.read_bytes()
    fd, backup = tempfile.mkstemp(prefix="mutate-quick.", suffix=target.suffix)
    os.close(fd)
    shutil.copyfile(target, backup)
    lines = original.decode("utf-8").splitlines(keepends=True)
    killed = total = 0
    try:
        for i, desc, new in mutants(lines, a.only or list(PATTERNS), target.suffix == ".py"):
            if total >= a.max:
                break
            if not new.endswith("\n") and lines[i].endswith("\n"):
                new += "\n"
            target.write_text("".join(lines[:i] + [new] + lines[i + 1:]), encoding="utf-8")
            res = run(a.test, a.timeout, target)
            total += 1
            caught = res != "pass"
            killed += caught
            print(f"{i + 1}:{desc} → {'検出' if caught else '見逃し'}{'（タイムアウト）' if res == 'timeout' else ''}")
    finally:
        shutil.copyfile(backup, target)
        os.unlink(backup)
        for pyc in target.parent.glob(f"__pycache__/{target.stem}.*.pyc"):
            pyc.unlink(missing_ok=True)
    if target.read_bytes() != original:
        print("復元に失敗した（バックアップと一致しない）", file=sys.stderr)
        return 2
    print(f"ミューテーションスコア: 検出 {killed} / 全 {total}")
    return 1 if killed < total else 0


if __name__ == "__main__":
    sys.exit(main())
