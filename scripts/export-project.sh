#!/bin/bash
# export-project.sh — キットをプロジェクト単位で配布用に書き出す
#
# scripts/install.sh（~/.claude へのグローバル導入。自分のPC上で複数プロジェクトを
# 横断する日常運用向け）とは別の用途。こちらは対象プロジェクトの直下に
# .claude/（skills・commands・hooks・settings.json・INDEX.md）と AGENTS.md・CLAUDE.md
# を書き出す。生成物は対象プロジェクトのgitにコミットする想定で、Codex・
# リモート/エフェメラルなClaude Code環境・teammateのclone先でも
# install不要でそのまま効く。
set -e
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$1"

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "使い方: ./scripts/export-project.sh <対象プロジェクトのパス>"
  echo "（対象ディレクトリが存在している必要があります）"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

echo "=== AIDD Kit プロジェクト配布 ==="
echo "対象: $TARGET"

backup_if_exists() {
  if [ -e "$1" ]; then
    cp -r "$1" "$1.bak"
    echo "⚠ 既存の $(basename "$1") を $(basename "$1").bak に退避（手動マージ推奨）"
  fi
}

mkdir -p "$TARGET/.claude/skills" "$TARGET/.claude/commands" "$TARGET/.claude/hooks"

# スキル一式（フルコピー。DAILY/LIBRARYの絞り込みはINDEX.mdを見て各エージェントが行う）
cp -r "$KIT_DIR/skills/"* "$TARGET/.claude/skills/"
echo "✅ スキル: $(ls "$KIT_DIR/skills" | wc -l)個"

# コマンド一式
cp "$KIT_DIR/claude-code/commands/"*.md "$TARGET/.claude/commands/"
echo "✅ コマンド: $(ls "$KIT_DIR/claude-code/commands" | wc -l)個"

# Hooks（プロジェクトスコープはリポジトリ相対パスで参照する）
# 前提: Claude Code のプロジェクトスコープ hooks はプロジェクトルートを
# 作業ディレクトリとして実行される。環境によって異なる場合は要検証。
cp "$KIT_DIR/claude-code/hooks/"*.sh "$TARGET/.claude/hooks/"
chmod +x "$TARGET/.claude/hooks/"*.sh
backup_if_exists "$TARGET/.claude/settings.json"
cat > "$TARGET/.claude/settings.json" << 'JSON'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/pre-write-check.sh" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/post-write-html.sh" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/session-summary.sh" }
        ]
      }
    ]
  }
}
JSON
echo "✅ Hooks: 3個（プロジェクトスコープ・相対パス参照）"

# INDEX.md（フルコピーなのでDAILY/LIBRARYの地図として同梱する）
cp "$KIT_DIR/INDEX.md" "$TARGET/.claude/INDEX.md"
echo "✅ INDEX.md 同梱"

# Codex用 AGENTS.md（INDEX.md参照をプロジェクト相対パスに変換）
backup_if_exists "$TARGET/AGENTS.md"
sed 's#<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md#.claude/INDEX.md#' \
  "$KIT_DIR/AGENTS.md.template" > "$TARGET/AGENTS.md"

# Claude Code用 CLAUDE.md（プロジェクトスコープ。同じくINDEX.md参照を変換）
backup_if_exists "$TARGET/CLAUDE.md"
sed 's#<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md#.claude/INDEX.md#' \
  "$KIT_DIR/CLAUDE.md.template" > "$TARGET/CLAUDE.md"
echo "✅ AGENTS.md / CLAUDE.md 生成済み（.claude/INDEX.md を参照する形に調整済み）"

echo ""
echo "=== 完了 ==="
echo "次にやること:"
echo "1. $TARGET/AGENTS.md と $TARGET/CLAUDE.md 内の残りの <...> プレースホルダ（GITHUB_OWNER等）を埋める"
echo "2. $TARGET で: git add .claude AGENTS.md CLAUDE.md && git commit"
echo "3. これでCodex・リモート/エフェメラルなClaude Code・teammateのclone先でも自動的に効く"
