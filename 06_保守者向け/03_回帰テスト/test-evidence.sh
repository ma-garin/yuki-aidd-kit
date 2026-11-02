#!/bin/bash
# test-evidence.sh — evidence.py（キットの効果の証拠レポート）の回帰テスト
#
# 固定の擬似入力（tool-time.json / log.csv / hook-decisions.log / e2e-history.jsonl）で各表の値を確かめる。
# 入力が全く無くても落ちず「未記録」と出すこと、--since で古い行を除くこと、--out で書き出すことも確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$KIT_DIR/02_共通/ツール/evidence.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

NOW=1790000000   # 固定の現在時刻
OLD=$((NOW - 60*86400)); NEW=$((NOW - 86400))
ISO_NEW=$(python3 -c "import datetime as d;print(d.datetime.fromtimestamp($NEW,d.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+0000'))")
ISO_OLD=$(python3 -c "import datetime as d;print(d.datetime.fromtimestamp($OLD,d.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+0000'))")

# 比 = 1.0, 1.2, 2.0, 0.5 → 中央値 1.10、範囲内 2/4
echo '{"history": [[10, 10], [10, 12], [5, 10], [10, 5], "壊れ"]}' > "$TMP/tt.json"
cat > "$TMP/log.csv" <<EOF
t0,t1,kind,plan_x,unit_s,xcorr,ext_plan_s,gen_s,margin_s,est_s,reest_s,actual_x,user_wait_s,ext_wait_s,long_gap_s,actual_s,ratio,result,unfinished
$NEW,,調査,,,,,,,600,,,,,,600,,,0
$NEW,,調査,,,,,,,600,,,,,,1200,,,0
$NEW,,調査,,,,,,,600,,,,,,660,,,0
$NEW,,UI改修,,,,,,,1000,,,,,,900,,,0
$NEW,,UI改修,,,,,,,1000,,,,,,9000,,,1
$OLD,,UI改修,,,,,,,1000,,,,,,9000,,,0
EOF
cat > "$TMP/hook.log" <<EOF
{"time": "$ISO_NEW", "hook": "secret-guard", "decision": "deny"}
{"time": "$ISO_NEW", "hook": "secret-guard", "decision": "block"}
{"time": "$ISO_NEW", "hook": "secret-guard", "decision": "warn"}
{"time": "$ISO_NEW", "hook": "secret-guard", "decision": "override"}
{"time": "$ISO_NEW", "hook": "git-gate", "decision": "warn"}
{"time": "$ISO_NEW", "hook": "git-gate", "decision": "info"}
{"time": "$ISO_OLD", "hook": "git-gate", "decision": "override"}
壊れた行
EOF
cat > "$TMP/e2e.jsonl" <<EOF
{"run": "r1", "time": "$ISO_NEW", "file": "a.spec.ts", "title": "t1", "project": "c", "outcome": "pass"}
{"run": "r1", "time": "$ISO_NEW", "file": "a.spec.ts", "title": "t2", "project": "c", "outcome": "fail"}
{"run": "r2", "time": "$ISO_NEW", "file": "a.spec.ts", "title": "t1", "project": "c", "outcome": "pass"}
{"run": "r2", "time": "$ISO_NEW", "file": "a.spec.ts", "title": "t2", "project": "c", "outcome": "flaky"}
{"run": "r2", "time": "$ISO_NEW", "file": "a.spec.ts", "title": "t3", "project": "c", "outcome": "skipped"}
{"run": "r0", "time": "$ISO_OLD", "file": "a.spec.ts", "title": "t1", "project": "c", "outcome": "fail"}
EOF
run() { python3 "$TOOL" --now "$NOW" --tool-time "$TMP/tt.json" --est-log "$TMP/log.csv" --hook-log "$TMP/hook.log" --e2e "$TMP/e2e.jsonl" "$@" 2>&1; }

echo "■ 全入力あり"
OUT=$(run); RC=$?
expect_exit "1. 正常終了" 0 $RC
expect_out "2. 先頭に集計期間（30日）" "| 集計期間 |" "$OUT"
expect_out "2. 集計期間の日数" "（30日） |" "$OUT"
expect_out "3. tool-timer 件数（壊れた要素は除く）" "| 件数 | 4 |" "$OUT"
expect_out "3. 校正係数 = 中央値 1.10" "| 校正係数（実測/見積の中央値） | 1.10 |" "$OUT"
expect_out "3. 範囲内割合 50.0%" "| 0.67〜1.5 に収まった割合 | 50.0% |" "$OUT"
expect_out "4. est 調査: 3件・中央値1.10・範囲外 33.3%" "| 調査 | 3 | 1.10 | 33.3% |" "$OUT"
expect_out "4. est UI改修: 未完と期間外を除き 1件" "| UI改修 | 1 | 0.90 | 0.0% |" "$OUT"
expect_out "5. hook secret-guard（block は deny）" "| secret-guard | 2 | 1 | 1 | 33.3% |" "$OUT"
expect_out "5. hook git-gate（期間外 override・info は数えない）" "| git-gate | 0 | 1 | 0 | 0.0% |" "$OUT"
expect_out "5. hook 合計" "| 合計 | 2 | 2 | 1 | 25.0% |" "$OUT"
expect_out "6. E2E 通過率（skipped・期間外を除く 2/4）" "| 通過率（pass ÷ 判定対象） | 50.0% |" "$OUT"
expect_out "6. E2E flaky 率 1/4" "| flaky 率（flaky ÷ 判定対象） | 25.0% |" "$OUT"
expect_out "6. E2E 実行数 2" "| 実行数（run） | 2 |" "$OUT"
[ -z "$(printf '%s\n' "$OUT" | grep -vE '^(#|\||$)')" ] && ok "7. 見出しと表以外の行が無い" || ng "7. 見出しと表以外の行が無い" "散文行あり"

