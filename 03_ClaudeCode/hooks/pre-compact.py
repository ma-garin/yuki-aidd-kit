#!/usr/bin/env python3
"""圧縮（/compact・自動圧縮）に「何を残し、何を捨てるか」を注入する PreCompact フック。

圧縮は会話全体を読む大きなリクエストで、指示が無いとツール出力の本文まで要約に残りやすい。
残すべきは判断の材料だけ。03_ClaudeCode/CLAUDE.md.template の `# Compact instructions` 節と同じ内容
（hook は Claude Code 専用なので、公式が読む場所にも同じものを置く）。
"""
import json
import sys

INSTRUCTIONS = (
    "圧縮の指示（yuki-aidd-kit）:\n"
    "残す — 決定事項とその理由／変更・作成したファイルのパス一覧／未解決の課題と次の一手／"
    "最後に実行したテストの集計行（PASS=n / FAIL=m）／ユーザーの制約（禁止事項・手動のみ等）。\n"
    "捨てる — ツール出力の本文／読んだファイルの内容（パスだけ残す）／途中経過・試行錯誤／挨拶や相槌。\n"
    "形式 — 見出しと箇条書き。散文にしない。"
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("hook_event_name", "PreCompact") != "PreCompact":
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreCompact", "additionalContext": INSTRUCTIONS,
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
