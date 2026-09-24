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

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
