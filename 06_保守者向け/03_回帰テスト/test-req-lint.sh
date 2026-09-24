#!/bin/bash
# test-req-lint.sh — req-lint.py（要件文の検査）の回帰テスト
# NG 3 種（数値の無い非機能目標・列挙数の不一致・ID の重複）と WARN 2 種（曖昧語・EARS 型に当たらない）が出ること、
# 正しい EARS 型の要件と配布雛形は 0 件で通ること（誤検知しない）を確かめる。終了コード 0/1/2 の契約も見る。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LINT="$KIT_DIR/02_共通/ツール/req-lint.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-200)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
run() { python3 "$LINT" "$@" 2>&1; }

echo "=== req-lint.py 回帰テスト ==="

echo "[ケース1: 正しい EARS 型の要件（5 型・英語）は NG=0 / WARN=0]"
cat > "$TMP/good.md" <<'EOF'
# 要件定義書

## 機能要件（REQ-F）

| ID | 要件（EARS 型） | 優先度 | 由来 RFD | 受入基準 |
|---|---|---|---|---|
| REQ-F-001 | 貸出画面は、利用者の貸出中の冊数を表示する。 | Must | RFD-001 | 冊数が 1 件単位で表示される |
| REQ-F-002 | 利用者が保存を押したとき、システムは入力内容を端末に保存する。 | Must | RFD-001 | 再読み込み後も残る |
| REQ-F-003 | オフラインの間、システムは入力を端末に保持する。 | Should | RFD-001 | 機内モードで 3 件入力して残る |
| REQ-F-004 | 通信に失敗した場合、システムは再送ボタンを表示する。 | Must | RFD-001 | 通信を切ると再送ボタンが出る |
| REQ-F-005 | 管理者機能を有効にした構成では、システムは操作ログを残す（90 日）。 | Could | RFD-001 | ログに 1 操作 1 行 |
| REQ-F-006 | When the user presses Export, the system shall save a CSV file. | Must | RFD-001 | CSV が 1 つ保存される |
| REQ-F-0xx |  | Should |  |  |

REQ-F-007: システムは、以下の 3 つの形式で出力する: CSV、PDF、JSON
REQ-F-008: システムは、以下の 2 つの帳票を出力する。
- 貸出票
- 返却票

平等・等しい・等号 は曖昧語にしない（熟語の「等」）。

## 非機能要件（REQ-N）

| ID | 特性 | 要件（EARS 型） | 由来 RFD | 判定基準 |
|---|---|---|---|---|
| REQ-N-001 | 性能効率性 | システムは、初回画面を 3 秒以内に表示する。 | RFD-001 | 3G 相当（1.6Mbps）で計測 |
| REQ-N-002 | 性能効率性 | システムは、同時 50 人の利用で応答を 200ms 以内に返す。 | RFD-001 | 負荷試験 |
| REQ-N-003 | 信頼性 | システムは、月間の可用性 99.9% を保つ。 | RFD-001 | 監視の稼働率 |
| REQ-N-004 | 性能効率性 | システムは、一覧を 1,000件 まで表示する。 | RFD-001 | 件数の上限で計測 |
| REQ-N-0xx | 使用性 |  |  |  |
EOF
OUT=$(run "$TMP/good.md"); RC=$?
expect_exit "正しい要件は exit 0" 0 "$RC"
expect_out  "NG=0 / WARN=0" "NG=0 / WARN=0" "$OUT"

echo "[ケース2: 配布雛形（init-lifecycle.sh 直後）は NG=0 / WARN=0]"
mkdir -p "$TMP/fresh"; bash "$KIT_DIR/00_導入/02_プロジェクト配布/init-lifecycle.sh" "$TMP/fresh" >/dev/null 2>&1
OUT=$(run "$TMP/fresh/docs/lifecycle/01-requirements.md"); RC=$?
expect_exit "雛形は exit 0（空の要件行・採番前の ID・HTML コメントの例は読まない）" 0 "$RC"
expect_out  "雛形は NG=0 / WARN=0" "NG=0 / WARN=0" "$OUT"

echo "[ケース3: NG 3 種]"
cat > "$TMP/bad.md" <<'EOF'
# 要件定義書

## 機能要件（REQ-F）

| ID | 要件 | 優先度 | 由来 RFD | 受入基準 |
|---|---|---|---|---|
| REQ-F-001 | システムは、以下の 3 つの形式で出力する: CSV、PDF | Must | RFD-001 | x |
| REQ-F-002 | 貸出画面は、利用者の貸出中の冊数を表示する。 | Must | RFD-001 | x |
| REQ-F-002 | 返却画面は、返却日を表示する。 | Must | RFD-001 | x |

