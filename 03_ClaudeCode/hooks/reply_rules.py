#!/usr/bin/env python3
"""応答ルール検査（保守者の応答スタイル規約を機械判定する）。reply-language.py（Stop）から呼ぶ。単体でも使える。

検査する規則（ID は差し戻し理由・集計の列名に使う）:
  R1 判定調の締め   最終行が「構いません」「十分です」「大丈夫です」「問題ありません」で終わる
  R2 結論ラベル     「結論:」「要約：」「まとめ」等の見出し・ラベル
  R3 開いた質問     「どうしますか」「いかがでしょうか」等（閉じた質問＝推奨付きの二択・番号選択に直す）
  R4 変更報告の表   「変更しました」等の変更報告なのに Before/After（変更前/変更後）の表が無い
  R5 タメ口         文末が「だよ」「だね」「じゃん」「しとく」等（です・ます調に直す）
コードブロック・引用（>）の中は検査しない（文面案・ログの引用を誤検知しない）。

使い方:
  python3 reply_rules.py check [ファイル]        # 1 応答（標準入力可）を検査。違反を 1 行ずつ。違反ありは exit 1
  python3 reply_rules.py stats <transcript.jsonl>...   # 会話記録の assistant 応答ごとの規則別違反率（QA4AI の集計用）
解除: 環境変数 AIDD_REPLY_LINT_OK=1（誤検知の回避。hook-decisions.log に解除が残る）。規則を足すときは RULES に追記する。
"""
from __future__ import annotations

import json
import re
import sys

_CODE_RE = re.compile(r"```.*?```", re.S)
_TABLE_ROW_RE = re.compile(r"^\s*\|")


def visible_text(msg: str) -> str:
    """コードブロック・引用行を除いた本文。"""
    t = _CODE_RE.sub("", msg)
    return "\n".join(l for l in t.splitlines() if not l.lstrip().startswith(">"))


def _last_line(text: str) -> str:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def r1_verdict_closer(text: str) -> str | None:
    last = _last_line(text)
    if _TABLE_ROW_RE.match(last) or last.startswith("見積"):
        return None
    if re.search(r"(構いません|十分です|大丈夫です|問題ありません|差し支えありません)[。.!！]?$", last):
        return f"判定調の締め「{last[-12:]}」→ 事実を述べて終える"
    return None


def r2_conclusion_label(text: str) -> str | None:
    m = re.search(r"^\s*(?:#{1,6}\s*|[-*]\s*)?(?:\*\*)?(結論|要約|まとめ|サマリー?|総括)(?:\*\*)?\s*(?:[:：]|$)",
                  text, re.M)
    return f"ラベル「{m.group(1)}」→ ラベルを付けず 1 行目に結論を書く" if m else None


def r3_open_question(text: str) -> str | None:
    m = re.search(r"(どう(し|いたし)ますか|どうしましょうか|いかが(でしょうか|ですか|しますか)|"
                  r"ご希望(は|が)(あります|ございます)か|何か(ありますか|ございますか))", text)
    return f"開いた質問「{m.group(1)}」→ 推奨付きの閉じた質問（番号選択）に直す" if m else None


_CHANGE_RE = re.compile(r"(変更|修正|更新|置き換え|書き換え|差し替え)(しました|済み|完了)")
_BA_RE = re.compile(r"^\s*\|.*(Before|変更前|旧).*\|.*(After|変更後|新).*\|", re.M | re.I)


def r4_change_table(text: str) -> str | None:
    if _CHANGE_RE.search(text) and not _BA_RE.search(text):
        return "変更報告に Before/After 表が無い → | 項目 | Before | After | の表で示す（散文禁止）"
    return None


_CASUAL_RE = re.compile(r"(だよ|だね|だよね|じゃん|しとく|しといた|やっとく|するね|したよ|かな|だぞ)(?:ね|よ)?(?:[。!！?？]|$)", re.M)


def r5_casual(text: str) -> str | None:
    for line in text.splitlines():
        if _TABLE_ROW_RE.match(line):
            continue
        m = _CASUAL_RE.search(line.strip())
        if m and not re.search(r"(です|ます|でした|ません)(ね|よ)?[。!！?？]?$", line.strip()):
            return f"タメ口「{line.strip()[-10:]}」→ です・ます調"
    return None


RULES = [("R1", r1_verdict_closer), ("R2", r2_conclusion_label), ("R3", r3_open_question),
         ("R4", r4_change_table), ("R5", r5_casual)]


# Stop で差し戻す規則。R4 は「修正しました。PASS=3」型の完了報告でも当たり誤検知が多いため既定は集計（stats）のみ。
# AIDD_REPLY_LINT_RULES=R1,R2,R3,R4,R5 で差し戻す規則を変えられる
HOOK_RULES_DEFAULT = ("R1", "R2", "R3", "R5")


def hook_rules() -> tuple[str, ...]:
    import os
    env = os.environ.get("AIDD_REPLY_LINT_RULES")
    return tuple(x.strip() for x in env.split(",") if x.strip()) if env else HOOK_RULES_DEFAULT


def check(msg: str, only: tuple[str, ...] | None = None) -> list[tuple[str, str]]:
    """違反の (規則ID, 説明) 一覧。only を渡すとその規則だけ検査する。"""
    text = visible_text(msg)
    out = []
    for rid, fn in RULES:
        if only is not None and rid not in only:
            continue
        try:
            r = fn(text)
        except re.error:
            r = None
        if r:
            out.append((rid, r))
    return out


def _assistant_texts(path: str):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message") if isinstance(e, dict) else None
            if not isinstance(m, dict) or m.get("role") != "assistant":
                continue
            c = m.get("content")
            if isinstance(c, str):
                txt = c
            elif isinstance(c, list):
                txt = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
            else:
                txt = ""
            if txt.strip():
                yield txt


def stats(paths: list[str]) -> None:
    n, hits = 0, {rid: 0 for rid, _ in RULES}
    for p in paths:
        for t in _assistant_texts(p):
            n += 1
            for rid, _ in check(t):
                hits[rid] += 1
    print(f"応答 {n} 件")
    for rid, _ in RULES:
        rate = 100 * hits[rid] / n if n else 0
        print(f"  {rid}: {hits[rid]} 件（{rate:.1f}%）")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("check", "stats"):
        print(__doc__)
        return 2
    if argv[1] == "stats":
        stats(argv[2:])
        return 0
    msg = open(argv[2], encoding="utf-8").read() if len(argv) > 2 else sys.stdin.read()
    v = check(msg)
    for rid, d in v:
        print(f"{rid}: {d}")
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
