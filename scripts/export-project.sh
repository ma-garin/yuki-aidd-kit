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
KIT_VERSION="$(cat "$KIT_DIR/VERSION" 2>/dev/null || echo unknown) $(git -C "$KIT_DIR" rev-parse --short HEAD 2>/dev/null || echo -) $(date -I)"

echo "=== AIDD Kit プロジェクト配布（版: $KIT_VERSION）==="
echo "対象: $TARGET"

backup_if_exists() {
  if [ -e "$1" ]; then
    cp -r "$1" "$1.bak"
    echo "⚠ 既存の $(basename "$1") を $(basename "$1").bak に退避（手動マージ推奨）"
  fi
}

mkdir -p "$TARGET/.claude/skills" "$TARGET/.claude/commands" "$TARGET/.claude/hooks" "$TARGET/.claude/rules"

# スキル一式（フルコピー。DAILY/LIBRARYの絞り込みはINDEX.mdを見て各エージェントが行う）
cp -r "$KIT_DIR/skills/"* "$TARGET/.claude/skills/"
echo "✅ スキル: $(ls "$KIT_DIR/skills" | wc -l)個"

# コマンド一式
cp "$KIT_DIR/commands/"*.md "$TARGET/.claude/commands/"
echo "✅ コマンド: $(ls "$KIT_DIR/commands" | wc -l)個"

# Hooks（プロジェクトスコープはリポジトリ相対パスで参照する）
# 前提: Claude Code のプロジェクトスコープ hooks はプロジェクトルートを
# 作業ディレクトリとして実行される。環境によって異なる場合は要検証。
cp "$KIT_DIR/hooks/"*.sh "$KIT_DIR/hooks/"*.py "$TARGET/.claude/hooks/"
chmod +x "$TARGET/.claude/hooks/"*.sh "$TARGET/.claude/hooks/"*.py
backup_if_exists "$TARGET/.claude/settings.json"
cat > "$TARGET/.claude/settings.json" << 'JSON'
{
  "effortLevel": "high",
  "autoCompactWindow": "200k",
  "bashOutputMaxChars": 12000,
  "env": { "CLAUDE_CODE_GOAL_CHECKIN_MINUTES": "0" },
  "statusLine": { "type": "command", "command": "python3 .claude/hooks/statusline.py", "padding": 2 },
  "hooks": {
    "PreToolUse": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/instruction-guard.py", "timeout": 5, "statusMessage": "保守者の指示に応答済みか確認中" } ] },
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/block-ci.py", "timeout": 5, "statusMessage": "自己ウェイク・CI 待ちでないか確認中" } ] },
      {
        "matcher": "Read|Grep|Glob",
        "hooks": [
          { "type": "command", "command": "python3 .claude/hooks/pre-read-guard.py", "timeout": 5, "statusMessage": "読む価値とサイズを確認中" },
          { "type": "command", "command": "bash .claude/hooks/block-explore.sh", "timeout": 5, "statusMessage": "実装モードの再探索を確認中" }
        ]
      },
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          { "type": "command", "command": "bash .claude/hooks/pre-write-check.sh" },
          { "type": "command", "command": "python3 .claude/hooks/block-phase.py", "timeout": 25, "statusMessage": "前工程の承認を確認中" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python3 .claude/hooks/block-gates.py", "timeout": 10, "statusMessage": "ゲート実行の要否を確認中" },
          { "type": "command", "command": "python3 .claude/hooks/filter-output.py", "timeout": 5, "statusMessage": "冗長な出力を絞る書き換えを確認中" }
        ]
      }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/prompt-priority.py", "timeout": 5 },
                  { "type": "command", "command": "python3 .claude/hooks/context-guard.py", "timeout": 5 } ] }
    ],
    "PreCompact": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/pre-compact.py", "timeout": 5 } ] }
    ],
    "InstructionsLoaded": [
      { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/log-instructions.py", "timeout": 5 } ] }
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
          { "type": "command", "command": "python3 .claude/hooks/reply-language.py", "timeout": 5 },
          { "type": "command", "command": "bash .claude/hooks/session-summary.sh" }
        ]
      }
    ]
  }
}
JSON
echo "✅ settings: effortLevel=high / autoCompactWindow=200k / bashOutputMaxChars=12000（トークン節約の既定。設計判断のときだけ /effort xhigh）"
echo "✅ Hooks: $(ls "$KIT_DIR/hooks/"*.sh "$KIT_DIR/hooks/"*.py | wc -l | tr -d ' ')個（プロジェクトスコープ・相対パス参照。block-explore.sh / block-phase.py も配線済み: .claude/mode ・ .claude/phase-gate が無ければ何もしない。filter-output.py が冗長な出力を絞る: 全量は FULL_OUTPUT=1）"

