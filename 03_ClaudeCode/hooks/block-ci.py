#!/usr/bin/env python3
"""自己ウェイク・定期実行・CI 待ちを禁止する PreToolUse フック（全ツール対象）。

根拠: rules/speed-harness.md H-9。internal/rules-rationale/token-economics.md。
待機して起き直すたびに全履歴を cache_read で読み直す（1 ターン = 文脈全量）。起き直しの回数を物理的に 0 にする。

deny するもの:
  - ツール名（末尾一致。MCP の接頭辞 mcp__xxx__ を問わない）:
    ScheduleWakeup / CronCreate / RemoteTrigger / send_later / create_trigger / subscribe_pr_activity / watch_url
  - Skill の loop / schedule
  - Bash の CI 起動・待機: gh run watch / gh run rerun / gh workflow run / gh pr checks --watch
ユーザーが明示的に要求した場合に限り、Bash は CI_REQUESTED=1 を付けて実行する（ツール呼び出しには例外なし）。
"""
import json
import re
import sys

_TOOLS = ("ScheduleWakeup", "CronCreate", "RemoteTrigger", "send_later",
          "create_trigger", "subscribe_pr_activity", "watch_url")
_SKILLS = ("loop", "schedule")
_CI_CMD = re.compile(
    r"(?:^|&&|\|\||;|\||\n)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*"
    r"gh\s+(?:run\s+(?:watch|rerun)|workflow\s+run|pr\s+checks\b[^\n;&|]*--watch)"
)
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


def reason_for(tool: str, tool_input: dict) -> str | None:
    """deny 理由を返す。許可なら None。"""
    if any(tool == t or tool.endswith("__" + t) for t in _TOOLS):
        return f"{tool} は禁止（自己ウェイク・定期実行。H-9）。待たずに本文で結果を報告して止まる"
    if tool == "Skill" and str(tool_input.get("skill", "")).split(":")[-1] in _SKILLS:
        return "loop / schedule スキルは禁止（定期実行。H-9）"
    if tool == "Bash":
        cmd = str(tool_input.get("command", ""))
        if "CI_REQUESTED=1" in cmd:
            return None
        if _CI_CMD.search(_QUOTED.sub("''", cmd)):
            return "CI の起動・待機は禁止（H-9）。ユーザーが求めたときだけ CI_REQUESTED=1 を付けて実行する"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    reason = reason_for(str(data.get("tool_name", "")), data.get("tool_input") or {})
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
        }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
