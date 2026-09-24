#!/usr/bin/env python3
"""check_design.py — デザイン出荷物と画面ファイルの「直値禁止」をリポジトリ実体で機械判定する。

02_共通/ひな形/design-system.md の再現チェックリストは「CSS に直値が残っていない」「アイコンは同梱で外部 CDN を
読まない」「alert() を使わない」を要求していたが、判定する手段が無かった（06_保守者向け/01_内部仕様/12_設計の枠組み.md DS-4）。
本スクリプトは次を検査する。NG>0 で exit 1、対象ファイルなしは exit 0（--baseline 使用時は「新規 NG」だけで判定）。

規則 ID 一覧（出力は `<ID> <file>:<line> 実測=<値> 期待=<値> 根拠=<句>` に統一）:
  D01 直値            色（#hex / rgb() / hsl()）はどこでも。px は padding/margin/gap/border-radius/
                      font-size/line-height に限る。
  D02 未定義トークン   var(--x) が tokens.css にも自ファイルにも無い。
  D03 未使用トークン   tokens.css で定義されているが対象のどこからも参照されない（WARN）。
  D04 外部CDN          <link>/<script>/@import/url() が http(s):// を読む。
  D05 alert()          alert(/confirm(/prompt( の直接使用（Feedback.confirm() は対象外）。
  D06 tokens.css未読込 .html が tokens.css を読み込んでいない。
  D07 フォーカス消去   outline: none/0 があるのに :focus-visible の対が無い。
  D08 拡大禁止         viewport の user-scalable=no / maximum-scale=1。
  D09 transition:all   意図しないプロパティまで巻き込む。
  D10 img寸法欠落      <img> に width/height が無い（属性でも style でも良い）。
  D11 非semantic onclick <div>/<span> の onclick（<button> 等に置き換える）。
  D12 色名             color 系プロパティに CSS 色名（white/black/red 等）を直書き。
  D13 色関数直値       oklch()/lab()/lch()/color-mix() の直値。
  D14 box-shadow直値   box-shadow に var() でない色（hex/rgb/hsl/色名）を含む。
  D15 z-index直値      z-index の数値直値（tokens.css の --z-* を使う）。
  D16 時間直値         transition/animation の時間（s/ms）の直値（var(--motion-*) を使う）。
  D17 100vh            100vh 単独（100dvh か min-height との併用を期待）。
  D18 入力欄font-size  input/select/textarea の font-size が 16px 未満（WARN。モバイルの自動拡大を誘発）。
  D19 hover偏重        :hover だけの規則（:focus-visible の対が無い。WARN。誤検知が多いため）。

出力は3層（結論 → 種別ごと → 全件は check-design-report.md）。--json で同じ内容を JSON で標準出力に出す。

使い方: python3 00_導入/03_点検/check_design.py [--root DIR] [--tokens FILE] [-o REPORT]
         [--baseline FILE [--baseline-write]] [--json] [PATH ...]
  PATH 省略時は 02_共通/ひな形/ui templates/components。ディレクトリは .css / .html / .js を再帰的に集める
  （.claude/ .git/ node_modules/ は除外。配布先で `.` を渡してもキットの雛形を検査対象にしない）。
  --tokens 省略時は 02_共通/ひな形/tokens.css → .claude/templates/tokens.css の順に探す（キット本体と配布先の両方で動く）。
  --baseline FILE  既知の NG を `規則ID\\t相対パス\\t正規化した行` で記録したファイル。指定すると、そこに載っている
                   NG は「既知」として数え、新しい NG だけを exit 1 にする（未指定時は全 NG が対象＝従来どおり）。
  --baseline-write 現在の NG 一覧で --baseline のファイルを書く。**件数が前回より増える更新は拒否**（exit 1・書かない）。
  基準線の書式と規律は 02_共通/ツール/baseline.py（security-scan.sh と共用）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 基準線の読み書きは security-scan と共用の部品（02_共通/ツール/baseline.py。B15）。キット内と、隣に置いた場合の両方で探す
for _d in (Path(__file__).resolve().parent, Path(__file__).resolve().parents[2] / "02_共通" / "ツール"):
    if (_d / "baseline.py").is_file() and str(_d) not in sys.path:
        sys.path.insert(0, str(_d))
import baseline  # noqa: E402
from baseline import normalize_line  # noqa: E402,F401  （Result が使う。従来どおりこのモジュールからも参照できる）

DEFAULT_TARGETS = ("02_共通/ひな形/ui", "02_共通/ひな形/components")
TOKENS_CANDIDATES = ("02_共通/ひな形/tokens.css", ".claude/templates/tokens.css")
SKIP_DIRS = {".claude", ".git", "node_modules", "dist", "build", ".venv", "__pycache__"}
EXTS = (".css", ".html", ".js")
HAIRLINE_MAX_PX = 3
PX_PROPS = ("padding", "margin", "gap", "border-radius", "font-size", "line-height")
NAMED_COLORS = ("white", "black", "red", "blue", "green", "yellow", "gray", "grey", "orange",
                "purple", "pink", "brown", "cyan", "magenta", "lime", "navy", "teal", "maroon",
                "olive", "silver", "gold")
COLOR_PROPS = ("color", "background", "background-color", "border-color", "outline-color", "fill", "stroke")
SMALL_FONT_TOKENS = ("--text-xs", "--text-sm", "--text-base")

RULES: dict[str, str] = {
    "D01": "直値", "D02": "未定義トークン", "D03": "未使用トークン", "D04": "外部CDN", "D05": "alert()",
    "D06": "tokens.css未読込", "D07": "フォーカス消去", "D08": "拡大禁止", "D09": "transition:all",
    "D10": "img寸法欠落", "D11": "非semantic onclick", "D12": "色名", "D13": "色関数直値",
    "D14": "box-shadow直値", "D15": "z-index直値", "D16": "時間直値", "D17": "100vh",
    "D18": "入力欄font-size", "D19": "hover偏重",
}

COLOR_RE = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\(")
COLOR_FUNC_RE = re.compile(r"\b(?:oklch|lab|lch|color-mix)\(", re.I)
NAMED_COLOR_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in COLOR_PROPS) + r")\s*:\s*(" +
    "|".join(NAMED_COLORS) + r")\b", re.I)
NAMED_COLOR_WORD_RE = re.compile(r"\b(?:" + "|".join(NAMED_COLORS) + r")\b", re.I)
BOX_SHADOW_RE = re.compile(r"\bbox-shadow\s*:\s*([^;{}]+)", re.I)
Z_INDEX_RE = re.compile(r"\bz-index\s*:\s*(-?\d+)\b", re.I)
TRANSITION_PROP_RE = re.compile(r"\b(transition|animation)(?:-duration|-delay)?\s*:\s*([^;{}]+)", re.I)
TIME_LITERAL_RE = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?m?s\b", re.I)
VH100_RE = re.compile(r"\b100vh\b")
RULE_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
INPUT_SELECTOR_RE = re.compile(r"\b(?:input|select|textarea)\b", re.I)
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*([^;]+)", re.I)
PX_PROP_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(p) for p in PX_PROPS) + r")(?:-[a-z]+)*\s*:\s*([^;{}]*)", re.I)
PX_VAL_RE = re.compile(r"(?<![\w.-])(\d+(?:\.\d+)?)px\b")
VAR_REF_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
VAR_DEF_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:")
VAR_FALLBACK_RE = re.compile(r"var\(\s*--[A-Za-z0-9_-]+\s*,[^()]*(?:\([^()]*\)[^()]*)*\)")
ANY_VAR_RE = re.compile(r"var\(\s*--[A-Za-z0-9_-]+(?:\s*,[^()]*(?:\([^()]*\)[^()]*)*)?\)")
CUSTOM_PROP_DECL_RE = re.compile(r"(?<![\w-])--[A-Za-z0-9_-]+\s*:[^;{}]*")   # --x: 値（定義。値の置き場所なので直値検査から外す）
CDN_RE = re.compile(r"""(?:<link[^>]+href|<script[^>]+src|@import\s+(?:url\()?|url\()\s*=?\s*["']?\s*(https?://[^"'\s)>]+)""", re.I)
DIALOG_RE = re.compile(r"(?<![\w.$])(?:window\.)?(alert|confirm|prompt)\s*\(")
OUTLINE_NONE_RE = re.compile(r"outline\s*:\s*(?:none|0(?:px)?)\b", re.I)
FOCUS_VISIBLE_RE = re.compile(r":focus-visible\b")
VIEWPORT_META_RE = re.compile(r"""<meta[^>]+name\s*=\s*["']viewport["'][^>]*>""", re.I)
VIEWPORT_CONTENT_RE = re.compile(r"""content\s*=\s*["']([^"']*)["']""", re.I)
VIEWPORT_LOCK_RE = re.compile(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\.0+)?\b", re.I)
TRANSITION_ALL_RE = re.compile(r"transition\s*:\s*all\b", re.I)
IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.I)
IMG_WIDTH_RE = re.compile(r"(?<![\w-])width\s*[:=]", re.I)
IMG_HEIGHT_RE = re.compile(r"(?<![\w-])height\s*[:=]", re.I)
NONSEMANTIC_ONCLICK_RE = re.compile(r"<(div|span)\b[^>]*\bonclick\s*=", re.I)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
SCRIPT_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)
JS_COMMENT_RE = re.compile(r"/\*.*?\*/|(?<![:\\])//[^\n]*", re.S)
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
# 単語境界必須（\w は Unicode 対応なので直後が日本語でも境界にならない）。
# 「token-exemptではない」のような部分一致でのバイパスを防ぐ（B-24-2）。
TOKEN_EXEMPT_RE = re.compile(r"\btoken-exempt\b")
REDUCED_MOTION_RE = re.compile(
    r"@media[^{]*prefers-reduced-motion:\s*reduce[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", re.I | re.S)


class Finding:
    __slots__ = ("rule", "file", "line", "actual", "expected", "reason")

    def __init__(self, rule: str, file: str, line: int, actual: str, expected: str, reason: str) -> None:
        self.rule, self.file, self.line = rule, file, line
        self.actual, self.expected, self.reason = actual, expected, reason

    @property
    def kind(self) -> str:
        return RULES[self.rule]

    @property
    def target(self) -> str:
        return f"{self.file}:{self.line}"

    @property
    def line_text(self) -> str:
        return f"{self.rule} {self.target} 実測={self.actual} 期待={self.expected} 根拠={self.reason}"

    def to_dict(self, is_ng: bool) -> dict:
        return {"id": self.rule, "kind": self.kind, "file": self.file, "line": self.line,
                "actual": self.actual, "expected": self.expected, "reason": self.reason,
                "severity": "NG" if is_ng else "WARN"}


class Result:
    def __init__(self) -> None:
        self.ng: list[Finding] = []
        self.warn: list[Finding] = []
        self._raw: dict[int, str] = {}   # id(finding) -> 正規化した行（baseline 用）

    def add(self, is_ng: bool, rule: str, file: str, line: int, actual: str, expected: str,
            reason: str, raw: str) -> None:
        f = Finding(rule, file, line, actual, expected, reason)
        (self.ng if is_ng else self.warn).append(f)
        self._raw[id(f)] = normalize_line(raw)

    def raw_of(self, f: Finding) -> str:
        return self._raw.get(id(f), "")

    def baseline_key(self, f: Finding) -> tuple[str, str, str]:
        return (f.rule, f.file, self.raw_of(f))


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


def blank_reduced_motion(text: str) -> str:
    """`@media (prefers-reduced-motion: reduce) { ... }` は全体規則で担保済みなので、
    その中の transition-duration: 0s 等は D09/D16 の対象にしない（A19 前提: reduced-motion は検査しない）。"""
    return REDUCED_MOTION_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def blank_html_comments(text: str) -> str:
    """<!-- ... --> を同じ長さの空白に置き換える（行番号を保つ）。コメント内の文字列でルールを誤検知／バイパスしない。"""
    return HTML_COMMENT_RE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def css_segments(f: Path, text: str) -> list[tuple[str, int]]:
    """直値検査にかける CSS 相当のテキストと、その開始行を返す。"""
    if f.suffix == ".css":
        return [(text, 1)]
    if f.suffix == ".html":
        return [(m.group(1), line_no(text, m.start(1))) for m in STYLE_RE.finditer(text)]
    return [(text, 1)]   # .js: 自己注入 CSS（テンプレート文字列）を含めて全文を見る


def raw_line(src_lines: list[str], ln: int) -> str:
    return src_lines[ln - 1] if 0 < ln <= len(src_lines) else ""


def check_literal_values(root: Path, f: Path, text: str, r: Result) -> None:
    src_lines = text.split("\n")
    for seg, start in css_segments(f, text):
        seg = blank_fallbacks(blank_comments(seg, css=f.suffix != ".js"))
        for i, line in enumerate(seg.split("\n")):
            ln = start + i
            if TOKEN_EXEMPT_RE.search(src_lines[ln - 1]):
                continue
            for m in COLOR_RE.finditer(line):
                # JS では '#id' セレクタや 'href="#"' があるので、色に見える 3/6/8 桁の hex だけ拾う
                tok = m.group(0)
                if tok.startswith("#") and not re.fullmatch(r"#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})", tok):
                    continue
                if tok.startswith("#") and f.suffix != ".css" and re.search(r"(?:getElementById|querySelector|href=|\bid=)\s*\(?\s*['\"]?" + re.escape(tok), line):
                    continue
                r.add(True, "D01", rel(root, f), ln, f"`{tok}`", "var(--color-*)", "色の直値", raw_line(src_lines, ln))
            for pm in PX_PROP_RE.finditer(line):
                for vm in PX_VAL_RE.finditer(pm.group(1)):
                    if float(vm.group(1)) <= HAIRLINE_MAX_PX:
                        continue
                    prop = pm.group(0).split(':')[0].strip()
                    r.add(True, "D01", rel(root, f), ln, f"`{vm.group(0)}`",
                          "var(--space-*/--text-*/--radius-*)", f"`{prop}` の px 直値", raw_line(src_lines, ln))


def check_new_ng_rules(root: Path, f: Path, text: str, r: Result) -> None:
    """A19 新規則: 色名・色関数・box-shadow・z-index・transition/animation の時間の直値（D12〜D16）。"""
    src_lines = text.split("\n")
    for seg, start in css_segments(f, text):
        blanked = blank_reduced_motion(blank_fallbacks(blank_comments(seg, css=f.suffix != ".js")))
        for m in NAMED_COLOR_RE.finditer(blanked):
            ln = start + line_no(blanked, m.start(1)) - 1
            if TOKEN_EXEMPT_RE.search(raw_line(src_lines, ln)):
                continue
            r.add(True, "D12", rel(root, f), ln, f"`{m.group(1)}`", "var(--color-*)",
                  "色名の直書き", raw_line(src_lines, ln))
        for m in COLOR_FUNC_RE.finditer(blanked):
            ln = start + line_no(blanked, m.start()) - 1
            if TOKEN_EXEMPT_RE.search(raw_line(src_lines, ln)):
                continue
            r.add(True, "D13", rel(root, f), ln, f"`{m.group(0)}`", "var(--color-*)",
                  "色関数の直値", raw_line(src_lines, ln))
        for m in BOX_SHADOW_RE.finditer(blanked):
            ln = start + line_no(blanked, m.start()) - 1
            if TOKEN_EXEMPT_RE.search(raw_line(src_lines, ln)):
                continue
            leftover = ANY_VAR_RE.sub("", m.group(1))
            if COLOR_RE.search(leftover) or COLOR_FUNC_RE.search(leftover) or NAMED_COLOR_WORD_RE.search(leftover):
                r.add(True, "D14", rel(root, f), ln, f"`box-shadow: {m.group(1).strip()}`",
                      "var(--shadow-sm/md/lg/pop)", "box-shadowの直値", raw_line(src_lines, ln))
        for m in Z_INDEX_RE.finditer(blanked):
            ln = start + line_no(blanked, m.start(1)) - 1
            if TOKEN_EXEMPT_RE.search(raw_line(src_lines, ln)):
                continue
            r.add(True, "D15", rel(root, f), ln, f"`z-index: {m.group(1)}`",
                  "var(--z-base/--z-dropdown/--z-sticky/--z-modal/--z-toast)", "z-indexの数値直値",
                  raw_line(src_lines, ln))
        for m in TRANSITION_PROP_RE.finditer(blanked):
            ln = start + line_no(blanked, m.start(2)) - 1
            if TOKEN_EXEMPT_RE.search(raw_line(src_lines, ln)):
                continue
            leftover = ANY_VAR_RE.sub("", m.group(2))
            tm = TIME_LITERAL_RE.search(leftover)
            if tm:
                r.add(True, "D16", rel(root, f), ln, f"`{tm.group(0)}`", "var(--motion-fast/--motion-normal/--motion-slow)",
                      f"`{m.group(1)}` の時間の直値", raw_line(src_lines, ln))


def check_100vh(root: Path, f: Path, text: str, r: Result) -> None:
    """100vh は出現ごとに判定する（ファイル内のどこかに 100dvh があっても他の箇所の 100vh 単独は見逃さない。B-24-3）。"""
    scan = blank_html_comments(blank_comments(text, css=f.suffix == ".css"))
    src_lines = text.split("\n")
    for m in VH100_RE.finditer(scan):
        ln = line_no(text, m.start())
        line_text = raw_line(src_lines, ln)
        if "min-height" in line_text.lower():
            continue
        if TOKEN_EXEMPT_RE.search(line_text):
            continue
        r.add(True, "D17", rel(root, f), ln, "`100vh`", "100dvh か min-height との併用",
              "100vh単独（モバイルのアドレスバー分ずれる）", line_text)


def check_new_warn_rules(root: Path, f: Path, text: str, r: Result) -> None:
    """A19 新規則: 入力欄の font-size（D18）・:hover 偏重（D19）。いずれも WARN。"""
    src_lines = text.split("\n")
    for seg, start in css_segments(f, text):
        blanked = blank_fallbacks(blank_comments(seg, css=f.suffix != ".js"))
        for bm in RULE_BLOCK_RE.finditer(blanked):
            selector, body = bm.group(1), bm.group(2)
            ln = start + line_no(blanked, bm.start()) - 1

            if INPUT_SELECTOR_RE.search(selector):
                fm = FONT_SIZE_RE.search(body)
                if fm:
                    val = fm.group(1).strip()
                    px = re.fullmatch(r"(\d+(?:\.\d+)?)px", val)
                    small_tok = next((t for t in SMALL_FONT_TOKENS if t in val), None)
                    if (px and float(px.group(1)) < 16) or small_tok:
                        r.add(False, "D18", rel(root, f), ln, f"`{val}`", "16px 以上（var(--text-md) 等）",
                              "入力欄のfont-sizeが16px未満（モバイルで自動拡大を誘発）", raw_line(src_lines, ln))

            if ":hover" in selector and ":focus-visible" not in selector:
                for part in selector.split(","):
                    if ":hover" not in part:
                        continue
                    base = part.split(":hover")[0].strip()
                    if base and re.search(re.escape(base) + r":focus-visible", blanked):
                        continue
                    r.add(False, "D19", rel(root, f), ln, f"`{part.strip()}`", ":focus-visible の対",
                          "hoverだけの規則（キーボード操作で見えない）", raw_line(src_lines, ln))
                    break


def check_tokens(root: Path, files: list[Path], texts: dict[Path, str], tokens_file: Path, r: Result) -> None:
    defined = set(VAR_DEF_RE.findall(tokens_file.read_text(encoding="utf-8"))) if tokens_file.is_file() else set()
    if not defined:
        r.add(True, "D02", rel(root, tokens_file), 1, "`(なし)`", "tokens.css に変数定義",
              "tokens.css が無いか変数定義が見つからない", "")
    used: set[str] = set()
    for f in files:
        if f.resolve() == tokens_file.resolve():
            continue
        text = texts[f]
        src_lines = text.split("\n")
        local = set(VAR_DEF_RE.findall(text))
        for m in VAR_REF_RE.finditer(text):
            name = m.group(1)
            used.add(name)
            if name not in defined and name not in local:
                ln = line_no(text, m.start())
                r.add(True, "D02", rel(root, f), ln, f"`var({name})`", "tokens.css に定義",
                      "未定義トークン", raw_line(src_lines, ln))
    # tokens.css 内での参照（例: --color-primary-light: var(--color-primary)）も使用に数える
    if tokens_file.is_file():
        used |= set(VAR_REF_RE.findall(tokens_file.read_text(encoding="utf-8")))
    for name in sorted(defined - used):
        r.add(False, "D03", rel(root, tokens_file), 1, f"`{name}`", "対象ファイルからの参照",
              "未使用トークン", name)


def check_cdn(root: Path, f: Path, text: str, r: Result) -> None:
    src_lines = text.split("\n")
    for m in CDN_RE.finditer(blank_comments(text, css=f.suffix == ".css")):
        ln = line_no(text, m.start())
        r.add(True, "D04", rel(root, f), ln, f"`{m.group(1)}`", "同梱（ローカル資産）",
              "外部CDNの読み込み", raw_line(src_lines, ln))


def check_dialogs(root: Path, f: Path, text: str, r: Result) -> None:
    src_lines = text.split("\n")
    segs = [(m.group(1), line_no(text, m.start(1))) for m in SCRIPT_RE.finditer(text)] if f.suffix == ".html" else ([(text, 1)] if f.suffix == ".js" else [])
    for seg, start in segs:
        seg = blank_comments(seg, css=False)
        for m in DIALOG_RE.finditer(seg):
            if re.search(r"function\s+$", seg[:m.start()]):
                continue   # 関数定義（feedback.js 自身の confirm(options) など）は呼び出しではない
            line = seg.split("\n")[line_no(seg, m.start()) - 1]
            if re.match(r"\s*(?:async\s+)?(?:alert|confirm|prompt)\s*\(", line) and line.rstrip().endswith("{"):
                continue   # メソッド定義
            ln = start + line_no(seg, m.start()) - 1
            r.add(True, "D05", rel(root, f), ln, f"`{m.group(1)}()`", "Feedback.error / Feedback.confirm",
                  "alert()系の直接使用", raw_line(src_lines, ln))


def check_tokens_loaded(root: Path, f: Path, text: str, r: Result) -> None:
    if f.suffix != ".html":
        return
    if re.search(r"""<link[^>]+href\s*=\s*["'][^"']*tokens\.css""", text, re.I):
        return
    if any("--color-primary:" in s for s, _ in css_segments(f, text)):
        return
    r.add(True, "D06", rel(root, f), 1, "`(link/style 無し)`", "<link href=tokens.css> か <style> 内定義",
          "tokens.css未読込", "")


def check_focus_motion_mobile(root: Path, f: Path, text: str, r: Result) -> None:
    """フォーカス消去・拡大禁止・transition: all・img 寸法欠落・非対話要素の onclick を検査する。

    他の検査（check_cdn / check_dialogs / check_literal_values）と同じく、コメントを空白に置き換えた本文で
    判定する（行番号は変わらないので line_no には元の text をそのまま渡してよい）。コメント内の文字列で
    誤検知したり、コメントを書くだけで検出を回避できたりしないようにする。
    """
    src_lines = text.split("\n")
    scan = blank_reduced_motion(blank_html_comments(blank_comments(text, css=f.suffix == ".css")))

    if not FOCUS_VISIBLE_RE.search(scan):
        for m in OUTLINE_NONE_RE.finditer(scan):
            ln = line_no(text, m.start())
            r.add(True, "D07", rel(root, f), ln, f"`{m.group(0)}`", ":focus-visible の対",
                  "フォーカス消去（キーボード操作で見えない）", raw_line(src_lines, ln))

    for m in TRANSITION_ALL_RE.finditer(scan):
        ln = line_no(text, m.start())
        r.add(True, "D09", rel(root, f), ln, "`transition: all`", "対象プロパティを明示",
              "意図しないプロパティまで巻き込む", raw_line(src_lines, ln))

    if f.suffix != ".html":
        return

    for vm in VIEWPORT_META_RE.finditer(scan):
        cm = VIEWPORT_CONTENT_RE.search(vm.group(0))
        lm = VIEWPORT_LOCK_RE.search(cm.group(1)) if cm else None
        if lm:
            ln = line_no(text, vm.start())
            r.add(True, "D08", rel(root, f), ln, f"`{lm.group(0)}`", "指定を除去",
                  "ピンチズーム禁止", raw_line(src_lines, ln))

    for m in IMG_TAG_RE.finditer(scan):
        tag = m.group(0)
        has_w, has_h = bool(IMG_WIDTH_RE.search(tag)), bool(IMG_HEIGHT_RE.search(tag))
        if not (has_w and has_h):
            missing = "／".join(n for n, ok in (("width", has_w), ("height", has_h)) if not ok)
            ln = line_no(text, m.start())
            r.add(True, "D10", rel(root, f), ln, missing, "width と height（属性/style）",
                  "img寸法欠落（レイアウトシフト）", raw_line(src_lines, ln))

    for m in NONSEMANTIC_ONCLICK_RE.finditer(scan):
        ln = line_no(text, m.start())
        r.add(True, "D11", rel(root, f), ln, f"`<{m.group(1)} onclick=...>`", "<button> 等",
              "非対話要素のonclick（キーボード操作不可）", raw_line(src_lines, ln))


def write_report(path: Path, root: Path, files: list[Path], r: Result, new_ng: list[Finding],
                  baseline_used: bool) -> None:
    lines = ["# デザイン検査レポート", "", f"- 対象: {len(files)} ファイル（`{root}`）",
             f"- NG: {len(r.ng)} 件（新規 {len(new_ng)} 件） ／ 警告: {len(r.warn)} 件" if baseline_used
             else f"- NG: {len(r.ng)} 件 ／ 警告: {len(r.warn)} 件",
             "- 規約: `02_共通/ひな形/design-system.md` 再現チェックリスト ／ `skills/design-system/SKILL.md`「トークン運用の規律」",
             "", "## NG 一覧", ""]
    header = ["| 規則ID | 種別 | 対象 | 実測 | 期待 | 根拠 |", "|---|---|---|---|---|---|"]
    lines += (header + [f"| {x.rule} | {x.kind} | {x.target} | {x.actual} | {x.expected} | {x.reason} |"
                         for x in r.ng]) if r.ng else ["なし。"]
    lines += ["", "## 警告", ""]
    lines += (header + [f"| {x.rule} | {x.kind} | {x.target} | {x.actual} | {x.expected} | {x.reason} |"
                         for x in r.warn]) if r.warn else ["なし。"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> set[tuple[str, str, str]]:
    return baseline.load_keys(path)


def save_baseline(path: Path, entries: set[tuple[str, str, str]]) -> None:
    baseline.save(path, entries, baseline.load(path))   # 既存行に理由・期限の列があれば引き継ぐ


def main() -> int:
    ap = argparse.ArgumentParser(description="デザイン出荷物の直値・トークン・CDN・alert() 検査")
    ap.add_argument("paths", nargs="*", help="検査対象（ファイルまたはディレクトリ）。省略時は 02_共通/ひな形/ui 02_共通/ひな形/components")
    ap.add_argument("--root", default=".")
    ap.add_argument("--tokens", default=None, help="トークン定義ファイル（root 相対）。省略時は 02_共通/ひな形/tokens.css → .claude/templates/tokens.css")
    ap.add_argument("-o", "--report", default="check-design-report.md")
    ap.add_argument("--baseline", default=None, help="既知の NG を記録したファイル。指定すると新規 NG だけを exit 1 にする")
    ap.add_argument("--baseline-write", action="store_true", help="現在の NG で --baseline のファイルを書く（件数が増える更新は拒否）")
    ap.add_argument("--json", action="store_true", help="結果を JSON で標準出力に出す（このときは他の文言を出さない）")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.tokens:
        tokens_file = Path(a.tokens) if Path(a.tokens).is_absolute() else root / a.tokens
    else:
        tokens_file = next((root / c for c in TOKENS_CANDIDATES if (root / c).is_file()), root / TOKENS_CANDIDATES[0])
    files = collect(root, a.paths or list(DEFAULT_TARGETS))
    if tokens_file.is_file() and tokens_file not in files:
        files.append(tokens_file)   # 未使用トークン検査のため常に読む（直値検査からは除外）

    def out(s: str = "") -> None:
        if not a.json:
            print(s)

    out(f"=== デザイン検査: {root} ===")
    if not [f for f in files if f.resolve() != tokens_file.resolve()]:
        if a.json:
            print(json.dumps({"ng": [], "warn": [], "known": 0, "baseline_total": 0}, ensure_ascii=False, indent=2))
        else:
            print("対象ファイルなし（.css / .html / .js が見つからない）。exit 0")
        return 0

    r = Result()
    texts = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}
    for f in files:
        if f.resolve() == tokens_file.resolve():
            continue
        check_literal_values(root, f, texts[f], r)
        check_new_ng_rules(root, f, texts[f], r)
        check_100vh(root, f, texts[f], r)
        check_new_warn_rules(root, f, texts[f], r)
        check_cdn(root, f, texts[f], r)
        check_dialogs(root, f, texts[f], r)
        check_tokens_loaded(root, f, texts[f], r)
        check_focus_motion_mobile(root, f, texts[f], r)
    check_tokens(root, files, texts, tokens_file, r)

    # --baseline: 既知/新規の分類（未指定なら baseline_set は空集合＝全 NG が「新規」＝従来どおり）
    baseline_path = Path(a.baseline) if a.baseline else None
    if baseline_path and not baseline_path.is_absolute():
        baseline_path = root / baseline_path
    baseline_set = load_baseline(baseline_path) if baseline_path else set()
    prev_total = len(baseline_set)
    new_ng = [x for x in r.ng if r.baseline_key(x) not in baseline_set]
    known_count = len(r.ng) - len(new_ng)

    if a.baseline and a.baseline_write:
        current_total = len(r.ng)
        if not baseline.update_allowed(baseline_path.is_file(), prev_total, current_total):
            out(f"❌ 基準線の更新を拒否: 現在の NG={current_total} 件 > 前回={prev_total} 件（増える方向）")
            return 1
        save_baseline(baseline_path, {r.baseline_key(x) for x in r.ng})
        out(f"✅ 基準線を更新: {current_total} 件を記録（{baseline_path}）")
        return 0

    report = Path(a.report)
    if not report.is_absolute():
        report = root / report
    write_report(report, root, files, r, new_ng, bool(a.baseline))

    if a.json:
        payload = {
            "ng": [x.to_dict(True) for x in r.ng],
            "warn": [x.to_dict(False) for x in r.warn],
            "known": known_count,
            "baseline_total": prev_total,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if new_ng else 0

    kinds: dict[str, int] = {}
    for x in new_ng:
        kinds[x.kind] = kinds.get(x.kind, 0) + 1
    print(f"対象: {len(files) - (1 if tokens_file.is_file() else 0)} ファイル")
    if new_ng:
        print(f"❌ NG={len(new_ng)}")
        for k, n in kinds.items():
            print(f"  - {k}: {n} 件")
        print("  例（先頭5件）:")
        for x in new_ng[:5]:
            print(f"    {x.line_text}")
    else:
        print("✅ NG=0")
    if a.baseline:
        print(f"既知 {known_count}（前回 {prev_total}）")
    if r.warn:
        print(f"⚠ 警告 {len(r.warn)} 件（未使用トークン等。詳細はレポート）")
    print(f"詳細: {report}")
    return 1 if new_ng else 0


if __name__ == "__main__":
    sys.exit(main())
