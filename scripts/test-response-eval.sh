#!/bin/bash
# test-response-eval.sh — response_eval.py（応答の盲検対比評価）の回帰テスト
# LLM は呼ばない。偽の runner（応答は system prompt の中身を返す／判定者は「GOOD」を含む側を高く採点）で、
# validate / run / score の分岐・盲検（判定者に条件名を渡さない）・順序入替・blocker・判定不能・--json を確認する
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL="$KIT_DIR/scripts/response_eval.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect() {   # expect "<名前>" <期待 exit> "<出力に含む文字列>" <実 exit> "<出力>"
  local name="$1" want_code="$2" want_str="$3" code="$4" out="$5"
  if [ "$code" != "$want_code" ]; then ng "$name" "exit=$code 期待 $want_code: ${out:0:120}"; return; fi
  if [ -n "$want_str" ] && ! printf '%s' "$out" | grep -qF -- "$want_str"; then ng "$name" "出力に「$want_str」が無い: ${out:0:120}"; return; fi
  ok "$name"
}

# 偽 runner: 引数 1 = system prompt ファイル。依頼文は stdin
FAKE="$TMP/fake-runner.sh"
cat > "$FAKE" <<'SH'
#!/bin/bash
SYS="$1"; IN=$(cat)
if grep -q "判定者" "$SYS"; then
  printf '%s\n----\n' "$IN" >> "${FAKE_LOG:-/dev/null}"
  X=$(printf '%s' "$IN" | awk '/^## 応答 X/{f=1;next} /^## 応答 Y/{f=0} f')
  Y=$(printf '%s' "$IN" | awk '/^## 応答 Y/{f=1;next} /^上の system prompt/{f=0} f')
  sx=5; sy=5
  case "${FAKE_MODE:-good-wins}" in
    good-wins) printf '%s' "$X" | grep -q GOOD && sx=9; printf '%s' "$Y" | grep -q GOOD && sy=9 ;;
    good-loses) printf '%s' "$X" | grep -q GOOD && sx=3; printf '%s' "$Y" | grep -q GOOD && sy=3 ;;
    tie) ;;
    garbage) echo "採点できません"; exit 0 ;;
    crash) exit 3 ;;
  esac
  bx=null; by=null
  if [ "${FAKE_MODE:-}" = "blocker-good" ]; then
    printf '%s' "$X" | grep -q GOOD && bx='"事実の捏造"'; printf '%s' "$Y" | grep -q GOOD && by='"事実の捏造"'
  fi
  s() { printf '{"正確性": %s, "自律": %s, "行動可能性": %s, "安全": %s, "簡潔": %s}' "$1" "$1" "$1" "$1" "$1"; }
  printf '判定します。\n{"scores": {"X": %s, "Y": %s}, "blocker": {"X": %s, "Y": %s}, "reason": "偽"}\n' "$(s $sx)" "$(s $sy)" "$bx" "$by"
else
  # 応答は system prompt の中身を写さない（写すと盲検の検査が応答文で誤検出する）
  if [ "$(head -1 "$SYS")" = "GOOD" ]; then printf 'GOOD な応答: %s\n' "${IN:0:20}"; else printf 'ふつうの応答: %s\n' "${IN:0:20}"; fi
fi
SH
chmod +x "$FAKE"
printf 'BASE\n' > "$TMP/base-system.md"
printf 'GOOD\n' > "$TMP/cand-system.md"
RUN="cmd:$FAKE {system}"
run() { python3 "$EVAL" "$@" 2>&1; }

echo "=== response_eval.py 回帰テスト ==="

echo "[validate]"
OUT=$(run validate --root "$KIT_DIR"); CODE=$?
expect "キットの cases.jsonl と rubric.md が通る（10 件・重み合計 100）" 0 "依頼文 10 件" "$CODE" "$OUT"
mkdir -p "$TMP/k/evals/response"; cp "$KIT_DIR/evals/response/rubric.md" "$TMP/k/evals/response/"
printf '{"id": "a", "prompt": "x"}\n{broken\n' > "$TMP/k/evals/response/cases.jsonl"
OUT=$(run validate --root "$TMP/k"); CODE=$?
expect "JSON でない行 → exit 1" 1 "JSON でない" "$CODE" "$OUT"
printf '{"id": "a", "prompt": "x"}\n{"id": "a", "prompt": "y"}\n' > "$TMP/k/evals/response/cases.jsonl"
OUT=$(run validate --root "$TMP/k"); CODE=$?
expect "id 重複 → exit 1" 1 "id 重複" "$CODE" "$OUT"
printf '{"id": "a", "prompt": "x"}\n' > "$TMP/k/evals/response/cases.jsonl"
sed -i 's/<!-- judge:end -->/<!-- judge:done -->/' "$TMP/k/evals/response/rubric.md"
OUT=$(run validate --root "$TMP/k"); CODE=$?
expect "rubric の judge:end 印が無い → exit 1" 1 "judge:end" "$CODE" "$OUT"
cp "$KIT_DIR/evals/response/rubric.md" "$TMP/k/evals/response/"; sed -i 's/簡潔/短さ/g' "$TMP/k/evals/response/rubric.md"
OUT=$(run validate --root "$TMP/k"); CODE=$?
expect "判定者指示から軸が消えた → exit 1" 1 "軸「簡潔」が無い" "$CODE" "$OUT"

