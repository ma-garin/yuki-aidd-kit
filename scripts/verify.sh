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
if [ -f "$CLAUDE_DIR/KIT_VERSION" ]; then echo "導入済みの版: $(cat "$CLAUDE_DIR/KIT_VERSION")"; fi
echo "リポジトリの版: $(cat "$KIT_DIR/VERSION" 2>/dev/null || echo unknown) $(git -C "$KIT_DIR" rev-parse --short HEAD 2>/dev/null || echo -)"
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
for f in "$KIT_DIR/claude-code/hooks/"*.sh "$KIT_DIR/claude-code/hooks/"*.py; do
  h=$(basename "$f")
  check "$h" "$CLAUDE_DIR/hooks/$h"
done

echo "[Rules]"
for f in "$KIT_DIR/rules/"*.md; do
  n=$(basename "$f")
  if find "$CLAUDE_DIR/rules" -name "$n" 2>/dev/null | grep -q .; then
    echo "  ✅ rules/$n"; OK=$((OK+1))
  else
    echo "  ❌ rules/$n（未配置: $CLAUDE_DIR/rules/**/$n）"; NG=$((NG+1))
  fi
done

echo ""
echo "結果: OK=$OK / NG=$NG"
if [ "$NG" -eq 0 ]; then echo "✅ 全て正常"; exit 0; else echo "⚠ 未配置あり。install.shを再実行してください"; exit 1; fi