REQ-F-003: システムは、以下の 2 つの帳票を出力する。
- 貸出票
- 返却票
- 督促状

## 非機能要件（REQ-N）

| ID | 特性 | 要件 | 由来 RFD | 判定基準 |
|---|---|---|---|---|
| REQ-N-001 | 性能効率性 | システムは、検索結果を短時間で返す。 | RFD-001 | 体感で待たない |
| REQ-N-002 | 信頼性 | システムは、同時アクセスに耐える。 | RFD-001 | 負荷試験で確認 |
EOF
OUT=$(run "$TMP/bad.md"); RC=$?
expect_exit "NG があれば exit 1" 1 "$RC"
expect_out  "数値の無い非機能目標（性能）" "数値の無い非機能目標: $TMP/bad.md:20 REQ-N-001" "$OUT"
expect_out  "数値の無い非機能目標（同時）" "数値の無い非機能目標: $TMP/bad.md:21 REQ-N-002" "$OUT"
expect_out  "列挙数の不一致（同じ行の : の後ろ）" "「以下の 3 つ」に対して列挙が 2 件" "$OUT"
expect_out  "列挙数の不一致（すぐ下の箇条書き）" "「以下の 2 つ」に対して列挙が 3 件" "$OUT"
expect_out  "要件 ID の重複" "要件 ID の重複: $TMP/bad.md:8 REQ-F-002" "$OUT"
expect_noout "RFD-001 の数字を数値と見ない（REQ-N-001 が NG のまま）" "REQ-N-001 — 「性能」があるが数値と単位が無い）" "$OUT"

echo "[ケース4: WARN 2 種（exit は 0 のまま）]"
cat > "$TMP/warn.md" <<'EOF'
| ID | 要件 | 優先度 | 由来 RFD | 受入基準 |
|---|---|---|---|---|
| REQ-F-001 | システムは、必要に応じて一覧を適切に並べ替える。 | Must | RFD-001 | 使いやすいこと |
| REQ-F-002 | The system shall provide a user friendly export, etc. | Must | RFD-001 | x |
| REQ-F-003 | CSV 出力 | Must | RFD-001 | 1 クリックで保存される |
| REQ-F-004 | 利用者が保存を押したとき、入力内容が残るように | Must | RFD-001 | x |
EOF
OUT=$(run "$TMP/warn.md"); RC=$?
expect_exit "WARN だけなら exit 0" 0 "$RC"
expect_out  "曖昧語（日本語・受入基準の列も見る）" "「適切に」「必要に応じて」「使いやすい」" "$OUT"
expect_out  "曖昧語（英語。空白・ハイフンの揺れと etc）" "「etc」「user-friendly」" "$OUT"
expect_out  "EARS 型に当たらない（名詞で終わる）" "EARS 型に当たらない: $TMP/warn.md:5 REQ-F-003" "$OUT"
expect_out  "EARS 型に当たらない（語尾が終止形でない）" "EARS 型に当たらない: $TMP/warn.md:6 REQ-F-004" "$OUT"
expect_noout "shall のある英語の要件は EARS 型とみなす" "EARS 型に当たらない: $TMP/warn.md:4" "$OUT"

echo "[ケース5: 辞書の追記（--words）と引数の誤り]"
printf '## 追加\n\n- `見やすい` — 例\n' > "$TMP/words.md"
printf '| ID | 要件 |\n|---|---|\n| REQ-F-001 | 一覧画面は、見やすい表を表示する。 |\n' > "$TMP/w2.md"
OUT=$(run "$TMP/w2.md")
expect_noout "既定の辞書に無い語は WARN にしない" "「見やすい」" "$OUT"
OUT=$(run "$TMP/w2.md" --words "$TMP/words.md")
expect_out  "--words で足した語を WARN にする" "「見やすい」" "$OUT"
REF="$KIT_DIR/03_ClaudeCode/skills/sdd-ecc-workflow/references/ambiguous-words.md"
[ -f "$REF" ] && grep -q '`適切に`' "$REF" && ok "辞書 references/ambiguous-words.md がある" || ng "辞書 references/ambiguous-words.md" "無い"
OUT=$(run "$TMP/none.md"); RC=$?
expect_exit "要件定義書が無い → exit 2" 2 "$RC"
OUT=$(run "$TMP/w2.md" --words "$TMP/nowords.md"); RC=$?
expect_exit "辞書が無い → exit 2" 2 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
