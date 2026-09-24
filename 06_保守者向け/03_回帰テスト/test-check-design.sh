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

echo "[ケース11: フォーカス消去・拡大禁止・transition:all・img寸法欠落・非semantic onclick]"
reset; cat > "$P/02_共通/ひな形/ui/focus.css" <<'CSS'
.a { outline: none; }
.b { outline: 0; transition: all .2s ease; }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "outline: none/0（:focus-visible 無し）で exit 1" 1 "$RC"
expect_rgrep "outline: none を検出" '`outline: none`'
expect_rgrep "outline: 0 を検出" '`outline: 0`'
expect_rgrep "transition: all を検出" "transition: all"
expect_out  "種別 フォーカス消去" "フォーカス消去" "$OUT"
expect_out  "種別 transition:all" "transition:all" "$OUT"

reset; cat > "$P/02_共通/ひな形/ui/zoom.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "viewport の user-scalable=no で exit 1" 1 "$RC"
expect_rgrep "user-scalable=no を検出" "user-scalable=no"

reset; cat > "$P/02_共通/ひな形/ui/zoom2.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1.0">
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "viewport の maximum-scale=1.0 で exit 1" 1 "$RC"
expect_rgrep "maximum-scale=1.0 を検出" "maximum-scale=1.0"

reset; cat > "$P/02_共通/ひな形/ui/img.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<img src="a.png" alt="">
<img src="b.png" alt="" width="40">
<div onclick="go()">押す</div>
<span onclick="go()">押す</span>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "img の width/height 欠落と div/span onclick で exit 1" 1 "$RC"
expect_rgrep "width/height 両方無しを検出" "width／height"
expect_rgrep "height だけ無しを検出" "img.html:3"
expect_rgrep "<div onclick> を検出" "<div onclick"
expect_rgrep "<span onclick> を検出" "<span onclick"
expect_out  "種別 img寸法欠落" "img寸法欠落" "$OUT"
expect_out  "種別 非semantic onclick" "非semantic onclick" "$OUT"

echo "[ケース12: ケース11の正当な例は NG にならない（誤検知しない）]"
reset; cat > "$P/02_共通/ひな形/ui/ok.css" <<'CSS'
.a:focus-visible { outline: 2px solid var(--color-primary); }
.b { outline: none; }
.c { transition: color .2s ease, background-color .2s ease; }
CSS
cat > "$P/02_共通/ひな形/ui/ok.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<meta name="viewport" content="width=device-width, initial-scale=1">
<img src="a.png" alt="" width="40" height="40">
<img src="b.png" alt="" style="width:40px;height:40px">
<button type="button" onclick="go()">押す</button>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "outline: none だが同ファイルに :focus-visible あり／width+height 揃った img／button の onclick は NG にならない" 0 "$RC"
expect_nrgrep "outline: none は :focus-visible があれば検出しない" "フォーカス消去"
expect_nrgrep "transition: color, background-color は transition: all にしない" "transition:all"
expect_nrgrep "viewport に拡大禁止指定が無ければ検出しない" "拡大禁止"
expect_nrgrep "width/height が揃った img は検出しない" "img寸法欠落"
expect_nrgrep "<button onclick> は非対話要素にしない" "非semantic onclick"

echo "[検証: check_focus_motion_mobile はコメントを読み飛ばさない（他の検査は blank_comments 済みテキストで判定するのに、この検査だけ生テキストを見ている）]"
reset; cat > "$P/02_共通/ひな形/ui/comment-fp.css" <<'CSS'
/* 過去の指定メモ: transition: all は使わない方針（削除済み）。 */
.a { color: var(--color-primary); }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "[検証] コメント内だけの transition: all は NG にならないはず" 0 "$RC"
expect_nrgrep "[検証] コメント内の transition: all を種別 transition:all に数えない" "transition:all"

reset; cat > "$P/02_共通/ひな形/ui/comment-bypass.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<!-- :focus-visible 対応はデザイン未定のためコメントで保留中 -->
<button style="outline: none;">送信</button>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "[検証] コメント中の \":focus-visible\" という文字列だけでは本物のフォーカス消去を見逃さない" 1 "$RC"
expect_rgrep "[検証] outline: none をフォーカス消去として検出する" "フォーカス消去"

reset; cat > "$P/02_共通/ひな形/ui/comment-viewport.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"> -->
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "HTML コメント内の viewport（user-scalable=no）は無視する" 0 "$RC"
expect_nrgrep "コメントアウトされた viewport を拡大禁止として検出しない" "拡大禁止"

