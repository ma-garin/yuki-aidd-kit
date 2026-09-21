#!/bin/bash
# test-git-gates.sh — git ゲート（秘密情報スキャン・UI 検証マーカー・UI hash）の回帰テスト
# 対象: scripts/pre-commit / scripts/pre-commit-ui-gate.sh / scripts/ui-hash.py
# 「手動 4 ケース確認」のみで再実行できなかった（06_保守者向け/01_内部仕様/09_指摘事項.md F-11）ことへの対処。
# 一時 git リポジトリを組み立て、各ゲートの終了コードと出力を assert する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | head -1)"; }
expect_empty(){ [ -z "$2" ] && ok "$1" || ng "$1" "出力あり: $(printf '%s' "$2" | head -1)"; }

# 一時リポジトリ（cwd を移して実行する。ゲートは git rev-parse --show-toplevel を使う）
R="$TMP/repo"; mkdir -p "$R/scripts" "$R/01_利用者向け資料" "$R/static"
cd "$R"
git init -q && git config user.email t@example.com && git config user.name t
cp "$KIT_DIR/02_共通/ツール/pre-commit" "$KIT_DIR/02_共通/ツール/pre-commit-ui-gate.sh" "$KIT_DIR/02_共通/ツール/ui-hash.py" scripts/
echo "base" > README.md && git add README.md && git commit -qm init

# gitleaks が入っている環境でもフォールバック経路（簡易パターン）を検証するため PATH を最小にする
run_precommit() { env PATH=/usr/bin:/bin bash scripts/pre-commit; }
stage() { printf '%s\n' "$2" > "$1"; git add "$1"; }
unstage_all() { git reset -q --hard HEAD; git clean -qfd -e scripts; mkdir -p "01_利用者向け資料" static; }  # clean で空ディレクトリが消えるので作り直す

echo "=== git ゲート 回帰テスト ==="

echo "[pre-commit（秘密情報）]"
stage config.py 'api_key = "sk-abcdefghijklmnopqrstuvwxyz"'
OUT=$(run_precommit 2>&1); RC=$?
expect_exit "API キーらしき文字列で exit 1" 1 "$RC"
expect_out  "検出メッセージを出す" "秘密情報らしき文字列を検出" "$OUT"
unstage_all
stage app.js "const v = localStorage.getItem('api_key');"
OUT=$(run_precommit 2>&1); RC=$?
expect_exit "localStorage 経由の api_key は許可（exit 0）" 0 "$RC"
unstage_all
stage notes.md "// password reset flow は別 PR"
OUT=$(run_precommit 2>&1); RC=$?
expect_exit "コメント行（//）の password は許可" 0 "$RC"
unstage_all
stage plain.txt "hello"
OUT=$(run_precommit 2>&1); RC=$?
expect_exit "無害な差分は exit 0 かつ無言" 0 "$RC"
expect_empty "無害な差分で出力なし" "$OUT"
unstage_all

echo "[ui-hash.py]"
printf '<html>v1</html>\n' > static/app.html
printf '<html>mock</html>\n' > "01_利用者向け資料/mock.html"
H1=$(python3 scripts/ui-hash.py disk)
[ ${#H1} -eq 16 ] && ok "disk hash は 16 桁" || ng "disk hash は 16 桁" "$H1"
printf '<html>v2</html>\n' > static/app.html
H2=$(python3 scripts/ui-hash.py disk)
[ "$H1" != "$H2" ] && ok "UI ファイルを変えると hash が変わる" || ng "UI ファイルを変えると hash が変わる" "同じ"
printf '<html>mock2</html>\n' > "01_利用者向け資料/mock.html"
H3=$(python3 scripts/ui-hash.py disk)
[ "$H2" = "$H3" ] && ok "01_利用者向け資料/ 配下の変更は既定で hash に影響しない" || ng "01_利用者向け資料/ 配下の変更は既定で hash に影響しない" "変わった"
H4=$(UI_HASH_EXCLUDE_PREFIXES= python3 scripts/ui-hash.py disk)
[ "$H2" != "$H4" ] && ok "除外接頭辞を空にすると 01_利用者向け資料/ も対象になる" || ng "除外接頭辞を空にすると 01_利用者向け資料/ も対象になる" "同じ"
git add static/app.html
HS=$(python3 scripts/ui-hash.py staged)
[ ${#HS} -eq 16 ] && ok "staged hash は 16 桁" || ng "staged hash は 16 桁" "$HS"
git reset -q

echo "[pre-commit-ui-gate.sh]"
gate() { bash scripts/pre-commit-ui-gate.sh; }
write_marker() { # hash, 秒前
  printf '%s %s %s\n' "$(git rev-parse HEAD)" "$1" "$(python3 -c "import datetime,sys;print((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=int(sys.argv[1]))).isoformat(timespec='seconds'))" "$2")" > .ui-verified
}
# UI ファイルが staged でない
stage plain.txt "x"
OUT=$(gate 2>&1); RC=$?
expect_exit "UI 未 stage なら exit 0" 0 "$RC"
expect_empty "UI 未 stage なら無言" "$OUT"
unstage_all
# 01_利用者向け資料/ 配下の HTML だけ
printf '<html>mock</html>\n' > "01_利用者向け資料/mock.html"; git add "01_利用者向け資料/mock.html"
OUT=$(gate 2>&1); RC=$?
expect_exit "01_利用者向け資料/*.html のみなら exit 0（設計モック）" 0 "$RC"
unstage_all
# マーカー無し
printf '<html>v1</html>\n' > static/app.html; git add static/app.html
rm -f .ui-verified
OUT=$(gate 2>&1); RC=$?
expect_exit "マーカー無しは BLOCKED（exit 1）" 1 "$RC"
expect_out  "E2E 未実行の理由を表示" "E2E テスト未実行" "$OUT"
# 期限切れ（3 時間前）
CUR=$(python3 scripts/ui-hash.py disk)
write_marker "$CUR" 10800
OUT=$(gate 2>&1); RC=$?
expect_exit "マーカーが古い（3h）と BLOCKED" 1 "$RC"
expect_out  "古すぎる旨を表示" "古すぎます" "$OUT"
# 短い上限を環境変数で
write_marker "$CUR" 30
OUT=$(UI_GATE_MAX_AGE=10 gate 2>&1); RC=$?
expect_exit "UI_GATE_MAX_AGE で上限を短くできる" 1 "$RC"
# hash 不一致
write_marker "deadbeefdeadbeef" 10
OUT=$(gate 2>&1); RC=$?
expect_exit "UI hash 不一致は BLOCKED" 1 "$RC"
expect_out  "検証後に変更された旨を表示" "検証後に UI ファイルが変更" "$OUT"
# 一致
write_marker "$CUR" 10
OUT=$(gate 2>&1); RC=$?
expect_exit "新しく hash 一致なら PASS（exit 0）" 0 "$RC"
expect_out  "hash 一致を表示" "[PASS] UI hash 一致" "$OUT"
expect_out  "目視確認の WARN を添える" "ブラウザ目視確認" "$OUT"
# 刷新モード
rm -f .ui-verified
echo "ダッシュボード刷新" > .rebuild-mode
OUT=$(gate 2>&1); RC=$?
expect_exit ".rebuild-mode があればマーカー無しでも exit 0" 0 "$RC"
expect_out  "刷新モードの WARN と理由" "刷新モード" "$OUT"
expect_out  "「未検証であり問題なしではない」と明示" "未検証" "$OUT"
rm -f .rebuild-mode
unstage_all

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
