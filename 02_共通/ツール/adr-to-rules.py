#!/usr/bin/env python3
"""採用済みの ADR と適用パスのある lessons を、paths 付きの rules（`decisions-<slug>.md`）に書き出す。

B-23（A15）。ADR・lessons を書いても、該当ファイルを編集するときに AI の文脈へ入る経路が無く、
捨てた案の再提案や撤回条件の見落としが起きうる。Claude Code の rules は frontmatter の `paths:` に当たる
ファイルを読んだときだけ読み込まれるので、決定の要旨をそこへ置く（Codex は AGENTS.md の 1 行で自分で読む）。

使い方:
    python3 scripts/adr-to-rules.py <ADR のディレクトリ> <lessons.md> --out .claude/rules
    （キットでは 02_共通/ツール/adr-to-rules.py。retro の最後に手で実行する。hook や定期実行にはしない）

読むもの:
  - ADR（<ADR のディレクトリ>/*.md）: 見出しの `**状態**:`（旧形式の `**ステータス**:` も読む）が採用のものだけ。
    採用として扱う表記: 採用・採用済み・採用（条件付き）・Accepted。既知の他の状態（検討中・却下・撤回・提案中・廃止・保留・
    Proposed・Rejected・Deprecated・Superseded）は黙って飛ばし、読めない値は警告して飛ばす。
    `**適用パス**` の下に `- ` で並べた glob（同じ行に書いてもよい）が paths になる。行は改行と `;` で分け、
    バッククォートで囲んだ部分があればそれだけ、無ければ最初の空白・`（`・`(` まで（後ろの注記は捨てる）。
    カンマは `{…}` の外だけ区切り（`src/**/*.{ts,tsx}` は 1 つ）。適用パスの無い採用 ADR は
    書き出さない（paths の無い rules は常時読み込みになり、全作業の文脈を増やすため。警告を出す）。
    要旨は `## 決定`・`## 捨てた案…`・`## 撤回条件` の節から各 3 行まで（表は 1 行 1 案に畳む。見出し行と「例:」の行は捨てる）。
    `**置換先**:` に書いた ADR は、置き換えた側が採用なら書き出さない（置換済み。警告を出す）。
  - lessons.md: `## ` 見出しごとの項目のうち、`**適用パス**` のあるものだけ。Keep / Problem / Try を各 3 行まで。
  HTML コメント（`<!-- -->`）の中は読まない（ひな形の記入例を拾わない）。

書き出し: `<out>/decisions-<slug>.md`。slug は ADR 番号（`ADR-007` → `adr-007`。番号が無ければファイル名）、
lessons は `lesson-<日付>-<見出しの英数字>`（英数字が無ければ見出しのハッシュ 8 桁）。本文を直しても slug は変わらない。
既存の同名ファイルは上書きする。このツールが書いた印（`adr-to-rules.py が生成`）のある `decisions-*.md` のうち、
今回書き出さなかったもの（採用でなくなった・適用パスを消した・置換された）は削除する。印の無いファイルには触らない。

同じ番号の採用 ADR が 2 つ以上あれば（番号の打ち間違い）、全部を警告し、ファイル名順で最初を採って exit 1。

終了コード: 0 = 完了（警告があっても）／1 = 同じ番号の採用 ADR がある（書き出しは済ませる）／2 = 引数・入力の誤り（ADR のディレクトリか lessons.md が無い。
何も書かず何も消さない。パスの打ち間違いで既存の出力を全部消さないため。lessons が無ければ空のファイルを渡す）。
標準ライブラリのみ。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

MARK = "adr-to-rules.py が生成"
MAX_LINES = 3
MAX_CHARS = 160
ENFORCEMENT = ("構造", "テスト", "静的検査", "レビューのみ")
# 状態欄の表記ゆれ。ADOPTED は採用として扱う。OTHER は書き出さない既知の状態。どちらでもない値は警告して飛ばす
ADOPTED = {"採用", "採用済み", "accepted"}
OTHER = {"検討中", "却下", "撤回", "提案中", "廃止", "保留", "proposed", "rejected", "deprecated", "superseded", "withdrawn"}
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
PAREN_RE = re.compile(r"[（(][^）)]*[）)]")
FIELD_RE = re.compile(r"^\s*(?:[-*]\s+)?\*{0,2}(?P<k>[^*:：\n（(]+?)\*{0,2}\s*(?:[（(][^）)\n]*[）)])?\s*\*{0,2}\s*[:：]\s*(?P<v>.*)$")
LIST_RE = re.compile(r"^\s*[-*]\s+(?P<v>.*)$")
ADR_NO_RE = re.compile(r"ADR[-_ ]?0*(\d+)", re.I)


# ---------------------------------------------------------------- 読み取り
def fields(lines: list[str]) -> dict[str, list[str] | str]:
    """見出しの欄（状態・適用パス・置換先・強制の区分）を読む。適用パスは続く `- ` の行も集める。"""
    out: dict[str, list[str] | str] = {}
    i = 0
    while i < len(lines):
        m = FIELD_RE.match(lines[i])
        key = m.group("k").strip() if m else ""
        if key in ("状態", "ステータス") and "状態" not in out:
            out["状態"] = m.group("v").strip()
        elif key in ("置換先", "強制の区分") and key not in out:
            out[key] = m.group("v").strip()
        elif key == "適用パス" and "適用パス" not in out:
            globs = split_globs(m.group("v"))
            j = i + 1
            while j < len(lines) and (LIST_RE.match(lines[j]) or (not lines[j].strip() and not globs)):
                lm = LIST_RE.match(lines[j])
                if lm:
                    globs += split_globs(lm.group("v"))
                j += 1
            out["適用パス"] = globs
            i = j
            continue
        i += 1
    return out


def split_outside_braces(value: str) -> list[str]:
    """カンマ（, 、）で分ける。`{…}` の中のカンマは区切りにしない（`src/**/*.{ts,tsx}` は 1 つ）。"""
    parts, cur, depth = [], "", 0
    for ch in value:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        if ch in ",、" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return parts + [cur]


def split_globs(value: str) -> list[str]:
    """適用パスの値を glob の並びにする。行は改行と `;` で分け、`- ` の箇条書き記号は落とす。
    バッククォートで囲んだ部分があればそれだけを glob とし、無ければ最初の空白・`（`・`(` までを取る
    （後ろの注記を paths に入れない）。カンマは `{…}` の外だけ区切り。空・記入例（<…>・例:）は捨てる。"""
    out = []
    for piece in re.split(r"[\n;]", value):
        piece = re.sub(r"^\s*[-*]\s+", "", piece).strip()
        if not piece:
            continue
        ticks = re.findall(r"`([^`]+)`", piece)
        if ticks:
            cands = [c for t in ticks for c in split_outside_braces(t)]
        else:
            cands = [re.split(r"[\s（(]", c.strip(), maxsplit=1)[0] for c in split_outside_braces(piece)]
        for tok in cands:
            tok = tok.strip().strip("'\"")
            if not tok or "<" in tok or ">" in tok or tok.startswith("例") or tok in ("なし", "-"):
                continue
            out.append(tok)
    return out


def plain(value: str) -> str:
    """括弧の注記と強調記号を外した値（状態・強制の区分の判定用）。"""
    return PAREN_RE.sub("", value).replace("*", "").strip()


def sections(text: str) -> dict[str, list[str]]:
    """`## ` 見出し → 本文の行。"""
    out: dict[str, list[str]] = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return out


def summarize(lines: list[str]) -> list[str]:
    """節の本文を 3 行までの要旨にする（表は 1 行 1 案。見出し行・区切り行・「例:」の行は捨てる）。"""
    rows: list[str] = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("|"):
            if re.fullmatch(r"\|?[\s:|-]+\|?", s):
                continue
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if re.fullmatch(r"\|[\s:|-]+\|?", nxt) and "-" in nxt:
                continue                                        # 表の見出し行
            cells = [c.strip() for c in s.strip("|").split("|")]
            cells = [c for c in cells if c]
            if not cells or cells[0].startswith("例"):
                continue
            s = "- " + "：".join(cells)
        elif s.startswith("例"):
            continue
        s = s.replace("**", "")
        rows.append(s if len(s) <= MAX_CHARS else s[:MAX_CHARS] + "…")
    if len(rows) > MAX_LINES:
        rows = rows[:MAX_LINES]
        rows[-1] += " …"
    return rows


def pick(secs: dict[str, list[str]], prefix: str) -> list[str]:
    for name, body in secs.items():
        if name.startswith(prefix):
            return summarize(body)
    return []


def ascii_slug(s: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


# ---------------------------------------------------------------- 組み立て
def render(paths: list[str], source: str, title: str, lead: str, parts: list[tuple[str, list[str]]]) -> str:
    out = ["---", "paths:"]
    out += ['  - "' + p.replace("\\", "\\\\").replace('"', '\\"') + '"' for p in paths]
    out += ["---", f"<!-- {MARK}（元: {source}）。手で直さず、元を直して再実行する -->", f"# {title}", "", lead]
    for head, rows in parts:
        out += ["", f"## {head}"] + (rows or ["（記載なし）"])
    return "\n".join(out) + "\n"


def rel(p: Path) -> str:
    try:
        return os.path.relpath(p)
    except ValueError:
        return str(p)


def status_of(fl: dict) -> str:
    """状態欄の値（括弧の注記・強調を外し、英字は小文字）。"""
    return plain(str(fl.get("状態", ""))).lower()


def read_adrs(adr_dir: Path, warn) -> tuple[dict[str, str], bool]:
    """採用 ADR → ({slug: 内容}, 同じ番号の採用 ADR が複数あったか)。"""
    parsed = []
    for f in sorted(adr_dir.glob("*.md")):
        text = COMMENT_RE.sub("", f.read_text(encoding="utf-8", errors="replace"))
        lines = text.splitlines()
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), f.stem)
        m = ADR_NO_RE.search(title) or ADR_NO_RE.search(f.stem)
        no = int(m.group(1)) if m else None
        head = lines[: next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))]
        fl = fields(head)
        st = status_of(fl)
        if "状態" not in fl:
            warn(f"{rel(f)}: 状態の欄が無い（書き出さない）")
        elif st not in ADOPTED and st not in OTHER:
            warn(f"{rel(f)}: 状態「{fl['状態']}」を読めない（採用・採用済み・Accepted だけを書き出す。書き出さない）")
        if st in ADOPTED:
            parsed.append((f, text, title, no, fl))
    # 同じ番号の採用 ADR が複数（番号の打ち間違い）: 両方を警告し、ファイル名順で最初を採る
    dup = False
    by_no: dict[int, list[Path]] = {}
    for f, _t, _ti, no, _fl in parsed:
        if no is not None:
            by_no.setdefault(no, []).append(f)
    for no, files in sorted(by_no.items()):
        if len(files) > 1:
            dup = True
            for f in files:
                warn(f"{rel(f)}: ADR-{no:03d} の採用が {len(files)} つある（{'・'.join(x.name for x in files)}）。"
                     f"ファイル名順で最初の {files[0].name} を採る。番号を直す")
    parsed = [p for p in parsed if p[3] is None or by_no[p[3]][0] == p[0]]
    replaced: dict[int, str] = {}
    for f, _t, _ti, no, fl in parsed:
        for n in ADR_NO_RE.findall(plain(str(fl.get("置換先", "")))):
            replaced[int(n)] = f"ADR-{no:03d}" if no is not None else f.name
    out: dict[str, str] = {}
    for f, text, title, no, fl in parsed:
        if no is not None and no in replaced and replaced[no] != f"ADR-{no:03d}":
            warn(f"{rel(f)}: {replaced[no]} に置き換えられている（書き出さない。状態を「撤回」に直す）")
            continue
        paths = fl.get("適用パス") or []
        if not paths:
            warn(f"{rel(f)}: 採用だが適用パスが無い（書き出さない。paths の無い rules は常時読み込みになる）")
            continue
        secs = sections(text)
        enf = plain(str(fl.get("強制の区分", "")))
        enf = enf if enf in ENFORCEMENT else "未記入"
        parts = [("決定", pick(secs, "決定")), ("捨てた案", pick(secs, "捨てた案")), ("撤回条件", pick(secs, "撤回条件"))]
        if not parts[2][1]:
            warn(f"{rel(f)}: 撤回条件が空（ひな形は空欄で承認しない決まり）")
        sup = [f"ADR-{int(n):03d}" for n in ADR_NO_RE.findall(plain(str(fl.get("置換先", ""))))]
        lead = ("この領域のファイルを扱う前に守る。捨てた案を再提案しない。撤回条件に当たる観測があれば、変える前に保守者に示す。"
                + (f"置き換えた決定: {'・'.join(sup)}（こちらが優先）。" if sup else ""))
        slug = f"adr-{no:03d}" if no is not None else (ascii_slug(f.stem) or hashlib.sha1(f.name.encode()).hexdigest()[:8])
        out[slug] = render(list(paths), rel(f), f"決定 {title}（強制の区分: {enf}）", lead, parts)
    return out, dup


def lesson_blocks(body: list[str]) -> dict[str, list[str]]:
    """lessons の項目の本文 → Keep / Problem / Try の行。適用パスの欄とその下の glob の行は入れない。"""
    blocks: dict[str, list[str]] = {"Keep": [], "Problem": [], "Try": []}
    cur = None
    for line in body:
        s = line.strip()
        m = re.match(r"^\*\*(Keep|Problem|Try)\*\*", s)
        if m:
            cur = m.group(1)
            continue
        fm = FIELD_RE.match(s)
        if fm and fm.group("k").strip() == "適用パス":
            cur = None
            continue
        if cur and s and s not in ("-", "- [ ]"):
            blocks[cur].append(line)
    return blocks


def read_lessons(lessons: Path) -> dict[str, str]:
    """適用パスのある lessons の項目 → {slug: 内容}。"""
    text = COMMENT_RE.sub("", lessons.read_text(encoding="utf-8", errors="replace"))
    out: dict[str, str] = {}
    for head, body in sections(text).items():
        fl = fields(body)
        paths = fl.get("適用パス") or []
        if not paths:
            continue
        m = re.match(r"(\d{4}-\d{2}-\d{2})\s*(.*)", head)
        date, rest = (m.group(1), m.group(2)) if m else ("", head)
        tail = ascii_slug(rest) or hashlib.sha1(head.encode("utf-8")).hexdigest()[:8]
        slug = base = "lesson-" + (f"{date}-{tail}" if date else tail)
        n = 2
        while slug in out:
            slug, n = f"{base}-{n}", n + 1
        blocks = lesson_blocks(body)
        parts = [(label, summarize(blocks[label])) for label in ("Keep", "Problem", "Try")]
        lead = "この領域のファイルを扱うときに、同じつまずきを繰り返さない（Problem）・次に試すこと（Try）を先に当てる。"
        out[slug] = render(list(paths), rel(lessons), f"学び {head}", lead, parts)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="採用 ADR と適用パスのある lessons を paths 付き rules に書き出す")
    ap.add_argument("adr_dir")
    ap.add_argument("lessons")
    ap.add_argument("--out", required=True, help="rules のディレクトリ（例: .claude/rules）")
    a = ap.parse_args(argv)
    adr_dir, lessons, out_dir = Path(a.adr_dir), Path(a.lessons), Path(a.out)
    if not adr_dir.is_dir():
        print(f"❌ ADR のディレクトリが無い: {adr_dir}（何も書かず何も消さない）", file=sys.stderr)
        return 2
    if not lessons.is_file():
        print(f"❌ lessons.md が無い: {lessons}（何も書かず何も消さない。lessons が無ければ空のファイルを渡す）", file=sys.stderr)
        return 2
    warns: list[str] = []
    docs, dup = read_adrs(adr_dir, warns.append)
    for slug, body in read_lessons(lessons).items():
        docs[slug if slug not in docs else slug + "-lesson"] = body
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for slug, body in sorted(docs.items()):
        f = out_dir / f"decisions-{slug}.md"
        if not f.is_file() or f.read_text(encoding="utf-8", errors="replace") != body:
            f.write_text(body, encoding="utf-8")
        written.append(f.name)
    removed = []
    for f in sorted(out_dir.glob("decisions-*.md")):
        if f.name in written:
            continue
        try:
            head = "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[:15])
        except OSError:
            continue
        if MARK in head:
            f.unlink()
            removed.append(f.name)
    for w in warns:
        print(f"⚠ {w}", file=sys.stderr)
    print(f"書き出し {len(written)} 件: {', '.join(written) or 'なし'}")
    print(f"削除 {len(removed)} 件: {', '.join(removed) or 'なし'}（採用でなくなった・適用パスを消した・置換された決定）")
    return 1 if dup else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