reset; cat > "$P/02_共通/ひな形/ui/comment-img.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<!-- <img src="a.png" alt=""> -->
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "HTML コメント内の img（width/height 無し）は無視する" 0 "$RC"
expect_nrgrep "コメントアウトされた img を img寸法欠落として検出しない" "img寸法欠落"

reset; cat > "$P/02_共通/ひな形/ui/comment-onclick.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<!-- <div onclick="go()">押す</div> -->
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "HTML コメント内の <div onclick> は無視する" 0 "$RC"
expect_nrgrep "コメントアウトされた <div onclick> を非semantic onclick として検出しない" "非semantic onclick"

echo "[ケース13: A19 新規則6種（色名・色関数・box-shadow直値・z-index直値・時間直値・100vh）]"
reset; cat > "$P/02_共通/ひな形/ui/new-rules.css" <<'CSS'
.a { color: red; background-color: white; }
.b { color: oklch(62% .19 259); border-color: color-mix(in srgb, red 50%, blue); }
.c { box-shadow: 0 2px 8px rgba(0,0,0,.2); }
.d { z-index: 40; }
.e { transition: opacity 1.5s ease; animation: spin 2s linear infinite; }
.f { height: 100vh; }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "新規則6種で exit 1" 1 "$RC"
expect_rgrep  "色名（red）を検出"      'D12'
expect_rgrep  "色名（white）を検出"    '`white`'
expect_rgrep  "oklch(を検出"          'D13'
expect_rgrep  "color-mix(を検出"       '`color-mix(`'
expect_rgrep  "box-shadowの直値を検出" 'D14'
expect_rgrep  "z-indexの直値を検出"    'D15'
expect_rgrep  "z-index: 40 の値を記録" '`z-index: 40`'
expect_rgrep  "transitionの時間直値を検出" 'D16'
expect_rgrep  "1.5s を検出"           '`1.5s`'
expect_rgrep  "animationの時間直値(2s)も検出" '`2s`'
expect_rgrep  "100vh単独を検出"        'D17'

echo "[ケース14: ケース13の正当な例は NG にならない（変数参照・100dvh・box-shadowはvar色のみ）]"
reset; cat > "$P/02_共通/ひな形/ui/new-rules-ok.css" <<'CSS'
.a { color: var(--color-critical); background-color: var(--color-surface); }
.b { box-shadow: 0 0 0 3px var(--color-primary-light); }
.c { box-shadow: var(--shadow-md); }
.d { z-index: var(--z-modal); }
.e { transition: opacity var(--motion-normal), transform var(--motion-fast); }
.f { min-height: 100vh; }
.g { height: 100dvh; }
@media (prefers-reduced-motion: reduce) { .h { transition-duration: 0s; animation-duration: 0s; } }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "変数参照・100dvh・min-height 併用・reduced-motion 除外は NG にならない" 0 "$RC"
expect_nrgrep "色名を誤検知しない" "D12"
expect_nrgrep "box-shadowを誤検知しない" "D14"
expect_nrgrep "z-indexを誤検知しない" "D15"
expect_nrgrep "時間直値を誤検知しない（reduced-motion 含む）" "D16"
expect_nrgrep "100vhを誤検知しない" "D17"

echo "[ケース14b: :hover + :focus-visible の対はWARNにならない／対が無いとWARN]"
reset; cat > "$P/02_共通/ひな形/ui/hover.css" <<'CSS'
.btn:hover, .btn:focus-visible { background: var(--color-surface-2); }
.card:hover { background: var(--color-surface-2); }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit ":hover のみは WARN であって NG にはしない" 0 "$RC"
expect_nrgrep "同じ規則内で対になっている .btn:hover は WARN にしない" '`.btn:hover`'
expect_rgrep  ".card:hover（対が無い）は WARN として記録" '`.card:hover`'

