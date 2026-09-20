#!/usr/bin/env python3
"""ターンの最後の応答が保守者の言語（日本語）と型（A-9 簡潔）に合っていなければ止める Stop フック。

instruction-guard.py（PreToolUse）はツールを呼ぶ前を見張る。こちらは**ツールを呼ばずに終わる応答**を見張る。

1. 言語（A-13）: 最後の人の発言に日本語があり、最後のアシスタント応答に日本語が無い（または応答が無い）場合、
   decision=block で続行させ、日本語で出し直させる。判定ロジックは instruction-guard.py と共有する。
2. 型（A-9。2026-09-20、保守者「結論は何か。ダラダラと長すぎる」「説明がくど過ぎて伝わっていない」）:
   日本語の最終応答について、冒頭の宣言文（「承知しました」「まず」「以下に」等）・末尾の申し出や締め
   （「必要であれば」「以上です」等）・「結論:」「要約:」のラベル行を検出して block する。
   出所は i-have-adhd の送信前チェック（冒頭の宣言文と末尾の申し出を消し、最初の行と最後の行だけで
   「次の行動」と「何が起きたか」が分かるか）。
stop_hook_active のときは何もしない（無限ループ防止）。バイパス用の環境変数は作らない。
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # hooks ディレクトリに __pycache__ を作らない

# 冒頭の宣言文（最初の行の先頭）。「はい」「いいえ」は閉じた質問への答えなので対象外
OPENER_RE = re.compile(
    r"^(承知(いた)?しました|了解(しました|です|いたしました)|かしこまりました|ご質問への回答として|"
    r"それでは|では[、,]|まず[、,]?|以下に|以下[、,]|お待たせしました)"
)
# 末尾の申し出・締め（最後の行のどこか）。「〜しますか」「はい／いいえ」の閉じた質問は対象外
CLOSER_RE = re.compile(
    r"(必要であれば|必要なら|必要に応じて|ご希望であれば|ご希望なら|よければ|お気軽に|お知らせください|"
    r"ご確認ください|以上です|以上となります|以上になります|参考になれば|お役に立てれば)"
)
# 結論・要約のラベル行（保守者の応答規約: 結論・要約ラベル禁止。「目的:」「残課題:」は A-1・A-3 の必須出力）
LABEL_RE = re.compile(r"^\s*(結論|要約|まとめ|サマリ|サマリー)\s*[:：]")


def load_guard():
    p = Path(__file__).resolve().parent / "instruction-guard.py"
    spec = importlib.util.spec_from_file_location("instruction_guard", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def last_reply(lines: list[str], g) -> str | None:
    """最後の人の発言より後の、最後のアシスタントのテキスト応答。サブエージェントなら None。"""
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if e.get("isSidechain"):
            return None
        a = g.assistant_text_of(e)
        if a is not None:
            return a
        if g.instruction_of(e) is not None:
            return None
    return None


def shape_violations(reply: str) -> list[str]:
    """A-9 の型に反する箇所。空なら合格。"""
    lines = [ln.strip() for ln in reply.splitlines() if ln.strip()]
    if not lines:
        return []
    found: list[str] = []
    m = OPENER_RE.match(lines[0])
    if m:
        found.append(f"冒頭の宣言文「{m.group(0)}」")
    m = CLOSER_RE.search(lines[-1])
    if m:
        found.append(f"末尾の申し出・締め「{m.group(0)}」")
    for ln in lines:
        m = LABEL_RE.match(ln)
        if m:
            found.append(f"ラベル行「{m.group(0).strip()}」")
            break
    return found


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("stop_hook_active"):
        return 0
    tp = data.get("transcript_path", "")
    if not tp or not Path(tp).is_file():
        return 0
    g = load_guard()
    try:
        lines = g.tail_lines(Path(tp))
        verdict = g.judge(lines)
    except OSError:
        return 0
    if verdict is not None:
        kind, inst = verdict
        head = " ".join(inst.split())[:80]
        if kind == "unanswered":
            reason = f"[reply-language] 保守者の指示「{head}」に応答せずに終わろうとしている。日本語で応答してから終える（A-13）"
        else:
            reason = f"[reply-language] 最後の応答に日本語が無い。指示「{head}」は日本語。日本語で出し直す（A-13）"
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0
    reply = last_reply(lines, g)
    if not reply or not g.has_ja(reply):
        return 0
    bad = shape_violations(reply)
    if not bad:
        return 0
    reason = (
        "[reply-language] A-9 簡潔: " + "／".join(bad) + " を消して出し直す。"
        "最初の行は結論か次の行動、最後の行は次の一手か判断の問い（はい／いいえ）。"
        "宣言（「〜します」）だけで終えない。締めの要約・申し出を書かない"
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