echo "■ --since 90 で古い行も入る"
OUT=$(run --since 90)
expect_out "8. UI改修が 2件になる" "| UI改修 | 2 |" "$OUT"
expect_out "8. 期間外の override が入る" "| git-gate | 0 | 1 | 1 |" "$OUT"

echo "■ 入力ファイル無し"
OUT=$(python3 "$TOOL" --now "$NOW" --tool-time "$TMP/無.json" --est-log "$TMP/無.csv" --hook-log "$TMP/無.log" --e2e "$TMP/無.jsonl" 2>&1); RC=$?
expect_exit "9. 落ちない" 0 $RC
expect_out "9. tool-timer は未記録" "| 件数 | 未記録 |" "$OUT"
expect_out "9. E2E は未記録" "| 実行数 | 未記録 |" "$OUT"
expect_noout "9. Traceback が出ない" "Traceback" "$OUT"

echo "■ --out"
run --out "$TMP/r.md" >/dev/null
[ -s "$TMP/r.md" ] && grep -qF "# yuki-aidd-kit 効果の証拠レポート" "$TMP/r.md" && ok "10. --out に書き出す" || ng "10. --out に書き出す" "ファイルが無いか空"

echo "■ --acceptance"
mkdir -p "$TMP/norepo"
OUT=$(cd "$TMP/norepo" && python3 "$TOOL" --acceptance --now "$NOW" --tool-time "$TMP/無.json" --e2e "$TMP/無.jsonl" 2>&1); RC=$?
expect_exit "11. 入力なしで落ちない" 0 $RC
expect_noout "11. Traceback が出ない" "Traceback" "$OUT"
expect_out "12. git リポジトリ外で版が未記録" "| 対象の版 | 未記録 |" "$OUT"
expect_out "12. --base 無しは未実行" "未実行（--base 無し）" "$OUT"
expect_out "12. 末尾の注意" "秘密情報・個人情報を含めない" "$OUT"
cat > "$TMP/cfg.jsonl" <<EOF
{"time": "$ISO_NEW", "changed": ["model", "hooks"], "extra": 1}
{"time": "$ISO_OLD", "changed": ["old"]}
EOF
printf 'requests==2.31.0\n# c\nflask>=3.0\n' > "$TMP/norepo/requirements.txt"
printf 'lint\tpass\nunit\tfail\n{"gate": "e2e", "result": "skipped"}\n' > "$TMP/gate.log"
OUT=$(cd "$TMP/norepo" && python3 "$TOOL" --acceptance --now "$NOW" --config-log "$TMP/cfg.jsonl" --gate-log "$TMP/gate.log" --hook-log "$TMP/hook.log" --e2e "$TMP/e2e.jsonl" --tool-time "$TMP/tt.json" 2>&1)
expect_out "13. ai-config-log の生キーを表にする" "| time | changed | extra |" "$OUT"
expect_out "13. 変更項目の配列を並べる" "| model, hooks | 1 |" "$OUT"
expect_noout "13. 期間外の行は出さない" "| old |" "$OUT"
expect_out "14. requirements.txt の依存（版あり）" "| requirements.txt | requests | ==2.31.0 |" "$OUT"
expect_out "14. 依存の件数" "| 依存の件数 | 2 |" "$OUT"
expect_out "15. --gate-log TAB 形式の合格" "| lint | 合格 |" "$OUT"
expect_out "15. --gate-log 不合格" "| unit | 不合格 |" "$OUT"
expect_out "15. --gate-log JSONL の未実行" "| e2e | 未実行 |" "$OUT"
expect_out "16. hook に止められた件数（deny+block）" "| 件数（deny・block） | 2 |" "$OUT"
printf '{"bad": 1}\n' > "$TMP/cfg2.jsonl"
OUT=$(cd "$TMP/norepo" && python3 "$TOOL" --acceptance --now "$NOW" --config-log "$TMP/cfg2.jsonl" 2>&1); RC=$?
expect_exit "17. 想定外の形式でも落ちない" 0 $RC
expect_out "17. 想定外のキーをそのまま表にする" "| bad |" "$OUT"
if git -C "$KIT_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  OUT=$(cd "$KIT_DIR" && python3 "$TOOL" --acceptance --now "$NOW" 2>&1)
  expect_out "18. git リポジトリ内で版を出す" "| 対象の版 | $(git -C "$KIT_DIR" rev-parse --short HEAD) |" "$OUT"
fi

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"; exit 0
else
  echo "⚠ 失敗あり。02_共通/ツール/evidence.py を確認してください"; exit 1
fi
