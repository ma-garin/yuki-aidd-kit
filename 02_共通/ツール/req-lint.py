#!/usr/bin/env python3
"""req-lint.py — 要件定義書の要件文を決定的に検査する（EARS 型・曖昧語・数値の無い非機能目標・列挙数・ID の重複）。

要件のひな形（02_共通/ひな形/lifecycle/01-requirements.md）は要件文を EARS 型で書かせる。本ツールはその書式と、
「適切に」「高速に」のような曖昧語、数値の無い非機能目標、「以下の 3 つ」と列挙の食い違い、ID の重複を機械で拾う。
意味（その要件が正しいか）は判定しない。標準ライブラリのみ・Python 3.9 互換。

使い方:
  python3 scripts/req-lint.py docs/lifecycle/01-requirements.md [--words 辞書.md ...]
終了コード: 0 = NG なし（WARN はあってよい）／ 1 = NG あり ／ 2 = 引数・入力の誤り（ファイルが無い）
工程承認ゲート: `.claude/phase-gate` があるプロジェクトでは check_approval.py --gate 2（基本設計への入口）が
  本ツールを隣から呼び、NG があれば未承認扱い（exit 1）にする。phase-gate が無ければ結果を出すだけ。

読む行:
  - 表の第1セルが要件 ID（`REQ-F-001` など 英大文字-…-3 桁以上）の行。本文は見出しが「要件」で始まる列（無ければ第2列）。
  - 行頭（`- ` や `**` の後でもよい）が `ID:` の行。本文はコロンの後ろ。
  - `### REQ-F-001 …` のような見出しは ID の重複の検査にだけ使う。
  採番前の ID（`REQ-F-0xx`）と、本文が空の行（ひな形のまま）は読まない。HTML コメントとフェンスコードの中は読まない。
NG（exit 1）:
  数値の無い非機能目標: 非機能要件の行（ID が REQ-N、または見出しに「非機能」を含む節の要件行）に
    性能・応答・件数・同時・可用・容量 のどれかがあるのに、数値と単位（3秒・200ms・99.9%・1万件・同時 50 人・
    3 秒以内・毎秒 100 リクエスト など）が無い。
  列挙数の不一致: 「以下の N つ／個／点／件」の N と、直後の箇条書きの項目数が違う。数えるのは最初の項目と
    同じインデントの項目だけ（入れ子は数えない。空行は無視。`<br>` 区切りのセル内も同じ）。箇条書きが続かなければ見ない。
    文中の列挙（`、` 区切り）は数えない（日付の `/`・括弧の中の `、` で数を誤るため）。
  要件 ID の重複: 同じ ID が 2 回以上定義されている。
WARN（exit に影響しない）:
  曖昧語: 辞書の語が要件の行にある。辞書は下の既定の語に、references/ambiguous-words.md の語（バッククォートで囲んだもの）を足す。
    辞書の「除外（複合語）」の節の語（高速道路・同等・等しい・三十分 など）は、照合の前に空白に置き換える（語の一部で誤検知しない）。
    コードスパン（`…`）・「」で囲んだ引用・`例:`／`NG 例:`／`OK 例:`／`>` で始まるセルと行は照合しない。
    辞書は `--words` で渡すか、次の順に見つかったものを全部読む: 隣の references/ → キットの
    03_ClaudeCode/skills/sdd-ecc-workflow/references/ → .claude/skills/… → ~/.claude/skills/…
  EARS 型に当たらない: 型の語と要件の述語の両方が無い。述語は語尾が動詞の終止形・「こと」・「ない」（「である」「がある」は述語にしない）。
    型の語は とき・時・際・たら（When）／ の間・間は・中（While）／ 場合（If）／ では・において（Where）／ 常に・常時・<主語>は（常時）。
    常時（Ubiquitous）  <主語>は、<応答>する。（「システムは便利である。」は述語が無いので当たらない）
    〜のとき（When）     <契機>とき（時・際・したら）、<主語>は<応答>する。
    〜の間（While）      <状態>の間（中）、<主語>は<応答>する。
    〜の場合（If）       <望まない事象>場合、<主語>は<応答>する。
    〜では（Where）      <機能・構成>では、<主語>は<応答>する。
    英語の EARS（The <system> shall / must … ／ When … ／ While … ／ If … then … ／ Where …）も当たりとする。
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ID_TOKEN = r"[A-Z]+(?:-[A-Z]+)*-\d{3,}"
ID_RE = re.compile(rf"^{ID_TOKEN}$")
ID_ANY_RE = re.compile(rf"(?<![A-Za-z0-9-]){ID_TOKEN}(?![A-Za-z0-9])")
LINE_REQ_RE = re.compile(rf"^\s*(?:[-*+]\s+)?\**({ID_TOKEN})\**\s*[:：]\s*(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
SEP_RE = re.compile(r"^\|[\s:|-]+\|$")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")
EXAMPLE_RE = re.compile(r"^(?:(?:NG|OK)\s*)?例\s*:|^>")          # 例の行・セル（NFKC 後）は曖昧語を照合しない
QUOTE_RE = re.compile(r"`[^`]*`|「[^」]*」")                       # コードスパンと「」の引用は照合しない
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
BR_RE = re.compile(r"<br\s*/?>", re.I)

NFR_WORDS = ("性能", "応答", "件数", "同時", "可用", "容量")
NUM_UNIT_RE = re.compile(
    r"(?:毎秒|毎分|毎時|毎日)\s*\d|"
    r"\d[\d,]*(?:\.\d+)?\s*(?:万|億|千|ms|ミリ秒|秒|sec|s(?![A-Za-z])|分|時間|h(?![A-Za-z])|日|週|か月|ヶ月|カ月|ケ月|年|"
    r"件|人|名|ユーザー?|同時|並列|接続|セッション|%|パーセント|[KMGT]i?B|[KMG]?bps|rps|qps|tps|req|リクエスト|fps|"
    r"回|桁|px|文字|画面|倍|行|クリック|タップ|操作|ステップ|以内|以上|未満|以下)", re.I)
KANJI_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
ENUM_RE = re.compile(r"以下の\s*(\d+|[一二三四五六七八九十])\s*(?:つ|個|点|件)")

# 曖昧語の既定（辞書ファイルが見つからなくてもこれだけは見る）
DEFAULT_JA = ("適切に", "必要に応じて", "など", "等", "高速", "十分", "可能な限り", "迅速", "柔軟",
              "使いやすい", "わかりやすい", "分かりやすい")
DEFAULT_EN = ("appropriate", "as needed", "etc", "fast", "sufficient", "flexible", "user-friendly")
# 除外（複合語）の既定。照合の前に空白に置き換える（辞書の「除外（複合語）」の節と同じ。辞書が無い配布先でも効かせる）
DEFAULT_EXCLUDE = ("高速道路", "高速化", "高速通信", "高速バス", "同等", "平等", "均等", "対等", "等価", "等し", "等分", "等号",
                   "等級", "等間隔", "等倍", "等幅", "上等", "高等", "初等", "中等", "劣等", "優等", "不等",
                   "十分間", "十分後", "十分前", "十分以上", "十分以内", "十分ごと", "十分おき", "数十分",
                   "二十分", "三十分", "四十分", "五十分", "六十分", "七十分", "八十分", "九十分")

# EARS 型（NFKC 後の本文に当てる）。型の語と述語（語尾が動詞の終止形・「こと」・「ない」）の両方があるときだけ型あり
END_RE = re.compile(r"(?:[うくぐすつぬぶむる]|こと|ない)$")
NOT_PRED_RE = re.compile(r"(?:ある|であること|であるもの)$")        # 「便利である」「機能がある」は振る舞いでない
EARS_JA = (
    ("When", re.compile(r"(?:とき|時|際)(?:[、,]|に|は)|たら")),
    ("While", re.compile(r"の間|間[、,]|間は|あいだ|中[、,]")),
    ("If", re.compile(r"場合")),
    ("Where", re.compile(r"では|において")),
    ("常時", re.compile(r"常に|常時|は")),
)
SHALL_RE = re.compile(r"(?i)\b(?:shall|must)\b")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def word_pattern(w: str) -> re.Pattern:
    """辞書の語 → 正規表現。英字の語は英字の境界で区切り、空白・ハイフンの揺れを許す。熟語の除外は mask_for_words が先に行う。"""
    if re.fullmatch(r"[A-Za-z][A-Za-z \-]*", w):
        body = r"[\s\-]+".join(re.escape(p) for p in re.split(r"[\s\-]+", w.strip()))
        return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])", re.I)
    return re.compile(re.escape(w))


def dictionary_paths(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(p) for p in explicit]
    here = Path(__file__).resolve().parent
    rel = Path("skills/sdd-ecc-workflow/references/ambiguous-words.md")
    cands = [here / "references" / "ambiguous-words.md",
             here.parent.parent / "03_ClaudeCode" / rel,
             Path.cwd() / ".claude" / rel,
             Path.home() / ".claude" / rel]
    out, seen = [], set()
    for c in cands:
        if c.is_file() and c.resolve() not in seen:
            seen.add(c.resolve())
            out.append(c)
    return out


def load_words(paths: list[Path]) -> tuple[list[str], list[str]]:
    """(曖昧語, 除外する複合語)。辞書の見出しに「除外」を含む節の語は除外に入れる。"""
    words, excl = list(DEFAULT_JA) + list(DEFAULT_EN), list(DEFAULT_EXCLUDE)
    for p in paths:
        text = COMMENT_RE.sub("", p.read_text(encoding="utf-8", errors="replace"))
        dest = words
        for line in text.splitlines():
            hm = HEADING_RE.match(line)
            if hm:
                dest = excl if "除外" in hm.group(2) else words
            elif LIST_RE.match(line):
                dest += [w.strip() for w in re.findall(r"`([^`]+)`", line) if w.strip()]

    def uniq(xs: list[str]) -> list[str]:
        seen, out = set(), []
        for w in xs:
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(w)
        return out
    return uniq(words), sorted(uniq(excl), key=len, reverse=True)


def mask_for_words(cells: list[str], excl: list[str]) -> str:
    """曖昧語の照合に使う本文。例のセル・行を捨て、コードスパンと「」の中、除外の複合語を空白にする。"""
    kept = [QUOTE_RE.sub(" ", c) for c in (nfkc(c).strip() for c in cells) if not EXAMPLE_RE.match(c)]
    body = " ".join(kept)
    for x in excl:
        body = body.replace(nfkc(x), " ")
    return body


def ears_type(stmt: str) -> str | None:
    s = nfkc(stmt).strip().rstrip("。.．").strip()
    s = re.sub(r"\s*\([^()]*\)$", "", s).rstrip("。. ")      # 末尾の補足（括弧書き）は語尾の判定から外す
    if not s:
        return None
    if SHALL_RE.search(s):
        return "英語"
    if not END_RE.search(s):
        s = re.split(r"[:：]", s, maxsplit=1)[0].strip()      # 「…出力する: CSV、PDF」は列挙の前で語尾を見る
        if not END_RE.search(s):
            return None
    if NOT_PRED_RE.search(s):
        return None
    for name, rx in EARS_JA:
        if rx.search(s):
            return name
    return None


def enum_count(following: list[str]) -> int | None:
    """「以下の N …」の直後の箇条書きの項目数。最初の項目と同じインデントだけ数える（入れ子・続きの行は飛ばし、空行は無視）。
    箇条書きが続かなければ None（数えない）。"""
    base, n = None, 0
    for ln in following:
        if not ln.strip():
            continue
        ind = len(ln.expandtabs(4)) - len(ln.expandtabs(4).lstrip())
        if LIST_RE.match(ln):
            if base is None:
                base = ind
            if ind == base:
                n += 1
                continue
            if ind > base:
                continue                  # 入れ子
            break
        if base is not None and ind > base:
            continue                      # 項目の続きの行
        break
    return n if base is not None else None


class Linter:
    def __init__(self, path: Path, words: list[str], excl: list[str]) -> None:
        self.path = path
        self.ng: list[tuple[str, str, str]] = []      # (種別, 場所, 内容)
        self.warn: list[tuple[str, str, str]] = []
        self.words = [(w, word_pattern(w)) for w in words]
        self.excl = excl
        self.defs: dict[str, list[int]] = {}

    def where(self, n: int, rid: str = "") -> str:
        return f"{self.path}:{n}" + (f" {rid}" if rid else "")

    def check_enum(self, n: int, text: str, following: list[str]) -> None:
        for m in ENUM_RE.finditer(text):
            want = int(m.group(1)) if m.group(1).isdigit() else KANJI_NUM[m.group(1)]
            got = enum_count(following)
            if got is not None and got != want:
                self.ng.append(("列挙数の不一致", self.where(n), f"「{m.group(0)}」に対して列挙が {got} 件"))

    def check_requirement(self, n: int, rid: str, stmt: str, cells: list[str], nfr: bool) -> None:
        """cells = ID を除く行のセル（行形式の要件は本文 1 つ）。"""
        body = nfkc(" ".join(c for c in cells if not EXAMPLE_RE.match(nfkc(c).strip())))
        if nfr:
            hit = [w for w in NFR_WORDS if w in body]
            if hit and not NUM_UNIT_RE.search(ID_ANY_RE.sub(" ", body)):
                self.ng.append(("数値の無い非機能目標", self.where(n, rid),
                                f"「{hit[0]}」があるが数値と単位が無い（例: 3秒以内・200ms・99.9%・1万件・同時 50 人）"))
        masked = mask_for_words(cells, self.excl)
        found = [w for w, rx in self.words if rx.search(masked)]
        if found:
            self.warn.append(("曖昧語", self.where(n, rid), "「" + "」「".join(found) + "」— 数値・条件・列挙に置き換える"))
        if ears_type(stmt) is None:
            self.warn.append(("EARS 型に当たらない", self.where(n, rid),
                              f"「{stmt.strip()[:40]}」— 常時／〜のとき／〜の間／〜の場合／〜では のどれかの型で書く"))

    def run(self) -> None:
        raw = self.path.read_text(encoding="utf-8", errors="replace")
        # HTML コメントは行数を保ったまま消す（行番号をエディタと一致させる）
        text = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), raw)
        lines = text.splitlines()
        in_fence, marker = False, ""
        section = ""
        header: list[str] | None = None
        prev = ""
        for i, line in enumerate(lines):
            n = i + 1
            fm = FENCE_RE.match(line)
            if fm:
                if not in_fence:
                    in_fence, marker = True, fm.group(1)
                elif fm.group(1) == marker:
                    in_fence = False
                prev = line
                continue
            if in_fence:
                prev = line
                continue
            s = line.strip()
            hm = HEADING_RE.match(line)
            if hm:
                section = hm.group(2)
                toks = section.split()
                if toks and ID_RE.match(toks[0]):
                    self.defs.setdefault(toks[0], []).append(n)
                header = None
                prev = line
                continue
            if s.startswith("|"):
                if SEP_RE.match(s):
                    header = [c.strip() for c in prev.strip().strip("|").split("|")] if prev.strip().startswith("|") else None
                    prev = line
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                for c in cells:
                    parts = BR_RE.split(c)
                    for k, part in enumerate(parts):
                        self.check_enum(n, part, parts[k + 1:])
                rid = nfkc(cells[0]).strip("*` ") if cells else ""
                if header is not None and ID_RE.match(rid):
                    self.defs.setdefault(rid, []).append(n)
                    k = next((j for j, h in enumerate(header) if h.startswith("要件")), 1)
                    stmt = cells[k] if k < len(cells) else ""
                    if stmt.strip():
                        self.check_requirement(n, rid, BR_RE.sub(" ", stmt), [BR_RE.sub(" ", c) for c in cells[1:]],
                                               rid.startswith("REQ-N") or "非機能" in section)
                prev = line
                continue
            header = None
            self.check_enum(n, line, lines[i + 1:])
            lm = LINE_REQ_RE.match(line)
            if lm and lm.group(2).strip():
                rid = lm.group(1)
                self.defs.setdefault(rid, []).append(n)
                self.check_requirement(n, rid, lm.group(2), [lm.group(2)],
                                       rid.startswith("REQ-N") or "非機能" in section)
            prev = line
        for rid, ns in self.defs.items():
            if len(ns) > 1:
                self.ng.append(("要件 ID の重複", self.where(ns[0], rid), f"{len(ns)} 回定義されている（行 {', '.join(map(str, ns))}）"))


def main() -> int:
    ap = argparse.ArgumentParser(description="要件定義書の要件文を検査する（EARS 型・曖昧語・非機能の数値・列挙数・ID 重複）")
    ap.add_argument("requirements", help="要件定義書（例 docs/lifecycle/01-requirements.md）")
    ap.add_argument("--words", action="append", default=[], help="曖昧語の辞書（references/ambiguous-words.md の形式）。複数可")
    a = ap.parse_args()
    path = Path(a.requirements)
    if not path.is_file():
        print(f"❌ 要件定義書が無い: {path}", file=sys.stderr)
        return 2
    missing = [w for w in a.words if not Path(w).is_file()]
    if missing:
        print(f"❌ 辞書が無い: {', '.join(missing)}", file=sys.stderr)
        return 2
    lt = Linter(path, *load_words(dictionary_paths(a.words)))
    lt.run()
    print(f"=== 要件の検査（req-lint）: {path} ===")
    print(("❌" if lt.ng else "✅") + f" NG={len(lt.ng)} / WARN={len(lt.warn)}")
    for kind, where, detail in lt.ng:
        print(f"  NG   {kind}: {where} — {detail}")
    for kind, where, detail in lt.warn:
        print(f"  WARN {kind}: {where} — {detail}")
    return 1 if lt.ng else 0


if __name__ == "__main__":
    sys.exit(main())
