#!/bin/bash
# test-agents.sh — サブエージェント定義の回帰テスト
# 対象: 03_ClaudeCode/agents/*.md
#
# エージェントは「目標を与えられて自走する主体」として定義する。
# frontmatter が壊れると委譲先が解決できず、ループ・終了条件が欠けると
# 「1 回実行して返すだけ」の変数に退化する。その退化を機械で検出する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
A="$KIT_DIR/03_ClaudeCode/agents"
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
has() { grep -qF -- "$2" "$3" 2>/dev/null && ok "$1" || ng "$1" "'$2' が $(basename "$3") に無い"; }

echo "=== AIDD Kit エージェント定義 回帰テスト ==="

echo "[存在]"
[ -d "$A" ] && ok "03_ClaudeCode/agents/ がある" || { ng "03_ClaudeCode/agents/ がある" "無い"; echo "PASS=$PASS / FAIL=$FAIL"; exit 1; }
[ -f "$A/aidd-lead.md" ] && ok "統括 aidd-lead.md がある" || ng "統括 aidd-lead.md がある" "無い"

echo "[frontmatter]"
for f in "$A"/*.md; do
  b=$(basename "$f" .md)
  [ "$(head -1 "$f")" = "---" ] && ok "$b: frontmatter で始まる" || ng "$b: frontmatter で始まる" "1行目が --- でない"
  n=$(sed -n '''s/^name: *//p''' "$f" | head -1)
  [ "$n" = "$b" ] && ok "$b: name がファイル名と一致" || ng "$b: name がファイル名と一致" "name=$n"
  for k in description tools model; do
    grep -q "^$k:" "$f" && ok "$b: $k がある" || ng "$b: $k がある" "無い"
  done
done

echo "[自走の要件（変数への退化を防ぐ）]"
for f in "$A"/*.md; do
  b=$(basename "$f" .md)
  grep -q "目標" "$f" && ok "$b: 目標がある" || ng "$b: 目標がある" "無い"
  grep -qE "ループ|手順" "$f" && ok "$b: ループ/手順がある" || ng "$b: ループ/手順がある" "無い"
  grep -q "終了条件\|判定を返す\|出力（" "$f" && ok "$b: 終了条件がある" || ng "$b: 終了条件がある" "無い"
  grep -qE "差し戻す条件|エスカレーション|越えない線" "$f" && ok "$b: 停止・差し戻しの条件がある" || ng "$b: 停止・差し戻しの条件がある" "無い"
done

echo "[ゲートスクリプトへの接続（終了条件が機械判定であること）]"
has "spec-agent: trace-check に接続" "trace-check.sh" "$A/spec-agent.md"
has "build-agent: check-design に接続" "check-design.sh" "$A/build-agent.md"
has "verify-agent: test-metrics に接続" "test-metrics.sh" "$A/verify-agent.md"
has "gate-agent: check-approval に接続" "check-approval.sh" "$A/gate-agent.md"

echo "[越えない線]"
has "gate-agent: AI は approver 欄を埋めない" "approver" "$A/gate-agent.md"
has "aidd-lead: 人間を待つのは要件定義と受け入れの2点" "受け入れ" "$A/aidd-lead.md"
grep -q "実装コードを読まない" "$A/spec-agent.md" && ok "spec-agent: 実装コードを読まない" || ng "spec-agent: 実装コードを読まない" "無い"
grep -q "緩めない\|緩める" "$A/verify-agent.md" && ok "verify-agent: アサーションを緩めない" || ng "verify-agent: アサーションを緩めない" "無い"

echo "[診断・修整の規律（B1: verify-agent のループ4・gate-agent の差し戻し条件）]"
has "verify-agent: 修整前に診断（odc_analysis.md）を書く" "診断" "$A/verify-agent.md"
has "verify-agent: 修整の差分を逆適用して赤に戻すことを確認する" "逆適用" "$A/verify-agent.md"
has "verify-agent: 修整は最小差分に限る" "最小差分" "$A/verify-agent.md"
has "gate-agent: 差し戻し条件に診断の有無がある" "診断" "$A/gate-agent.md"

echo "[塊 H: B35 仕様欠落起因の失敗・B36/B42 qa-review-standards]"
has "verify-agent: 差し戻す条件に仕様欠落がある" "仕様欠落" "$A/verify-agent.md"
has "verify-agent: 仕様欠落の差し戻しは保守者が承認するまで完了にしない" "保守者が承認" "$A/verify-agent.md"
QA="$KIT_DIR/03_ClaudeCode/skills/qa-review-standards"
has "qa-review-standards: Critical/High は未確認として起票できる（B36 トリアージ）" "として起票し、重大度を確定しない" "$QA/SKILL.md"
has "qa-review-standards: AI 生成コードのレビュー観点を参照する（B42）" "ai-code-review" "$QA/SKILL.md"
[ -f "$QA/references/ai-code-review.md" ] && ok "qa-review-standards: references/ai-code-review.md がある" || ng "qa-review-standards: references/ai-code-review.md がある" "無い"
has "qa-review-standards: ペルソナ15は本文を持たず ai-code-review.md を参照する" "ai-code-review.md" "$QA/references/personas.md"

echo "[委譲]"
grep -q "^tools:.*Task" "$A/aidd-lead.md" && ok "aidd-lead だけが Task（委譲）を持つ" || ng "aidd-lead だけが Task を持つ" "tools に Task が無い"
OTHER=$(grep -l "^tools:.*Task" "$A"/*.md | grep -v aidd-lead | wc -l | tr -d " ")
[ "$OTHER" -eq 0 ] && ok "実行役は Task を持たない（再委譲で無限に広がらない）" || ng "実行役は Task を持たない" "$OTHER 本が持っている"

echo "[A20: E2E に axe のアクセシビリティ検査が組み込まれている]"
E2E="$KIT_DIR/03_ClaudeCode/skills/e2e-cycle/SKILL.md"
has "e2e-cycle: axe への言及がある" "axe" "$E2E"
has "e2e-cycle: serious/critical を FAIL にする基準がある" "serious" "$E2E"

echo "[塊 K: B54 uiux_review の観点にキーボードと支援技術を足した]"
VP="$KIT_DIR/03_ClaudeCode/skills/uiux_review/references/viewpoints.md"
VPN=$(grep -c '^### VP-[0-9]\{3\} ' "$VP"); VPU=$(grep -o '^### VP-[0-9]\{3\}' "$VP" | sort -u | wc -l | tr -d ' ')
[ "$VPN" -eq 80 ] && [ "$VPU" -eq 80 ] && head -1 "$VP" | grep -qF "（80件）" && grep -q '^### VP-080 ' "$VP" \
  && ok "viewpoints.md の観点は 80 件（番号の重複なし・見出しの件数と一致・VP-080 まで）" \
  || ng "viewpoints.md の観点は 80 件" "観点=$VPN 一意=$VPU 見出し=$(head -1 "$VP")"

# --- [検証: 塊H] 検証担当が足した節（実装担当とは別。赤は赤のまま残す） ------------
echo "[検証: 塊H]"
QAR="$KIT_DIR/03_ClaudeCode/skills/qa-review-standards/references/ai-code-review.md"
# ペルソナ 15 の本文（件数だけ数えるテスト・0 件で PASS・非決定的な生成）を ai-code-review.md に寄せた。寄せ先で観点が消えていないか
has "[検証] ペルソナ15の観点「0 件で PASS」が寄せ先 ai-code-review.md に残る" "0 件" "$QAR"
has "[検証] ペルソナ15の観点「件数だけ数えるテスト」が寄せ先 ai-code-review.md に残る" "件数" "$QAR"

echo ""
echo "PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
