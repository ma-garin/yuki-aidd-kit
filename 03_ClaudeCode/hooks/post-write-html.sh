#!/bin/bash
# post-write-html.sh
# HTMLファイル保存後: サイズ確認・部分編集推奨の通知
# Claude Code hooks はツール入力を stdin の JSON で渡す（tool_input.file_path）

INPUT=$(cat)
if command -v jq >/dev/null 2>&1; then
  FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  FILE=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
fi
if [ -z "$FILE" ] || [[ "$FILE" != *.html ]]; then exit 0; fi

SIZE=$(wc -c < "$FILE" 2>/dev/null || echo 0)
LINES=$(wc -l < "$FILE" 2>/dev/null || echo 0)
SIZE_KB=$((SIZE / 1024))

echo "=== [AIDD Hook: post-write HTML] ==="
echo "📄 $FILE — ${LINES}行 / ${SIZE_KB}KB"

# 500行超えたら部分編集推奨
if [ "$LINES" -gt 500 ]; then
  echo "💡 500行超: 次回編集は全体再生成でなく部分置換編集を推奨（トークン節約）"
fi

# localStorageスキーマの存在確認
if ! grep -q "localStorage" "$FILE" 2>/dev/null; then
  if grep -q "function\|class " "$FILE" 2>/dev/null; then
    echo "💡 データ永続化: localStorageが未使用です。必要であれば追加を検討"
  fi
fi

echo "====================================="
exit 0