echo "[run: B が勝つ]"
export FAKE_LOG="$TMP/judge.log"; : > "$FAKE_LOG"
OUT=$(FAKE_MODE=good-wins run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out1"); CODE=$?
expect "候補が全案件で勝つ → exit 0" 0 "B の勝ち 10 引分 0 負け 0" "$CODE" "$OUT"
[ -f "$TMP/out1/report.md" ] && ok "report.md が出る" || ng "report.md が出る" "無い"
grep -q "| 平均（100 点満点） | 50.0 | 90.0 |" "$TMP/out1/report.md" && ok "平均が重み付きで 50 / 90" || ng "平均が重み付きで 50 / 90" "$(grep 平均 "$TMP/out1/report.md")"
N=$(grep -c '^----$' "$FAKE_LOG")
[ "$N" = "20" ] && ok "判定は案件ごとに順序を入れ替えて 2 回（10 件 → 20 回）" || ng "判定 2 回" "$N 回"
if grep -qE "base-system|cand-system|基準|候補|BASE" "$FAKE_LOG"; then ng "盲検: 判定者に条件名・ファイル名・system prompt の中身を渡さない" "漏れあり"; else ok "盲検: 判定者に条件名・ファイル名・system prompt の中身を渡さない"; fi
grep -q '"assign"' "$TMP/out1/plan.json" && ok "plan.json に割当（seed 付き）が残る" || ng "plan.json" "無い"
ls "$TMP/out1"/*.judge.AX.txt >/dev/null 2>&1 && ls "$TMP/out1"/*.judge.AY.txt >/dev/null 2>&1 && ok "判定の入出力が案件・順序ごとに残る" || ng "判定の入出力" "無い"

echo "[run: 分岐]"
: > "$FAKE_LOG"
OUT=$(FAKE_MODE=good-wins run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out2" --single-order); CODE=$?
N=$(grep -c '^----$' "$FAKE_LOG")
[ "$CODE" = "0" ] && [ "$N" = "10" ] && ok "--single-order は判定 1 回（10 回）" || ng "--single-order" "exit=$CODE 判定 $N 回"
OUT=$(FAKE_MODE=good-loses run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out3" --json); CODE=$?
J=$(printf '%s' "$OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["ok"], d["exit"], d["error"]["type"], d["data"]["mean"]["A"], d["data"]["mean"]["B"])')
[ "$CODE" = "1" ] && [ "$J" = "False 1 response.worse 50.0 30.0" ] && ok "候補が負ける → exit 1・--json は ok=false type=response.worse" || ng "候補が負ける" "exit=$CODE $J"
OUT=$(FAKE_MODE=blocker-good run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out4"); CODE=$?
expect "候補に blocker → 合計 0・exit 1" 1 "B に blocker" "$CODE" "$OUT"
grep -q "| 平均（100 点満点） | 50.0 | 0.0 |" "$TMP/out4/report.md" && ok "blocker の側の平均は 0" || ng "blocker の側の平均は 0" "$(grep 平均 "$TMP/out4/report.md")"
OUT=$(FAKE_MODE=tie run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out5"); CODE=$?
expect "同点 → 悪くないので exit 0・引分 10" 0 "引分 10" "$CODE" "$OUT"
OUT=$(FAKE_MODE=garbage run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out6" --json); CODE=$?
J=$(printf '%s' "$OUT" | python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d["exit"], d["error"]["type"], bool(d["error"]["hint"]), d["error"]["retry_argv"][0])')
[ "$CODE" = "2" ] && [ "$J" = "2 response.undetermined True ./scripts/response-eval.sh" ] && ok "判定者が JSON を返さない → exit 2 type=response.undetermined hint retry_argv" || ng "判定不能" "exit=$CODE $J"
OUT=$(FAKE_MODE=crash run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/out7"); CODE=$?
expect "runner が非 0 で終わる → exit 2" 2 "runner が exit 3" "$CODE" "$OUT"
OUT=$(run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "cmd:$TMP/no-such {system}" --out "$TMP/out8"); CODE=$?
expect "runner が無い → exit 2" 2 "runner が見つからない" "$CODE" "$OUT"
OUT=$(run run --root "$KIT_DIR" --a "$TMP/base-system.md" --runner "$RUN" --out "$TMP/out9"); CODE=$?
expect "--b が無い → exit 1" 1 "--a と --b" "$CODE" "$OUT"
OUT=$(run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "cmd:$FAKE" --out "$TMP/out9"); CODE=$?
expect "cmd: runner に {system} が無い → exit 1" 1 "{system}" "$CODE" "$OUT"

echo "[seed / score]"
FAKE_MODE=good-wins run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/s1" --seed 7 >/dev/null
FAKE_MODE=good-wins run run --root "$KIT_DIR" --a "$TMP/base-system.md" --b "$TMP/cand-system.md" --runner "$RUN" --out "$TMP/s2" --seed 7 >/dev/null
cmp -s "$TMP/s1/plan.json" "$TMP/s2/plan.json" && ok "同じ seed なら X/Y の割当が同じ（再現可能）" || ng "seed 再現" "plan.json が違う"
python3 - "$TMP/s1/plan.json" <<'PYEOF' && ok "割当は AX と AY が混在する（全案件同じ位置にならない）" || ng "割当の混在" "片寄り"
import json, sys
a = json.load(open(sys.argv[1]))["assign"].values(); sys.exit(0 if len(set(a)) == 2 else 1)
PYEOF
OUT=$(run score --root "$KIT_DIR" --out "$TMP/out1"); CODE=$?
expect "score は records.json から集計をやり直す" 0 "B の勝ち 10" "$CODE" "$OUT"
OUT=$(run score --root "$KIT_DIR" --out "$TMP/none"); CODE=$?
expect "records.json が無ければ exit 2" 2 "先に run" "$CODE" "$OUT"

echo "[ラッパ]"
OUT=$(bash "$KIT_DIR/scripts/response-eval.sh" validate --root "$KIT_DIR" 2>&1); CODE=$?
expect "response-eval.sh は本体へ引数を渡す" 0 "validate" "$CODE" "$OUT"

echo
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
