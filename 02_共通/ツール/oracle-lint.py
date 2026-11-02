#!/usr/bin/env python3
"""oracle-lint.py — テストの「期待値の出どころ」を grep 型で静的検査する（AI が書いたテストを信じる前の確認 ①）。

実装を呼んで期待値を作るテストは、実装が間違っていても緑になる（同じ間違いを 2 回計算するだけ）。
本ツールは pytest（test_*.py ・*_test.py）と JS/TS（*.test.* ・*.spec.*）を行単位で読み、次を出す。
assert の削除は test-weaken-check.py、Playwright の書き方は pw-spec-lint.py、flaky は e2e_history.py が見る（重複しない）。
標準ライブラリのみ・Python 3.10 以上。

使い方:
  python3 02_共通/ツール/oracle-lint.py <ディレクトリかファイル>... [--sut 名前]... [--baseline FILE] [--json]
    --sut       被テスト対象（SUT）の関数・モジュール名。省略時はテストファイルの import / require から推定
    --baseline  既知の NG を書いたファイル（本ツールの出力行をそのまま貼る。行番号は無視し「ファイル + 種別 + 説明」で照合）
終了コード: 0 = NG なし ／ 1 = NG あり ／ 2 = 対象ファイルが無い

NG（exit 1）:
  実装依存の期待値   assert / expect の期待値側（== の右辺・assertEqual の第 2 引数・toBe/toEqual 等の引数）が SUT の呼び出し。
                     expected / want / exp で始まる変数に SUT の呼び出し結果を代入している行も NG（期待値を実装から計算）。
WARN（exit に影響しない）:
  要求IDが無い       テスト関数名・docstring・直前のコメント・本文に R\\d+ ／ spec: ／ req: のどれも無い。
  境界値が無い       比較に使う整数リテラル N があるのに、N-1 と N+1 がファイル内のどこにも出ない（当日/翌日型の境目の漏れ）。
出力: 1 行 1 件 `ファイル:行: NG|WARN 種別 — 説明`
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEST_LIBS = {"pytest", "unittest", "mock", "os", "sys", "re", "json", "datetime", "pathlib", "typing", "vitest", "jest",
             "@playwright/test", "assert", "node:assert", "node:test", "chai", "expect", "describe", "it", "test",
             "beforeEach", "afterEach", "date", "timedelta", "patch", "Path", "dataclasses", "collections", "math"}
REQ = re.compile(r"\bR\d+\b|spec:|req:", re.I)
NUM_CMP = re.compile(r"(?:[<>]=?|[=!]==?)\s*(-?\d+)\b(?!\.\d)|\b(\d+)\s*(?:[<>]=?|[=!]==?)(?!>)")
JS_EXPECT = re.compile(r"\.(?:toBe|toEqual|toStrictEqual|toBeCloseTo|toMatchObject)\((.*)\)")


def is_test_file(p: Path) -> bool:
    n = p.name
    if p.suffix == ".py":
        return n.startswith("test_") or n.endswith("_test.py")
    return bool(re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", n))


def collect(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = Path(t)
        if p.is_file():
            out.append(p)
        elif p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and is_test_file(f) and "node_modules" not in f.parts)
    return out


def guess_sut(text: str) -> set[str]:
    names: set[str] = set()
    for m in re.finditer(r"^\s*from\s+([\w.]+)\s+import\s+\(?([^)\n]+)", text, re.M):
        if m.group(1).split(".")[0] not in TEST_LIBS:
            names |= {x.split(" as ")[-1].strip() for x in m.group(2).split(",") if x.strip()}
    for m in re.finditer(r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?\s*$", text, re.M):
        if m.group(1).split(".")[0] not in TEST_LIBS:
            names.add(m.group(2) or m.group(1))
    for m in re.finditer(r"import\s+(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\})?\s*from\s*['\"]([^'\"]+)['\"]", text):
        if m.group(3) in TEST_LIBS:
            continue
        if m.group(1):
            names.add(m.group(1))
        names |= {x.split(" as ")[-1].strip() for x in (m.group(2) or "").split(",") if x.strip()}
    for m in re.finditer(r"(?:const|let|var)\s+(?:\{([^}]*)\}|(\w+))\s*=\s*require\(\s*['\"]([^'\"]+)['\"]", text):
        if m.group(3) in TEST_LIBS:
            continue
        names |= {x.split(":")[-1].strip() for x in (m.group(1) or m.group(2)).split(",") if x.strip()}
    return names - TEST_LIBS


def calls_sut(expr: str, sut: set[str]) -> str | None:
    for n in sut:
        if re.search(rf"(?<![\w.]){re.escape(n)}\s*(?:\.\w+\s*)?\(", expr):
            return n
    return None


def expected_side(line: str) -> str | None:
    s = line.strip()
    m = re.match(r"assert\s+(.+?)\s*(?:==|!=)\s*(.+?)(?:,\s*['\"].*)?$", s)
    if m:
        return m.group(2)
    m = re.search(r"assert(?:Equal|Equals|NotEqual|AlmostEqual)\((.+)\)", s)
    if m:
        depth, parts, cur = 0, [], ""
        for ch in m.group(1):
            if ch in "([{": depth += 1
            if ch in ")]}": depth -= 1
            if ch == "," and depth == 0:
                parts.append(cur); cur = ""
            else:
                cur += ch
        parts.append(cur)
        return parts[1] if len(parts) > 1 else None
    m = JS_EXPECT.search(s)
    return m.group(1) if m else None


def lint(path: Path, sut_arg: list[str]) -> list[tuple[int, str, str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    sut = set(sut_arg) or guess_sut(text)
    hits: list[tuple[int, str, str, str]] = []
    for i, ln in enumerate(lines, 1):
        code = ln.split("#")[0] if path.suffix == ".py" else re.sub(r"//.*", "", ln)
        exp = expected_side(code)
        n = calls_sut(exp, sut) if exp else None
        if n:
            hits.append((i, "NG", "実装依存の期待値", f"期待値側で SUT の {n}() を呼んでいる（実装の誤りをそのまま期待値にする）"))
            continue
        m = re.match(r"\s*(?:const|let|var)?\s*((?:expected|expect_|want|exp)\w*)\s*=\s*(.+)", code, re.I)
        if m and (n := calls_sut(m.group(2), sut)):
            hits.append((i, "NG", "実装依存の期待値", f"期待値 {m.group(1)} を SUT の {n}() から計算している"))
    # 要求ID: テストごとの塊（直前のコメント〜次のテストの手前）
    starts = [i for i, ln in enumerate(lines) if re.match(r"\s*(?:async\s+)?def\s+test\w*\s*\(", ln)
              or re.match(r"\s*(?:test|it)(?:\.\w+)?\s*\(", ln)]
    for k, s in enumerate(starts):
        b = s
        while b > 0 and re.match(r"\s*(#|//|/\*|\*|@)", lines[b - 1]):
            b -= 1
        e = starts[k + 1] if k + 1 < len(starts) else len(lines)
        if not REQ.search("\n".join(lines[b:e])):
            name = re.search(r"def\s+(\w+)|\(\s*['\"`]([^'\"`]*)", lines[s])
            label = (name.group(1) or name.group(2)) if name else "?"
            hits.append((s + 1, "WARN", "要求IDが無い", f"{label} に R<番号>・spec:・req: が無い（何の要求を確かめるか辿れない）"))
    # 境界値
    nums = {int(x) for x in re.findall(r"(?<![\w.])-?\d+(?![\w.])", text)}
    seen: set[int] = set()
    for i, ln in enumerate(lines, 1):
        for m in NUM_CMP.finditer(ln):
            v = int(m.group(1) or m.group(2))
            if v in seen or (v - 1) in nums or (v + 1) in nums:
                continue
            seen.add(v)
            hits.append((i, "WARN", "境界値が無い", f"{v} と比べているが {v - 1} / {v + 1} がファイル内に無い（境目の前後を確かめていない）"))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="テストの期待値の出どころ（実装依存）・要求ID・境界値を静的検査する")
    ap.add_argument("target", nargs="+", help="テストのディレクトリかファイル")
    ap.add_argument("--sut", action="append", default=[], help="被テスト対象の名前（複数可。省略時は import から推定）")
    ap.add_argument("--baseline", help="既知の NG（本ツールの出力行）を書いたファイル。該当 NG は数えない")
    ap.add_argument("--json", action="store_true", help="結果を JSON で出す")
    a = ap.parse_args()
    files = collect(a.target)
    if not files:
        print("対象のテストファイルが無い", file=sys.stderr)
        return 2
    known: set[str] = set()
    if a.baseline and Path(a.baseline).is_file():
        for ln in Path(a.baseline).read_text(encoding="utf-8").splitlines():
            m = re.match(r"(.+?):\d+:\s*(.+)$", ln.strip())
            if m:
                known.add(f"{m.group(1)}|{m.group(2)}")
    rows = []
    for f in files:
        for line, lv, kind, msg in lint(f, a.sut):
            if lv == "NG" and f"{f}|{lv} {kind} — {msg}" in known:
                continue
            rows.append({"file": str(f), "line": line, "level": lv, "kind": kind, "message": msg})
    ng = sum(r["level"] == "NG" for r in rows)
    if a.json:
        print(json.dumps({"ng": ng, "warn": len(rows) - ng, "items": rows}, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{r['file']}:{r['line']}: {r['level']} {r['kind']} — {r['message']}")
        print(f"oracle-lint: {len(files)} ファイル / NG {ng} / WARN {len(rows) - ng}")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
