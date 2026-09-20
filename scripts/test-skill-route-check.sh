#!/bin/bash
# test-skill-route-check.sh — skill_route_check.py（スキル発火の機械判定）の回帰テスト
# 対象: 構造（ケース不足）/ 発火（positive が top_k 外）/ 誤発火（negative で 1 位・owner 不在）/ 衝突（description の類似）/ 床（--min-rank1）
#       --explain / --json / skills 無し（exit 2）。フィクスチャはキットの skills/ と evals/routing/ のコピーを壊して作る
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK="$KIT_DIR/scripts/skill_route_check.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
# 使い方: expect "<名前>" <期待 exit> "<出力に含む文字列>" <実 exit> "<出力>"
expect() {
  local name="$1" want_code="$2" want_str="$3" code="$4" out="$5"
  if [ "$code" != "$want_code" ]; then ng "$name" "exit=$code 期待 $want_code"; return; fi
  if [ -n "$want_str" ] && ! printf '%s' "$out" | grep -qF -- "$want_str"; then ng "$name" "出力に「$want_str」が無い"; return; fi
  ok "$name"
}
# キットのコピー（skills/*/SKILL.md と evals/routing のみ）
fresh() {
  local d="$1"; rm -rf "$d"; mkdir -p "$d/skills" "$d/evals"
  cp -r "$KIT_DIR/skills/." "$d/skills/"
  cp -r "$KIT_DIR/evals/routing" "$d/evals/routing"
}
run() { python3 "$CHECK" --root "$1" "${@:2}" 2>&1; }

echo "=== skill_route_check.py 回帰テスト ==="

echo "[合格]"
OUT=$(run "$KIT_DIR"); CODE=$?
expect "リポジトリ自身: exit 0・NG=0" 0 "✅ NG=0" "$CODE" "$OUT"
expect "スキル数とケース数が一致して表示される" 0 "スキル 20 / ケース 20" "$CODE" "$OUT"

echo "[構造]"
K="$TMP/k1"; fresh "$K"; rm "$K/evals/routing/retro.json"
OUT=$(run "$K"); CODE=$?
expect "ケースファイルが無いスキル → exit 1・構造 NG" 1 "構造 retro: evals/routing/retro.json が無い" "$CODE" "$OUT"
fresh "$K"; python3 - "$K/evals/routing/retro.json" <<'PYEOF'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8")); d["positive"] = d["positive"][:2]; d["negative"] = d["negative"][:1]
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
OUT=$(run "$K"); CODE=$?
expect "positive 2 件 → 構造 NG（≧ 3）" 1 "構造 retro: positive が 2 件" "$CODE" "$OUT"
expect "negative 1 件 → 構造 NG（≧ 2）" 1 "構造 retro: negative が 1 件" "$CODE" "$OUT"
fresh "$K"; echo '{ broken' > "$K/evals/routing/retro.json"
OUT=$(run "$K"); CODE=$?
expect "JSON でないケース → 構造 NG" 1 "構造 retro: JSON でない" "$CODE" "$OUT"
fresh "$K"; cp "$K/evals/routing/retro.json" "$K/evals/routing/ghost.json"
OUT=$(run "$K"); CODE=$?
expect "スキルの無いケース → 構造 NG" 1 "構造 ghost: ケースはあるがスキルが無い" "$CODE" "$OUT"

echo "[発火]"
fresh "$K"; sed -i 's/^description:.*/description: ""/' "$K/skills/retro/SKILL.md"
OUT=$(run "$K"); CODE=$?
expect "description を空にすると positive が top_k 外 → 発火 NG" 1 "発火 retro:" "$CODE" "$OUT"
expect "発火 NG は description に発火語を足せと言う" 1 "description に発火語を足す" "$CODE" "$OUT"

echo "[誤発火]"
fresh "$K"; python3 - "$K/evals/routing/retro.json" <<'PYEOF'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8")); d["negative"][0]["owner"] = "no-such-skill"
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
OUT=$(run "$K"); CODE=$?
expect "owner が存在しない → 誤発火 NG" 1 "owner \`no-such-skill\` が存在しない" "$CODE" "$OUT"
fresh "$K"; python3 - "$K/evals/routing/retro.json" <<'PYEOF'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8")); d["negative"].append({"prompt": d["positive"][0]["prompt"]})
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
PYEOF
OUT=$(run "$K"); CODE=$?
expect "positive の依頼文を negative に置くと 1 位 → 誤発火 NG" 1 "誤発火 retro:" "$CODE" "$OUT"

echo "[衝突]"
fresh "$K"; DESC=$(grep '^description:' "$K/skills/retro/SKILL.md")
sed -i "s|^description:.*|$DESC|" "$K/skills/done-gate/SKILL.md"
OUT=$(run "$K"); CODE=$?
expect "description を複製すると類似 ≧ 0.75 → 衝突 NG" 1 "衝突 done-gate ↔ retro" "$CODE" "$OUT"

echo "[床]"
OUT=$(run "$KIT_DIR" --min-rank1 101); CODE=$?
expect "--min-rank1 101 は必ず下回る → 床 NG" 1 "床 rank-1 率" "$CODE" "$OUT"
OUT=$(run "$KIT_DIR" --min-rank1 50); CODE=$?
expect "--min-rank1 50 は満たす → exit 0" 0 "✅ NG=0" "$CODE" "$OUT"

echo "[--explain]"
OUT=$(run "$KIT_DIR" --explain "振り返りをして学びをまとめて"); CODE=$?
expect "--explain は順位を 5 行表示して exit 0" 0 "1. retro" "$CODE" "$OUT"
N=$(printf '%s\n' "$OUT" | grep -c '^[1-5]\. ')
if [ "$N" = "5" ]; then ok "--explain の行数は 5"; else ng "--explain の行数は 5" "$N 行"; fi

echo "[--json]"
OUT=$(run "$KIT_DIR" --json); CODE=$?
J=$(printf '%s' "$OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["ok"], d["exit"], "rank1_rate" in d["data"], "error" in d)')
if [ "$CODE" = "0" ] && [ "$J" = "True 0 True False" ]; then ok "--json 合格: ok=true exit=0 data.rank1_rate あり error なし"; else ng "--json 合格" "exit=$CODE $J"; fi
fresh "$K"; rm "$K/evals/routing/retro.json"
OUT=$(run "$K" --json); CODE=$?
J=$(printf '%s' "$OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); e=d.get("error",{}); print(d["ok"], d["exit"], e.get("type"), bool(e.get("hint")), e.get("retry_argv"))')
if [ "$CODE" = "1" ] && [ "$J" = "False 1 routing.failed True ['./scripts/skill-route-check.sh']" ]; then ok "--json NG: ok=false exit=1 type=routing.failed hint retry_argv"; else ng "--json NG" "exit=$CODE $J"; fi

echo "[判定不能]"
OUT=$(run "$TMP/none"); CODE=$?
expect "skills/ が無い → exit 2" 2 "skills/ が無い" "$CODE" "$OUT"

echo "[ラッパ]"
OUT=$(bash "$KIT_DIR/scripts/skill-route-check.sh" --root "$KIT_DIR" 2>&1); CODE=$?
expect "skill-route-check.sh は本体へ引数を渡す" 0 "✅ NG=0" "$CODE" "$OUT"

echo
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
