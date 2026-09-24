#!/bin/bash
# init-lifecycle.sh — 工程文書（RFD〜保守運用）の雛形を対象プロジェクトへ配置する
#
# 配置先: <対象プロジェクト>/docs/lifecycle/
# 規約: skills/dev-lifecycle/SKILL.md
#
# 使い方:
#   ./00_導入/02_プロジェクト配布/init-lifecycle.sh <対象プロジェクトのパス> [--github]
#     --github : GitHub の Issue / PR テンプレートも .github/ へ配置する
#
# 既存ファイルは上書きしない（スキップして報告する）。
set -e
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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
for f in "$KIT_DIR/02_共通/ひな形/lifecycle/"*.md; do
  base=$(basename "$f")
  dest="$TARGET/docs/lifecycle/$base"
  if [ -e "$dest" ]; then
    echo "  ↷ スキップ（既存）: $base"; SKIP=$((SKIP+1))
  else
    cp "$f" "$dest"; echo "  ✅ $base"; NEW=$((NEW+1))
  fi
done
echo "工程文書: 新規 $NEW / スキップ $SKIP"

# --- 工程承認記録 -----------------------------------------------------------
# 1工程1ファイル。雛形は templates/lifecycle/approvals/phase-approval.md。
# 仕様: 02_共通/ひな形/lifecycle/approvals/README.md / 検査: scripts/check-approval.sh
mkdir -p "$TARGET/docs/lifecycle/approvals"
ANEW=0; ASKIP=0
dest="$TARGET/docs/lifecycle/approvals/README.md"
if [ -e "$dest" ]; then ASKIP=$((ASKIP+1))
else cp "$KIT_DIR/02_共通/ひな形/lifecycle/approvals/README.md" "$dest"; ANEW=$((ANEW+1)); fi
while IFS='|' read -r n name covers; do
  [ -n "$n" ] || continue
  dest="$TARGET/docs/lifecycle/approvals/phase-${n}.md"
  if [ -e "$dest" ]; then
    echo "  ↷ スキップ（既存）: approvals/phase-${n}.md"; ASKIP=$((ASKIP+1)); continue
  fi
  covers_args=$(echo "$covers" | tr -d ' ' | tr ',' ' ')
  sed -e "s|__PHASE_NAME__|${name}|g" \
      -e "s|__PHASE__|${n}|g" \
      -e "s|__COVERS_ARGS__|${covers_args}|g" \
      -e "s|__COVERS__|${covers}|g" \
      "$KIT_DIR/02_共通/ひな形/lifecycle/approvals/phase-approval.md" > "$dest"
  echo "  ✅ approvals/phase-${n}.md"; ANEW=$((ANEW+1))
done <<'PHASES'
0|RFD|docs/lifecycle/00-rfd.md
1|要件定義|docs/lifecycle/01-requirements.md
2|基本設計|docs/lifecycle/02-basic-design.md
3|詳細設計|docs/lifecycle/03-detailed-design.md
4|実装|docs/lifecycle/04-implementation.md
5|単体テスト|docs/lifecycle/05-unit-test.md
6|結合テスト|docs/lifecycle/06-integration-test.md
7|システムテスト|docs/lifecycle/07-system-test.md
8|受け入れテスト|docs/lifecycle/08-acceptance-test.md
9|保守運用|docs/lifecycle/09-operations.md
PHASES
echo "工程承認記録: 新規 $ANEW / スキップ $ASKIP"

if [ "$WITH_GITHUB" -eq 1 ]; then
  echo ""
  echo "=== GitHub テンプレートを配置 ==="
  mkdir -p "$TARGET/.github/ISSUE_TEMPLATE"
  for f in "$KIT_DIR/02_共通/ひな形/github/ISSUE_TEMPLATE/"*.md; do
    base=$(basename "$f")
    dest="$TARGET/.github/ISSUE_TEMPLATE/$base"
    if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: ISSUE_TEMPLATE/$base"
    else cp "$f" "$dest"; echo "  ✅ ISSUE_TEMPLATE/$base"; fi
  done
  dest="$TARGET/.github/pull_request_template.md"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: pull_request_template.md"
  else cp "$KIT_DIR/02_共通/ひな形/github/pull_request_template.md" "$dest"; echo "  ✅ pull_request_template.md"; fi

  mkdir -p "$TARGET/.github/workflows"
  dest="$TARGET/.github/workflows/lifecycle-check.yml"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: workflows/lifecycle-check.yml"
  else cp "$KIT_DIR/02_共通/ひな形/github/workflows/lifecycle-check.yml" "$dest"; echo "  ✅ workflows/lifecycle-check.yml"; fi

  mkdir -p "$TARGET/scripts"
  dest="$TARGET/scripts/trace-check.sh"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: scripts/trace-check.sh"
  else cp "$KIT_DIR/02_共通/ツール/trace-check.sh" "$dest"; chmod +x "$dest"; echo "  ✅ scripts/trace-check.sh（CI から実行するため同梱）"; fi
  # 版つきリンク（C7 suspect・--impact・--refresh）の版の計算。trace-check.sh が隣を参照する
  dest="$TARGET/scripts/section_hash.py"
  if [ -e "$dest" ]; then echo "  ↷ スキップ（既存）: scripts/section_hash.py"
  else cp "$KIT_DIR/02_共通/ツール/section_hash.py" "$dest"; chmod +x "$dest"; echo "  ✅ scripts/section_hash.py（trace-check.sh の C7 が使う）"; fi
fi

echo ""
echo "=== 完了 ==="
echo "次にやること:"
echo "1. docs/lifecycle/00-rfd.md から順に埋める（AI に任せる場合は /rfd → /lifecycle <工程名>）"
echo "2. 工程の区切りごとに: ./scripts/trace-check.sh docs/lifecycle"
echo "3. 工程の出口で: /phase-review <工程番号> → 人間が docs/lifecycle/approvals/phase-<n>.md を埋める"
echo "4. 承認の有効性を確認: ./scripts/check-approval.sh（--phase <n> で1工程だけ）"
echo "5. 工程の入口/出口基準: skills/dev-lifecycle/references/phase-gates.md"
echo ""
echo "未承認のまま次工程へ進むのを物理的に止めたい場合: touch .claude/phase-gate"
