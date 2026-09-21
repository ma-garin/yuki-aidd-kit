#!/usr/bin/env python3
"""保守者の発言が「作業より優先」であることを、発言の直後に注入する UserPromptSubmit フック。

「今すぐ」「報告」「説明」「なぜ」「止め」等を含む発言には、次のツール呼び出しより先に日本語で応答する旨を
additionalContext で添える（instruction-guard.py が同じことを物理的に強制する。こちらは何をすべきかを先に伝える）。
語を含まない通常の発言には何も足さない（毎回のコストを増やさない）。
"""
import json
import re
import sys

URGENT_RE = re.compile(r"(今すぐ|直ちに|報告|説明|なぜ|理由|止め|やめ|中断|答え|回答|怒)")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = data.get("prompt") or ""
    if not isinstance(prompt, str) or not URGENT_RE.search(prompt):
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "[prompt-priority] この発言は進行中の作業より優先する。次のツール呼び出しより先に、この発言に日本語で応答する"
                             "（報告・説明・理由を求められたら、切り分けの途中でも止めて答える。instruction-guard.py が強制する。A-13）",
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
