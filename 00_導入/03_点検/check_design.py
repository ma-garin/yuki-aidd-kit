#!/usr/bin/env python3
"""check_design.py — デザイン出荷物と画面ファイルの「直値禁止」をリポジトリ実体で機械判定する。

02_共通/ひな形/design-system.md の再現チェックリストは「CSS に直値が残っていない」「アイコンは同梱で外部 CDN を
読まない」「alert() を使わない」を要求していたが、判定する手段が無かった（06_保守者向け/01_内部仕様/12-design-framework.md DS-4）。
本スクリプトは次を検査する。NG>0 で exit 1、対象ファイルなしは exit 0。

  1. 直値        色（#hex / rgb() / hsl()）はどこでも NG。px は padding / margin / gap / border-radius /
                 font-size / line-height に限り NG（幅・高さ・ブレークポイントは対象外）。
                 除外: 3px 以下のヘアライン、var(--x, フォールバック) の中、行内に token-exempt コメント、tokens.css 自身、
                 カスタムプロパティの定義（`--x: 値;`。単一 HTML に tokens.css を貼った箇所や自ファイルの変数定義）
  2. 未定義トークン var(--x) が tokens.css にも自ファイルにも定義されていない
  3. 未使用トークン tokens.css で定義されているが対象ファイルのどこからも参照されない（WARN）
  4. 外部 CDN    <link>/<script>/@import/url() が http(s):// を読む（閉じたネットワークで欠ける。icons.js 同梱の理由）
  5. alert()     alert( / confirm( / prompt( の直接使用（Feedback.confirm() は対象外）
  6. tokens.css  .html が tokens.css を読み込んでいない（<link> か、<style> 内に --color-primary: の定義）

出力は3層（結論 → 種別ごと → 全件は check-design-report.md）。

使い方: python3 00_導入/03_点検/check_design.py [--root DIR] [--tokens FILE] [-o REPORT] [PATH ...]
  PATH 省略時は 02_共通/ひな形/ui templates/components。ディレクトリは .css / .html / .js を再帰的に集める
  （.claude/ .git/ node_modules/ は除外。配布先で `.` を渡してもキットの雛形を検査対象にしない）。
  --tokens 省略時は 02_共通/ひな形/tokens.css → .claude/templates/tokens.css の順に探す（キット本体と配布先の両方で動く）。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_TARGETS = ("02_共通/ひな形/ui", "02_共通/ひな形/components")
TOKENS_CANDIDATES = ("02_共通/ひな形/tokens.css", ".claude/templates/tokens.css")
SKIP_DIRS = {".claude", ".git", "node_modules", "dist", "build", ".venv", "__pycache__"}
EXTS = (".css", ".html", ".js")
HAIRLINE_MAX_PX = 3
PX_PROPS = ("padding", "margin", "gap", "border-radius", "font-size", "line-height")

COLOR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(")
PX_PROP_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in PX_PROPS) + r")(?:-[a-z]+)*\s*:\s*([^;{}]*)", re.I)
PX_VAL_RE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)px\b")
VAR_REF_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
VAR_DEF_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
VAR_FALLBACK_RE = re.compile(r"var\(\s*--[A-Za-z0-9_-]+\s*,[^()]*(?:\([^()]*\)[^()]*)*\)")
CUSTOM_PROP_DECL_RE = re.compile(r"(?<![\w-])--[A-Za-z0-9_-]+\s*:[^;{}]*")   # --x: 値（定義。値の置き場所なので直値検査から外す）
CDN_RE = re.compile(r"""(?:<link[^>]+href|<script[^>]+src|@import\s+(?:url\()?|url\()\s*=?\s*["']?\s*(https?://[^"'\s)>]+)""", re.I)
DIALOG_RE = re.compile(r"(?<![\w.$])(?:window\.)?(alert|confirm|prompt)\s*\(")
STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
JS_COMMENT_RE = re.compile(r"/\*.*?\*/|(?<![:\\])//[^\n]*", re.S)
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


class Result:
    def __init__(self) -> None:
        self.ng: list[tuple[str, str, str]] = []
        self.warn: list[tuple[str, str, str]] = []

    def add(self, is_ng: bool, kind: str, target: str, detail: str) -> None:
        (self.ng if is_ng else self.warn).append((kind, target, detail))


def collect(root: Path, targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        p = (root / t) if not Path(t).is_absolute() else Path(t)
        if p.is_dir():
            out += sorted(f for f in p.rglob("*") if f.is_file() and f.suffix in EXTS
                          and not (set(f.relative_to(p).parts[:-1]) & SKIP_DIRS))
        elif p.is_file():
            out.append(p)
    return out


def rel(root: Path, f: Path) -> str:
    try:
        return f.relative_to(root).as_posix()
    except ValueError:
        return f.as_posix()


def line_no(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def blank_comments(text: str, css: bool) -> str:
    """コメントを同じ長さの空白に置き換える（行番号を保つ）。ただし token-exempt の判定は元テキストで行う。"""
    pat = CSS_COMMENT_RE if css else JS_COMMENT_RE
    return pat.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def blank_fallbacks(text: str) -> str:
    text = VAR_FALLBACK_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    return CUSTOM_PROP_DECL_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def css_segments(f: Path, text: str) -> list[tuple[str, int]]:
    """直値検査にかける CSS 相当のテキストと、その開始行を返す。"""
    if f.suffix == ".css":
        return [(text, 1)]
    if f.suffix == ".html":
        return [(m.group(1), line_no(text, m.start(1))) for m in STYLE_RE.finditer(text)]
    return [(text, 1)]   # .js: 自己注入 CSS（テンプレート文字列）を含めて全文を見る


def check_literal_values(root: Path, f: Path, text: str, r: Result) -> None:
    src_lines = text.split("\n")
    for seg, start in css_segments(f, text):
        seg = blank_fallbacks(blank_comments(seg, css=f.suffix != ".js"))
        for i, line in enumerate(seg.split("\n")):
            ln = start + i
            if "token-exempt" in src_lines[ln - 1]:
                continue
            for m in COLOR_RE.finditer(line):
                # JS では '#id' セレクタや 'href="#"' があるので、色に見える 3/6/8 桁の hex だけ拾う
                tok = m.group(0)
                if tok.startswith("#") and not re.fullmatch(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})", tok):
                    continue
                if tok.startswith("#") and f.suffix != ".css" and re.search(r"(?:getElementById|querySelector|href=|\bid=)\s*\(?\s*['\"]?" + re.escape(tok), line):
                    continue
                r.add(True, "直値", f"{rel(root, f)}:{ln}", f"色の直値 `{tok}` → tokens.css の変数に寄せる")
            for pm in PX_PROP_RE.finditer(line):
                for vm in PX_VAL_RE.finditer(pm.group(1)):
                    if float(vm.group(1)) <= HAIRLINE_MAX_PX:
                        continue
                    r.add(True, "直値", f"{rel(root, f)}:{ln}",
                          f"`{pm.group(0).split(':')[0].strip()}` に px 直値 `{vm.group(0)}` → var(--space-*/--text-*/--radius-*)")


def check_tokens(root: Path, files: list[Path], texts: dict[Path, str], tokens_file: Path, r: Result) -> None:
    defined = set(VAR_DEF_RE.findall(tokens_file.read_text(encoding="utf-8"))) if tokens_file.is_file() else set()
    if not defined:
        r.add(True, "tokens", rel(root, tokens_file), "tokens.css が無いか、変数定義が見つからない")
    used: set[str] = set()
    for f in files:
        if f.resolve() == tokens_file.resolve():
            continue
        text = texts[f]
        local = set(VAR_DEF_RE.findall(text))
        for m in VAR_REF_RE.finditer(text):
            name = m.group(1)
            used.add(name)
            if name not in defined and name not in local:
                r.add(True, "未定義トークン", f"{rel(root, f)}:{line_no(text, m.start())}", f"`var({name})` が tokens.css に無い")
    # tokens.css 内での参照（例: --color-primary-light: var(--color-primary)）も使用に数える
    if tokens_file.is_file():
        used |= set(VAR_REF_RE.findall(tokens_file.read_text(encoding="utf-8")))
    for name in sorted(defined - used):
        r.add(False, "未使用トークン", rel(root, tokens_file), f"`{name}` は対象ファイルのどこからも参照されていない")


def check_cdn(root: Path, f: Path, text: str, r: Result) -> None:
    for m in CDN_RE.finditer(blank_comments(text, css=f.suffix == ".css")):
        r.add(True, "外部CDN", f"{rel(root, f)}:{line_no(text, m.start())}", f"`{m.group(1)}` を読み込んでいる（同梱する）")


def check_dialogs(root: Path, f: Path, text: str, r: Result) -> None:
    segs = [(m.group(1), line_no(text, m.start(1))) for m in SCRIPT_RE.finditer(text)] if f.suffix == ".html" else ([(text, 1)] if f.suffix == ".js" else [])
    for seg, start in segs:
        seg = blank_comments(seg, css=False)
        for m in DIALOG_RE.finditer(seg):
            if re.search(r"function\s+$", seg[:m.start()]):
                continue   # 関数定義（feedback.js 自身の confirm(options) など）は呼び出しではない
            line = seg.split("\n")[line_no(seg, m.start()) - 1]
            if re.match(r"\s*(?:async\s+)?(?:alert|confirm|prompt)\s*\(", line) and line.rstrip().endswith("{"):
                continue   # メソッド定義
            r.add(True, "alert()", f"{rel(root, f)}:{start + line_no(seg, m.start()) - 1}",
                  f"`{m.group(1)}()` の直接使用 → feedback.js の Feedback.error / Feedback.confirm を使う")


def check_tokens_loaded(root: Path, f: Path, text: str, r: Result) -> None:
    if f.suffix != ".html":
        return
    if re.search(r"""<link[^>]+href\s*=\s*["'][^"']*tokens\.css""", text, re.I):
        return
    if any("--color-primary:" in s for s, _ in css_segments(f, text)):
        return
    r.add(True, "tokens.css未読込", rel(root, f), "tokens.css の <link> も <style> 内のトークン定義も無い")


def write_report(path: Path, root: Path, files: list[Path], r: Result) -> None:
    lines = ["# デザイン検査レポート", "", f"- 対象: {len(files)} ファイル（`{root}`）", f"- NG: {len(r.ng)} 件 ／ 警告: {len(r.warn)} 件",
             "- 規約: `02_共通/ひな形/design-system.md` 再現チェックリスト ／ `skills/design-system/SKILL.md`「トークン運用の規律」", "", "## NG 一覧", ""]
    lines += (["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.ng]) if r.ng else ["なし。"]
    lines += ["", "## 警告", ""]
    lines += (["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.warn]) if r.warn else ["なし。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="デザイン出荷物の直値・トークン・CDN・alert() 検査")
    ap.add_argument("paths", nargs="*", help="検査対象（ファイルまたはディレクトリ）。省略時は 02_共通/ひな形/ui 02_共通/ひな形/components")
    ap.add_argument("--root", default=".")
    ap.add_argument("--tokens", default=None, help="トークン定義ファイル（root 相対）。省略時は 02_共通/ひな形/tokens.css → .claude/templates/tokens.css")
    ap.add_argument("-o", "--report", default="check-design-report.md")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.tokens:
        tokens_file = Path(a.tokens) if Path(a.tokens).is_absolute() else root / a.tokens
    else:
        tokens_file = next((root / c for c in TOKENS_CANDIDATES if (root / c).is_file()), root / TOKENS_CANDIDATES[0])
    files = collect(root, a.paths or list(DEFAULT_TARGETS))
    if tokens_file.is_file() and tokens_file not in files:
        files.append(tokens_file)   # 未使用トークン検査のため常に読む（直値検査からは除外）
    print(f"=== デザイン検査: {root} ===")
    if not [f for f in files if f.resolve() != tokens_file.resolve()]:
        print("対象ファイルなし（.css / .html / .js が見つからない）。exit 0")
        return 0

    r = Result()
    texts = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}
    for f in files:
        if f.resolve() == tokens_file.resolve():
            continue
        check_literal_values(root, f, texts[f], r)
        check_cdn(root, f, texts[f], r)
        check_dialogs(root, f, texts[f], r)
        check_tokens_loaded(root, f, texts[f], r)
    check_tokens(root, files, texts, tokens_file, r)

    report = Path(a.report)
    if not report.is_absolute():
        report = root / report
    write_report(report, root, files, r)

    kinds: dict[str, int] = {}
    for k, _, _ in r.ng:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"対象: {len(files) - (1 if tokens_file.is_file() else 0)} ファイル")
    if r.ng:
        print(f"❌ NG={len(r.ng)}")
        for k, n in kinds.items():
            print(f"  - {k}: {n} 件")
        print("  例（先頭5件）:")
        for k, t, d in r.ng[:5]:
            print(f"    {k}: {t} — {d}")
    else:
        print("✅ NG=0")
    if r.warn:
        print(f"⚠ 警告 {len(r.warn)} 件（未使用トークン等。詳細はレポート）")
    print(f"詳細: {report}")
    return 1 if r.ng else 0


if __name__ == "__main__":
    sys.exit(main())
