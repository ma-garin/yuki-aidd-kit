#!/bin/bash
# install.sh — AIDD Kitを ~/.claude へ導入
set -e
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLAUDE_DIR="$HOME/.claude"
KIT_VERSION="$(cat "$KIT_DIR/VERSION" 2>/dev/null || echo unknown) $(git -C "$KIT_DIR" rev-parse --short HEAD 2>/dev/null || echo -) $(date -I)"

echo "=== AIDD Kit インストール（版: $KIT_VERSION）==="
mkdir -p "$CLAUDE_DIR/skills" "$CLAUDE_DIR/commands" "$CLAUDE_DIR/hooks" "$CLAUDE_DIR/rules/aidd-kit" "$HOME/.agents/skills"

# グローバルCLAUDE.md（既存があればバックアップ）
if [ -f "$CLAUDE_DIR/CLAUDE.md" ]; then
  cp "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md.bak"
  echo "⚠ 既存のCLAUDE.mdを CLAUDE.md.bak に退避（手動マージ推奨）"
fi
cp "$KIT_DIR/03_ClaudeCode/CLAUDE.md.template" "$CLAUDE_DIR/CLAUDE.md"
# 共通規約の本体 AGENTS.md（CLAUDE.md の `@AGENTS.md` が ~/.claude/AGENTS.md を解決する）
if [ -f "$CLAUDE_DIR/AGENTS.md" ]; then
  cp "$CLAUDE_DIR/AGENTS.md" "$CLAUDE_DIR/AGENTS.md.bak"
  echo "⚠ 既存のAGENTS.mdを AGENTS.md.bak に退避（手動マージ推奨）"
fi
cp "$KIT_DIR/04_Codex/AGENTS.md.template" "$CLAUDE_DIR/AGENTS.md"

# スキル
cp -r "$KIT_DIR/03_ClaudeCode/skills/"* "$CLAUDE_DIR/skills/"
# Codex用に同じスキルを ~/.agents/skills/ にも配る（出典: https://learn.chatgpt.com/codex/build-skills）
cp -r "$KIT_DIR/03_ClaudeCode/skills/"* "$HOME/.agents/skills/"
echo "✅ スキル: $(ls "$KIT_DIR/03_ClaudeCode/skills" | wc -l)個（~/.claude/skills/ と ~/.agents/skills/ の両方）"

# コマンド
cp "$KIT_DIR/03_ClaudeCode/commands/"*.md "$CLAUDE_DIR/commands/"
echo "✅ コマンド: $(ls "$KIT_DIR/03_ClaudeCode/commands" | wc -l)個"

# Hooks
cp "$KIT_DIR/03_ClaudeCode/hooks/"*.sh "$KIT_DIR/03_ClaudeCode/hooks/"*.py "$CLAUDE_DIR/hooks/"
chmod +x "$CLAUDE_DIR/hooks/"*.sh "$CLAUDE_DIR/hooks/"*.py
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  echo "⚠ settings.json が既存。hooks / statusLine と、トークン節約の 3 キー（effortLevel=high / autoCompactWindow=200k / bashOutputMaxChars=12000）と env.CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0を手動でマージしてください（参照: agent/hooks/settings.json）"
else
  cp "$KIT_DIR/03_ClaudeCode/hooks/settings.json" "$CLAUDE_DIR/settings.json"
fi
echo "✅ Hooks: $(ls "$KIT_DIR/03_ClaudeCode/hooks/"*.sh "$KIT_DIR/03_ClaudeCode/hooks/"*.py | wc -l | tr -d ' ')個"
# 指示優先の 3 hook は既存 settings.json にも merge する（A-13。手動マージ待ちにしない）
python3 "$KIT_DIR/00_導入/01_インストール/install_guard.py" --home "$HOME" --hooks-dir "$KIT_DIR/03_ClaudeCode/hooks" | grep -E "配線|変更なし" || true

# 判定スクリプト（block-phase.py が ~/.claude/scripts/ から探す。phase-hash.py は同じ場所に必要）
mkdir -p "$CLAUDE_DIR/scripts"
cp "$KIT_DIR/02_共通/ツール/check_approval.py" "$KIT_DIR/02_共通/ツール/phase-hash.py" "$CLAUDE_DIR/scripts/"
chmod +x "$CLAUDE_DIR/scripts/"*.py
echo "✅ Scripts: check_approval.py / phase-hash.py（工程承認ゲートの判定。.claude/phase-gate があるプロジェクトでのみ発動）"

# Rules（常時読み込み。~/.claude/rules 配下の別ディレクトリに同名があれば重複を避けてスキップ）
RULES_OK=0
for f in "$KIT_DIR/02_共通/rules/"*.md; do
  n=$(basename "$f")
  if find "$CLAUDE_DIR/rules" -path "$CLAUDE_DIR/rules/aidd-kit" -prune -o -name "$n" -print 2>/dev/null | grep -q .; then
    echo "↷ rules/$n は ~/.claude/rules 配下に既存のためスキップ（手動で差分確認）"
  else
    cp "$f" "$CLAUDE_DIR/rules/aidd-kit/$n"; RULES_OK=$((RULES_OK+1))
  fi
done
echo "✅ Rules: ${RULES_OK}個（~/.claude/rules/aidd-kit/）"

# 版の刻印（verify.sh が表示。配布先と同じ書式: <VERSION> <commit> <日付>）
# 利用者向け資料（01_利用者向け資料/ 直下: 利用ガイド・操作マニュアルほか）。共有の ~/.claude では rules と同じく aidd-kit/ で名前空間を分ける
mkdir -p "$CLAUDE_DIR/docs/aidd-kit"
DOCS_N=0
for f in "$KIT_DIR/01_利用者向け資料/"*; do
  [ -f "$f" ] || continue
  cp "$f" "$CLAUDE_DIR/docs/aidd-kit/"; DOCS_N=$((DOCS_N+1))
done
echo "✅ 利用者向け資料: ${DOCS_N}個（$CLAUDE_DIR/docs/aidd-kit/。まず 01_利用ガイド.html を開く）"

printf '%s\n' "$KIT_VERSION" > "$CLAUDE_DIR/KIT_VERSION"
echo "✅ KIT_VERSION: $KIT_VERSION"

# Codex用
echo ""
echo "Codexを使う場合: ln -s ~/.claude/AGENTS.md ~/.codex/AGENTS.md（または cp）。CLAUDE.md と同じ本体を読ませる"
echo ""
echo "=== 完了 ==="
echo "確認: ./00_導入/01_インストール/verify.sh"
