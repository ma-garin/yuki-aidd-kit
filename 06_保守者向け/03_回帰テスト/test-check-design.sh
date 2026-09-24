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
cat >> "$P/02_共通/ひな形/ui/baseline.css" <<'CSS'
.a { color: red; }
CSS
OUT=$(run --baseline "$BL2" 02_共通/ひな形/ui); RC=$?
expect_exit "同じ文面の NG を足しても既知に紛れない（#n で数える。exit 1）" 1 "$RC"
cut -f1-3 "$BL2" > "$TMP/baseline-old.tsv"
reset; cat > "$P/02_共通/ひな形/ui/baseline.css" <<'CSS'
.a { color: red; }
CSS
OUT=$(run --baseline "$TMP/baseline-old.tsv" 02_共通/ひな形/ui); RC=$?
expect_exit "旧形式（#n 無しの 3 列）の基準線は #1 として読む（exit 0）" 0 "$RC"
printf '\xff\xfe\x00bad\n' > "$TMP/baseline-bin.tsv"
OUT=$(run --baseline "$TMP/baseline-bin.tsv" 02_共通/ひな形/ui); RC=$?
expect_exit "UTF-8 でない基準線は判定不能（exit 2）" 2 "$RC"
expect_noout "壊れた基準線で Traceback を出さない" "Traceback" "$OUT"

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

# --- 塊 K: B49 HTML の a11y（D20〜D24）・B50 コントラスト（D25）・B51 AI 既定意匠（D26・D27） ---
echo "[ケースK1: D20 img の alt 欠落（alt=\"\" は装飾として許可）]"
reset; cat > "$P/02_共通/ひな形/ui/alt.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<img src="a.png" width="40" height="40">
<img src="deco.png" alt="" width="40" height="40">
<img src="logo.png" alt="社内図書館" width="40" height="40">
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "alt の無い img で exit 1" 1 "$RC"
expect_rgrep "alt 無しを D20 で検出" "| D20 | img alt欠落 | 02_共通/ひな形/ui/alt.html:2 |"
expect_nrgrep "alt=\"\"（装飾）は D20 にしない" "alt.html:3 |"
expect_nrgrep "alt に説明がある img は D20 にしない" "alt.html:4 |"

echo "[ケースK2: D21 入力欄のラベル欠落]"
reset; cat > "$P/02_共通/ひな形/ui/label.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<input id="q" placeholder="書名で検索">
<select id="s"><option>a</option></select>
<textarea id="t"></textarea>
<label for="ok1">名前</label><input id="ok1">
<label>メール <input type="email"></label>
<input aria-label="検索">
<span id="lb">期限</span><input type="date" aria-labelledby="lb">
<input type="hidden" name="csrf"><input type="submit" value="送信"><input type="button" value="戻る">
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "ラベルの無い input/select/textarea で exit 1" 1 "$RC"
expect_rgrep "placeholder だけの input を D21 で検出" "| D21 | 入力欄ラベル欠落 | 02_共通/ひな形/ui/label.html:2 |"
expect_rgrep "ラベルの無い select を検出" "label.html:3 |"
expect_rgrep "ラベルの無い textarea を検出" "label.html:4 |"
for n in 5 6 7 8 9; do expect_nrgrep "正当なラベル付け（label for・囲む label・aria-label・aria-labelledby・hidden/submit/button）は D21 にしない（$n 行目）" "label.html:$n |"; done

echo "[ケースK3: D22 html の lang 欠落]"
reset; printf '<!doctype html>\n<html>\n<head><link rel="stylesheet" href="../tokens.css"></head>\n<body></body>\n</html>\n' > "$P/02_共通/ひな形/ui/nolang.html"
printf '<!doctype html>\n<head><link rel="stylesheet" href="../tokens.css"></head>\n' > "$P/02_共通/ひな形/ui/nohtml.html"
printf '<!doctype html>\n<html lang="ja">\n<head><link rel="stylesheet" href="../tokens.css"></head>\n</html>\n' > "$P/02_共通/ひな形/ui/lang.html"
printf '<link rel="stylesheet" href="../tokens.css">\n<div class="card">断片</div>\n' > "$P/02_共通/ひな形/ui/fragment.html"
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "lang の無い html で exit 1" 1 "$RC"
expect_rgrep "<html> の lang 無しを D22 で検出" "| D22 | html lang欠落 | 02_共通/ひな形/ui/nolang.html:2 |"
expect_rgrep "doctype があって <html> が無い文書も D22" "| D22 | html lang欠落 | 02_共通/ひな形/ui/nohtml.html:1 |"
expect_nrgrep "lang=\"ja\" は D22 にしない" "| 02_共通/ひな形/ui/lang.html:"
expect_nrgrep "<html> も doctype も無い断片は D22 の対象外" "fragment.html"

