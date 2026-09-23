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
  # 工程承認ゲート（B-21）: .claude/phase-gate が無いプロジェクトでは何もしない（常に配線してよい）。
  # block-phase.py（03_ClaudeCode/hooks/block-phase.py:95,105）と同じ基準を、Codex 等 Claude Code の hook 層が
  # 効かない経路でも通すために pre-commit でも行う。dev-lifecycle の手順は「成果物の作成・commit」が
  # 「承認」より前（手順3→5）なので、当該工程が未承認なだけの初稿は通す。拒否するのは:
  #   (a) 前工程の承認ゲートを通らない（--gate N が 1 か 2）
  #   (b) 当該工程の承認記録が判定不能（--phase N の状態が「判定不能」）
  #   (c) 当該工程が承認済みだったのに成果物が変わり失効した（--phase N の状態が「失効」）
  # 判定不能を合格に数えない。承認記録が無い／差し戻し中の「未承認」はここでは拒否しない（初稿はここを通る）。
  cat <<'GATE'
if [ -f "$ROOT/.claude/phase-gate" ]; then
  CHECKER="$ROOT/scripts/check_approval.py"
  STAGED_LC=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '^docs/lifecycle/0[0-9]-[^/]+\.md$' || true)
  if [ -n "$STAGED_LC" ]; then
    if [ ! -f "$CHECKER" ]; then
      echo "❌ 工程承認ゲート（.claude/phase-gate）が有効ですが scripts/check_approval.py がありません"
      echo "   ./00_導入/02_プロジェクト配布/export-project.sh . を再実行するか、使わないなら .claude/phase-gate を削除してください"
      exit 1
    fi
    while IFS= read -r lf; do
      [ -n "$lf" ] || continue
      n=$(printf '%s' "$lf" | sed -E 's#^docs/lifecycle/0([0-9])-.*$#\1#')
      GATE_OUT=$(python3 "$CHECKER" --root "$ROOT" --gate "$n" 2>&1)
      GATE_RC=$?
      if [ "$GATE_RC" -ne 0 ]; then
        echo "❌ 第${n}工程 承認ゲート未通過（${lf}）— 前工程が未承認・失効・判定不能です（判定不能を合格に数えない）"
        echo "$GATE_OUT" | sed 's/^/   /'
        exit 1
      fi
      PHASE_OUT=$(python3 "$CHECKER" --root "$ROOT" --phase "$n" 2>&1)
      if printf '%s\n' "$PHASE_OUT" | grep -q '判定不能'; then
        echo "❌ 第${n}工程 承認ゲート未通過（${lf}）— 承認記録が判定不能です（判定不能を合格に数えない）"
        echo "$PHASE_OUT" | sed 's/^/   /'
        exit 1
      fi
      if printf '%s\n' "$PHASE_OUT" | grep -q '失効'; then
        echo "❌ 第${n}工程 承認ゲート未通過（${lf}）— 承認後に成果物が変更され失効しています"
        echo "   docs/lifecycle/approvals/phase-${n}.md の判定を「未記入」に戻すか、承認を取り直してください"
        echo "$PHASE_OUT" | sed 's/^/   /'
        exit 1
      fi
      # ここまで来たら「承認済み」または「未承認（記録が無い・差し戻し中）の初稿」— どちらも通す
    done <<< "$STAGED_LC"
  fi
fi
GATE
  echo 'exit 0'
} > "$HOOK"
chmod +x "$HOOK"

echo "✅ $HOOK に配線しました"
[ "$HAS_SECRET" = true ] && echo "   - scripts/pre-commit（秘密情報スキャン。gitleaks があれば使う）"
[ "$HAS_UI" = true ]     && echo "   - scripts/pre-commit-ui-gate.sh（UI 変更に .ui-verified を要求）"
echo "   - 工程承認ゲート（.claude/phase-gate があるときだけ有効。scripts/check_approval.py --phase/--gate）"
echo ""
echo "確認: $TARGET で秘密情報を含むファイルを stage して git commit すると止まります。"
echo "解除: ./00_導入/02_プロジェクト配布/install-git-hooks.sh $TARGET --uninstall"
