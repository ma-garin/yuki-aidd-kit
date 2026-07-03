#!/bin/bash
# verify.sh — インストール確認
# チェックリストはリポジトリ実体（skills/ commands/ hooks/）から自動導出する。
# 資産を追加してもこのファイルの更新は不要（Roadmap M6 で決定）。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
OK=0; NG=0

check() {
  if [ -e "$2" ]; then echo "  ✅ $1"; OK=$((OK+1)); else echo "  ❌ $1（未配置: $2）"; NG=$((NG+1)); fi
}

echo "=== AIDD Kit インストール確認 ==="
echo "[グローバル設定]"
check "CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"
check "settings.json" "$CLAUDE_DIR/settings.json"

echo "[スキル]"
for d in "$KIT_DIR/skills/"*/; do
  s=$(basename "$d")
  check "$s" "$CLAUDE_DIR/skills/$s/SKILL.md"
done

echo "[コマンド]"
for f in "$KIT_DIR/claude-code/commands/"*.md; do
  c=$(basename "$f" .md)
  check "/$c" "$CLAUDE_DIR/commands/$c.md"
done

echo "[Hooks]"
for f in "$KIT_DIR/claude-code/hooks/"*.sh; do
  h=$(basename "$f" .sh)
  check "$h.sh" "$CLAUDE_DIR/hooks/$h.sh"
done

echo ""
echo "結果: OK=$OK / NG=$NG"
[ "$NG" -eq 0 ] && echo "✅ 全て正常" || echo "⚠ 未配置あり。install.shを再実行してください"
