#!/bin/bash
# test-test-metrics.sh — test-metrics.sh（test_metrics.py）の回帰テスト
#
# 一時プロジェクトに init-lifecycle.sh / init-test-docs.sh で雛形を置き、表を書き換えて
# 「配布雛形が壊れないこと」「合格に数えてはいけない状態を落とさないこと」「exit 0/1/2 の契約」を確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-200)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
TODAY=2026-09-20
run() { python3 "$KIT_DIR/tools/test_metrics.py" --root "$1" --today "$TODAY" -o "$TMP/report.md" "${@:2}" 2>&1; }
proj() { local d="$TMP/p$RANDOM$RANDOM"; mkdir -p "$d"; "$KIT_DIR/scripts/init-lifecycle.sh" "$d" >/dev/null; "$KIT_DIR/scripts/init-test-docs.sh" "$d" >/dev/null; echo "$d"; }

# 07/08 の表を実データに置き換えるヘルパ（ST 8 件・UAT 5 件・DEF 3 件。実施日は 3 日に分散）
fill() { rm -f "$1/docs/system_test_cases.csv"; python3 - "$1" <<'PY'
import sys, re
from pathlib import Path
p = Path(sys.argv[1])
st = p/"docs/lifecycle/07-system-test.md"; s = st.read_text()
rows = "\n".join([
 "| ST-001 | REQ-N-001 | 性能効率性 | 3G | 3秒以内 | 2.1秒 | pass | e1 | 2026-09-17 | 藤曲 |",
 "| ST-002 | REQ-N-001 | 性能効率性 | 4G | 2秒以内 | 1.4秒 | pass | e2 | 2026-09-17 | 藤曲 |",
 "| ST-003 | REQ-N-002 | デバイス対応 | 360px |  |  | fail | e3 | 2026-09-18 | 藤曲 |",
 "| ST-004 | REQ-N-002 | デバイス対応 | 1366px |  |  | pass | e4 | 2026-09-18 | 藤曲 |",
 "| ST-005 | REQ-N-003 | 信頼性 | オフライン |  |  | pass | e5 | 2026-09-19 | 田中 |",
 "| ST-006 | REQ-N-003 | 信頼性 | 再接続 |  |  | 未実施 |  |  |  |",
 "| ST-007 | REQ-N-004 | セキュリティ | XSS |  |  | blocked |  |  |  |",
 "| ST-008 | REQ-N-004 | セキュリティ | CSRF |  |  |  |  |  |  |",
])
s = re.sub(r"\| ST-001 \|.*?\n(?:\| ST-0xx \|.*?\n)+", rows + "\n", s, count=1, flags=re.S)
s = s.replace("| DEF-ID | 対象 ST | 対象 REQ-N | severity | 内容 | evidence | 起票日 | 対応 |\n|---|---|---|---|---|---|---|---|",
 "| DEF-ID | 対象 ST | 対象 REQ-N | severity | 内容 | evidence | 起票日 | 対応 |\n|---|---|---|---|---|---|---|---|\n"
 "| DEF-001 | ST-003 | REQ-N-002 | Critical | 360px で横スクロール | e3 | 2026-09-12 | 未対応 |\n"
 "| DEF-002 | ST-003 | REQ-N-002 | Low | 余白が狭い | e3 | 2026-09-18 | 修正済 |\n", 1)
s = s.replace("YYYY-MM-DD", "2026-09-17", 1); st.write_text(s)
ua = p/"docs/lifecycle/08-acceptance-test.md"; s = ua.read_text()
rows = "\n".join([
 "| UAT-001 | 貸出 | REQ-F-001 |  |  |  | 合 |  | 2026-09-19 | 司書A |",
 "| UAT-002 | 返却 | REQ-F-002 |  |  |  | 合 |  | 2026-09-19 | 司書A |",
 "| UAT-003 | 予約 | REQ-F-003 |  |  |  | 否 |  | 2026-09-19 | 司書A |",
 "| UAT-004 | 延滞 | REQ-F-004 |  |  |  |  |  |  |  |",
 "| UAT-005 | 検索 | REQ-F-005 |  |  |  |  |  |  |  |",
])
s = re.sub(r"\| UAT-001 \|.*?\n\| UAT-0xx \|.*?\n", rows + "\n", s, count=1, flags=re.S)
s = s.replace("| DEF-0xx |  |  |  | <起票日> | 修正する / 次リリースへ送る / 受容する |",
              "| DEF-003 | UAT-003 | 予約が二重登録 | High | 2026-09-19 | 修正する |", 1)
s = s.replace("YYYY-MM-DD", "2026-09-19", 1); ua.write_text(s)
PY
}