echo "[ケース15: 基準線 — 既知はexit0・新規はexit1・増える更新は拒否]"
reset; cat > "$P/02_共通/ひな形/ui/baseline.css" <<'CSS'
.a { color: red; }
CSS
BL2="$TMP/baseline2.tsv"
run --baseline "$BL2" --baseline-write 02_共通/ひな形/ui >/dev/null 2>&1
OUT=$(run --baseline "$BL2" 02_共通/ひな形/ui); RC=$?
expect_exit "基準線に記録済みの NG は既知として exit 0" 0 "$RC"
expect_out "既知件数を表示" "既知 1（前回 1）" "$OUT"
cat >> "$P/02_共通/ひな形/ui/baseline.css" <<'CSS'
.b { color: blue; }
CSS
OUT=$(run --baseline "$BL2" 02_共通/ひな形/ui); RC=$?
expect_exit "基準線に無い新規 NG は exit 1" 1 "$RC"
OUT=$(run --baseline "$BL2" --baseline-write 02_共通/ひな形/ui); RC=$?
expect_exit "NG が増える方向の --baseline-write は拒否して書かない" 1 "$RC"
[ "$(wc -l < "$BL2")" -eq 1 ] && ok "拒否時は基準線ファイルを書き換えない" || ng "拒否時は基準線ファイルを書き換えない" "行数が変わった"
reset; cat > "$P/02_共通/ひな形/ui/baseline.css" <<'CSS'
.a { color: red; }
CSS
OUT=$(run --baseline "$BL2" --baseline-write 02_共通/ひな形/ui); RC=$?
expect_exit "件数が減る更新は許可される" 0 "$RC"

echo "[ケース16: --json が妥当な JSON]"
reset; cat > "$P/02_共通/ひな形/ui/json.css" <<'CSS'
.a { color: red; padding: 20px; }
CSS
JOUT=$(run --json 02_共通/ひな形/ui); RC=$?
expect_exit "--json でも NG があれば exit 1" 1 "$RC"
echo "$JOUT" | python3 -c "
import json,sys
d = json.load(sys.stdin)
assert isinstance(d['ng'], list) and len(d['ng']) >= 2, d
assert all({'id','file','line','actual','expected','reason','severity'} <= e.keys() for e in d['ng'])
assert any(e['id'] == 'D01' for e in d['ng'])
assert any(e['id'] == 'D12' for e in d['ng'])
" && ok "--json は妥当な JSON で D01/D12 を含む" || ng "--json は妥当な JSON で D01/D12 を含む" "パース失敗または内容不足"

echo "[検証: B-24-1 誤検知の逆（正当な書き方が NG/WARN にならない）]"
reset; cat > "$P/02_共通/ひな形/ui/legit.css" <<'CSS'
.a { color: var(--color-fg-ref); }
.b { color: inherit; }
.c { color: currentColor; }
.d { color: transparent; }
/* background: white; ← コメントの中の直値 */
.e { z-index: var(--z-modal); }
.f { z-index: auto; }
.g { transition: opacity var(--motion-fast); }
.h { min-height: 100dvh; }
.i { box-shadow: none; }
.j { box-shadow: var(--shadow-md); }
.k:hover, .k:focus-visible { background: var(--color-surface-2); }
input { font-size: 1rem; }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_nrgrep "変数参照(color: var(...))はD12を誤検知しない" "D12"
expect_nrgrep "inherit/currentColor/transparentは色名扱いにしない" "色名の直書き"
expect_nrgrep "コメント中のbackground: whiteを誤検知しない" "コメントの中の直値"
expect_nrgrep "z-index: var(--z-modal)はD15を誤検知しない" "D15"
expect_nrgrep "transition var(--motion-fast)はD16を誤検知しない" "D16"
expect_nrgrep "min-height:100dvh単体はD17を誤検知しない" "D17"
expect_nrgrep ":hover,:focus-visible併記はD19警告にしない" "D19"

echo "[検証: B-24-2 赤: token-exempt はコメント文中の部分一致でも成立してしまう（バイパス）]"
# 「token-exemptではない直値」＝本来は除外対象でないと書いているのに、部分一致で D12 が消える。
reset; cat > "$P/02_共通/ひな形/ui/bypass.css" <<'CSS'
.a { background: white; } /* token-exemptではない直値のはずだが検出されない */
.b { background: black; }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_rgrep "期待: white もD12で検出されるべき" "\`white\`"

echo "[検証: B-24-3 赤: 100dvh がファイル内のどこか1箇所にあると、無関係な100vh単独が全て見逃される]"
reset; cat > "$P/02_共通/ひな形/ui/vh.css" <<'CSS'
.ok { height: 100dvh; }
.bug { height: 100vh; }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_rgrep "期待: 併用なしの.bugの100vhはD17で検出されるべき" "D17"

echo "[検証: B-24-4 赤: 方針「出荷物とサンプルはNG=0。基準線はfixtureで、サンプルを隠さない」に反する]"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$KIT_DIR" -o "$TMP/report.md" 01_利用者向け資料/90_サンプル/図書貸出 2>&1); RC=$?
expect_exit "サンプルは基準線なしでもNG=0であるべき（指揮官方針）" 0 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
