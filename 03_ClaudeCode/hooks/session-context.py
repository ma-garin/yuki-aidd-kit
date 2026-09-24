#!/usr/bin/env python3
"""圧縮・再開の直後に CURRENT_STATE.md の要点を数行だけ再注入する SessionStart フック（B62）。

圧縮（/compact・自動圧縮）や再開（--resume・--continue）の後に残るのは要約だけで、CURRENT_STATE.md は人が
指示しない限り読まれない。要約から落ちた「今どこにいて・何を守り・次に何をするか」を、決まった数行で戻す。

  - 対象: SessionStart の source が compact・resume のときだけ（配線の matcher も `compact|resume`）。
    startup・clear では何もしない（起動時は CLAUDE.md の「最初の 5 分」で読む）
  - 読む: `$CLAUDE_PROJECT_DIR`（無ければ入力の cwd）の `CURRENT_STATE.md`、無ければ `.claude/CURRENT_STATE.md`
  - 注入: 中身のある最初の「現在の作業」「制約」「次の一手」の 3 節の本文を、見出し行も含めて**合計 12 行以内**。
    見出しの語は揺れを許す（現在の作業＝現在の作業・現在のフェーズ・フェーズ／制約＝制約・決まっていること／
    次の一手＝次の一手・次のタスク・次にやるなら）。コメント・空行・雛形の例（`例:`・`○○`・`T-XX`）は数えない。
    1 行は 120 字まで
  - 古さ: 「最終更新」節（または `最終更新: YYYY-MM-DD` の行）の日付、無ければファイルの更新時刻から
    30 日を超えていたら先頭に「古い（YYYY-MM-DD）」を付ける（古い引継ぎを今の状態と取り違えない）。
    存在しない日付（2026-13-45 等）は古さを判定せず、本文だけを注入する
  - ファイルが無い・3 節とも中身が無い・入力が読めない → 何も出さない（fail-open。常に exit 0）

限界: 要約に何が残ったかは見ない（transcript の要約本文は版によって取れない）。CURRENT_STATE.md の更新は人と
AI の手作業のまま（context-compression スキル・pre-compact.py の指示で促す）。
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

MAX_LINES = 12
STALE_DAYS = 30
LINE_MAX = 120
SOURCES = frozenset({"compact", "resume"})
SECTIONS = (
    ("現在の作業", ("現在の作業", "現在のフェーズ", "フェーズ")),
    ("制約", ("制約", "決まっていること")),
    ("次の一手", ("次の一手", "次のタスク", "次にやるなら")),
)
_HEAD = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_PLACEHOLDER = re.compile(r"^(?:[-*]\s*)?(?:\d+\.\s*)?(?:例[:：]|<)|○○|T-XX")


def find_state(data: dict) -> Path | None:
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), data.get("cwd")):
        if not isinstance(base, str) or not base:
            continue
        for rel in ("CURRENT_STATE.md", ".claude/CURRENT_STATE.md"):
            p = Path(base) / rel
            if p.is_file():
                return p
    return None


def split_sections(text: str) -> list[tuple[str, list[str]]]:
    out: list[tuple[str, list[str]]] = []
    fence = False
    for line in _COMMENT.sub("", text).splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        m = None if fence else _HEAD.match(line)
        if m:
            out.append((m.group(1), []))
        elif out:
            out[-1][1].append(line)
    return out


def body(lines: list[str]) -> list[str]:
    keep = []
    for line in lines:
        s = line.strip()
        if not s or re.fullmatch(r"\|?[\s:|-]+\|?", s) or _PLACEHOLDER.search(s):
            continue
        keep.append(s if len(s) <= LINE_MAX else s[:LINE_MAX - 1] + "…")
    return keep


def _date(m: re.Match) -> datetime.date | None:
    try:
        return datetime.date(*map(int, m.groups()))
    except ValueError:      # 2026-13-45 のような存在しない日付。古さは判定しない（本文は注入する）
        return None


def last_updated(sections: list[tuple[str, list[str]]], text: str, path: Path) -> tuple[datetime.date | None, str]:
    """(日付, 表示用の文字列)。書かれた日付が存在しなければ (None, 書かれたまま)。"""
    for title, lines in sections:
        if "最終更新" in title:
            for line in lines:
                m = _DATE.search(line)
                if m:
                    return _date(m), m.group(0)
    m = re.search(r"最終更新[^\n\d]{0,6}(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return _date(m), m.group(0)[-10:]
    d = datetime.date.fromtimestamp(path.stat().st_mtime)
    return d, d.isoformat()


def build(path: Path, today: datetime.date) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = split_sections(text)
    picked: list[tuple[str, list[str]]] = []
    for label, words in SECTIONS:
        # 見出しが当たり、中身（雛形の例を除く）がある最初の節
        items = next((b for title, lines in sections if any(w in title for w in words) for b in [body(lines)] if b), [])
        if items:
            picked.append((label, items))
    if not picked:
        return ""
    updated, shown = last_updated(sections, text, path)
    stale = updated is not None and (today - updated).days > STALE_DAYS
    note = shown if updated is not None else f"{shown}（日付として読めないので古さは判定しない）"
    head = (f"{'古い（' + shown + '）。' if stale else ''}"
            f"[session-context] 圧縮・再開の後の再注入: {path.name} の要点（最終更新 {note}。"
            "全文は必要なときだけ読む）")
    budget = MAX_LINES - 1                     # 見出し 1 行を除いた残り。各節にまず 1 行＋本文を均等に配る
    take = {label: 0 for label, _ in picked}
    while budget > 0:
        moved = False
        for label, items in picked:
            if budget > 0 and take[label] < len(items):
                take[label] += 1
                budget -= 1
                moved = True
        if not moved:
            break
    lines = [head]
    for label, items in picked:
        for i, item in enumerate(items[:take[label]]):
            lines.append(f"【{label}】{item}" if i == 0 else f"　{item}")
    return "\n".join(lines[:MAX_LINES])


def main() -> int:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict) or data.get("source") not in SOURCES:
            return 0
        path = find_state(data)
        if path is None:
            return 0
        ctx = build(path, datetime.date.today())
        if ctx:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "SessionStart", "additionalContext": ctx}}, ensure_ascii=False))
    except Exception:   # 再注入は付け足し。読めない・壊れた入力でもセッションを止めない
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
