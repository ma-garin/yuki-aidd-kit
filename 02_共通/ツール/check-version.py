#!/usr/bin/env python3
"""check-version.py — 版の表記が真実源 `VERSION` と食い違っていないかを検査する（キット自身用・読むだけ）。

版の真実源は `VERSION`（CHANGELOG.md 冒頭・構成管理計画書）。CHANGELOG の最新のリリース見出しや、
利用者向け資料の表紙（`Ver.X.Y.Z`）を書き換え忘れると、配った版と資料の版が食い違ったまま気づけない。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。git は使わない（Codex の Windows 環境でも動く）。

検査:
  V1 VERSION         ルートの VERSION が `X.Y.Z`（数字 3 つ）の 1 行（NG）
  V2 CHANGELOG       「## 未リリース」を除く最初の `## Ver.X.Y.Z` 見出しが VERSION と一致（NG）
  V3 見出しの順      CHANGELOG の `## Ver.` 見出しが新しい順に並び、同じ版が 2 回無い（WARN）
  V4 版の表記        配る文書（README.md・INDEX.md・00〜04 の *.md / *.html / *.template / *.json / *.yml / *.yaml / *.toml）の
                     `Ver.X.Y.Z`・`Ver X.Y.Z`・`"version": "X.Y.Z"`（キット名の直後）を VERSION と突き合わせる（NG）
                     対象外: 「（8.6.0〜）」のような導入版の注記（〜 が続くもの）・05/06（履歴・保守者の記録）・CHANGELOG 本文・
                     フェンスコード・回帰テストの fixtures
使い方: python3 02_共通/ツール/check-version.py [--root DIR] [--json]
終了コード: 0=一致 / 1=NG あり / 2=VERSION・CHANGELOG が読めない
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
HEAD_RE = re.compile(r"^##\s+Ver\.?\s*(\d+\.\d+\.\d+)")
# Ver.8.6.0 / Ver 8.6.0 / ver.8.6.0（直後が 〜・~ のものは導入版の注記なので拾わない）
STATED_RE = re.compile(r"(?<![A-Za-z])[Vv]er\.?\s?(\d+\.\d+\.\d+)(?![\d.]|\s?[〜~])")
KIT_JSON_RE = re.compile(r'"(?:aidd[-_]?kit[-_]?)?version"\s*:\s*"(\d+\.\d+\.\d+)"', re.I)
SCAN_TOP = ("README.md", "INDEX.md")
SCAN_DIRS = ("00_導入", "01_利用者向け資料", "02_共通", "03_ClaudeCode", "04_Codex")
SCAN_EXT = {".md", ".html", ".template", ".json", ".yml", ".yaml", ".toml"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", "fixtures", ".claude"}


def key(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def iter_targets(root: Path) -> list[Path]:
    out = [root / f for f in SCAN_TOP if (root / f).is_file()]
    for d in SCAN_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_file() and f.suffix in SCAN_EXT and not (set(f.relative_to(root).parts) & SKIP_PARTS):
                out.append(f)
    return out


def stated_versions(text: str, is_json: bool) -> list[tuple[int, str]]:
    """(行番号, 版) を返す。Markdown のフェンスコード内は見ない。"""
    out: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in STATED_RE.finditer(line):
            out.append((i, m.group(1)))
        if is_json:
            for m in KIT_JSON_RE.finditer(line):
                out.append((i, m.group(1)))
    return out


def run(root: Path) -> tuple[dict, int]:
    res: dict = {"version": None, "ng": [], "warn": [], "checked_files": 0}
    vf = root / "VERSION"
    try:
        lines = [l.strip() for l in vf.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError as e:
        res["ng"].append(f"V1 VERSION を読めない: {e}")
        return res, 2
    if len(lines) != 1 or not SEMVER_RE.match(lines[0]):
        res["ng"].append(f"V1 VERSION は X.Y.Z の 1 行にする（実際: {lines!r}）")
        return res, 1
    ver = lines[0]
    res["version"] = ver
    cl = root / "CHANGELOG.md"
    try:
        cl_lines = cl.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        res["ng"].append(f"V2 CHANGELOG.md を読めない: {e}")
        return res, 2
    heads = [(i, m.group(1)) for i, l in enumerate(cl_lines, start=1) if (m := HEAD_RE.match(l))]
    if not heads:
        res["ng"].append("V2 CHANGELOG.md に `## Ver.X.Y.Z` の見出しが 1 つも無い")
    else:
        ln, top = heads[0]
        res["changelog_top"] = top
        if top != ver:
            res["ng"].append(f"V2 CHANGELOG.md:{ln} 最新のリリース見出しは Ver.{top}、VERSION は {ver}")
        seen: set[str] = set()
        for (l1, a), (_, b) in zip(heads, heads[1:]):
            if key(a) <= key(b):
                res["warn"].append(f"V3 CHANGELOG.md:{l1} Ver.{a} の次に Ver.{b}（新しい順になっていない）")
        for l1, a in heads:
            if a in seen:
                res["warn"].append(f"V3 CHANGELOG.md:{l1} Ver.{a} が 2 回ある")
            seen.add(a)
    for f in iter_targets(root):
        res["checked_files"] += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln, v in stated_versions(text, f.suffix == ".json"):
            if v != ver:
                res["ng"].append(f"V4 {f.relative_to(root).as_posix()}:{ln} Ver.{v} と書いてある（VERSION は {ver}）")
    return res, 1 if res["ng"] else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="版の表記を VERSION と突き合わせる")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    res, rc = run(Path(a.root))
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return rc
    for r in res["ng"]:
        print(f"NG  {r}")
    for r in res["warn"]:
        print(f"WARN {r}")
    if rc == 2:
        print("判定不能: VERSION / CHANGELOG.md を読めない")
    else:
        print(f"{'NG' if rc else 'OK'}: VERSION={res['version']} NG={len(res['ng'])} WARN={len(res['warn'])}"
              f"（{res['checked_files']} ファイルを照合）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
