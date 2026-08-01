#!/bin/bash
# init-lifecycle.sh — 工程文書（RFD〜保守運用）の雛形を対象プロジェクトへ配置する
#
# 配置先: <対象プロジェクト>/docs/lifecycle/
# 規約: skills/dev-lifecycle/SKILL.md
#
# 使い方:
#   ./scripts/init-lifecycle.sh <対象プロジェクトのパス> [--github]
#     --github : GitHub の Issue / PR テンプレートも .github/ へ配置する
#
# 既存ファイルは上書きしない（スキップして報告する）。
set -e
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=""
WITH_GITHUB=0

while [ $# -gt 0 ]; do
  case "$1" in
    --github) WITH_GITHUB=1; shift ;;
    -h|--help) echo "使い方: $0 <対象プロジェクトのパス> [--github]"; exit 0 ;;
    *) TARGET="$1"; shift ;;
  esac
done

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "使い方: $0 <対象プロジェクトのパス> [--github]"
  echo "（対象ディレクトリが存在している必要があります）"
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

echo "=== 工程文書の雛形を配置 ==="
echo "対象: $TARGET/docs/lifecycle"

mkdir -p "$TARGET/docs/lifecycle"
NEW=0; SKIP=0
for f in "$KIT_DIR/templates/lifecycle/"*.md; do
  base=$(basename "$f")
  dest="$TARGET/docs/lifecycle/$base"
  if [ -e "$dest" ]; then
    echo "  ↷ スキップ（既存）: $base"; SKIP=$((SKIP+1))
  else
    cp "$f" "$dest"; echo "  ✅ $base"; NEW=$((NEW+1))
  fi
done
echo "工程文書: 新規 $NEW / スキップ $SKIP"

if [ "$WITH_GITHUB" -eq 1 ]; then
  echo ""
  echo "=== GitHub テンプレートを配置 ==="
  mkdir -p "$TARGET/.github/ISSUE_TEMPLATE"
  for f in "$KIT_DIR/templates/github/ISSUE_TEMPLATE/"*.md; do
    base=$(basename "$f")
    dest="$TARGET/.github/ISSUE_TEMPLATE/$base"
    if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: ISSUE_TEMPLATE/$base"
    else cp "$f" "$dest"; echo "  ✅ ISSUE_TEMPLATE/$base"; fi
  done
  dest="$TARGET/.github/pull_request_template.md"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: pull_request_template.md"
  else cp "$KIT_DIR/templates/github/pull_request_template.md" "$dest"; echo "  ✅ pull_request_template.md"; fi

  mkdir -p "$TARGET/.github/workflows"
  dest="$TARGET/.github/workflows/lifecycle-check.yml"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: workflows/lifecycle-check.yml"
  else cp "$KIT_DIR/github-actions/lifecycle-check.yml" "$dest"; echo "  ✅ workflows/lifecycle-check.yml"; fi

  mkdir -p "$TARGET/scripts"
  dest="$TARGET/scripts/trace-check.sh"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: scripts/trace-check.sh"
  else cp "$KIT_DIR/scripts/trace-check.sh" "$dest"; chmod +x "$dest"; echo "  ✅ scripts/trace-check.sh（CI から実行するため同梱）"; fi
fi

echo ""
echo "=== 完了 ==="
echo "次にやること:"
echo "1. docs/lifecycle/00-rfd.md から順に埋める（AI に任せる場合は /rfd → /lifecycle <工程名>）"
echo "2. 工程の区切りごとに: ./scripts/trace-check.sh docs/lifecycle"
echo "3. 工程の入口/出口基準: skills/dev-lifecycle/references/phase-gates.md"
