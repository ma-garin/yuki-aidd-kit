#!/bin/bash
# init-test-docs.sh — テスト活動の文書雛形・機能契約・ゲートスクリプトを対象プロジェクトへ配置する
# 使い方: ./scripts/init-test-docs.sh <対象プロジェクト> [--ci]
#   docs/test/      TESTING_STRATEGY / DEFINITION_OF_DONE / iso29119-*（計画・設計仕様・完了報告・インシデント）
#   docs/           system_test_cases.csv（e2e-cycle ステップ1 の出力形式）
#   quality/        feature_contracts.yml
#   scripts/        quality_harness.py / ui-hash.py / pre-commit-ui-gate.sh
#   --ci            .github/workflows/test-gates.yml
# 既存ファイルは上書きしない。運用は skills/test-strategy/SKILL.md。
set -e
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="$1"; CI=false; [ "${2:-}" = "--ci" ] && CI=true
if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "使い方: ./scripts/init-test-docs.sh <対象プロジェクト> [--ci]"; exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"
put() { # src, dst
  if [ -e "$2" ]; then echo "↷ ${2#$TARGET/} は既存のためスキップ"
  else mkdir -p "$(dirname "$2")"; cp "$1" "$2"; echo "✅ ${2#$TARGET/}"; fi
}
echo "=== テスト活動の雛形を配置: $TARGET ==="
for f in TESTING_STRATEGY.md DEFINITION_OF_DONE.md iso29119-test-plan.md iso29119-test-design-spec.md iso29119-test-completion-report.md iso29119-incident-report.md; do
  put "$KIT_DIR/templates/test/$f" "$TARGET/docs/test/$f"
done
put "$KIT_DIR/templates/test/system_test_cases.csv" "$TARGET/docs/system_test_cases.csv"
put "$KIT_DIR/templates/test/feature_contracts.yml" "$TARGET/quality/feature_contracts.yml"
for s in quality_harness.py ui-hash.py pre-commit-ui-gate.sh; do
  put "$KIT_DIR/scripts/$s" "$TARGET/scripts/$s"; chmod +x "$TARGET/scripts/$s"
done
mkdir -p "$TARGET/docs/quality/evidence"
if $CI; then put "$KIT_DIR/github-actions/test-gates.yml" "$TARGET/.github/workflows/test-gates.yml"; fi
echo ""
echo "次にやること:"
echo "1. docs/test/*.md の <PROJECT> と <...> を埋める（レベル別コマンド・対象/対象外・リスク登録簿）"
echo "2. quality/feature_contracts.yml に機能を登録し、python3 scripts/quality_harness.py で PASS を確認"
echo "3. verify-ui（E2E）の最後に .ui-verified を書き、.git/hooks/pre-commit から scripts/pre-commit-ui-gate.sh を呼ぶ"
echo "4. ゲートの実行タイミング（日常は H-7・マイルストーンはフルゲート）を CLAUDE.md にも 1 行書く"
