#!/bin/bash
# test-trace-check.sh — trace-check.sh の回帰テスト
# 検査ロジック（重複定義・未定義参照・所有ファイル違反・追跡表未記載・カバー漏れ・孤立テスト）が
# 実際に検出できることを、合格ケースと不合格ケースの両方で確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHECK="$KIT_DIR/scripts/trace-check.sh"
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
echo "[ケース4: templates/lifecycle の雛形]"
mkdir -p "$TMP/fresh"
bash "$KIT_DIR/scripts/init-lifecycle.sh" "$TMP/fresh" >/dev/null 2>&1
OUT=$(bash "$CHECK" "$TMP/fresh/docs/lifecycle" -o "$TMP/fresh-report.md" 2>&1); RC=$?
expect_exit "init-lifecycle.sh 直後は NG=0" 0 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
