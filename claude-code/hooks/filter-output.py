#!/usr/bin/env python3
"""冗長な出力を「Claude が読む前に」絞る PreToolUse フック（Bash）。

公式の削減策「hook で前処理してから Claude に渡す」（code.claude.com/docs/en/costs）の実装。
PostToolUse は出力を書き換えられないため、PreToolUse で **コマンド側を書き換える**（`updatedInput`）。

対象と書き換え（1 行のコマンドだけ。改行・ヒアドキュメントを含むものは触らない）:
  - テストランナー（pytest / npm test / npx vitest / jest / go test / cargo test / make test 等）
      → 失敗行の前後 5 行 ＋ 末尾 5 行（集計行）だけを出す。**終了コードは元のコマンドのまま**
  - 冗長な install / build（npm install / pip install / npm run build / docker build / cargo build / make 単体）
      → 末尾 40 行だけ
  - `git log` に件数指定が無い → `--oneline -20` を補う
  - `git diff` / `git diff --cached` に対象指定が無い → `--stat` に置き換える

全量が要るとき: コマンドに `FULL_OUTPUT=1` を付ける（例: `FULL_OUTPUT=1 GATES_REQUESTED=1 pytest tests/`）。
絞ったときは必ず systemMessage で「絞った・全量の取り方」を Claude に伝える（黙って欠けると再探索が増えて逆効果）。

`block-gates.py`（ゲートはユーザー要求時のみ）と同じ matcher に後段として並べる。deny が 1 つでもあれば deny が勝つ。
キット自身の回帰テスト（`bash scripts/test-*.sh`）はテストランナーの形をしていないので絞られない。
"""
import json
import re
import sys

# block-gates.py と同じ「コマンド開始位置」照合。ヒアドキュメント・引用文字列を除いてから当てる
_HEREDOC = re.compile(r"<<-?\s*'?\"?(\w+)'?\"?.*?\n.*?\n\1\s*$", re.DOTALL | re.MULTILINE)
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_START = r"(?:^|&&|\|\||;|\||\n)\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S+\s+)*"

_TEST_RE = re.compile(
    _START + r"(?:venv/bin/)?(?:python3?\s+-m\s+)?"
    r"(?:pytest\b|jest\b|vitest\b|npx\s+(?:vitest|jest|playwright\s+test)\b|"
    r"(?:npm|yarn|pnpm)\s+(?:run\s+)?test\b|go\s+test\b|cargo\s+test\b|make\s+test\b)"
)
_BUILD_RE = re.compile(
    _START + r"(?:npm\s+(?:install|ci|run\s+build)\b|pip3?\s+install\b|yarn\s+install\b|pnpm\s+install\b|"
    r"docker\s+build\b|cargo\s+build\b|go\s+build\b|make\s*$|make\s+(?:all|build)\b)"
)
_GIT_LOG_RE = re.compile(r"^\s*git\s+log\b(?P<rest>.*)$")
_GIT_DIFF_RE = re.compile(r"^\s*git\s+diff(?:\s+(--cached|--staged))?\s*$")
_LOG_LIMITED = re.compile(r"(?:^|\s)(?:-n\s*\d+|-\d+|--max-count[= ]\d+|-p\b|--stat\b|--patch\b)")
_LOG_FORMATTED = re.compile(r"(?:^|\s)(?:--oneline|--format|--pretty|--graph)\b")

FAIL_PATTERN = r"(FAIL|ERROR|Error|error:|failed|Traceback|AssertionError|✗|❌|panic:)"


def _wrap(cmd: str, filter_cmd: str) -> str:
    """元のコマンドを一時ファイルへ落とし、絞った出力を出し、元の終了コードで終える。"""
    return (
        f'__o=$(mktemp); {{ {cmd}; }} >"$__o" 2>&1; __rc=$?; '
        f'{filter_cmd}; rm -f "$__o"; exit $__rc'
    )


def rewrite(cmd: str) -> tuple[str, str] | None:
    """(書き換え後コマンド, systemMessage) を返す。触らないときは None。"""
    if "FULL_OUTPUT=1" in cmd:
        return None
    if "\n" in cmd.strip():
        return None                     # 複数行・ヒアドキュメントは触らない（壊す方が高くつく）
    stripped = _QUOTED.sub("", _HEREDOC.sub("", cmd))

    if _TEST_RE.search(stripped):
        new = _wrap(cmd, f"grep -A 5 -E '{FAIL_PATTERN}' \"$__o\" | head -120; "
                         f"echo '--- 末尾 5 行（集計）---'; tail -5 \"$__o\"")
        return new, ("テスト出力を失敗行の前後と末尾 5 行に絞りました（filter-output.py）。"
                     f"全量が要るとき: FULL_OUTPUT=1 {cmd}")

    if _BUILD_RE.search(stripped):
        new = _wrap(cmd, 'tail -40 "$__o"')
        return new, (f"install / build の出力を末尾 40 行に絞りました（filter-output.py）。全量: FULL_OUTPUT=1 {cmd}")

    m = _GIT_LOG_RE.match(stripped)
    if m and not _LOG_LIMITED.search(m.group("rest")):
        extra = " -20" if _LOG_FORMATTED.search(m.group("rest")) else " --oneline -20"
        new = re.sub(r"^(\s*git\s+log)", lambda mm: mm.group(1) + extra, cmd, count=1)
        return new, f"git log に件数指定が無いので `{extra.strip()}` を補いました。全履歴: FULL_OUTPUT=1 {cmd}"

    m = _GIT_DIFF_RE.match(stripped)
    if m:
        new = "git diff --stat" + (f" {m.group(1)}" if m.group(1) else "")
        return new, ("git diff に対象指定が無いので --stat に置き換えました。"
                     "個別の差分は `git diff -- <path>`、全量は FULL_OUTPUT=1 git diff")
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    tool_input = data.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "")
    if not cmd:
        return 0
    r = rewrite(cmd)
    if r is None:
        return 0
    new_cmd, msg = r
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "command": new_cmd},
        },
        "systemMessage": msg,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
