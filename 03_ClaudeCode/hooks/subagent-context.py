#!/usr/bin/env python3
"""委譲先の規約をサブエージェントの起動時に注入する SubagentStart フック。

親セッションへの注入（UserPromptSubmit の prompt-priority.py 等）はサブエージェントに届かない。
委譲先は H-4 の「委譲プロンプトに同梱するもの」を受け取る側の規約を知らないまま動き、
渡された確定情報の再調査・上限超過・長い返却をしていた。aidd-lead が起動する spec/build/gate/verify-agent と、
H-4 で委譲する汎用エージェントの両方に、受け手側の規約を毎回添える（出典: DietrichGebert/ponytail の
ponytail-subagent.js。SessionStart の注入が子に届かない問題への同じ対処）。

  - 全エージェント: 保守者の時計（リモート環境は UTC で動く）、H-4 の受け手側規約、approver 欄を埋めない
  - 検証系（agent_type が gate / verify / review / qa を含む）: 「壊れている箇所を探せ」を追加（H-4 役割分離）
"""
import datetime
import json
import os
import re
import sys
import zoneinfo

LOCAL_TZ = os.environ.get("AIDD_TZ", "Asia/Tokyo")   # prompt-priority.py と同じ保守者の時計
VERIFIER_RE = re.compile(r"(gate|verify|review|qa)", re.IGNORECASE)

RULES = (
    "委譲先の規約（H-4）:\n"
    "- 委譲プロンプトで渡された確定情報（URL・API・データ投入経路・既知不具合・禁止事項）は再調査しない\n"
    "- 指示されたツール回数上限を守る。上限が近づいたら、その時点の結果を書き出して返す\n"
    "- 結果は指示された書き出し先に書き、返却は 10 行以内の要約にする\n"
    "- approver 欄は埋めない（AI は承認しない）"
)
VERIFIER = ("検証系の姿勢: 「合っているか」ではなく「壊れている箇所を探せ」。"
            "作った側の説明や自己申告を合格の根拠にしない（H-4 役割分離）")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    agent_type = data.get("agent_type") or ""
    try:
        now = datetime.datetime.now(zoneinfo.ZoneInfo(LOCAL_TZ)).strftime("%Y-%m-%d %H:%M")
        head = f"[subagent-context] 現在 {now}（{LOCAL_TZ}）。記録に日付・時刻を書くときはこの時計を使う。\n"
    except Exception:
        head = "[subagent-context]\n"
    ctx = head + RULES
    if isinstance(agent_type, str) and VERIFIER_RE.search(agent_type):
        ctx += "\n" + VERIFIER
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": ctx}},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
