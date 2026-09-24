#!/usr/bin/env python3
"""cite-check.py — ADR・rules・lessons の中の引用（根拠にしたファイル・見出し・行）が消えた・変わったことを検知する。

ADR や規則の主張がどこを根拠にしているかを引用で書かせ、引用先が消えたら NG、変わったら stale（要再確認）として出す。
版の計算は隣の section_hash.py（trace-check.sh の C7 と共用。正規化後 sha256 の先頭 7 桁）。標準ライブラリのみ・Python 3.9 互換。

使い方:
  python3 scripts/cite-check.py <root>              検査だけ（ファイルに一切書き込まない）
  python3 scripts/cite-check.py <root> --record     版の無い引用に現在の版（@版）を書き足す
  python3 scripts/cite-check.py <root> --refresh    stale（記録と現在が違う）の版を現在の版に書き換える
  python3 scripts/cite-check.py <root> --strict     対象外にした引用（キット参照・配布された規則の未作成の参照）も WARN で出す
    --record・--refresh は「引用先を読み、主張が正しいと保守者が確かめた」記録。保守者だけが打つ（AI は打たない＝AI は承認しない）。
    手順（retro の最後）: cite-check を流す（書き込みなし）→ stale の主張を読み直して直す → 保守者が --refresh → commit で残す。
終了コード: 0 = NG なし（WARN はあってよい）／ 1 = NG あり ／ 2 = 引数の誤り・section_hash.py が無い

対象（<root> 配下。.git・node_modules・skills などのディレクトリは見ない。skills は対象外）:
  - ADR: ファイル名が ADR-<番号>… の *.md、または adr・adrs・decisions という名前のディレクトリの *.md
  - rules: rules という名前のディレクトリの *.md（adr-to-rules.py が生成した decisions-*.md は元の ADR を見るので飛ばす）
  - lessons: lessons.md
引用の書き方（バッククォートで囲む。HTML コメントとフェンスコードの中は読まない）:
  `path#見出し`   見出しの節（その見出しから、同じレベル以上の次の見出しの手前まで）。見出しは完全一致、無ければ部分一致で 1 つ
  `path:行` `path:行-行`   その行
  `path`          ファイル全体。末尾が / ならディレクトリ（有無だけ見る。版は持たない）
  path は <root> → <root>/.claude（配布先のキットの配置: `rules/`・`skills/`・`templates/` は .claude/ の下）→ 引用した文書 の順に
  相対で探す。<root> の外は見ない。
  path はパス区切り（/）を含み、最後の要素が既知の拡張子（.md .py .ts など）を持つこと。ファイル名だけ（`prompt-priority.py`）・
  `application/json`・`requests.get` は引用と見ない。
  版は後ろに `@版` で書く（例 `docs/spec.md#認証方式@a1b2c3d`）。版は --record が書く。手で作らない。
配布先の .claude/rules/ の対象外（数えない。--strict のときだけ WARN）:
  - キット参照: 引用先がキットのディレクトリ（00_導入/ 〜 06_保守者向け/）で始まり、実在しない
  - 未作成の参照: 版の無い引用で、引用先が実在しない（配布した規則が指すプロジェクトの成果物は、作られるまで無い）
  版を記録した（@版 のある）引用の引用先が消えたら、.claude/rules/ でも NG。
判定:
  NG   ファイル無し・見出し無し・見出しが曖昧（複数に当たる）・行が無い・版の書式不正（7 桁の小文字 16 進でない）
  WARN stale（記録した版と現在の版が違う）。版の無い引用は件数だけ出す（--record で記録すると stale を検知できる）
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import section_hash
except ImportError:
    section_hash = None

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", "skills"}
ADR_DIRS = {"adr", "adrs", "decisions"}
ADR_NAME_RE = re.compile(r"^adr[-_ ]?\d+", re.I)
GENERATED_MARK = "adr-to-rules.py が生成"
EXTS = {"md", "markdown", "txt", "rst", "py", "ts", "tsx", "js", "jsx", "mjs", "cjs", "json", "yml", "yaml", "toml",
        "ini", "cfg", "conf", "sh", "bash", "zsh", "ps1", "csv", "tsv", "html", "htm", "css", "scss", "sql", "go",
        "rs", "java", "kt", "swift", "rb", "php", "c", "h", "cpp", "hpp", "cs", "vue", "svelte", "xml", "lock",
        "env", "example", "tf", "proto", "graphql", "ipynb"}
SPAN_RE = re.compile(r"`([^`\n]+)`")
CITE_RE = re.compile(r"^(?P<path>[^\s`#@:*?{}\[\]<>|\"']+?)"
                     r"(?:#(?P<head>[^`@]+?)|:(?P<l1>\d+)(?:-(?P<l2>\d+))?)?"
                     r"(?:@(?P<ver>[0-9A-Za-z]*))?$")
HASH_RE = re.compile(r"^[0-9a-f]{7}$")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
KIT_DIRS = ("00_導入/", "01_利用者向け資料/", "02_共通/", "03_ClaudeCode/", "04_Codex/", "05_プロジェクト管理/", "06_保守者向け/")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s)).strip().strip("#").strip()


def is_target(p: Path) -> bool:
    if p.suffix.lower() != ".md":
        return False
    if p.name.lower() == "lessons.md":
        return True
    if ADR_NAME_RE.match(p.name) or p.parent.name.lower() in ADR_DIRS:
        return True
    return p.parent.name.lower() == "rules"


def targets(root: Path) -> list[Path]:
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            p = Path(dp) / fn
            if is_target(p):
                out.append(p)
    return out


def is_cite(path: str) -> bool:
    """引用とみなす path か。パス区切りを含み、ディレクトリは末尾 /、ファイルは最後の要素が既知の拡張子を持つ。"""
    if "/" not in path:
        return False                      # ファイル名だけ（prompt-priority.py）は引用にしない
    if path.endswith("/"):
        return bool(path.strip("/"))
    last = path.rsplit("/", 1)[-1]
    if "." not in last.strip("."):
        return False
    return last.rsplit(".", 1)[-1].lower() in EXTS


def headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """(行 index, レベル, 見出し文字列)。フェンスコード内の # は見出しにしない。"""
    out, in_fence, marker = [], False, ""
    for i, line in enumerate(lines):
        fm = FENCE_RE.match(line)
        if fm:
            if not in_fence:
                in_fence, marker = True, fm.group(1)
            elif fm.group(1) == marker:
                in_fence = False
            continue
        if in_fence:
            continue
        hm = HEADING_RE.match(line)
        if hm:
            out.append((i, len(hm.group(1)), hm.group(2)))
    return out


