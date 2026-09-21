#!/bin/bash
# pre-write-check.sh
# 書き込み前にスコープ違反・秘密情報混入を検出
# Claude Code hooks はツール入力を stdin の JSON で渡す（tool_input.file_path）

INPUT=$(cat)
if command -v jq >/dev/null 2>&1; then
  FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  FILE=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
fi
if [ -z "$FILE" ]; then exit 0; fi

ERRORS=()

# APIキー・秘密情報パターン検出（ファイル名ベース）
if [[ "$FILE" =~ \.(env|pem|key|secret)$ ]]; then
  ERRORS+=("⚠ 秘密情報ファイルへの書き込み: $FILE")
fi

# 単一HTMLツールへの外部ファイル分割検出
if [[ "$FILE" =~ \.css$|\.js$ ]]; then
  PARENT=$(dirname "$FILE")
  if ls "$PARENT"/*.html &>/dev/null 2>&1; then
    ERRORS+=("⚠ 同階層にHTMLあり: 単一HTMLツールのプロジェクトならCSS/JS外部分割は規約違反です（通常のWebプロジェクトなら無視してよい）。意図的ですか？ ($FILE)")
  fi
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "=== [AIDD Hook: pre-write] ==="
  for e in "${ERRORS[@]}"; do echo "$e"; done
  echo "=============================="
fi

exit 0  # 警告のみ、ブロックしない
