#!/usr/bin/env bash
# pre-commit-ui-gate.sh — UI 変更コミットに E2E 検証マーカー（.ui-verified）を要求する
#
# 配置: <project>/scripts/pre-commit-ui-gate.sh。<project>/.git/hooks/pre-commit から
#   bash scripts/pre-commit-ui-gate.sh || exit 1
# として呼ぶ（秘密情報スキャンの scripts/pre-commit と併用）。
# マーカーは verify-ui（E2E 全 PASS）後に 1 行で書く:
#   printf "%s %s %s\n" "$(git rev-parse HEAD)" "$(python3 scripts/ui-hash.py disk)" "$(date -Iseconds)" > .ui-verified
# 刷新モード: echo "理由" > .rebuild-mode で毎コミットの要求を止める（未検証と明示。マイルストーンで必ず実行）。
# 仕様: skills/test-strategy/references/ui-verified-gate.md。出所: WebSpec2Doc .githooks/pre-commit v2。
set -uo pipefail
ROOT="$(git rev-parse --show-toplevel)"
MARKER="${ROOT}/.ui-verified"
MARKER_MAX_AGE="${UI_GATE_MAX_AGE:-7200}"
PY="${ROOT}/venv/bin/python"; [ -x "$PY" ] || PY="python3"

STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
UI_CHANGED=false
while IFS= read -r f; do
  case "$f" in
    docs/*.html|docs/*.js|docs/*.css) ;;   # 設計モック。実 UI ではない
    *.html|*.js|*.css) UI_CHANGED=true ;;
  esac
done <<< "$STAGED"
$UI_CHANGED || exit 0

if [ -f "${ROOT}/.rebuild-mode" ]; then
  echo "[WARN] 刷新モード — UI 変更時の E2E ゲートをスキップ（理由: $(head -1 "${ROOT}/.rebuild-mode")）"
  echo "       E2E は未実行です。「未検証」であり「問題なし」ではありません。マイルストーンで必ず verify-ui を実行し、完了後に .rebuild-mode を消してください。"
  exit 0
fi

blocked() {
  echo ""
  echo "[BLOCKED] COMMIT BLOCKED — Definition of Done 違反: $*"
  echo "          実行してください: make verify-ui（E2E 全 PASS でマーカーが更新される）"
  echo ""
  exit 1
}

[ -f "$MARKER" ] || blocked "E2E テスト未実行（.ui-verified が存在しません）"

TS=$(awk '{print $3}' "$MARKER"); EPOCH=0
if [ -n "$TS" ]; then
  EPOCH=$("$PY" -c "import datetime,sys; print(int(datetime.datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()))" "$TS" 2>/dev/null || echo 0)
fi
AGE=$(( $(date +%s) - EPOCH ))
[ "$AGE" -le "$MARKER_MAX_AGE" ] || blocked "E2E 検証が古すぎます（${AGE}秒前 — 上限 ${MARKER_MAX_AGE}秒）"

VERIFIED=$(awk '{print $2}' "$MARKER")
if [ -n "$VERIFIED" ] && [ -f "${ROOT}/scripts/ui-hash.py" ]; then
  CURRENT=$("$PY" "${ROOT}/scripts/ui-hash.py" disk 2>/dev/null || echo "error")
  if [ "$CURRENT" = "error" ]; then
    echo "[WARN] UI hash の計算に失敗。タイムスタンプのみで判定します。"
  elif [ "$CURRENT" != "$VERIFIED" ]; then
    blocked "E2E 検証後に UI ファイルが変更されています（検証時 ${VERIFIED} / 現在 ${CURRENT}）"
  else
    echo "[PASS] UI hash 一致（${CURRENT}）"
  fi
fi
echo "[PASS] E2E 検証済み（${AGE}秒前）"
echo "[WARN] ブラウザ目視確認も実施しましたか？（DEFINITION_OF_DONE.md Type B / uiux_review）"
exit 0