class Cite:
    def __init__(self, src: Path, line_no: int, raw: str, m: re.Match) -> None:
        self.src, self.line_no, self.raw = src, line_no, raw
        self.path, self.head, self.ver = m.group("path"), m.group("head"), m.group("ver")
        self.l1 = int(m.group("l1")) if m.group("l1") else None
        self.l2 = int(m.group("l2")) if m.group("l2") else self.l1
        self.has_at = "@" in raw

    @property
    def base(self) -> str:
        """@版 を除いた引用。"""
        return self.raw.split("@", 1)[0] if self.has_at else self.raw


def resolve(root: Path, src: Path, rel: str) -> Path | None:
    for base in (root, root / ".claude", src.parent):
        p = (base / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            continue
        if p.exists():
            return p
    return None


def current_version(root: Path, c: Cite) -> tuple[str | None, str | None]:
    """(版, NG の理由)。ディレクトリは版を持たない（(None, None)）。"""
    target = resolve(root, c.src, c.path)
    if target is None:
        return None, f"ファイル無し（{c.path}）"
    if target.is_dir():
        return None, None
    lines = section_hash.read_lines(target)
    if c.head is not None:
        want = norm(c.head)
        hs = headings(lines)
        exact = [h for h in hs if norm(h[2]) == want]
        cand = exact or [h for h in hs if want and want in norm(h[2])]
        if not cand:
            return None, f"見出し無し（{c.path} に「{c.head}」が無い）"
        if len(cand) > 1:
            return None, f"見出しが曖昧（{c.path} で {len(cand)} 個に当たる: " + "・".join(h[2] for h in cand[:3]) + "）"
        i, lv, _ = cand[0]
        end = next((j for j, l2, _ in hs if j > i and l2 <= lv), len(lines))
        return section_hash.short_hash("\n".join(lines[i:end])), None
    if c.l1 is not None:
        n = len(lines) - (1 if lines and lines[-1] == "" else 0)
        if c.l1 < 1 or c.l2 < c.l1 or c.l2 > n:
            return None, f"行が無い（{c.path} は {n} 行。引用は {c.l1}" + (f"-{c.l2}" if c.l2 != c.l1 else "") + "）"
        return section_hash.short_hash("\n".join(lines[c.l1 - 1:c.l2])), None
    return section_hash.short_hash("\n".join(lines)), None


def scan(src: Path) -> list[Cite]:
    with src.open(encoding="utf-8", errors="replace", newline="") as fh:
        raw = fh.read()
    # HTML コメントは行数を保ったまま消す（書き戻す行番号を rewrite と一致させる）
    text = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), raw)
    out, in_fence, marker = [], False, ""
    for n, line in enumerate(text.split("\n"), start=1):
        line = line[:-1] if line.endswith("\r") else line
        fm = FENCE_RE.match(line)
        if fm:
            if not in_fence:
                in_fence, marker = True, fm.group(1)
            elif fm.group(1) == marker:
                in_fence = False
            continue
        if in_fence:
            continue
        for sm in SPAN_RE.finditer(line):
            m = CITE_RE.match(sm.group(1).strip())
            if m and is_cite(m.group("path")):
                out.append(Cite(src, n, sm.group(1).strip(), m))
    return out