# Rules（.claude/rules/*.md は Claude Code が常時読み込む。speed-harness.md の H-2 はプロジェクトごとに埋める）
cp "$KIT_DIR/rules/"*.md "$TARGET/.claude/rules/"
echo "✅ Rules: $(ls "$KIT_DIR/rules/"*.md | wc -l | tr -d ' ')個（.claude/rules/。speed-harness.md の H-2 環境チートシートを埋めること）"

# 版の刻印（配布先がどの版のキットから出たかを判別するため。書式: <VERSION> <commit> <日付>）
printf '%s\n' "$KIT_VERSION" > "$TARGET/.claude/KIT_VERSION"
echo "✅ .claude/KIT_VERSION: $KIT_VERSION"

# INDEX.md（フルコピーなのでDAILY/LIBRARYの地図として同梱する）
cp "$KIT_DIR/INDEX.md" "$TARGET/.claude/INDEX.md"
echo "✅ INDEX.md 同梱"

# テンプレート（dev-lifecycle の工程雛形など。スキル本文から参照されるため同梱する）
mkdir -p "$TARGET/.claude/templates"
cp -r "$KIT_DIR/templates/"* "$TARGET/.claude/templates/"
echo "✅ templates 同梱（lifecycle 工程雛形・design-system・ADR ほか）"

# トレーサビリティ検査スクリプト（工程文書を使う場合に CI/ローカル双方から実行する）
mkdir -p "$TARGET/scripts"
if [ -e "$TARGET/scripts/trace-check.sh" ]; then
  echo "↷ scripts/trace-check.sh は既存のためスキップ"
else
  cp "$KIT_DIR/tools/trace-check.sh" "$TARGET/scripts/trace-check.sh"
  chmod +x "$TARGET/scripts/trace-check.sh"
  echo "✅ scripts/trace-check.sh 同梱"
fi

# テスト活動のゲートスクリプト（機能契約ハーネス・UI 検証マーカー。文書雛形は init-test-docs.sh で配置）
for s in quality_harness.py ui-hash.py pre-commit-ui-gate.sh check_approval.py check-approval.sh phase-hash.py test_metrics.py test-metrics.sh; do
  if [ -e "$TARGET/scripts/$s" ]; then echo "↷ scripts/$s は既存のためスキップ"
  else cp "$KIT_DIR/tools/$s" "$TARGET/scripts/$s"; chmod +x "$TARGET/scripts/$s"; echo "✅ scripts/$s 同梱"; fi
done

# Codex用 AGENTS.md（INDEX.md参照をプロジェクト相対パスに変換）
backup_if_exists "$TARGET/AGENTS.md"
sed 's#<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md#.claude/INDEX.md#' \
  "$KIT_DIR/AGENTS.md.template" > "$TARGET/AGENTS.md"

# Claude Code用 CLAUDE.md（プロジェクトスコープ。同じくINDEX.md参照を変換）
backup_if_exists "$TARGET/CLAUDE.md"
sed 's#<YOUR_WORKSPACE>/yuki-aidd-kit/INDEX.md#.claude/INDEX.md#' \
  "$KIT_DIR/CLAUDE.md.template" > "$TARGET/CLAUDE.md"
echo "✅ AGENTS.md（共通規約の本体）/ CLAUDE.md（@AGENTS.md + Claude Code 固有）生成済み（INDEX 参照は .claude/INDEX.md に調整済み）"

echo ""
echo "=== 完了 ==="
echo "次にやること:"
echo "1. $TARGET/AGENTS.md と $TARGET/CLAUDE.md 内の残りの <...> プレースホルダ（GITHUB_OWNER等）を埋める"
echo "2. $TARGET で: git add .claude AGENTS.md CLAUDE.md scripts/ && git commit"
echo "3. これでCodex・リモート/エフェメラルなClaude Code・teammateのclone先でも自動的に効く"
echo "4. 工程（RFD〜保守運用）で進める場合: $KIT_DIR/scripts/init-lifecycle.sh $TARGET --github"
echo "5. サンドボックス（denyRead / network allowlist / permissions）を使う場合: $KIT_DIR/templates/settings.sandbox.json を .claude/settings.json にマージ"
echo "6. テスト戦略・DoD・29119 文書・機能契約を置く場合: $KIT_DIR/scripts/init-test-docs.sh $TARGET --ci"
echo "7. 未承認のまま次工程へ進むのを物理的に止める場合: touch $TARGET/.claude/phase-gate（判定は scripts/check-approval.sh）"