echo "[ケースK4: D23 名前の無いボタン・リンク]"
reset; cat > "$P/02_共通/ひな形/ui/name.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<button type="button"></button>
<button type="button"><span data-icon="close" data-icon-size="16"></span></button>
<a href="#top"></a>
<button type="button" aria-label="閉じる"><span data-icon="close" data-icon-size="16"></span></button>
<button type="button"><span data-icon="save" data-icon-size="16"></span>保存する</button>
<a href="/"><img src="logo.png" alt="ホーム" width="40" height="40"></a>
<a name="anchor"></a>
<a href="#x" aria-labelledby="t1"><span data-icon="info"></span></a>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "名前の無いボタン・リンクで exit 1" 1 "$RC"
expect_rgrep "空の button を D23 で検出" "| D23 | 名前の無いボタン・リンク | 02_共通/ひな形/ui/name.html:2 |"
expect_rgrep "アイコンだけの button（aria-label 無し）を検出" "name.html:3 |"
expect_rgrep "中身の無い <a href> を検出" "name.html:4 |"
for n in 5 6 7 8 9; do expect_nrgrep "名前のあるボタン・リンク（aria-label・テキスト・img alt・href 無し a・aria-labelledby）は D23 にしない（$n 行目）" "name.html:$n |"; done

echo "[ケースK5: D24 見出しの飛びは WARN]"
reset; cat > "$P/02_共通/ひな形/ui/heading.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<h1>一覧</h1>
<h3>飛んだ見出し</h3>
<h2>節</h2>
<h3>小節</h3>
<h2>次の節</h2>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "見出しの飛びだけなら exit 0（WARN）" 0 "$RC"
expect_rgrep "h1→h3 を D24 の警告に記録" "| D24 | 見出しの飛び | 02_共通/ひな形/ui/heading.html:3 |"
expect_nrgrep "h2→h3（1 段ずつ）と h3→h2（浅くなる）は D24 にしない" "heading.html:5 |"
expect_nrgrep "浅くなる見出しは D24 にしない" "heading.html:6 |"
expect_out "警告の件数を種別ごとに出す" "見出しの飛び 1" "$OUT"

echo "[ケースK6: D25 コントラスト（対の表 × 実物の tokens.css）]"
reset; printf '.a { color: var(--color-text); }\n' > "$P/02_共通/ひな形/ui/c.css"
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "対の表が無いだけなら exit 0（WARN）" 0 "$RC"
expect_rgrep "対の表が無いことを D25 の警告に出す" "対の表が無い"
cat > "$P/02_共通/ひな形/ui/contrast-pairs.md" <<'MD'
| 前景 | 背景 | 種別 | 扱い | 用途 |
|---|---|---|---|---|
| `--color-text` | `--color-bg` | 本文 | | 本文 |
| `--color-medium` | `--color-medium-bg` | 本文 | | Medium バッジの地色（文字色未適用。意図的に未対応） |
| `--color-primary` | `--color-border-strong` | UI 部品 | | 種別によるしきい値差の確認用 |
| `--color-primary` | `--color-border-strong` | 本文 | | 種別によるしきい値差の確認用 |
| `--color-medium` | `--color-medium-bg` | 本文 | 保留 | 保留（扱い）の確認用 |
| `--color-nope` | `--color-bg` | 本文 | | 打ち間違い |
MD
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "4.5 未満の対・未定義トークンで exit 1" 1 "$RC"
expect_rgrep "tokens.css の隣の ui/contrast-pairs.md を既定で読む" "## コントラスト対照表（D25）"
expect_rgrep "Medium の地色（ライト）を NG で検出" "| D25 | コントラスト不足 | 02_共通/ひな形/ui/contrast-pairs.md:4 | \`--color-medium × --color-medium-bg\`（ライト）"
expect_nrgrep "Medium の地色のダーク（届いている）は NG にしない" "\`--color-medium × --color-medium-bg\`（ダーク）"
expect_nrgrep "本文 15:1 の対は NG にしない" "contrast-pairs.md:3 |"
expect_nrgrep "同じ色でも UI 部品（3:1）なら NG にしない" "contrast-pairs.md:5 |"
expect_rgrep "同じ色で本文（4.5:1）なら NG" "contrast-pairs.md:6 |"
expect_rgrep "未定義トークンは判定不能として NG" "判定不能: \`--color-nope\` が定義されていない"
expect_rgrep "扱い=保留 は警告にとどめる" "扱い=保留"
grep -F "contrast-pairs.md:7" "$TMP/report.md" | grep -q "^| D25" && [ "$(sed -n '/## NG 一覧/,/## 警告/p' "$TMP/report.md" | grep -c 'contrast-pairs.md:7')" -eq 0 ] \
  && ok "保留の行は NG 一覧に出ない" || ng "保留の行は NG 一覧に出ない" "NG 一覧に出た／警告に無い"
