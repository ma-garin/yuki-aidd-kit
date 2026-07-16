#!/bin/bash
# block-explore.sh
# 実装モード（プロジェクトルートに .claude/mode が存在する状態）で、
# 探索系ツール（Read / Grep / Glob）を物理ブロックする。
# plan 確定後の実装フェーズに再探索を止め、実装完了までの時間を短縮する目的。
#
# Claude Code の PreToolUse hook。stdin にツール入力の JSON が渡る。
# 探索を止めたいときは exit 2（ツール実行をブロックし、stderr の内容を Claude にフィードバック）。
# それ以外は exit 0（許可）。

INPUT=$(cat)

# プロジェクトルート（Claude Code が設定。無ければカレントディレクトリ）
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"
MODE_FILE="$PROJECT_DIR/.claude/mode"

# 実装モードでなければ何もしない（探索を許可）
if [ ! -f "$MODE_FILE" ]; then
  exit 0
fi

# ツール名を取得（settings.json の matcher で Read|Grep|Glob に限定済みだが二重に確認）
if command -v jq >/dev/null 2>&1; then
  TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
else
  TOOL=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null)
fi

case "$TOOL" in
  Read|Grep|Glob)
    echo "=== [AIDD Hook: block-explore] 実装モード中です ===" >&2
    echo "探索系ツール（$TOOL）は .claude/mode 存在時はブロックされます。" >&2
    echo "plan で確定済みの方針・対象ファイルに基づいて実装を進めてください。" >&2
    echo "再探索が必要になったら /plan で実装モードを解除してから調査してください。" >&2
    exit 2
    ;;
  *)
    exit 0
    ;;
esac
