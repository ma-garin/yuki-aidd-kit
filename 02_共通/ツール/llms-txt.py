#!/usr/bin/env python3
"""llms-txt.py — INDEX.md からリポジトリ直下の llms.txt（https://llmstxt.org の形式）を生成する（キット自身用）。

llms.txt は「このリポジトリを読む LLM が最初に開く地図」。INDEX.md と別に手で書くと食い違うので、
INDEX.md の表（エージェント・スキル・rules・コマンド・文書）から機械で作り、--check で古さを検出する。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。リンクはリポジトリのルートからの相対パス（URL にはしない）。

形式:
  # <INDEX の H1 から「— INDEX」を除いたもの>
  > <INDEX の H1 直後の 1 行>
  （生成物である旨の 1 段落）
  ## Docs / ## エージェント / ## DAILY スキル / ## rules      … 主要な文書（INDEX の各表の 1 列目と 1 行要約）
  ## Optional                                                  … LIBRARY スキル・コマンド・保守者向け（省いてよいもの）
  表の 1 列目のバッククォート内の名前を、実在するパス（skills/<名前>/SKILL.md・agents/<名前>.md・rules/<名前>.md・
  commands/<名前>.md・そのままのパス）に解決する。解決できない行は飛ばして標準エラーに出す（hooks の表は対象外）。

使い方: python3 02_共通/ツール/llms-txt.py [--root DIR] [-o FILE] [--check]
  --check  生成し直した内容と既存の llms.txt を比べ、違えば exit 1（書き込まない）
終了コード: 0=生成した・最新 / 1=--check で古い / 2=INDEX.md が読めない
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# INDEX の H2 の先頭一致 → (llms.txt の節名, Optional に入れるか)。ここに無い節（hooks・ECC 連携など）は載せない
SECTIONS = (
    ("docs/", "Docs", False),
    ("エージェント", "エージェント", False),
    ("DAILY スキル", "DAILY スキル", False),
    ("02_共通/rules/", "rules", False),
    ("LIBRARY スキル", "Optional", True),
    ("スラッシュコマンド", "Optional", True),
    ("06_保守者向け/内部仕様/", "Optional", True),
    ("internal/", "Optional", True),
)
FIXED_DOCS = (
    ("README.md", "キットの入口（導入方式・構成・版の扱い）"),
    ("INDEX.md", "全資産の地図（この llms.txt の生成元）"),
    ("CHANGELOG.md", "版ごとの変更内容（版の真実源は VERSION）"),
    ("04_Codex/README.md", "Codex での配置とスキルの生成"),
)
DESC_MAX = 120
CELL_NAME_RE = re.compile(r"`([^`]+)`")


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def clean(desc: str) -> str:
    d = re.sub(r"\*\*|<[^>]+>", "", desc)
    d = re.sub(r"\s+", " ", d).strip()
    return d if len(d) <= DESC_MAX else d[: DESC_MAX - 1] + "…"


def resolve(root: Path, name: str) -> str | None:
    n = name.strip()
    if n.startswith("/"):  # `/rfd` はスラッシュコマンド（同名のスキルより先に commands/ を見る）
        cands = [f"03_ClaudeCode/commands/{n[1:]}.md"]
    else:
        cands = [n, f"03_ClaudeCode/skills/{n}/SKILL.md", f"03_ClaudeCode/agents/{n}.md",
                 f"02_共通/rules/{n}.md", f"03_ClaudeCode/commands/{n}.md"]
    for c in cands:
        if (root / c).is_file():
            return c
    return None


def parse_index(root: Path) -> tuple[str, str, list[tuple[str, bool, str, str]], list[str]]:
    lines = (root / "INDEX.md").read_text(encoding="utf-8").splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), "INDEX")
    title = re.sub(r"\s*[—-]\s*INDEX\s*$", "", title)
    h1 = next((i for i, l in enumerate(lines) if l.startswith("# ")), -1)
    summary = next((l.strip() for l in lines[h1 + 1:] if l.strip()), "")
    entries: list[tuple[str, bool, str, str]] = []
    skipped: list[str] = []
    section: tuple[str, bool] | None = None
    for l in lines:
        if l.startswith("## "):
            head = l[3:].strip()
            section = next(((name, opt) for pre, name, opt in SECTIONS if head.startswith(pre)), None)
            continue
        if section is None or not l.lstrip().startswith("|"):
            continue
        cs = cells(l)
        if len(cs) < 2 or set(cs[0]) <= set("-: ") or not CELL_NAME_RE.search(cs[0]):
            continue
        name = CELL_NAME_RE.search(cs[0]).group(1)
        path = resolve(root, name)
        if path is None:
            skipped.append(f"{section[0]}: {name}")
            continue
        entries.append((section[0], section[1], path, clean(cs[1])))
    return title, summary, entries, skipped


def render(root: Path) -> tuple[str, list[str]]:
    title, summary, entries, skipped = parse_index(root)
    out = [f"# {title}", "", f"> {summary}", "",
           "生成物: `02_共通/ツール/llms-txt.py` が `INDEX.md` から生成する。直接編集しない。"
           "リンクはリポジトリのルートからの相対パス。読む順は `INDEX.md` の「2層の読み方」に従う。", ""]
    seen: set[str] = set()
    order: list[str] = []
    groups: dict[str, list[tuple[str, str]]] = {}
    groups["Docs"] = [(p, d) for p, d in FIXED_DOCS if (root / p).is_file()]
    seen.update(p for p, _ in groups["Docs"])
    order.append("Docs")
    for sec, opt, path, desc in entries:
        if path in seen:
            continue
        seen.add(path)
        if sec not in groups:
            groups[sec] = []
            order.append(sec)
        groups[sec].append((path, desc))
    order = [s for s in order if s != "Optional"] + (["Optional"] if "Optional" in groups else [])
    for sec in order:
        out.append(f"## {sec}")
        out.append("")
        for path, desc in groups[sec]:
            out.append(f"- [{path}]({path}): {desc}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n", skipped


def main() -> int:
    ap = argparse.ArgumentParser(description="INDEX.md から llms.txt を生成する")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("-o", "--output", default=None, help="書き出し先（既定: <root>/llms.txt）")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    try:
        text, skipped = render(root)
    except OSError as e:
        print(f"判定不能: INDEX.md を読めない（{e}）", file=sys.stderr)
        return 2
    for s in skipped:
        print(f"飛ばした（実在するパスに解決できない）: {s}", file=sys.stderr)
    out = Path(a.output) if a.output else root / "llms.txt"
    n = sum(1 for l in text.splitlines() if l.startswith("- ["))
    if a.check:
        try:
            cur = out.read_text(encoding="utf-8")
        except OSError:
            cur = None
        if cur != text:
            print(f"NG: {out.name} が INDEX.md と食い違う（python3 02_共通/ツール/llms-txt.py で再生成）")
            return 1
        print(f"OK: {out.name} は最新（リンク {n} 件）")
        return 0
    with open(out, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(text)
    print(f"生成: {out}（リンク {n} 件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
