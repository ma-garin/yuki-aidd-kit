#!/bin/bash
# test-check-design.sh — check-design.sh（check_design.py）の回帰テスト
# 出荷物（tokens.css / ui/*.css / components/*）が NG=0 で通ることと、
# 各検査が「壊した箇所を検出できること」「除外規則が効くこと」を一時ファイルで確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | head -4 | tr '\n' ' ')"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
expect_rgrep(){ grep -qF -- "$2" "$TMP/report.md" && ok "$1" || ng "$1" "レポートに '$2' が無い"; }
expect_nrgrep(){ grep -qF -- "$2" "$TMP/report.md" && ng "$1" "レポートに '$2' が出た" || ok "$1"; }

# 一時プロジェクト: tokens.css は実物を使い、検査対象だけ差し替える
P="$TMP/proj"; mkdir -p "$P/02_共通/ひな形/ui"
cp "$KIT_DIR/02_共通/ひな形/tokens.css" "$P/02_共通/ひな形/tokens.css"
run() { python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$P" -o "$TMP/report.md" "$@" 2>&1; }
reset() { rm -rf "$P/02_共通/ひな形/ui"; mkdir -p "$P/02_共通/ひな形/ui"; }

echo "=== check-design.sh 回帰テスト ==="

echo "[ケース1: 出荷物が NG=0]"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$KIT_DIR" -o "$TMP/report.md" 2>&1); RC=$?
expect_exit "02_共通/ひな形/ui + 02_共通/ひな形/components が exit 0" 0 "$RC"
expect_out  "結論に NG=0" "NG=0" "$OUT"
grep -q "デザイン検査レポート" "$TMP/report.md" && ok "詳細レポートを書き出す" || ng "詳細レポートを書き出す" "無い"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$KIT_DIR" -o "$TMP/report.md" 01_利用者向け資料/90_サンプル/図書貸出 2>&1); RC=$?
expect_exit "同梱の事例 01_利用者向け資料/90_サンプル/図書貸出 も exit 0" 0 "$RC"

echo "[ケース2: 色の直値（S9 以前の SKILL.md 由来）]"
reset; cat > "$P/02_共通/ひな形/ui/x.css" <<'CSS'
.badge-medium { color: #856404; background: var(--color-medium-bg); }
.info-ic .tooltip { background: #20242B; color: #F2F4F7; }
.modal-backdrop { background: rgba(8,12,18,.46); }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "色の直値で exit 1" 1 "$RC"
expect_out  "種別 直値" "直値" "$OUT"
expect_rgrep "#856404 を検出" '`#856404`' 
expect_rgrep "rgba( を検出" '`rgba(`'
expect_out  "対象と行番号を示す" "02_共通/ひな形/ui/x.css:1" "$OUT"

echo "[ケース3: px 直値の判定範囲]"
reset; cat > "$P/02_共通/ひな形/ui/px.css" <<'CSS'
.a { padding: 16px; }
.b { width: 240px; height: 44px; }
.c { border: 2px solid var(--color-border); border-radius: 3px; }
.d { margin: 12px 0; }   /* token-exempt: レガシー画面の互換 */
.e { gap: var(--space-2, 8px); font-size: var(--text-sm, 13px); }
@media (max-width: 768px) { .f { line-height: 1.5; } }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "padding: 16px で exit 1" 1 "$RC"
expect_rgrep "padding の 16px を検出" '`16px`'
expect_nrgrep "width / height の px は対象外" '`240px`'
expect_nrgrep "3px 以下のヘアラインは除外" '`3px`'
expect_nrgrep "token-exempt 行は除外" '`12px`'
expect_nrgrep "var(--x, フォールバック) の中は除外" '`8px`'
expect_nrgrep "メディアクエリの px は対象外" '`768px`'

echo "[ケース4: 未定義トークン]"
reset; printf '.a { color: var(--color-brand); }\n.b { --local: 1px; padding: var(--local); }\n' > "$P/02_共通/ひな形/ui/u.css"
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "未定義トークンで exit 1" 1 "$RC"
expect_rgrep "--color-brand を検出" '`var(--color-brand)`'
expect_nrgrep "自ファイル定義の変数は未定義にしない" '`var(--local)`'

echo "[ケース5: 未使用トークンは WARN のみ]"
reset; printf '.a { color: var(--color-primary); }\n' > "$P/02_共通/ひな形/ui/w.css"
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "未使用トークンだけなら exit 0" 0 "$RC"
expect_out  "警告として出す" "警告" "$OUT"
expect_rgrep "未使用トークンをレポートに列挙" "未使用トークン"

echo "[ケース6: 外部 CDN]"
reset; cat > "$P/02_共通/ひな形/ui/cdn.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP">
<script src="https://cdn.jsdelivr.net/npm/lucide"></script>
<style>@import url(https://example.com/x.css);</style>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "外部 CDN で exit 1" 1 "$RC"
expect_rgrep "fonts.googleapis.com を検出" "fonts.googleapis.com"
expect_rgrep "script src の CDN を検出" "cdn.jsdelivr.net"
expect_rgrep "@import url(https://) を検出" "example.com/x.css"

echo "[ケース7: alert() / confirm() の直接使用]"
reset; cat > "$P/02_共通/ひな形/ui/dlg.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<script>
  // alert('コメント内は無視');
  function confirm(options) { return true; }   // 定義は呼び出しではない
  const yes = await Feedback.confirm({ title: 't' });
  if (!yes) alert('やめました');
  window.prompt('名前');
</script>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "alert() で exit 1" 1 "$RC"
expect_rgrep "alert( を検出" '`alert()`'
expect_rgrep "window.prompt( を検出" '`prompt()`'
expect_nrgrep "Feedback.confirm( と関数定義は対象外" '`confirm()`'

echo "[ケース8: tokens.css の読み込み]"
reset; printf '<style>.a{color:var(--color-primary)}</style>\n' > "$P/02_共通/ひな形/ui/no.html"
printf '<style>:root{--color-primary:#1976D2}</style>\n' > "$P/02_共通/ひな形/ui/inline.html"   # 単一 HTML: <style> に貼る形
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "tokens.css 未読込で exit 1" 1 "$RC"
expect_rgrep "no.html を検出" "no.html"
expect_nrgrep "<style> 内に定義があれば読込扱い" "inline.html |"

echo "[ケース9: 対象なし・複数パス]"
reset; OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "対象ファイルなしは exit 0" 0 "$RC"
expect_out  "対象なしの旨を表示" "対象ファイルなし" "$OUT"
mkdir -p "$P/static"; printf '.a { padding: 24px; }\n' > "$P/static/app.css"
OUT=$(run 02_共通/ひな形/ui static); RC=$?
expect_exit "配布先向けに任意のパスを渡せる" 1 "$RC"
expect_out  "static/app.css を検査" "static/app.css:1" "$OUT"

echo "[ケース10: 配布先プロジェクトの形（export-project.sh 後の単一 HTML）]"
# tokens.css は .claude/templates/ にある。単一 HTML には tokens.css を <style> に貼る。.claude/ 配下の雛形は検査対象にしない
D="$TMP/dist"; rm -rf "$D"; mkdir -p "$D/.claude/templates" "$D/.claude/hooks"
cp "$KIT_DIR/02_共通/ひな形/tokens.css" "$D/.claude/templates/tokens.css"
printf '.x { padding: 99px; color: #123456; }\n' > "$D/.claude/hooks/should-be-ignored.css"
{ printf '<style>\n'; cat "$KIT_DIR/02_共通/ひな形/tokens.css"; printf '.app { padding: var(--space-4); color: var(--color-text); }\n</style>\n'; } > "$D/tool.html"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$D" -o "$TMP/report.md" . 2>&1); RC=$?
expect_exit "--tokens 省略で .claude/templates/tokens.css を自動検出し exit 0" 0 "$RC"
expect_out  "対象は tool.html の 1 ファイルだけ（.claude/ は走査しない）" "対象: 1 ファイル" "$OUT"
expect_nrgrep "貼り込んだ tokens.css の定義行（--x: #hex）を直値にしない" "色の直値"
expect_nrgrep ".claude/ 配下の直値は報告しない" "should-be-ignored"
printf '.y { --local-gap: 12px; gap: var(--local-gap); margin: 24px; }\n' > "$D/extra.css"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$D" -o "$TMP/report.md" . 2>&1); RC=$?
expect_exit "定義行以外の直値（margin: 24px）は引き続き検出" 1 "$RC"
expect_nrgrep "自ファイルの --local-gap: 12px 定義は直値にしない" '`12px`'
expect_rgrep  "margin: 24px は検出" '`24px`'

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