echo "=== test-metrics.sh 回帰テスト ==="

echo "[ケース1: 配布雛形（init 直後）]"
P=$(proj); OUT=$(run "$P"); RC=$?
expect_exit "status は exit 0" 0 "$RC"
expect_out  "記入例の行だけでも数字が出る" "消化率" "$OUT"
expect_out  "推定には根拠が付く" "根拠: 直近" "$OUT"
OUT=$(run "$P" --gate); RC=$?
expect_exit "雛形のままの --gate は 1（消化率 < 100）" 1 "$RC"
expect_out  "満たさない基準を名指しする" "満たさない基準: 1." "$OUT"

echo "[ケース2: 実行記録が無いプロジェクト]"
E="$TMP/empty"; mkdir -p "$E"
OUT=$(run "$E"); RC=$?
expect_exit "status は exit 0（対象なし）" 0 "$RC"
expect_out  "雛形の置き方を案内" "init-lifecycle.sh" "$OUT"
OUT=$(run "$E" --gate); RC=$?
expect_exit "--gate は 2（判定できない）" 2 "$RC"

echo "[ケース3: 実データ（ST 8 / UAT 5 / DEF 3）]"
P=$(proj); fill "$P"; OUT=$(run "$P" --level ST); RC=$?
expect_out  "ST: 実行 5（pass 4・fail 1）" "実行 5（pass 4・fail 1）" "$OUT"
expect_out  "ST の消化率 62.5%（5/8）" "62.5%" "$OUT"
expect_out  "Critical/High 未解決 1（DEF-001 のみ。Low の修正済は数えない）" "Critical・High 未解決 1" "$OUT"
expect_out  "滞留を検知（DEF-001 は 8 日 open）" "[stale]" "$OUT"
expect_out  "Critical の未解決を検知" "[severe]" "$OUT"
OUT=$(run "$P" --level UAT)
expect_out  "UAT の 合 / 否 を pass / fail に正規化（実行 3、fail 1）" "実行 3（pass 2・fail 1）" "$OUT"
OUT=$(run "$P")
expect_out  "ALL の欠陥 3 件" "欠陥: 3 件" "$OUT"
OUT=$(run "$P" --gate); RC=$?
expect_exit "Critical 未解決・消化率不足 → exit 1" 1 "$RC"

