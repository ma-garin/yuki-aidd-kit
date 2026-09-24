#!/bin/bash
# test-trace-check.sh — trace-check.sh の回帰テスト
# 検査ロジック（重複定義・未定義参照・所有ファイル違反・追跡表未記載・カバー漏れ・孤立テスト・C7 suspect）が
# 実際に検出できることを、合格ケースと不合格ケースの両方で確認する。--impact / --refresh も確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$KIT_DIR/02_共通/ツール/trace-check.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng()  { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }

expect_exit() { # 名前, 期待exit, 実exit
  [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"
}
expect_report_has() { # 名前, 期待文字列, レポートパス
  grep -qF "$2" "$3" && ok "$1" || ng "$1" "レポートに '$2' が無い"
}
expect_report_lacks() { # 名前, 出てはいけない文字列, レポートパス
  grep -qF "$2" "$3" && ng "$1" "レポートに '$2' が出た" || ok "$1"
}

echo "=== trace-check.sh 回帰テスト ==="

# --- ケース1: 整合の取れた工程文書（NG=0 を期待） ---------------------------
G="$TMP/good/docs/lifecycle"; mkdir -p "$G"
cat > "$G/00-rfd.md" <<'EOF'
# RFD
### RFD-001 エクスポート形式の追加
決定: CSV を追加する。
EOF
cat > "$G/01-requirements.md" <<'EOF'
# 要件定義書
| ID | 要件 | 優先度 | 由来 RFD | 受入基準 |
|---|---|---|---|---|
| REQ-F-001 | CSV 出力 | Must | RFD-001 | 1クリックで CSV が保存される |
| REQ-N-001 | 初回ロード | Must | RFD-001 | 3G相当で3秒以内 |
EOF
cat > "$G/02-basic-design.md" <<'EOF'
# 基本設計書
| ID | 要素 | 責務 | 対応 REQ |
|---|---|---|---|
| BD-001 | エクスポータ | CSV 生成 | REQ-F-001 |
| BD-002 | 初期化処理 | 起動高速化 | REQ-N-001 |
EOF
cat > "$G/03-detailed-design.md" <<'EOF'
# 詳細設計書
### DD-001 to_csv()
対応 BD: BD-001
EOF
cat > "$G/04-implementation.md" <<'EOF'
# 実装記録
| ID | タスク | 対応 DD | 状態 |
|---|---|---|---|
| T-001 | to_csv 実装 | DD-001 | 完了 |
EOF
cat > "$G/05-unit-test.md" <<'EOF'
# 単体テスト
| ID | 対象 DD | 区分 | 結果 |
|---|---|---|---|
| UT-001 | DD-001 | 正常系 | pass |
EOF
cat > "$G/06-integration-test.md" <<'EOF'
# 結合テスト
| ID | 対象 BD | 観点 | 結果 |
|---|---|---|---|
| IT-001 | BD-001 | I/F契約 | pass |
EOF
cat > "$G/07-system-test.md" <<'EOF'
# システムテスト
| ID | 対象 REQ-N | 実測値 | 合否 |
|---|---|---|---|
| ST-001 | REQ-N-001 | 2.1秒 | 合 |
EOF
cat > "$G/08-acceptance-test.md" <<'EOF'
# 受け入れテスト
| ID | 対応 REQ-F | 合否 |
|---|---|---|
| UAT-001 | REQ-F-001 | 合 |
EOF
cat > "$G/09-operations.md" <<'EOF'
# 保守運用
| ID | 監視対象 | 正常の基準 |
|---|---|---|
| OPS-001 | 稼働 | 200 応答 |
EOF
cat > "$G/traceability-matrix.md" <<'EOF'
# トレーサビリティマトリクス
| REQ-ID | 要件（要約） | 由来 RFD | BD | DD | 実装 T | UT | IT | ST | UAT | 状態 |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-F-001 | CSV 出力 | RFD-001 | BD-001 | DD-001 | T-001 | UT-001 | IT-001 | - | UAT-001 | 合格 |
| REQ-N-001 | 初回ロード | RFD-001 | BD-002 | - | T-001 | - | - | ST-001 | - | 合格 |
EOF

echo "[ケース1: 整合の取れた工程文書]"
OUT=$(bash "$CHECK" "$G" -o "$TMP/good-report.md" 2>&1); RC=$?
expect_exit "NG=0 で exit 0" 0 "$RC"
printf '%s' "$OUT" | grep -q "NG=0" && ok "結論に NG=0 が出る" || ng "結論に NG=0 が出る" "$(printf '%s' "$OUT" | head -3)"
expect_report_has "詳細レポートを書き出す" "トレーサビリティ検査レポート" "$TMP/good-report.md"
# UAT-001 から T-001 を誤検出しないこと（トークン境界の回帰）
expect_report_lacks "UAT-001 を T-001 と誤検出しない" "未定義参照 | T-001" "$TMP/good-report.md"

# --- ケース2: 各種 NG を仕込んだ工程文書 ------------------------------------
B="$TMP/bad/docs/lifecycle"; mkdir -p "$B"
cp "$G/00-rfd.md" "$G/02-basic-design.md" "$G/03-detailed-design.md" \
   "$G/04-implementation.md" "$G/06-integration-test.md" "$G/09-operations.md" "$B/"
cat > "$B/01-requirements.md" <<'EOF'
# 要件定義書
| ID | 要件 | 優先度 | 由来 RFD | 受入基準 |
|---|---|---|---|---|
| REQ-F-001 | CSV 出力 | Must | RFD-001 | 1クリックで CSV が保存される |
| REQ-N-001 | 初回ロード | Must | RFD-001 | 3G相当で3秒以内 |
| REQ-F-002 | PDF 出力 | Should | RFD-001 | 1クリックで PDF が保存される |
EOF
# 単体テスト側に詳細設計の対応表を複製 → 重複定義／所有ファイル違反
cat > "$B/05-unit-test.md" <<'EOF'
# 単体テスト
| ID | 対象 DD | 区分 | 結果 |
|---|---|---|---|
| UT-001 | DD-001 | 正常系 | pass |
| UT-009 | DD-001 | 境界値 | pass |
| DD-001 | to_csv() | 参考 | - |
EOF
# 存在しない ST-999 を参照
cat > "$B/07-system-test.md" <<'EOF'
# システムテスト
| ID | 対象 REQ-N | 実測値 | 合否 |
|---|---|---|---|
| ST-001 | REQ-N-001 | 2.1秒 | 合 |

未実施: ST-999 は次回計測する。
EOF
cat > "$B/08-acceptance-test.md" <<'EOF'
# 受け入れテスト
| ID | 対応 REQ-F | 合否 |
|---|---|---|
| UAT-001 | REQ-F-001 | 合 |
EOF
# REQ-F-002 は追跡表に無い／REQ-N-001 は ST 未割当かつ BD 列が空
cat > "$B/traceability-matrix.md" <<'EOF'
# トレーサビリティマトリクス
| REQ-ID | 要件（要約） | 由来 RFD | BD | DD | 実装 T | UT | IT | ST | UAT | 状態 |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-F-001 | CSV 出力 | RFD-001 | BD-001 | DD-001 | T-001 | UT-001 | IT-001 | - | UAT-001 | 合格 |
| REQ-N-001 | 初回ロード | RFD-001 |  | - | T-001 | - | - | - | - | 検証中 |
EOF

echo "[ケース2: NG を仕込んだ工程文書]"
OUT=$(bash "$CHECK" "$B" -o "$TMP/bad-report.md" 2>&1); RC=$?
expect_exit "NG>0 で exit 1" 1 "$RC"
R="$TMP/bad-report.md"
expect_report_has "重複定義を検出（DD-001 を単体テストにも定義）" "| 重複定義 | DD-001 |" "$R"
expect_report_has "所有ファイル違反を検出（DD-001）"           "| 所有ファイル違反 | DD-001 |" "$R"
expect_report_has "未定義参照を検出（ST-999）"                 "| 未定義参照 | ST-999 |" "$R"
expect_report_has "追跡表に未記載を検出（REQ-F-002）"          "| 追跡表に未記載 | REQ-F-002 |" "$R"
expect_report_has "カバー漏れ（BD 列が空欄）を検出"            "追跡表の BD 列が空欄" "$R"
expect_report_has "カバー漏れ（REQ-N の ST 未割当）を検出"     "システムテスト未割当" "$R"
expect_report_has "孤立テストを検出（UT-009）"                 "| 孤立テスト | UT-009 |" "$R"

# --- ケース3: 対象が無い場合はスキップ（CI を不用意に落とさない） -----------
echo "[ケース3: 対象なし]"
OUT=$(bash "$CHECK" "$TMP/does-not-exist" -o "$TMP/none-report.md" 2>&1); RC=$?
expect_exit "ディレクトリ不在でも exit 0（スキップ）" 0 "$RC"
mkdir -p "$TMP/empty"
OUT=$(bash "$CHECK" "$TMP/empty" -o "$TMP/none-report.md" 2>&1); RC=$?
expect_exit "文書ゼロでも exit 0（スキップ）" 0 "$RC"

# --- ケース4: 配布する雛形そのものが NG=0 で始まること -----------------------
# （雛形が最初から NG を出すと、利用者が trace-check の出力を無視するようになる）
echo "[ケース4: 02_共通/ひな形/lifecycle の雛形]"
mkdir -p "$TMP/fresh"
bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-lifecycle.sh" "$TMP/fresh" >/dev/null 2>&1
OUT=$(bash "$CHECK" "$TMP/fresh/docs/lifecycle" -o "$TMP/fresh-report.md" 2>&1); RC=$?
expect_exit "init-lifecycle.sh 直後は NG=0" 0 "$RC"
mkdir -p "$TMP/fresh-gh"
bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-lifecycle.sh" "$TMP/fresh-gh" --github >/dev/null 2>&1
[ -f "$TMP/fresh-gh/scripts/trace-check.sh" ] && [ -f "$TMP/fresh-gh/scripts/section_hash.py" ] \
  && ok "init-lifecycle.sh --github は trace-check.sh の隣に section_hash.py も置く（C7 が隣を参照する）" \
  || ng "init-lifecycle.sh --github は section_hash.py も置く" "scripts/section_hash.py が無い"

# --- ケース5〜9: 版つきリンク（C7 suspect）・--impact・--refresh ------------------
HASH="$KIT_DIR/02_共通/ツール/section_hash.py"
ver() { python3 "$HASH" hash "$1" "$2" | cut -d@ -f2; }   # 対象ディレクトリ, ID → 現在の版（7 桁）
sedi() { local f="${@: -1}"; sed "${@:1:$#-1}" "$f" > "$f.sedi" && mv "$f.sedi" "$f"; }
# 詳細設計に子節と次の DD を足した版（見出しで定義した ID の節の範囲を確かめるため）
mkv() { # 出力先ディレクトリ
  mkdir -p "$1"; cp "$G"/*.md "$1/"
  cat > "$1/03-detailed-design.md" <<'EOF'
# 詳細設計書
### DD-001 to_csv()
対応 BD: BD-001
#### 異常系
空配列なら見出し行だけを出す。
### DD-002 to_pdf()
対応 BD: BD-001
EOF
  cat > "$1/05-unit-test.md" <<'EOF'
# 単体テスト
| ID | 対象 DD | 区分 | 結果 |
|---|---|---|---|
| UT-001 | DD-001 | 正常系 | pass |
| UT-002 | DD-002 | 正常系 | pass |
EOF
  local rf dd; rf=$(ver "$1" REQ-F-001); dd=$(ver "$1" DD-001)
  cat > "$1/traceability-matrix.md" <<EOF
# トレーサビリティマトリクス
| REQ-ID | 要件（要約） | 由来 RFD | BD | DD | 実装 T | UT | IT | ST | UAT | 状態 |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-F-001@$rf | CSV 出力 | RFD-001 | BD-001 | DD-001@$dd, DD-002 | T-001 | UT-001, UT-002 | IT-001 | - | UAT-001 | 合格 |
| REQ-N-001 | 初回ロード | RFD-001 | BD-002 | - | T-001 | - | - | ST-001 | - | 合格 |
EOF
}
run_v() { bash "$CHECK" "$1" -o "$1.report.md" 2>&1; }

echo "[ケース5: 版つきリンクが現在の版と一致 → NG=0。空白・全角半角だけの変更も一致のまま]"
V="$TMP/ver/docs/lifecycle"; mkv "$V"
OUT=$(run_v "$V"); RC=$?
expect_exit "版が一致していれば NG=0" 0 "$RC"
expect_report_lacks "C7 は出ない" "C7 suspect" "$V.report.md"
sedi 's/| REQ-F-001 | CSV 出力 | Must |/|  REQ-F-001  |   CSV　出力 | Ｍｕｓｔ |/' "$V/01-requirements.md"
printf '\n\n' >> "$V/01-requirements.md"
OUT=$(run_v "$V"); RC=$?
expect_exit "空白・空行・全角英字だけの変更は suspect にしない（NFKC と空白の正規化）" 0 "$RC"

echo "[ケース6: 上流を書き換えると C7 suspect]"
OLD=$(ver "$V" REQ-F-001)
sedi 's/1クリックで CSV が保存される/2クリックで CSV が保存される/' "$V/01-requirements.md"
NEW=$(ver "$V" REQ-F-001)
OUT=$(run_v "$V"); RC=$?
expect_exit "上流の要件を変えると exit 1" 1 "$RC"
expect_report_has "C7 の対象は追跡表の file:line" "| C7 suspect | $V/traceability-matrix.md:4 |" "$V.report.md"
expect_report_has "内容は「上流 ID が変わった（記録 → 現在）」" "上流 REQ-F-001 が変わった（記録 $OLD → 現在 $NEW）" "$V.report.md"
expect_report_lacks "@ の無い REQ-N-001 は suspect にしない" "上流 REQ-N-001" "$V.report.md"
W="$TMP/ver2/docs/lifecycle"; mkv "$W"
sedi 's/| REQ-N-001 | 初回ロード | Must | RFD-001 | 3G相当で3秒以内 |/| REQ-N-001 | 初回ロード | Must | RFD-001 | 4G相当で1秒以内 |/' "$W/01-requirements.md"
OUT=$(run_v "$W"); RC=$?
expect_exit "表で定義した ID の単位は行（同じ表の別の要件を変えても suspect にしない）" 0 "$RC"
sedi 's/空配列なら見出し行だけを出す。/空配列なら例外を投げる。/' "$W/03-detailed-design.md"
OUT=$(run_v "$W"); RC=$?
expect_exit "見出しで定義した ID は子節（#### 異常系）の変更も suspect" 1 "$RC"
expect_report_has "DD-001 の suspect" "上流 DD-001 が変わった" "$W.report.md"
X="$TMP/ver3/docs/lifecycle"; mkv "$X"
printf '次の DD の本文を足した。\n' >> "$X/03-detailed-design.md"
OUT=$(run_v "$X"); RC=$?
expect_exit "同じレベルの次の見出し（### DD-002）以降の変更は DD-001 を suspect にしない" 0 "$RC"
sedi 's/1クリックで CSV が保存される/2クリックで CSV が保存される/' "$X/01-requirements.md"
sedi 's/REQ-F-001@[0-9a-f]*/REQ-F-001/' "$X/traceability-matrix.md"
OUT=$(run_v "$X"); RC=$?
expect_exit "@ の無いリンクは従来どおり（上流を変えても C7 にしない）" 0 "$RC"
sedi 's/| REQ-F-001 |/| REQ-F-001@zz |/' "$X/traceability-matrix.md"
OUT=$(run_v "$X"); RC=$?
expect_exit "書式の壊れた記録（@zz）は NG" 1 "$RC"
expect_report_has "書式不正を出す" "の書式が不正" "$X.report.md"

echo "[ケース7: --impact（下流の連鎖）]"
OUT=$(bash "$CHECK" "$V" --impact REQ-F-001 2>&1); RC=$?
expect_exit "--impact は exit 0" 0 "$RC"
for id in BD-001 DD-001 DD-002 T-001 UT-001 UT-002 IT-001 UAT-001; do
  printf '%s\n' "$OUT" | grep -q "$id（" && ok "--impact REQ-F-001 に $id" || ng "--impact REQ-F-001 に $id" "$(printf '%s' "$OUT" | tr '\n' ' ')"
done
printf '%s\n' "$OUT" | grep -q '^    DD-001（' && ok "連鎖で出す（DD-001 は BD-001 の下）" || ng "連鎖で出す（DD-001 は BD-001 の下）" "$(printf '%s' "$OUT" | tr '\n' '/')"
printf '%s\n' "$OUT" | grep -q '^      UT-001（' && ok "連鎖で出す（UT-001 は DD-001 の下）" || ng "連鎖で出す（UT-001 は DD-001 の下）" "$(printf '%s' "$OUT" | tr '\n' '/')"
printf '%s\n' "$OUT" | grep -qE 'ST-001（|BD-002（' && ng "別の要件の下流は出さない" "ST-001 / BD-002 が出た" || ok "別の要件の下流（ST-001・BD-002）は出さない"
expect_out() { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_out "suspect になる記録の場所を出す" "traceability-matrix.md:4 REQ-F-001@" "$OUT"
OUT=$(bash "$CHECK" "$V" --impact DD-001 2>&1)
printf '%s\n' "$OUT" | grep -q 'UT-001（' && ok "--impact DD-001 に UT-001" || ng "--impact DD-001 に UT-001" "無い"
printf '%s\n' "$OUT" | grep -qE 'BD-001（|UT-002（' && ng "--impact DD-001 は上流・兄弟を出さない" "BD-001 / UT-002 が出た" || ok "--impact DD-001 は上流・兄弟（BD-001・UT-002）を出さない"
OUT=$(bash "$CHECK" "$V" --impact REQ-F-999 2>&1); RC=$?
expect_exit "--impact 存在しない ID は exit 1" 1 "$RC"

echo "[ケース8: --refresh で記録を現在の版にすると suspect が消える]"
OUT=$(bash "$CHECK" "$V" --refresh REQ-F-001 2>&1); RC=$?
expect_exit "--refresh は exit 0" 0 "$RC"
grep -qF "REQ-F-001@$NEW |" "$V/traceability-matrix.md" && ok "記録が現在の版 $NEW に書き換わる" || ng "記録が現在の版に書き換わる" "$(sed -n 4p "$V/traceability-matrix.md")"
expect_out "保守者の再確認の記録だと出す（AI は打たない）" "AI は --refresh を打たない" "$OUT"
OUT=$(run_v "$V"); RC=$?
expect_exit "--refresh 後は NG=0" 0 "$RC"
OUT=$(bash "$CHECK" "$V" --refresh REQ-F-999 2>&1); RC=$?
expect_exit "--refresh 定義の無い ID は exit 1（書き換えない）" 1 "$RC"

echo "[ケース9: section_hash.py が隣に無いとき]"
S="$TMP/solo"; mkdir -p "$S"; cp "$CHECK" "$S/trace-check.sh"
OUT=$(bash "$S/trace-check.sh" "$W" -o "$TMP/solo-report.md" 2>&1); RC=$?
expect_exit "版つきリンクがあるのに版を計算できない → NG（判定不能を合格に数えない）" 1 "$RC"
expect_report_has "判定不能と出す" "判定不能" "$TMP/solo-report.md"
OUT=$(bash "$S/trace-check.sh" "$G" -o "$TMP/solo-report.md" 2>&1); RC=$?
expect_exit "版つきリンクが無ければ section_hash.py 無しでも従来どおり NG=0" 0 "$RC"


echo "[ケース10: 版の切り出し・正規化の細部・引数の欠け]"
Y="$TMP/ver4/docs/lifecycle"; mkv "$Y"; RF=$(ver "$Y" REQ-F-001); DD=$(ver "$Y" DD-001)
sedi "s/| REQ-F-001@$RF |/| （REQ-F-001@$RF） |/; s/DD-001@$DD, DD-002/DD-001@$DD;DD-002/" "$Y/traceability-matrix.md"
OUT=$(run_v "$Y"); RC=$?
expect_exit "版は @ の直後の英数字だけ読む（（REQ-F-001@版） と DD-001@版;DD-002 は書式不正にしない）" 0 "$RC"
sedi 's/| REQ-F-001 | CSV 出力 | Must | RFD-001 | 1クリックで CSV が保存される |/|REQ-F-001|CSV 出力|  Must|RFD-001  |1クリックで CSV が保存される|/' "$Y/01-requirements.md"
python3 - "$Y/03-detailed-design.md" <<'PY'
import sys
p = sys.argv[1]; s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s.replace("対応 BD: BD-001\n#### 異常系", "対応\nBD: BD-001\n#### 異常系", 1))
PY
grep -q '^BD: BD-001$' "$Y/03-detailed-design.md" || ng "（前提）段落の折り返しを変えた" "書き換わっていない"
OUT=$(run_v "$Y"); RC=$?
expect_exit "表の | の周りの空白差・段落の折り返し位置（空白の位置での改行）の差だけなら suspect にしない" 0 "$RC"
# 引数の欠けで回り続けても検査全体を止めないよう 5 秒で打ち切る（124 = 時間切れ）
wait5() { "$@" > "$TMP/w5.out" 2>&1 & local p=$! i=0; while kill -0 "$p" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
  if kill -0 "$p" 2>/dev/null; then kill "$p" 2>/dev/null; wait "$p" 2>/dev/null; return 124; fi; wait "$p"; }
wait5 bash "$CHECK" "$Y" -o; RC=$?
expect_exit "-o に値が無い → 使い方を出して exit 2" 2 "$RC"
expect_out "使い方を出す" "使い方:" "$(cat "$TMP/w5.out")"
wait5 bash "$CHECK" "$Y" --impact -o; RC=$?
expect_exit "--impact の値がオプション（-o）→ exit 2" 2 "$RC"

echo "[ケース11: --tests（テストコードと CSV のテスト ID の突合。C8 NG・C9 WARN）]"
T11="$TMP/t11"; mkdir -p "$T11/docs" "$T11/e2e/sub" "$T11/tests" "$T11/e2e/node_modules/x"; cp -r "$TMP/good/docs/lifecycle" "$T11/docs/"
printf 'テストID,ロール,対象機能,期待される結果,結果,仕様の状態\nST-101,一般,貸出,a,,\nST-102,一般,返却,b,,\nST-103,一般,予約,c,,\nST-104,一般,延滞,d,,範囲外\n' > "$T11/docs/system_test_cases.csv"
printf "import { test } from '@playwright/test';\n// spec: ST-101\ntest('ST-101 貸出', async () => {});\n" > "$T11/e2e/lend.spec.ts"
printf "/** @spec ST-102, ST-103 */\ntest('返却と予約', async () => {});\n" > "$T11/e2e/sub/return.test.ts"
printf '// spec: ST-103\n' > "$T11/e2e/node_modules/x/dep.spec.ts"
printf 'def test_lend():\n    """spec: UT-001"""\n' > "$T11/e2e/test_unit.py"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/e2e" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "全 ID がコードにある（// spec: と @spec の複数 ID）→ exit 0" 0 "$RC"
expect_report_lacks "範囲外の行（ST-104）は C8 にしない" "| C8 テストコード未対応 | ST-104 |" "$T11/r.md"
expect_report_lacks "工程文書で定義済みの ID（UT-001）は C9 にしない" "| C9 CSV に無い ID | UT-001 |" "$T11/r.md"
expect_report_has "突合の件数をレポートに出す" "spec の ID 4 件" "$T11/r.md"
printf "/** @spec ST-102 */\ntest('返却', async () => {});\n" > "$T11/e2e/sub/return.test.ts"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/e2e" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "CSV の ID（ST-103）がコードに無い → C8 NG で exit 1" 1 "$RC"
expect_report_has "C8 に ST-103 を出す（node_modules の中の spec: ST-103 は数えない）" "| C8 テストコード未対応 | ST-103 |" "$T11/r.md"
printf "/** @spec ST-102,ST-103 */\n// spec: ST-999\n" > "$T11/e2e/sub/return.test.ts"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/e2e" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "コードの ID（ST-999）が CSV に無いだけなら WARN（exit 0）" 0 "$RC"
expect_report_has "C9 に ST-999 を出す" "| C9 CSV に無い ID | ST-999 |" "$T11/r.md"
printf 'ST-101 と ST-102 と ST-103（spec: の無い ID は拾わない）\n' > "$T11/tests/test_other.py"
printf "test('ST-101', () => {})\n" > "$T11/e2e/lend.spec.ts"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/e2e" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "題名に ID があっても spec: / @spec が無ければ未対応（C8）" 1 "$RC"
expect_report_has "C8 に ST-101" "| C8 テストコード未対応 | ST-101 |" "$T11/r.md"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "--tests が無ければ従来どおり（C8・C9 をしない）" 0 "$RC"
expect_report_lacks "--tests 無しでは C8 を出さない" "C8" "$T11/r.md"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/nope" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "テストのディレクトリが無い → 判定不能で NG" 1 "$RC"
OUT=$(bash "$CHECK" "$T11/docs/lifecycle" --tests "$T11/e2e" --csv "$T11/none.csv" -o "$T11/r.md" 2>&1); RC=$?
expect_exit "CSV が無い → 判定不能で NG（合格に数えない）" 1 "$RC"
expect_report_has "判定不能と出す" "判定不能（テストケースの CSV が無い" "$T11/r.md"
T12="$TMP/t12"; mkdir -p "$T12/docs" "$T12/e2e"; cp "$T11/docs/system_test_cases.csv" "$T12/docs/"
printf '// spec: ST-101, ST-102, ST-103\n' > "$T12/e2e/all.spec.ts"
OUT=$(bash "$CHECK" "$T12/docs/lifecycle" --tests "$T12/e2e" -o "$T12/r.md" 2>&1); RC=$?
expect_exit "工程文書が無くても --tests なら突合する（CSV は docs/ から探す）→ exit 0" 0 "$RC"
expect_report_has "工程文書なしでも突合の件数を出す" "突合対象 3 件" "$T12/r.md"

# --- [検証: B-22] 検証担当が足した節（実装担当とは別。赤は赤のまま残す） ------------
echo "[検証: B-22]"
# 時間切れ付きで実行する（macOS に timeout が無いため bash で待つ）。戻り値 124 = 時間切れ
run_to() { "$@" > "$TMP/to.out" 2>&1 & local p=$! i=0; while kill -0 "$p" 2>/dev/null && [ $i -lt 50 ]; do sleep 0.1; i=$((i+1)); done
  if kill -0 "$p" 2>/dev/null; then kill "$p" 2>/dev/null; wait "$p" 2>/dev/null; return 124; fi; wait "$p"; }
Q="$TMP/vq/docs/lifecycle"; mkv "$Q"
printf '%s\n' "$(sed 's/$/   /' "$Q/01-requirements.md")" > "$Q/01-requirements.md.t" && mv "$Q/01-requirements.md.t" "$Q/01-requirements.md"
sedi 's/$/\r/' "$Q/01-requirements.md"
printf '# 詳細設計書\n\n\n### DD-001   to_csv()  \n対応 BD: BD-001\n\n#### 異常系\n\n空配列なら見出し行だけを出す。   \n### DD-002 to_pdf()\n対応 BD: BD-001\n' > "$Q/03-detailed-design.md"
OUT=$(run_v "$Q"); RC=$?
expect_exit "[検証] 末尾空白・CRLF・見出し節の空行増減だけなら suspect にしない" 0 "$RC"
sedi 's/### DD-001   to_csv()/### DD-001 to_csv(rows)/' "$Q/03-detailed-design.md"
OUT=$(run_v "$Q"); RC=$?
expect_report_has "[検証] ID の節の見出し自体を変えると suspect" "上流 DD-001 が変わった" "$Q.report.md"
Q2="$TMP/vq2/docs/lifecycle"; mkv "$Q2"; sedi 's/| REQ-F-001@[0-9a-f]* |/| REQ-F-001@ |/' "$Q2/traceability-matrix.md"
OUT=$(run_v "$Q2"); RC=$?
expect_exit "[検証] @ の後ろが空（REQ-F-001@）でも落ちずに NG" 1 "$RC"
expect_report_has "[検証] @ の後ろが空は書式不正" "記録 'REQ-F-001@' の書式が不正" "$Q2.report.md"
Q3="$TMP/vq3/docs/lifecycle"; mkdir -p "$Q3"
printf '# 要件\n| ID | 要件 |\n|---|---|\n| REQ-F-001 | a |\n' > "$Q3/01-requirements.md"
printf '# 詳細設計\n### DD-001 x\n根拠: REQ-F-001。検証: UT-001\n' > "$Q3/03-detailed-design.md"
printf '# 単体\n| ID | 対象 | 結果 |\n|---|---|---|\n| UT-001 | DD-001（REQ-F-001） | pass |\n' > "$Q3/05-unit-test.md"
run_to bash "$CHECK" "$Q3" --impact REQ-F-001; RC=$?
expect_exit "[検証] --impact 追跡表なし・相互参照ありでも止まる" 0 "$RC"
grep -q '^    UT-001（' "$TMP/to.out" && ok "[検証] --impact 3 段（REQ→DD→UT）を連鎖で出す" || ng "[検証] --impact 3 段（REQ→DD→UT）" "$(tr '\n' '/' < "$TMP/to.out")"
run_to bash "$CHECK" "$Q3" --impact; RC=$?
expect_exit "[検証] --impact に ID が無い → exit 2（時間切れ 124 はハング）" 2 "$RC"
run_to bash "$CHECK" "$Q3" --refresh; RC=$?
expect_exit "[検証] --refresh に ID が無い → exit 2（時間切れ 124 はハング）" 2 "$RC"
Q4="$TMP/vq4/docs/lifecycle"; mkv "$Q4"
sedi 's/REQ-F-001@[0-9a-f]*/REQ-F-001@0000000/; s/$/\r/' "$Q4/traceability-matrix.md"; cp "$Q4/traceability-matrix.md" "$TMP/vq4.orig"
bash "$CHECK" "$Q4" --refresh REQ-F-001 >/dev/null 2>&1
N=$(diff "$TMP/vq4.orig" "$Q4/traceability-matrix.md" | grep -c '^>')
[ "$N" -eq 1 ] && ok "[検証] --refresh は CRLF の追跡表でも対象の 1 行だけ書き換える" || ng "[検証] --refresh は CRLF の追跡表でも対象の 1 行だけ" "書き換わった行 $N / $(wc -l < "$TMP/vq4.orig")（改行が LF に変わる）"
Q5="$TMP/vq5/docs/lifecycle"; mkv "$Q5"; D5=$(ver "$Q5" DD-001)
sedi "s/DD-001@$D5, DD-002/DD-001@0000000;DD-002/" "$Q5/traceability-matrix.md"
printf '\n補足: REQ-F-001@0000000 は表の外の記述。\n' >> "$Q5/traceability-matrix.md"
bash "$CHECK" "$Q5" --refresh DD-001 >/dev/null 2>&1
grep -q 'DD-002' "$Q5/traceability-matrix.md" && ok "[検証] --refresh DD-001 は隣の DD-002（; 区切り）を消さない" || ng "[検証] --refresh DD-001 は隣の DD-002 を消さない" "$(sed -n 4p "$Q5/traceability-matrix.md" | cut -d'|' -f6)"
grep -q '^補足: REQ-F-001@0000000 は' "$Q5/traceability-matrix.md" && ok "[検証] --refresh は表の外の行を書き換えない" || ng "[検証] --refresh は表の外の行を書き換えない" "書き換わった"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
