#!/bin/bash
# test-security-scan.sh — security-scan.sh の回帰テスト（B-24 A18）
# 走査器が導入されていない環境を PATH を絞って再現し、grep 代替の検出・判定不能・レポート表形式を確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCAN="$KIT_DIR/02_共通/ツール/security-scan.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
NOTOOLS_PATH="/usr/bin:/bin"   # 走査器（pip-audit 等）が無い最小 PATH（sh/find/grep/python3 は要る）

ok()  { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng()  { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_rgrep(){ grep -qF -- "$2" "$TMP/report.md" && ok "$1" || ng "$1" "レポートに '$2' が無い"; }
expect_nrgrep(){ grep -qF -- "$2" "$TMP/report.md" && ng "$1" "レポートに '$2' が出た" || ok "$1"; }

run_notools() { PATH="$NOTOOLS_PATH" bash "$SCAN" "$1" -o "$TMP/report.md" 2>&1; }

echo "=== security-scan.sh 回帰テスト ==="

echo "[ケース1: 走査器が無い環境で eval( を含む fixture → 簡易の指摘と exit 1]"
D="$TMP/proj1"; mkdir -p "$D"
cat > "$D/app.py" <<'PY'
import subprocess, os
def run(cmd):
    eval(cmd)
    exec(cmd)
    os.system(cmd)
    subprocess.call(cmd, shell=True)
PY
cat > "$D/view.js" <<'JS'
el.innerHTML = userInput;
document.write(userInput);
JS
OUT=$(run_notools "$D"); RC=$?
expect_exit "走査器0・危険コードありで exit 1" 1 "$RC"
expect_out  "簡易の印を出す" "簡易" "$OUT"
expect_rgrep "grep（簡易）の行がある" "grep（簡易）"
expect_rgrep "eval( を検出" "eval("
expect_rgrep "os.system( を検出" "os.system("
expect_rgrep "shell=True を検出" "shell=True"
expect_rgrep "innerHTML= を検出" "innerHTML"
expect_rgrep "document.write( を検出" "document.write("
expect_rgrep "file:line 形式で場所を示す" "$D/app.py:3"
expect_rgrep "未検査（未導入）の一覧を書く" "未検査"
expect_rgrep "pip-audit を未検査として記録" "pip-audit"
expect_rgrep "gitleaks を未検査として記録" "gitleaks"

echo "[ケース2: 対象なし（危険なパターンを含まないファイルのみ）→ exit 0]"
D="$TMP/proj2"; mkdir -p "$D"
cat > "$D/app.py" <<'PY'
def add(a, b):
    return a + b
PY
OUT=$(run_notools "$D"); RC=$?
expect_exit "危険なコードが無ければ exit 0" 0 "$RC"
expect_out  "指摘なしを表示" "指摘なし" "$OUT"

echo "[ケース3: 走査器0・grep対象も0（scannable なファイルが無い）→ 判定不能で exit 2]"
D="$TMP/proj3"; mkdir -p "$D"
printf 'ただのテキスト\n' > "$D/README.txt"
OUT=$(run_notools "$D"); RC=$?
expect_exit "走査器も対象ファイルも無ければ exit 2" 2 "$RC"
expect_out  "判定不能を明示" "判定不能" "$OUT"

echo "[ケース4: 対象ディレクトリが存在しない → 判定不能で exit 2]"
OUT=$(run_notools "$TMP/does-not-exist"); RC=$?
expect_exit "対象ディレクトリが無ければ exit 2" 2 "$RC"

echo "[ケース5: レポートは表形式（ツール／規則／file:line／重大度／要旨）]"
D="$TMP/proj1"
run_notools "$D" >/dev/null
expect_rgrep "レポートの見出し" "セキュリティ走査レポート"
expect_rgrep "指摘一覧の表ヘッダ" "| ツール | 規則 | file:line | 重大度 | 要旨 |"
expect_rgrep "未検査の見出し" "未検査"

echo "[ケース6: 誤検知の逆ケース — 危険パターンに見えて呼び出しでない文字列は拾いすぎない]"
D="$TMP/proj6"; mkdir -p "$D"
cat > "$D/safe.py" <<'PY'
# eval関数は使っていません（コメントの中の文字列）
def evaluate(cmd):
    return "evaluation: " + cmd
PY
OUT=$(run_notools "$D"); RC=$?
expect_exit "eval という語だけで exec/eval 呼び出しにしない（'evaluate' や 'evaluation' は eval( に一致しない）" 0 "$RC"

echo "[検証: B-24-5 スタブ（実物と同形のJSON）で ツール／規則／file:line／重大度 の表が正しく出る]"
STUBS="$TMP/stubs"; mkdir -p "$STUBS"
cat > "$STUBS/pip-audit" <<'SH'
#!/bin/bash
echo '{"dependencies":[{"name":"flask","version":"1.0","vulns":[{"id":"PYSEC-2021-1"}]}]}'
SH
cat > "$STUBS/osv-scanner" <<'SH'
#!/bin/bash
echo '{"results":[{"source":{"path":"lock.json"},"packages":[{"package":{"name":"lodash"},"vulnerabilities":[{"id":"GHSA-xxxx","severity":[{"type":"CVSS_V3","score":"CRITICAL"}]}]}]}]}'
SH
cat > "$STUBS/bandit" <<'SH'
#!/bin/bash
echo '{"results":[{"test_id":"B301","filename":"app.py","line_number":5,"issue_severity":"HIGH","issue_text":"pickle使用"}]}'
SH
cat > "$STUBS/gitleaks" <<'SH'
#!/bin/bash
OUT=""; for ((i=1;i<=$#;i++)); do [ "${!i}" = "--report-path" ] && { j=$((i+1)); OUT="${!j}"; }; done
echo '[{"RuleID":"generic-api-key","File":"config.py","StartLine":12}]' > "$OUT"
SH
chmod +x "$STUBS"/*
D="$TMP/proj7"; mkdir -p "$D"; echo "flask==1.0" > "$D/requirements.txt"
OUT=$(PATH="$STUBS:/usr/bin:/bin" bash "$SCAN" "$D" -o "$TMP/report.md" 2>&1); RC=$?
expect_exit "スタブ4本すべてhigh/critical相当でexit1" 1 "$RC"
expect_rgrep "pip-auditの行がある" "pip-audit"
expect_rgrep "osv-scannerの行がある" "osv-scanner"
expect_rgrep "banditの行がある" "bandit"
expect_rgrep "gitleaksの行がある" "gitleaks"
expect_rgrep "file:lineが出る(bandit)" "app.py:5"
expect_rgrep "file:lineが出る(gitleaks)" "config.py:12"

echo "[検証: B-24-6 赤: 導入済みツールが壊れたJSONを返すと『解析失敗（未検査扱い）』にならず黙って指摘0扱いになる]"
BROKEN="$TMP/broken"; mkdir -p "$BROKEN"
cat > "$BROKEN/pip-audit" <<'SH'
#!/bin/bash
echo '{not valid json'
SH
cat > "$BROKEN/gitleaks" <<'SH'
#!/bin/bash
OUT=""; for ((i=1;i<=$#;i++)); do [ "${!i}" = "--report-path" ] && { j=$((i+1)); OUT="${!j}"; }; done
echo 'not json either' > "$OUT"
SH
chmod +x "$BROKEN"/*
D="$TMP/proj8"; mkdir -p "$D"; echo "flask==1.0" > "$D/requirements.txt"
OUT=$(PATH="$BROKEN:/usr/bin:/bin" bash "$SCAN" "$D" -o "$TMP/report.md" 2>&1); RC=$?
# 期待: pip-audit/gitleaks は「導入済みだが解析失敗」として未検査扱いになり、指摘0を安全と断定しない。
expect_rgrep "期待: 解析失敗をpip-auditについて明示" "pip-audit"
expect_rgrep "期待: 解析失敗をgitleaksについて明示" "gitleaks"
[ "$RC" -eq 2 ] && ok "期待: 壊れたJSONは判定不能(exit2)として扱う" || ng "期待: 壊れたJSONは判定不能(exit2)として扱う" "実際 exit=$RC（指摘0のexit0で通ってしまう＝黙って見逃す）"

echo "[基準線（--baseline。B15）: 既知は exit 0・新規は exit 1・増える更新は拒否・理由と期限]"
D="$TMP/proj9"; mkdir -p "$D"
printf '%s\n' 'def run(cmd):' '    eval(cmd)' > "$D/app.py"
BL="$TMP/baseline.tsv"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" --baseline-write 2>&1); RC=$?
expect_exit "理由（--reason）なしで新しい指摘を基準線に載せようとすると exit 2" 2 "$RC"
[ ! -e "$BL" ] && ok "理由なしのときは基準線を書かない" || ng "理由なしのときは基準線を書かない" "書かれた"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" --baseline-write --reason "移行中の旧コード。B-99 で置き換える" 2>&1); RC=$?
expect_exit "理由付きの初回の --baseline-write は exit 0" 0 "$RC"
[ "$(wc -l < "$BL" | tr -d ' ')" -eq 1 ] && ok "基準線に 1 件を記録" || ng "基準線に 1 件を記録" "$(wc -l < "$BL") 行"
[ "$(awk -F'\t' '{print NF}' "$BL")" -eq 6 ] && ok "書式は 規則ID/相対パス/指紋/#n/理由/期限 の 6 列（check_design と同じ先頭 4 列）" || ng "書式が 6 列" "$(cat "$BL")"
grep -q "sha256:" "$BL" && ! grep -q "eval(cmd)" "$BL" && ok "3 列目は行そのものでなく指紋（sha256）" || ng "3 列目は指紋" "$(cat "$BL")"
awk -F'\t' '{print $6}' "$BL" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' && ok "期限（既定 90 日後）を書く" || ng "期限を書く" "$(cat "$BL")"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" 2>&1); RC=$?
expect_exit "基準線に載った既知の指摘だけなら exit 0" 0 "$RC"
expect_out  "既知の件数と前回を表示（件数の推移）" "既知 1（前回 1）" "$OUT"
expect_rgrep "レポートの行に［既知］の印" "［既知］"
expect_rgrep "レポートに基準線の節（件数の推移）" "件数の推移"
printf '%s\n' '    os.system(cmd)' >> "$D/app.py"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" 2>&1); RC=$?
expect_exit "基準線に無い新規の指摘は exit 1" 1 "$RC"
expect_out  "新規の件数を表示" "新規 1" "$OUT"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" --baseline-write --reason "増やす" 2>&1); RC=$?
expect_exit "件数が増える --baseline-write は拒否（exit 1）" 1 "$RC"
[ "$(wc -l < "$BL" | tr -d ' ')" -eq 1 ] && ok "拒否したときは基準線を書き換えない" || ng "拒否したときは基準線を書き換えない" "$(wc -l < "$BL") 行"
printf '%s\n' 'def run(cmd):' '    eval(cmd)' > "$D/app.py"
OUT=$(AIDD_TODAY=2099-01-01 PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" 2>&1); RC=$?
expect_exit "期限切れの除外は既知に数えない（exit 1）" 1 "$RC"
expect_out  "期限切れを表示" "期限なし/期限切れ 1" "$OUT"
cut -f1-3 "$BL" > "$TMP/bl-noreason.tsv"   # 旧形式（#n 無し・理由なし）
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$TMP/bl-noreason.tsv" 2>&1); RC=$?
expect_exit "理由の無い除外は既知に数えない（exit 1）" 1 "$RC"
expect_out  "理由なしを表示（旧形式の #n 無しは #1 として照合する）" "理由なし 1" "$OUT"
printf 'x\n' > "$TMP/bl-short.tsv"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$TMP/bl-short.tsv" 2>&1); RC=$?
expect_exit "列の足りない基準線は判定不能（exit 2）" 2 "$RC"
expect_out  "理由は「基準線を読めない（パス）」" "基準線を読めない（$TMP/bl-short.tsv）" "$OUT"
printf '%s\n' 'def run(cmd):' '    return cmd' > "$D/app.py"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" 2>&1); RC=$?
expect_out  "直した指摘は「解消」として数える" "解消 1" "$OUT"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL" --baseline-write 2>&1); RC=$?
expect_exit "件数が減る更新は理由なしでも許可（exit 0）" 0 "$RC"
[ ! -s "$BL" ] && ok "解消した指摘は基準線から外れる（0 件）" || ng "解消した指摘は基準線から外れる" "$(wc -l < "$BL") 行"
# 秘密の指摘でも基準線に値を残さない（gitleaks のスタブ。値は AWS 公式の偽キー）
D="$TMP/proj10"; mkdir -p "$D"; printf '%s\n' 'AWS_KEY = "AKIAIOSFODNN7EXAMPLE"' > "$D/config.py"
GLS="$TMP/glstub"; mkdir -p "$GLS"
cat > "$GLS/gitleaks" <<'SH'
#!/bin/bash
OUT=""; SRC=""; for ((i=1;i<=$#;i++)); do [ "${!i}" = "--report-path" ] && { j=$((i+1)); OUT="${!j}"; }; [ "${!i}" = "--source" ] && { j=$((i+1)); SRC="${!j}"; }; done
echo "[{\"RuleID\":\"aws-access-token\",\"File\":\"$SRC/config.py\",\"StartLine\":1}]" > "$OUT"
SH
chmod +x "$GLS/gitleaks"
BL3="$TMP/baseline-secret.tsv"
OUT=$(PATH="$GLS:/usr/bin:/bin" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BL3" --baseline-write --reason "偽キーの検出確認" 2>&1); RC=$?
expect_exit "秘密の指摘も基準線に記録できる" 0 "$RC"
grep -q "AKIAIOSFODNN7EXAMPLE" "$BL3" && ng "基準線に秘密値を書かない" "値が書かれた" || ok "基準線に秘密値を書かない（指紋だけ）"
# 判定不能（走査器の解析失敗）のときは基準線を書かない
OUT=$(PATH="$BROKEN:/usr/bin:/bin" bash "$SCAN" "$TMP/proj8" -o "$TMP/report.md" --baseline "$TMP/bl-broken.tsv" --baseline-write --reason x 2>&1); RC=$?
expect_exit "解析失敗があるときの --baseline-write は exit 2" 2 "$RC"
[ ! -e "$TMP/bl-broken.tsv" ] && ok "判定不能のときは基準線を書かない" || ng "判定不能のときは基準線を書かない" "書かれた"

echo "[検証: 塊G]"
# 検証担当（塊G）が足した節。基準線の指紋（規則・パス・行の文面）が同じ新規を既知に紛れさせないこと、壊れた基準線で落ちないこと。
D="$TMP/projG"; mkdir -p "$D"
printf '%s\n' 'def run(cmd):' '    eval(cmd)' > "$D/app.py"
BLG="$TMP/baseline-G.tsv"
PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BLG" --baseline-write --reason "旧コード" >/dev/null 2>&1
printf '%s\n' 'def run2(cmd):' '    eval(cmd)' >> "$D/app.py"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$BLG" 2>&1); RC=$?
expect_exit "同じ文面の eval を別の行に足した新規は既知に紛れさせない（exit 1）" 1 "$RC"
expect_out  "同じ文面の新規も「新規 1」と数える（既知が前回より増えない）" "新規 1" "$OUT"
printf '\xff\xfe\x00bad' > "$TMP/bl-bin.tsv"
OUT=$(PATH="$NOTOOLS_PATH" bash "$SCAN" "$D" -o "$TMP/report.md" --baseline "$TMP/bl-bin.tsv" --baseline-write --reason x 2>&1); RC=$?
expect_exit "UTF-8 でない基準線への --baseline-write は判定不能（exit 2）" 2 "$RC"
printf '%s' "$OUT" | grep -q "Traceback" && ng "壊れた基準線で Traceback を出さない" "Traceback が出た（理由も「件数が増える方向」と誤表示）" || ok "壊れた基準線で Traceback を出さない"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