echo "[ケース4: 判定できない行は分母に入り、ゲートは 2]"
P=$(proj); fill "$P"; sed -i 's/| ST-005 | REQ-N-003 | 信頼性 | オフライン |  |  | pass |/| ST-005 | REQ-N-003 | 信頼性 | オフライン |  |  | たぶんOK |/' "$P/docs/lifecycle/07-system-test.md"
OUT=$(run "$P" --level ST)
expect_out  "判定不能 1 を数える" "判定不能 1" "$OUT"
expect_out  "分母に残る（全 8 のまま、実行 4）" "全 8 / 実行 4" "$OUT"
expect_out  "検知に語彙外の値を出す" "「たぶんOK」" "$OUT"
sed -i 's/| ST-006 | REQ-N-003 | 信頼性 | 再接続 |  |  | 未実施 |/| ST-006 | REQ-N-003 | 信頼性 | 再接続 |  |  | pass |/; s/| ST-007 | REQ-N-004 | セキュリティ | XSS |  |  | blocked |/| ST-007 | REQ-N-004 | セキュリティ | XSS |  |  | pass |/; s/| ST-008 | REQ-N-004 | セキュリティ | CSRF |  |  |  |/| ST-008 | REQ-N-004 | セキュリティ | CSRF |  |  | pass |/' "$P/docs/lifecycle/07-system-test.md"
# ここまでで unread だけが残る状態にはならない（UAT 未実施が残る）ので、UAT 側も埋める
sed -i 's/| UAT-004 | 延滞 | REQ-F-004 |  |  |  |  |/| UAT-004 | 延滞 | REQ-F-004 |  |  |  | 合 |/; s/| UAT-005 | 検索 | REQ-F-005 |  |  |  |  |/| UAT-005 | 検索 | REQ-F-005 |  |  |  | 合 |/' "$P/docs/lifecycle/08-acceptance-test.md"
sed -i 's/| 2026-09-12 | 未対応 |/| 2026-09-12 | 修正済 |/; ' "$P/docs/lifecycle/07-system-test.md"; sed -i 's/| 2026-09-19 | 修正する |/| 2026-09-19 | 修正済 |/' "$P/docs/lifecycle/08-acceptance-test.md"
OUT=$(run "$P" --gate); RC=$?
expect_exit "unread が 1 件残ると --gate は 2（判定不能を合格に数えない）" 2 "$RC"

echo "[ケース5: 全件 pass・Critical 解消 → 進める]"
sed -i 's/| たぶんOK |/| pass |/' "$P/docs/lifecycle/07-system-test.md"
sed -i 's/| ST-003 | REQ-N-002 | デバイス対応 | 360px |  |  | fail |/| ST-003 | REQ-N-002 | デバイス対応 | 360px |  |  | pass |/' "$P/docs/lifecycle/07-system-test.md"
sed -i 's/| UAT-003 | 予約 | REQ-F-003 |  |  |  | 否 |/| UAT-003 | 予約 | REQ-F-003 |  |  |  | 合 |/' "$P/docs/lifecycle/08-acceptance-test.md"
sed -i 's/| UT-002 | DD-001 | 異常系 | 入力不正 |  |  |  |  |  |  |/| UT-002 | DD-001 | 異常系 | 入力不正 |  |  |  | pass |  |  |/; s/| UT-003 | DD-001 | 境界値 | 上限+1 |  |  |  |  |  |  |/| UT-003 | DD-001 | 境界値 | 上限+1 |  |  |  | pass |  |  |/' "$P/docs/lifecycle/05-unit-test.md"
OUT=$(run "$P" --gate); RC=$?
expect_exit "全基準 ✓ → exit 0" 0 "$RC"
expect_out  "判定候補は「進める」。GO/NO-GO は人" "進める" "$OUT"

echo "[ケース6: 欠陥表が無い → 密度は None（0 ではない）]"
P=$(proj); python3 - "$P" <<'PY'
import sys, re
from pathlib import Path
for f in Path(sys.argv[1]).glob("docs/lifecycle/0[5-8]-*.md"):
    s = f.read_text(); s = re.sub(r"\| DEF-ID \|.*?(?=\n\n|\n## )", "", s, flags=re.S); f.write_text(s)
PY
OUT=$(run "$P")
expect_out  "密度・未解決は算出できない" "欠陥表なし" "$OUT"
expect_noout "0 件と書かない" "欠陥: 0 件" "$OUT"
OUT=$(run "$P" --gate); RC=$?
expect_exit "severe_open が None → 判定不能 → exit 2" 2 "$RC"

echo "[ケース7: 基準表]"
P=$(proj); fill "$P"; rm "$P/docs/test/TESTING_STRATEGY.md"
OUT=$(run "$P" --gate); RC=$?
expect_exit "基準表が無ければ 2" 2 "$RC"
expect_out  "基準なしと出す" "基準が無い" "$OUT"
P=$(proj); fill "$P"; sed -i 's/| `severe_open == 0` | `qa-review-standards`（ISTQB severity） |/| `severe_open == 0` |  |/' "$P/docs/test/TESTING_STRATEGY.md"
OUT=$(run "$P" --gate)
expect_out  "出典が空の行は読まない" "読まず 3." "$OUT"
expect_noout "読まなかった基準は判定に出ない" "✗ 3." "$OUT"

