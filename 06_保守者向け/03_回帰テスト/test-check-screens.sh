#!/bin/bash
# test-check-screens.sh — check-screens.sh（check_screens.py）の回帰テスト
# 一時ディレクトリに画面のフィクスチャを作り、S01〜S03・W01・除外・判定不能を検出できることを確かめる。
# 前提: python の playwright と chromium（無ければ exit 2 を確かめて終わる）
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | head -6 | tr '\n' ' ')"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

F="$TMP/fx"; mkdir -p "$F"
run() { python3 "$KIT_DIR/00_導入/03_点検/check_screens.py" --viewports 1366x768 --out "$TMP/out" "$@" 2>&1; }
HEAD='<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>t</title><style>html,body{margin:0}</style></head><body>'

echo "=== check-screens.sh 回帰テスト ==="

if ! python3 -c "import playwright.sync_api" 2>/dev/null; then
  OUT=$(run "$F"); RC=$?
  expect_exit "playwright が無いと exit 2" 2 "$RC"
  expect_out  "導入方法を示す" "pip install playwright" "$OUT"
  echo ""; echo "結果: PASS=$PASS / FAIL=$FAIL"; exit 1
fi

cat > "$F/fit.html" <<HTML
$HEAD<main style="height:200px">収まる</main></body></html>
HTML
cat > "$F/tall.html" <<HTML
$HEAD<main style="height:3000px">縦にはみ出す</main></body></html>
HTML
cat > "$F/wide.html" <<HTML
$HEAD<main style="width:4000px;height:100px">横にはみ出す</main></body></html>
HTML
cat > "$F/tabs.html" <<HTML
$HEAD<div role="tablist"><button role="tab" onclick="show(1)">一枚目</button><button role="tab" onclick="show(2)">二枚目</button></div>
<section id="p1" style="height:100px">短い</section><section id="p2" hidden style="height:3000px">長い</section>
<script>function show(n){p1.hidden=n!==1;p2.hidden=n!==2;}</script></body></html>
HTML
cat > "$F/form.html" <<HTML
$HEAD<div class="form-area" style="height:200px;overflow:auto"><div style="height:1000px">長いフォーム</div></div>
<div class="table-wrap" style="height:100px;overflow:auto"><table><tr><td style="height:500px">表</td></tr></table></div></body></html>
HTML
cat > "$F/print.html" <<HTML
<!doctype html><html><head><meta name="aidd-screen-check" content="skip"><title>t</title></head><body><div style="height:5000px">印刷用</div></body></html>
HTML

echo "[ケース1: 収まるページ]"
OUT=$(run "$F/fit.html"); RC=$?
expect_exit "収まるページは exit 0" 0 "$RC"
expect_out  "NG=0" "NG=0" "$OUT"
expect_out  "検査した数／指定した数を出す" "検査 1 / 指定 1" "$OUT"
[ -f "$TMP/out/check-screens-report.md" ] && ok "レポートを書き出す" || ng "レポートを書き出す" "無い"
ls "$TMP/out"/*fit.html-1366x768.png >/dev/null 2>&1 && ok "スクショを書き出す" || ng "スクショを書き出す" "無い"

echo "[ケース2: 縦にはみ出す（S01）]"
OUT=$(run "$F/tall.html"); RC=$?
expect_exit "縦スクロールで exit 1" 1 "$RC"
expect_out  "S01 を出す" "S01" "$OUT"
expect_noout "S02 は出ない" "S02" "$OUT"

echo "[ケース3: 横にはみ出す（S02）]"
OUT=$(run "$F/wide.html"); RC=$?
expect_exit "横スクロールで exit 1" 1 "$RC"
expect_out  "S02 を出す" "S02" "$OUT"

echo "[ケース4: 2 枚目のタブだけはみ出す（S03）]"
OUT=$(run "$F/tabs.html"); RC=$?
expect_exit "隠れたタブのはみ出しで exit 1" 1 "$RC"
expect_out  "S03 を二枚目で出す" "S03 $F/tabs.html 1366x768 タブ=二枚目" "$OUT"
expect_noout "一枚目は NG にしない" "タブ=一枚目" "$OUT"

echo "[ケース5: フォームの内部スクロール（W01）]"
OUT=$(run "$F/form.html"); RC=$?
expect_exit "WARN だけなら exit 0" 0 "$RC"
expect_out  "W01 でフォーム領域を出す" "div.form-area" "$OUT"
expect_noout "表の内部スクロールは WARN にしない" "table-wrap" "$OUT"

echo "[ケース6: skip メタのページは除外]"
OUT=$(run "$F/print.html" "$F/fit.html"); RC=$?
expect_exit "除外ページは判定しない（exit 0）" 0 "$RC"
expect_out  "除外数を出す" "除外 1" "$OUT"
expect_out  "検査 1 / 指定 2" "検査 1 / 指定 2" "$OUT"

echo "[ケース7: 存在しないパス]"
OUT=$(run "$TMP/nothing.html"); RC=$?
expect_exit "存在しないパスは exit 2" 2 "$RC"
expect_out  "判定不能として出す" "パスが無い" "$OUT"

echo "[ケース8: ディレクトリを再帰で検査]"
OUT=$(run "$F"); RC=$?
expect_exit "NG を含むディレクトリは exit 1" 1 "$RC"
expect_out  "6 ファイル中 5 検査・1 除外" "検査 5 / 指定 6、除外 1" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
