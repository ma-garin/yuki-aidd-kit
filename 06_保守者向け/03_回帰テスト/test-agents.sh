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

echo "[委譲]"
grep -q "^tools:.*Task" "$A/aidd-lead.md" && ok "aidd-lead だけが Task（委譲）を持つ" || ng "aidd-lead だけが Task を持つ" "tools に Task が無い"
OTHER=$(grep -l "^tools:.*Task" "$A"/*.md | grep -v aidd-lead | wc -l | tr -d " ")
[ "$OTHER" -eq 0 ] && ok "実行役は Task を持たない（再委譲で無限に広がらない）" || ng "実行役は Task を持たない" "$OTHER 本が持っている"

echo ""
echo "PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
