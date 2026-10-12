#!/usr/bin/env python3
"""pack-context.py — 作業指示書に添える「文脈パック」（抜粋＋sha256）を 1 枚の Markdown にまとめる。

Codex（別モデル）は git が無く、指示書が指す文書の「どの版を見たか」を後から確かめられない。
渡した抜粋と、その時点のファイル全体の sha256・節の版をパックに刻み、受け取った成果を照合するときに
`--verify` で「パック作成後に元のファイルが変わったか」を機械で判定する。
節の切り出しは md-section.py（見出しの部分一致・同レベル以上の次の見出しまで）、節の版は
section_hash.py の正規化（空白・改行の差を吸収した sha256 先頭 7 桁）をそのまま使う（同じ規約を二重に持たない）。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。Windows でも動く（`C:\\x\\a.md` の `:` はドライブとして扱う）。

指定（spec）:
  <file>                  ファイル全体
  <file>:<見出し>          見出しに <見出し> を含む節（部分一致・大小無視）。`<file>#<見出し>` も同じ
  一致 0 件・2 件以上は md-section.py get と同じく候補を出して exit 1

使い方:
  python3 02_共通/ツール/pack-context.py <spec> [<spec> ...] [-o context-pack.md] [--root DIR] [--title 題]
  python3 02_共通/ツール/pack-context.py --verify context-pack.md [--root DIR]
    --root  パスの表示と --verify の起点（既定: カレントディレクトリ）
終了コード: 0=正常（--verify は全件一致） / 1=ファイル・見出しが無い・--verify で食い違い / 2=引数誤り
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 部品の import で __pycache__ を作らない（読むだけの道具）
_HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    if spec is None or spec.loader is None:
        raise ImportError(filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    MD = _load("md_section", "md-section.py")        # 節の切り出し（parse_headings・section_span）
    SH = _load("section_hash", "section_hash.py")     # 節の版（normalize）
except (ImportError, OSError) as e:  # 配布先で部品が欠けているときは判定不能
    print(f"判定不能: 隣の md-section.py / section_hash.py を読めない（{e}）", file=sys.stderr)
    sys.exit(2)

PACK_RE = re.compile(r"^<!-- pack: (?P<path>.+?) sha256=(?P<sha>[0-9a-f]{64})(?: section=(?P<sec>.*?))? -->$")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def section_version(text: str) -> str:
    return hashlib.sha256(SH.normalize(text).encode("utf-8")).hexdigest()[:7]


def split_spec(spec: str) -> tuple[str, str]:
    """spec → (ファイル, 見出し)。ファイルとして実在すればそのまま全体。Windows のドライブ `C:` は区切りにしない。"""
    if Path(spec).is_file():
        return spec, ""
    for sep in ("#", ":"):
        if sep in spec:
            f, _, q = spec.rpartition(sep)
            if sep == ":" and re.fullmatch(r"[A-Za-z]", f):
                continue
            if f:
                return f, q
    return spec, ""


def fence_for(body: str) -> str:
    longest = max((len(m.group(0)) for m in re.finditer(r"`{3,}", body)), default=0)
    return "`" * max(3, longest + 1)


def rel(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def extract(spec: str) -> tuple[Path, str, int, int, str] | str:
    """(ファイル, 見出しパス, 開始行, 終了行, 本文) か、エラー文を返す。"""
    fname, query = split_spec(spec)
    f = Path(fname)
    if not f.is_file():
        return f"ファイルが見つかりません: {fname}"
    lines = MD.read_lines(f)
    if not query:
        return f, "（全体）", 1, len(lines), "\n".join(lines)
    headings = MD.parse_headings(lines)
    hits = [i for i, h in enumerate(headings) if query.lower() in h.title.lower()]
    if len(hits) != 1:
        msg = [f"見出しが{'見つかりません' if not hits else '複数一致しました'}: 「{query}」（{fname}）"]
        for i in (hits or range(len(headings))):
            s, e = MD.section_span(lines, headings, i, same_or_higher=True)
            msg.append(f"  {MD.heading_path(headings, i)}（{s}-{e}行）")
        return "\n".join(msg)
    i = hits[0]
    s, e = MD.section_span(lines, headings, i, same_or_higher=True)
    return f, MD.heading_path(headings, i), s, e, MD.span_text(lines, s, e)


def build(specs: list[str], root: Path, title: str) -> tuple[str, list[str]]:
    errors: list[str] = []
    items = []
    for spec in specs:
        r = extract(spec)
        if isinstance(r, str):
            errors.append(r)
        else:
            items.append(r)
    if errors:
        return "", errors
    out = [f"# 文脈パック: {title}", "",
           f"pack-context.py が {len(items)} 件の抜粋をまとめた。sha256 は**ファイル全体**、節の版は section_hash.py の正規化による先頭 7 桁。",
           "受け取った側は `python3 scripts/pack-context.py --verify <このファイル>` でパック作成後の変更を確かめる。", "",
           "| # | ファイル | 節 | 行 | sha256（ファイル全体） | 節の版 |", "|---|---|---|---|---|---|"]
    marks = []
    for n, (f, path, s, e, body) in enumerate(items, start=1):
        digest = sha256_file(f)
        ver = section_version(body)
        out.append(f"| {n} | `{rel(f, root)}` | {path.replace('|', '｜')} | {s}-{e} | `{digest}` | `{ver}` |")
        marks.append((n, f, path, s, e, body, digest, ver))
    out.append("")
    for n, f, path, s, e, body, digest, ver in marks:
        sec = "" if path == "（全体）" else f" section={path}"
        fence = fence_for(body)
        leaf = path.split(" > ")[-1].lstrip("#").strip()
        out += [f"## {n}. `{rel(f, root)}` — {leaf}（{s}-{e}行）", "",
                f"<!-- pack: {rel(f, root)} sha256={digest}{sec} -->", "",
                f"{fence}{'markdown' if f.suffix.lower() == '.md' else ''}", body, fence, ""]
    return "\n".join(out), []


def verify(pack: Path, root: Path) -> int:
    try:
        text = pack.read_text(encoding="utf-8")
    except OSError as e:
        print(f"判定不能: パックを読めない（{e}）", file=sys.stderr)
        return 2
    marks = [m for m in (PACK_RE.match(l.strip()) for l in text.splitlines()) if m]
    if not marks:
        print(f"NG: パックの記録（<!-- pack: … -->）が 0 件: {pack}")
        return 1
    bad = 0
    for m in marks:
        f = root / m.group("path")
        if not f.is_file():
            print(f"NG  消えた: {m.group('path')}")
            bad += 1
        elif sha256_file(f) != m.group("sha"):
            print(f"NG  変わった: {m.group('path')}（パック {m.group('sha')[:12]}… ≠ 現在 {sha256_file(f)[:12]}…）")
            bad += 1
        else:
            print(f"OK  {m.group('path')}")
    print(f"{'NG' if bad else 'OK'}: {len(marks)} 件中 {bad} 件がパック作成後に変わった・消えた")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="抜粋＋sha256 の文脈パックを作る／照合する")
    ap.add_argument("specs", nargs="*", help="<file> または <file>:<見出し>")
    ap.add_argument("-o", "--output", default=None, help="書き出し先（既定: 標準出力）")
    ap.add_argument("--root", default=".", help="パスの表示と --verify の起点")
    ap.add_argument("--title", default="作業指示書の参照資産")
    ap.add_argument("--verify", default=None, metavar="PACK", help="パックの sha256 と現在のファイルを照合する")
    a = ap.parse_args()
    root = Path(a.root)
    if a.verify:
        return verify(Path(a.verify), root)
    if not a.specs:
        ap.print_usage(sys.stderr)
        return 2
    text, errors = build(a.specs, root, a.title)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8", newline="\n")
        print(f"文脈パック: {a.output}（{len(a.specs)} 件）")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
