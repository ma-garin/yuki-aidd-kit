#!/usr/bin/env python3
"""`git commit` の前に「変更を説明する文書が同じ差分で未更新」を止める PreToolUse フック（キット開発用）。

根拠: 2026-09-19（M23）、hook を変えたのに userguide・PRD・spec/04 が古いまま残り、
`check-docs.sh` の NG=0 を「文書は最新」と取り違えて完了報告した。行数・件数の突合は
内容の鮮度を見ない。コミットの直前に検査 12（`check_docs.py --only-changed`）を回し、
NG なら deny する。理由に未更新の文書名を載せるので、同じコミットで直すしかない。

発動条件: tool_name が Bash で、コマンド開始位置に `git commit` があり、
プロジェクト（CLAUDE_PROJECT_DIR か cwd）に `scripts/check_docs.py` があるとき。
無いプロジェクト（配布先）では何もしない。バイパス用の環境変数は作らない。
"""
import json
import os
import re
import subprocess
import sys
import tempfile

_COMMIT = re.compile(r"(?:^|&&|\|\||;|\n)\s*git\s+(?:-C\s+\S+\s+)?commit\b")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not _COMMIT.search(cmd):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    checker = os.path.join(root, "scripts", "check_docs.py")
    if not os.path.isfile(checker):
        return 0
    report = os.path.join(tempfile.gettempdir(), "check-docs-changed-report.md")
    try:
        res = subprocess.run(
            [sys.executable, checker, "--root", root, "--only-changed", "--skip-tests", "-o", report],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        print(json.dumps({"systemMessage": f"[docs-gate] 検査を実行できず素通し: {e}"}, ensure_ascii=False))
        return 0
    if res.returncode == 0:
        return 0
    lines = [ln.strip() for ln in res.stdout.splitlines() if "変更文書:" in ln][:6]
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "docs-gate: 変更したファイルを説明する文書が同じ差分で未更新（check-docs 検査 12）。"
                "同じコミットで文書を直してから commit すること。 "
                + " ／ ".join(lines) + f" （全件: {report}）"
            ),
        }
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