echo "[ケース8: 偏りの検知（母数 ≥ 10、区分 ≥ 5、+15pt）]"
P=$(proj); python3 - "$P" <<'PY'
import sys
from pathlib import Path
p = Path(sys.argv[1])/"docs/lifecycle/06-integration-test.md"; s = p.read_text()
rows = "".join(f"| IT-{i:03d} | BD-001 | {'外部I/F' if i<=6 else 'I/F契約'} | s |  |  | {'fail' if i<=4 else 'pass'} | 2026-09-19 | x |\n" for i in range(1,13))
import re
s = re.sub(r"\| IT-001 \|.*?\n(?:\| IT-0xx \|.*?\n)+", rows, s, count=1, flags=re.S); p.write_text(s)
PY
OUT=$(run "$P" --level IT)
expect_out  "「外部I/F」の不合格率の偏りを検知" "[bias]" "$OUT"

echo "[ケース9: --history と --into]"
P=$(proj); fill "$P"
OUT=$(run "$P" --history); RC=$?
expect_out  "初回は履歴を開始" "履歴を開始" "$OUT"
[ -f "$P/docs/test/metrics-history.tsv" ] && grep -q "ALL" "$P/docs/test/metrics-history.tsv" && ok "metrics-history.tsv に ALL 行" || ng "metrics-history.tsv に ALL 行" "無い"
sed -i 's/| UAT-004 | 延滞 | REQ-F-004 |  |  |  |  |/| UAT-004 | 延滞 | REQ-F-004 |  |  |  | 合 |/' "$P/docs/lifecycle/08-acceptance-test.md"
OUT=$(run "$P" --history)
expect_out  "2 回目は前回との差分" "前回 2026-09-20 から: 実行" "$OUT"
R="$P/docs/test/iso29119-test-completion-report.md"; BEFORE=$(grep -c '' "$R"); TAIL_BEFORE=$(sed -n '/metrics:end/,$p' "$R" | md5sum)
OUT=$(run "$P" --into docs/test/iso29119-test-completion-report.md)
expect_out  "置き換えた旨" "✅ 置き換え" "$OUT"
grep -q "| ST | 8 | " "$R" && ok "§2 にレベル別の表が入る" || ng "§2 にレベル別の表が入る" "無い"
grep -q "判定候補:" "$R" && ok "判定候補が入る（GO/NO-GO は人）" || ng "判定候補が入る" "無い"
[ "$(sed -n '/metrics:end/,$p' "$R" | md5sum)" = "$TAIL_BEFORE" ] && ok "マーカーの外は無変更" || ng "マーカーの外は無変更" "変わった"
OUT=$(run "$P" --into docs/test/iso29119-test-completion-report.md)
[ "$(grep -c 'metrics:begin' "$R")" -eq 1 ] && ok "再実行してもマーカーは 1 組のまま" || ng "再実行してもマーカーは 1 組のまま" "$(grep -c metrics:begin "$R")"

echo "[ケース10: CSV の実行記録を読む]"
P=$(proj); printf 'テストID,ロール,対象機能,ツアー観点,テスト目的,前提条件,手順,期待される結果,severity,結果,実施日,実施者,DEF\nST-101,一般,貸出,Money,x,x,x,x,High,pass,2026-09-19,藤曲,\nST-102,一般,返却,Money,x,x,x,x,High,fail,2026-09-19,藤曲,DEF-001\nST-103,一般,予約,Money,x,x,x,x,Low,,,,\n' > "$P/docs/system_test_cases.csv"
OUT=$(run "$P" --level ST)
expect_out  "CSV の 3 件が加わる（07 の 1 件 + 3）" "全 4 / 実行 3" "$OUT"
P=$(proj); printf 'テストID,ロール,対象機能\nST-201,一般,貸出\n' > "$P/docs/system_test_cases.csv"
OUT=$(run "$P" --level ST)
expect_out  "結果列の無い旧形式 CSV は読まない（07 の 1 件だけ）" "全 1 / 実行 1" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