def rewrite(src: Path, fixes: dict[tuple[int, str], str]) -> None:
    """(行番号, 元の引用) → 新しい引用 に置き換える。改行コードは保ち、対象の行以外は変えない。"""
    with src.open(encoding="utf-8", newline="") as fh:
        rows = fh.read().split("\n")
    for (n, old), new in fixes.items():
        rows[n - 1] = rows[n - 1].replace(f"`{old}`", f"`{new}`")
    with src.open("w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(rows))


def main() -> int:
    ap = argparse.ArgumentParser(description="ADR・rules・lessons の引用先の消失・変更を検知する")
    ap.add_argument("root")
    ap.add_argument("--record", action="store_true", help="版の無い引用に現在の版を書き足す（保守者の確認の記録。AI は打たない）")
    ap.add_argument("--refresh", action="store_true", help="食い違う版を現在の版に書き換える（保守者の再確認の記録。AI は打たない）")
    ap.add_argument("--strict", action="store_true", help=".claude/rules/ で対象外にした引用も WARN で出す")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not root.is_dir():
        print(f"❌ ディレクトリが無い: {a.root}", file=sys.stderr)
        return 2
    if section_hash is None:
        print(f"❌ 隣に section_hash.py が無い（{Path(__file__).resolve().parent}）。版を計算できない", file=sys.stderr)
        return 2
    ng, warn, info = [], [], []
    files = targets(root)
    ncites = unversioned = skipped = 0
    for src in files:
        rel = src.relative_to(root)
        in_rules = ("/" + rel.as_posix()).find("/.claude/rules/") >= 0
        fixes: dict[tuple[int, str], str] = {}
        if GENERATED_MARK in src.read_text(encoding="utf-8", errors="replace"):
            continue
        for c in scan(src):
            ncites += 1
            where = f"{rel}:{c.line_no}"
            if c.has_at and not HASH_RE.match(c.ver or ""):
                ng.append(("版の書式不正", where, f"`{c.raw}`（@ の後は cite-check --record が書く 7 桁の小文字 16 進）"))
                continue
            cur, why = current_version(root, c)
            if why and in_rules and why.startswith("ファイル無し"):
                path = c.path[2:] if c.path.startswith("./") else c.path
                kind = ("キット参照（対象外）" if path.startswith(KIT_DIRS) else
                        "未作成の参照（対象外）" if not c.has_at else "")
                if kind:
                    skipped += 1
                    if a.strict:
                        warn.append((kind, where, f"`{c.raw}` — 配布先に無い"))
                    continue
            if why:
                ng.append(("引用先が無い", where, f"`{c.raw}` — {why}"))
                continue
            if cur is None:
                continue                     # ディレクトリ（版を持たない）
            if not c.has_at:
                unversioned += 1
                if a.record:
                    fixes[(c.line_no, c.raw)] = f"{c.base}@{cur}"
                    info.append(f"  記録 {where}: `{c.base}@{cur}`")
            elif c.ver != cur:
                if a.refresh:
                    fixes[(c.line_no, c.raw)] = f"{c.base}@{cur}"
                    info.append(f"  更新 {where}: `{c.raw}` → @{cur}")
                else:
                    warn.append(("stale", where, f"`{c.base}` が変わった（記録 {c.ver} → 現在 {cur}）。主張を見直し、"
                                                 "保守者が --refresh で記録し直す"))
        if fixes:
            rewrite(src, fixes)
    print(f"=== 引用の検査（cite-check）: {root} ===")
    print(("❌" if ng else "✅") + f" NG={len(ng)} / WARN={len(warn)}（対象 {len(files)} ファイル・引用 {ncites} 件"
          f"・版の記録なし {unversioned} 件・対象外 {skipped} 件）")
    for kind, where, detail in ng:
        print(f"  NG   {kind}: {where} — {detail}")
    for kind, where, detail in warn:
        print(f"  WARN {kind}: {where} — {detail}")
    if unversioned and not a.record:
        print(f"ℹ 版の記録なし {unversioned} 件は有無だけ見た（保守者が --record で版を記録すると、変更を stale で検知できる）")
    if skipped and not a.strict:
        print(f"ℹ 対象外 {skipped} 件（.claude/rules/ のキット参照・未作成の参照。--strict で一覧）")
    if info:
        print(f"版を書いた（{len(info)} 件）:")
        print("\n".join(info))
        print("  これは保守者が引用先を読んだ記録。commit で残す（AI は --record・--refresh を打たない）")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
