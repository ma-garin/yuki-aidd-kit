#!/bin/bash
# install-git-hooks.sh — 秘密情報スキャンと UI 検証マーカーのゲートを .git/hooks/pre-commit に配線する
#
# なぜ必要か（B-14 / `06_保守者向け/01_内部仕様/11_目標運用モデル.md` D-4）:
#   Claude Code の hook 層は Codex では効かない。両方で効くのは **git hook 層とスクリプト層**だけ。
#   これまで配線手順は文章にしかなく、配布しても実際には繋がっていない可能性が高かった。
#
# 使い方:
#   ./00_導入/02_プロジェクト配布/install-git-hooks.sh <対象プロジェクトのパス>
#   ./00_導入/02_プロジェクト配布/install-git-hooks.sh <対象> --uninstall   # 退避した元の hook へ戻す
#
# 前提: 対象に scripts/pre-commit（秘密情報）と scripts/pre-commit-ui-gate.sh（UI）が置かれていること。
#   `export-project.sh` が両方を配る。片方しか無い場合は在るものだけ配線する。
# 既存の .git/hooks/pre-commit は .bak に退避してから上書きする（冪等。二重配線しない）。
set -uo pipefail

TARGET="${1:-}"
MODE="${2:-}"
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "使い方: ./00_導入/02_プロジェクト配布/install-git-hooks.sh <対象プロジェクトのパス> [--uninstall]"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"
GITDIR="$(git -C "$TARGET" rev-parse --git-dir 2>/dev/null)" || { echo "❌ $TARGET は git リポジトリではありません"; exit 1; }
case "$GITDIR" in /*) ;; *) GITDIR="$TARGET/$GITDIR" ;; esac
HOOK="$GITDIR/hooks/pre-commit"

if [ "$MODE" = "--uninstall" ]; then
  if [ -f "$HOOK.bak" ]; then
    mv "$HOOK.bak" "$HOOK"; echo "✅ 元の pre-commit を復元しました"
  else
    rm -f "$HOOK"; echo "✅ pre-commit を削除しました（退避ファイルは無し）"
  fi
  exit 0
fi

mkdir -p "$GITDIR/hooks"
HAS_SECRET=false; HAS_UI=false
[ -f "$TARGET/scripts/pre-commit" ] && HAS_SECRET=true
[ -f "$TARGET/scripts/pre-commit-ui-gate.sh" ] && HAS_UI=true
if [ "$HAS_SECRET" = false ] && [ "$HAS_UI" = false ]; then
  echo "❌ $TARGET/scripts/ にゲートスクリプトがありません。先に export-project.sh を実行してください"
  exit 1
fi

# 既存を退避（自分が作ったものは退避しない＝再実行で .bak を壊さない）
if [ -f "$HOOK" ] && ! grep -q 'AIDD Kit git hooks' "$HOOK" 2>/dev/null; then
  cp "$HOOK" "$HOOK.bak"
  echo "⚠ 既存の pre-commit を pre-commit.bak に退避しました"
fi

{
  echo '#!/bin/bash'
  echo '# AIDD Kit git hooks — install-git-hooks.sh が生成。手で編集しないこと（再実行で上書きされる）'
  echo '# Claude Code でも Codex でも効く唯一の強制層（11_目標運用モデル.md D-4）'
  echo 'set -uo pipefail'
  echo 'ROOT="$(git rev-parse --show-toplevel)"'
  [ "$HAS_SECRET" = true ] && echo 'bash "$ROOT/scripts/pre-commit" || exit 1'
  [ "$HAS_UI" = true ]     && echo 'bash "$ROOT/scripts/pre-commit-ui-gate.sh" || exit 1'
  echo 'exit 0'
} > "$HOOK"
chmod +x "$HOOK"

echo "✅ $HOOK に配線しました"
[ "$HAS_SECRET" = true ] && echo "   - scripts/pre-commit（秘密情報スキャン。gitleaks があれば使う）"
[ "$HAS_UI" = true ]     && echo "   - scripts/pre-commit-ui-gate.sh（UI 変更に .ui-verified を要求）"
echo ""
echo "確認: $TARGET で秘密情報を含むファイルを stage して git commit すると止まります。"
echo "解除: ./00_導入/02_プロジェクト配布/install-git-hooks.sh $TARGET --uninstall"