rm -f "$P/02_共通/ひな形/ui/contrast-pairs.md"

echo "[ケースK7: D25 ダーク・半透明・hsl・対象外の色（専用の tokens）]"
T2="$TMP/tok2.css"; cat > "$T2" <<'CSS'
:root { --fg: #767676; --bg: #FFFFFF; --veil: rgba(0,0,0,.5); --fg-w: #FFFFFF; --veil3: rgba(0,0,0,.1); --h-fg: hsl(0, 0%, 46%); --ok-fg: oklch(40% .1 250); --color-bg: #222222; --color-surface: #333333; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --fg: #555555; --bg: #222222; } }
:root[data-theme="dark"] { --fg: #555555; --bg: #222222; }
CSS
cat > "$TMP/pairs2.md" <<'MD'
| 前景 | 背景 | 種別 |
|---|---|---|
| `--fg` | `--bg` | 本文 |
| `--fg` | `--veil` | 本文 |
| `--fg-w` | `--veil3` | 本文 |
| `--h-fg` | `--bg` | 本文 |
| `--ok-fg` | `--bg` | 本文 |
MD
reset; printf '.a { color: var(--fg); background: var(--bg); }\n' > "$P/02_共通/ひな形/ui/c.css"
OUT=$(run --tokens "$T2" --pairs "$TMP/pairs2.md" 02_共通/ひな形/ui); RC=$?
expect_exit "ダークだけ届かない対で exit 1" 1 "$RC"
expect_nrgrep "#767676 × 白（4.54:1）はライトで NG にしない" "\`--fg × --bg\`（ライト）"
expect_rgrep "ダーク（data-theme と prefers-color-scheme が同じ値）を 1 つにまとめて NG" "\`--fg × --bg\`（ダーク）"
expect_rgrep "半透明の背景は下地に重ねて計算する（黒 50% の上の灰色は NG）" "\`--fg × --veil\`（ライト）"
expect_nrgrep "半透明の背景の下地は --color-bg / --color-surface（白いキャンバスではない。暗い下地の上の白文字は NG にしない）" "\`--fg-w × --veil3\`"
expect_nrgrep "hsl() を計算できる（白に対して 4.5 以上）" "\`--h-fg × --bg\`（ライト）"
expect_rgrep "oklch() は計算対象外として警告" "計算対象外"
OUT=$(run --tokens "$T2" --pairs "$TMP/no-such-pairs.md" 02_共通/ひな形/ui); RC=$?
expect_exit "--pairs に指定したファイルが無いと判定不能（exit 1）" 1 "$RC"

echo "[ケースK8: D26 装飾グラデーション（WARN）]"
reset; cat > "$P/02_共通/ひな形/ui/grad.css" <<'CSS'
.hero { background: linear-gradient(135deg, var(--color-primary), var(--color-surface)); }
.card { background-image: radial-gradient(circle, var(--color-primary-light), var(--color-surface)); }
.x { --slop-bg: conic-gradient(var(--color-primary), var(--color-surface)); }
.y { background: var(--slop-bg); }
.fade { mask-image: linear-gradient(var(--color-text), transparent); -webkit-mask-image: linear-gradient(var(--color-text), transparent); }
.frame { border-image: linear-gradient(var(--color-primary), var(--color-surface)) 1; }
/* background: linear-gradient(red, blue) はコメント */
.plain { background: var(--color-surface); }
CSS
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "グラデーションだけなら exit 0（WARN）" 0 "$RC"
expect_rgrep "background の linear-gradient を D26 で警告" "| D26 | 装飾グラデーション | 02_共通/ひな形/ui/grad.css:1 |"
expect_rgrep "background-image の radial-gradient を警告" "grad.css:2 |"
expect_rgrep "グラデーションのトークン経由（var(--slop-bg)）も警告" "grad.css:4 |"
expect_nrgrep "mask-image のグラデーションは D26 にしない" "grad.css:5 |"
expect_nrgrep "border-image のグラデーションは D26 にしない" "grad.css:6 |"
expect_nrgrep "コメントの中のグラデーションは D26 にしない" "grad.css:7 |"
cat > "$P/02_共通/ひな形/ui/grad.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<div class="hero" style="background: linear-gradient(var(--color-primary), var(--color-surface))">見出し</div>
<!-- <div style="background: linear-gradient(var(--color-primary), var(--color-surface))"></div> -->
<script>card.innerHTML = '<div style="background: linear-gradient(var(--color-primary), var(--color-surface))"></div>';</script>
<script>/* background: linear-gradient(a, b) は使わない */ const note = 'グラデーションは使わない';</script>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_rgrep "HTML の style 属性のグラデーションも警告" "| D26 | 装飾グラデーション | 02_共通/ひな形/ui/grad.html:2 |"
expect_nrgrep "HTML コメントの中は D26 にしない" "grad.html:3 |"
expect_rgrep "インライン <script> で差し込むグラデーションも .js と同じく警告" "grad.html:4 |"
[ "$(grep -c 'grad.html:4 |' "$TMP/report.md")" -eq 1 ] && ok "script 内の style 属性を 2 回数えない" || ng "script 内の style 属性を 2 回数えない" "$(grep -c 'grad.html:4 |' "$TMP/report.md") 件"
expect_nrgrep "<script> のコメント・グラデーションを含まない文字列は D26 にしない" "grad.html:5 |"

echo "[ケースK9: D27 絵文字アイコン（WARN）]"
reset; cat > "$P/02_共通/ひな形/ui/emoji.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<button type="button">🔍</button>
<span>⚙️</span>
<ul><li>🏠</li></ul>
<button type="button"><span>✅</span></button>
<p>貸出が完了しました🎉</p>
<span>保存しました 🎉</span>
<button type="button" aria-label="閉じる">×</button>
<span>‹</span><span>✓</span>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "絵文字アイコンだけなら exit 0（WARN）" 0 "$RC"
expect_rgrep "button の中身が絵文字だけを D27 で警告" "| D27 | 絵文字アイコン | 02_共通/ひな形/ui/emoji.html:2 |"
expect_rgrep "異体字セレクタ付き（⚙️）を警告" "emoji.html:3 |"
expect_rgrep "li の中身が絵文字だけを警告" "emoji.html:4 |"
[ "$(grep -c 'emoji.html:5 |' "$TMP/report.md")" -eq 1 ] && ok "入れ子（button>span）は内側の 1 件だけ" || ng "入れ子（button>span）は内側の 1 件だけ" "$(grep -c 'emoji.html:5 |' "$TMP/report.md") 件"
for n in 6 7 8 9; do expect_nrgrep "文中の絵文字・記号（× ‹ ✓）は D27 にしない（$n 行目）" "emoji.html:$n |"; done

echo "[ケースK10: 新規則の NG は基準線に乗り、WARN は乗らない]"
reset; cat > "$P/02_共通/ひな形/ui/bl.html" <<'HTML'
<link rel="stylesheet" href="../tokens.css">
<img src="a.png" width="40" height="40">
<h1>a</h1><h3>b</h3>
HTML
cp "$KIT_DIR/02_共通/ひな形/ui/contrast-pairs.md" "$P/02_共通/ひな形/ui/contrast-pairs.md"
printf '| 前景 | 背景 | 種別 |\n|---|---|---|\n| `--color-medium` | `--color-medium-bg` | 本文 |\n' > "$P/02_共通/ひな形/ui/contrast-pairs.md"
BLK="$TMP/baseline-k.tsv"; rm -f "$BLK"
run --baseline "$BLK" --baseline-write 02_共通/ひな形/ui >/dev/null 2>&1
grep -q "^D20	" "$BLK" && grep -q "^D25	" "$BLK" && ok "D20・D25 の NG を基準線に書く" || ng "D20・D25 の NG を基準線に書く" "$(cut -f1 "$BLK" 2>/dev/null | tr '\n' ' ')"
grep -q "^D24	" "$BLK" && ng "WARN（D24）は基準線に書かない" "書かれた" || ok "WARN（D24）は基準線に書かない"
OUT=$(run --baseline "$BLK" 02_共通/ひな形/ui); RC=$?
expect_exit "基準線に載った D20・D25 は既知として exit 0" 0 "$RC"
printf '<input id="late" placeholder="x">\n' >> "$P/02_共通/ひな形/ui/bl.html"
OUT=$(run --baseline "$BLK" 02_共通/ひな形/ui); RC=$?
expect_exit "基準線に無い新しい D21 は exit 1" 1 "$RC"
JOUT=$(run --json 02_共通/ひな形/ui)
echo "$JOUT" | python3 -c "
import json,sys
d = json.load(sys.stdin)
assert any(e['id'] == 'D20' for e in d['ng']) and any(e['id'] == 'D25' for e in d['ng']), d['ng']
assert any(e['id'] == 'D24' and e['severity'] == 'WARN' for e in d['warn'])
assert d['contrast'] and d['contrast'][0]['fg'] == '--color-medium' and d['contrast'][0]['verdict'] == 'NG'
" && ok "--json に D20/D25 の NG・D24 の WARN・対照表（contrast）が入る" || ng "--json に D20/D25 の NG・D24 の WARN・対照表が入る" "内容不足"

echo "[ケースK11: 出荷物の対の表を実際に読み、ライトとダークの両方を計算している]"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/check_design.py" --root "$KIT_DIR" -o "$TMP/report.md" 2>&1); RC=$?
expect_exit "出荷物（対の表つき）は NG=0" 0 "$RC"
expect_rgrep "対照表に本文 × ページ背景（ライト）が OK で載る" "| \`--color-text\` | \`--color-bg\` | 本文 | ライト |"
expect_rgrep "対照表にダークの行がある" "| \`--color-text\` | \`--color-bg\` | 本文 | ダーク |"
expect_nrgrep "出荷物の対の表は読めている（対の表が無い警告を出さない）" "対の表が無い"
N=$(grep -c '^| `--' "$TMP/report.md")
[ "$N" -ge 12 ] && ok "対照表に 6 対以上 × 2 テーマ（$N 行）" || ng "対照表に 6 対以上 × 2 テーマ" "$N 行"

echo "[ケースK12: 差し戻し — 装飾 img・子孫の名前・<template> の除外]"
reset; cat > "$P/02_共通/ひな形/ui/k12.html" <<'HTML'
<!doctype html><html lang="ja"><head><link rel="stylesheet" href="../tokens.css"></head><body>
<img src="a.png" role="none" width="40" height="40">
<img src="b.png" aria-hidden="false" width="40" height="40">
<button type="button"><span><span aria-label="検索"></span></span></button>
<a href="/"><span><svg><title>ホーム</title></svg></span></a>
<button type="button"><span aria-labelledby="lb1"></span></button>
<template><button type="button"></button><img src="c.png"><input id="tpl"></template>
<button type="button"></button>
</body></html>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_exit "template の外の空 button で exit 1" 1 "$RC"
expect_nrgrep "role=none の img は D20 にしない" "| D20 | img alt欠落 | 02_共通/ひな形/ui/k12.html:2 |"
expect_rgrep "aria-hidden=false の img（alt 無し）は D20 のまま" "| D20 | img alt欠落 | 02_共通/ひな形/ui/k12.html:3 |"
for n in 4 5 6; do expect_nrgrep "子孫の aria-label・<svg><title>・aria-labelledby で名前がある button/a は D23 にしない（$n 行目）" "k12.html:$n |"; done
expect_nrgrep "<template> の中（空 button・alt 無し img・ラベル無し input）は走査しない" "k12.html:7 |"
expect_rgrep "<template> の後ろの空 button は行番号どおり D23" "| D23 | 名前の無いボタン・リンク | 02_共通/ひな形/ui/k12.html:8 |"

echo "[検証: 塊K]"
# 実装担当とは別担当による確認。D20/D23 の判定に見つかった誤検知を赤のまま残す（実装担当が直す）。
reset; cat > "$P/02_共通/ひな形/ui/verify-fp.html" <<'HTML'
<!doctype html><html lang="ja"><head><title>t</title></head><body>
<img src="a.png" role="presentation">
<img src="b.png" aria-hidden="true">
<button type="button"><svg aria-label="閉じる"></svg></button>
</body></html>
HTML
OUT=$(run 02_共通/ひな形/ui); RC=$?
expect_nrgrep "role=presentation の img（alt 無し）を D20 で誤検知しない" "| D20 | img alt欠落 | 02_共通/ひな形/ui/verify-fp.html:2 |"
expect_nrgrep "aria-hidden=true の img（alt 無し）を D20 で誤検知しない" "| D20 | img alt欠落 | 02_共通/ひな形/ui/verify-fp.html:3 |"
expect_nrgrep "中の <svg aria-label> だけを持つ button を D23 で誤検知しない" "verify-fp.html:4 |"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
