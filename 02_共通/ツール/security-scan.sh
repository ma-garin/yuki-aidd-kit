#!/bin/bash
# security-scan.sh — 導入済みの無料走査器だけを順に実行し、指摘を一つの表にまとめる（B-24 A18）。
#
# 対象: [dir]（既定 "."）
# 実行するもの（`command -v` で検出できたものだけ。無いものは「未検査」として記録する）:
#   依存      pip-audit（requirements*.txt）／ osv-scanner（DIR を直接）／ npm audit --json（package.json）
#             ／ trivy fs（DIR を直接）
#   SAST      semgrep（ローカル規則 .semgrep.yml/.semgrep.yaml/.semgrep/ がある場合のみ。
#             `--config auto` `--config p/…` はネットワークが要るので使わない）／ bandit -r（Python）
#             → SAST が1つも無いときだけ grep シグネチャで代替し、結果に「簡易」と印を付ける
#   秘密      gitleaks detect（.git があれば --no-git 無し、無ければ --no-git）
#
# 出力: security-report.md（表: ツール／規則／file:line／重大度／要旨 ＋ 未導入・解析失敗は「未検査」の行）
# 終了コード:
#   0 = 指摘なし
#   1 = 指摘あり（重大度が high/critical/中 以上のものが1件でも。解析失敗があっても他に指摘があれば 1 を優先）
#   2 = 判定不能（走査器が1つも無く grep 代替の対象ファイルも無い、または走査器の出力が1つでも解析失敗で
#       かつ他に high/critical/中 以上の指摘が無い）
# 未検査（未導入・解析失敗とも）を合格に数えない。EPSS・ネット取得は使わない（走査器の導入もしない）。
# 走査器の出力が JSON として読めない・想定の形でないときは、その走査器を「解析失敗（未検査）」として扱い、
# stderr に1行出す（判定不能を合格にしないため。指摘なしと解析失敗は違う）。
#
# 使い方: ./02_共通/ツール/security-scan.sh [対象ディレクトリ] [-o レポート出力先]
#          [--baseline FILE [--baseline-write --reason 理由 [--expires YYYY-MM-DD]]]
#
# 基準線（B15。書式・規律は同じ場所の baseline.py。check_design.py と同形）:
#   --baseline FILE   既知の指摘（重大度が中以上）を `規則ID<TAB>相対パス<TAB>行の指紋<TAB>理由<TAB>期限` で記録した
#                     ファイル。載っている指摘は「既知」として数えず、新規だけで exit 1 にする。ただし理由の無い行・
#                     期限の無い行・期限切れの行は既知に数えない（NG のまま）。3 列目は行の sha256 の先頭 16 桁
#                     （秘密値を基準線に書かない）。
#   --baseline-write  現在の指摘で FILE を書く。**件数が前回より増える更新は拒否**（exit 1・書かない）。
#                     新しく載せる指摘には --reason が要る（無ければ exit 2）。期限は --expires、既定は 90 日後。
#                     判定不能（走査器の解析失敗・対象なし）のときは書かない（exit 2）。

set -u
DIR="."
REPORT="./security-report.md"
BASELINE=""; BASELINE_WRITE=0; BL_REASON=""; BL_EXPIRES=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) REPORT="$2"; shift 2 ;;
    --baseline) BASELINE="${2:-}"; shift 2 ;;
    --baseline-write) BASELINE_WRITE=1; shift ;;
    --reason) BL_REASON="${2:-}"; shift 2 ;;
    --expires) BL_EXPIRES="${2:-}"; shift 2 ;;
    -h|--help) echo "使い方: $0 [対象ディレクトリ] [-o レポート出力先] [--baseline FILE [--baseline-write --reason 理由 [--expires YYYY-MM-DD]]]"; exit 0 ;;
    *) DIR="$1"; shift ;;
  esac
done

if [ ! -d "$DIR" ]; then
  echo "❌ 対象ディレクトリが無い: $DIR"
  exit 2
fi
BASELINE_PY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/baseline.py"
if [ "$BASELINE_WRITE" -eq 1 ] && [ -z "$BASELINE" ]; then
  echo "❌ --baseline-write には --baseline FILE が要る"
  exit 2
fi
if [ -n "$BASELINE" ] && [ ! -f "$BASELINE_PY" ]; then
  echo "❌ 判定不能: 基準線の部品 baseline.py が無い（security-scan.sh と同じ場所に置く）: $BASELINE_PY"
  exit 2
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
ROWS="$TMP/rows.tsv"          # tool<TAB>rule<TAB>file:line<TAB>severity<TAB>summary
NOT_SCANNED="$TMP/not_scanned.txt"
: > "$ROWS"; : > "$NOT_SCANNED"

add_row() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >> "$ROWS"; }
mark_not_scanned() { echo "$1" >> "$NOT_SCANNED"; }
PARSE_FAIL_ANY=0
mark_parse_fail() {   # $1 = ツール名（対象の補足があれば呼び出し側で埋め込む）
  echo "$1（解析失敗のため未検査）" >> "$NOT_SCANNED"
  echo "security-scan: ${1} の出力を解析できなかったため「解析失敗」として扱う（未検査。合格に数えない）" >&2
  PARSE_FAIL_ANY=1
}

TOOLS_FOUND=0   # 依存・SAST・秘密のいずれかを実際に実行できたら 1

# --- 依存の既知脆弱性 --------------------------------------------------------
DEP_RAN=0
if command -v pip-audit >/dev/null 2>&1; then
  REQ_FILES=$(find "$DIR" -maxdepth 3 -type f -name 'requirements*.txt' 2>/dev/null)
  if [ -n "$REQ_FILES" ]; then
    DEP_RAN=1; TOOLS_FOUND=1
    while IFS= read -r rf; do
      [ -z "$rf" ] && continue
      OUT=$(pip-audit -r "$rf" -f json 2>/dev/null)
      TOOLOUT="$TMP/rows_pip-audit.tsv"
      if python3 - "$rf" "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
rf, out = sys.argv[1], sys.argv[2]
data = json.loads(out or "{}")   # 例外は呼び出し側で「解析失敗」として捕まえる
deps = data.get("dependencies", data) if isinstance(data, dict) else data
if isinstance(deps, dict):
    deps = deps.get("dependencies", [])
for dep in (deps or []):
    for v in dep.get("vulns", []):
        ident = v.get("id", "?")
        print(f"pip-audit\t{ident}\t{rf}\thigh\t{dep.get('name','?')} {dep.get('version','?')} の既知脆弱性")
PY
      then
        cat "$TOOLOUT" >> "$ROWS"
      else
        mark_parse_fail "pip-audit（$rf）"
      fi
    done <<< "$REQ_FILES"
  else
    mark_not_scanned "pip-audit（requirements*.txt が無い）"
  fi
else
  mark_not_scanned "pip-audit（未導入）"
fi

if command -v osv-scanner >/dev/null 2>&1; then
  DEP_RAN=1; TOOLS_FOUND=1
  OUT=$(osv-scanner --format json -r "$DIR" 2>/dev/null)
  TOOLOUT="$TMP/rows_osv-scanner.tsv"
  if python3 - "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
data = json.loads(sys.argv[1] or "{}")
for res in data.get("results", []):
    src = res.get("source", {}).get("path", "?")
    for pkg in res.get("packages", []):
        name = pkg.get("package", {}).get("name", "?")
        for v in pkg.get("vulnerabilities", []):
            sev = "high"
            for s in v.get("severity", []):
                if str(s.get("score", "")).upper().startswith(("CRITICAL",)):
                    sev = "critical"
            print(f"osv-scanner\t{v.get('id','?')}\t{src}\t{sev}\t{name} の既知脆弱性")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "osv-scanner"
  fi
else
  mark_not_scanned "osv-scanner（未導入）"
fi

if command -v npm >/dev/null 2>&1 && [ -f "$DIR/package.json" ]; then
  DEP_RAN=1; TOOLS_FOUND=1
  OUT=$(cd "$DIR" && npm audit --json 2>/dev/null)
  TOOLOUT="$TMP/rows_npm-audit.tsv"
  if python3 - "$DIR" "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
d, out = sys.argv[1], sys.argv[2]
data = json.loads(out or "{}")
vulns = data.get("vulnerabilities", {})
for name, v in vulns.items():
    sev = v.get("severity", "high")
    print(f"npm audit\t{name}\t{d}/package.json\t{sev}\t{name} の既知脆弱性（{v.get('via', ['?'])[0] if isinstance(v.get('via'), list) else '?'}）")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "npm audit"
  fi
elif [ -f "$DIR/package.json" ]; then
  mark_not_scanned "npm audit（npm 未導入）"
fi

if command -v trivy >/dev/null 2>&1; then
  DEP_RAN=1; TOOLS_FOUND=1
  OUT=$(trivy fs --scanners vuln --format json --quiet "$DIR" 2>/dev/null)
  TOOLOUT="$TMP/rows_trivy.tsv"
  if python3 - "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
data = json.loads(sys.argv[1] or "{}")
for r in data.get("Results", []) or []:
    target = r.get("Target", "?")
    for v in r.get("Vulnerabilities", []) or []:
        sev = (v.get("Severity") or "high").lower()
        print(f"trivy\t{v.get('VulnerabilityID','?')}\t{target}\t{sev}\t{v.get('PkgName','?')} の既知脆弱性")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "trivy fs"
  fi
else
  mark_not_scanned "trivy fs（未導入）"
fi

# --- SAST（危険なコードパターン） --------------------------------------------
SAST_RAN=0
SEMGREP_CONFIG=""
for c in "$DIR/.semgrep.yml" "$DIR/.semgrep.yaml" "$DIR/.semgrep"; do
  [ -e "$c" ] && SEMGREP_CONFIG="$c" && break
done
if command -v semgrep >/dev/null 2>&1 && [ -n "$SEMGREP_CONFIG" ]; then
  SAST_RAN=1; TOOLS_FOUND=1
  OUT=$(semgrep --config "$SEMGREP_CONFIG" --json --quiet "$DIR" 2>/dev/null)
  TOOLOUT="$TMP/rows_semgrep.tsv"
  if python3 - "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
data = json.loads(sys.argv[1] or "{}")
sevmap = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
for r in data.get("results", []) or []:
    path = r.get("path", "?")
    line = r.get("start", {}).get("line", "?")
    sev = sevmap.get((r.get("extra", {}).get("severity") or "").upper(), "medium")
    print(f"semgrep\t{r.get('check_id','?')}\t{path}:{line}\t{sev}\t{(r.get('extra', {}).get('message') or '')[:80]}")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "semgrep"
  fi
elif command -v semgrep >/dev/null 2>&1; then
  mark_not_scanned "semgrep（ローカル規則が無い。--config auto/p/… はネットが要るので使わない）"
else
  mark_not_scanned "semgrep（未導入）"
fi

if command -v bandit >/dev/null 2>&1; then
  SAST_RAN=1; TOOLS_FOUND=1
  OUT=$(bandit -r "$DIR" -f json -q 2>/dev/null)
  TOOLOUT="$TMP/rows_bandit.tsv"
  if python3 - "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
data = json.loads(sys.argv[1] or "{}")
sevmap = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
for r in data.get("results", []) or []:
    sev = sevmap.get((r.get("issue_severity") or "").upper(), "medium")
    print(f"bandit\t{r.get('test_id','?')}\t{r.get('filename','?')}:{r.get('line_number','?')}\t{sev}\t{(r.get('issue_text') or '')[:80]}")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "bandit"
  fi
else
  mark_not_scanned "bandit（未導入）"
fi

# SAST が1つも無いときだけ grep シグネチャで代替する（結果は「簡易」と明記）。
# 簡易代替の限界: 行頭が # ／ // ／ * ／ <!-- の行（1行コメント・docstring/ブロックコメントの開始行）は除外するが、
# 複数行コメント・docstring の「途中の行」は行単体では判別できないため取り切れないことがある（誤検知/見逃しの余地）。
GREP_RAN=0
SIG_RE='eval\(|exec\(|subprocess\.[A-Za-z_]*\(.*shell[[:space:]]*=[[:space:]]*True|os\.system\(|pickle\.loads|yaml\.load\(([^)]*\)([^L]|L[^o]))?|innerHTML[[:space:]]*\*?=|document\.write\(|dangerouslySetInnerHTML|child_process\.exec\('
if [ "$SAST_RAN" -eq 0 ]; then
  GREP_FILES=$(find "$DIR" -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.jsx' -o -name '*.tsx' -o -name '*.html' \) \
    ! -path '*/node_modules/*' ! -path '*/.git/*' ! -path '*/dist/*' ! -path '*/build/*' 2>/dev/null)
  if [ -n "$GREP_FILES" ]; then
    GREP_RAN=1
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      grep -nE "$SIG_RE" "$f" 2>/dev/null | while IFS=: read -r ln rest; do
        trimmed="${rest#"${rest%%[![:space:]]*}"}"
        case "$trimmed" in
          '#'*|'//'*|'*'*|'<!--'*) continue ;;
        esac
        match=$(printf '%s' "$rest" | grep -oE "$SIG_RE" | head -1)
        add_row "grep（簡易）" "$match" "$f:$ln" "high" "危険なコードパターンの直接使用（SAST 未導入のため grep 代替）"
      done
    done <<< "$GREP_FILES"
  fi
fi

# --- 秘密（履歴含む） --------------------------------------------------------
if command -v gitleaks >/dev/null 2>&1; then
  TOOLS_FOUND=1
  GL_NOGIT=""
  [ -d "$DIR/.git" ] || GL_NOGIT="--no-git"
  OUT=$(gitleaks detect --source "$DIR" $GL_NOGIT --report-format json --report-path "$TMP/gitleaks.json" --exit-code 0 2>/dev/null; cat "$TMP/gitleaks.json" 2>/dev/null)
  TOOLOUT="$TMP/rows_gitleaks.tsv"
  if python3 - "$OUT" <<'PY' > "$TOOLOUT" 2>/dev/null
import json, sys
data = json.loads(sys.argv[1] or "[]")
for f in data or []:
    print(f"gitleaks\t{f.get('RuleID','?')}\t{f.get('File','?')}:{f.get('StartLine','?')}\tcritical\t秘密情報らしき文字列を検出")
PY
  then
    cat "$TOOLOUT" >> "$ROWS"
  else
    mark_parse_fail "gitleaks"
  fi
else
  mark_not_scanned "gitleaks（未導入）"
fi

# --- 基準線（--baseline） ---------------------------------------------------
if [ -n "$BASELINE" ] && [ "$BASELINE_WRITE" -eq 1 ]; then
  if [ "$PARSE_FAIL_ANY" -eq 1 ] || { [ "$TOOLS_FOUND" -eq 0 ] && [ "$GREP_RAN" -eq 0 ]; }; then
    echo "❌ 判定不能のため基準線を書かない（走査器の解析失敗、または走査器も対象ファイルも無い）"
    exit 2
  fi
  WOUT=$(python3 "$BASELINE_PY" classify --baseline "$BASELINE" --rows "$ROWS" --root "$DIR" \
         --write --reason "$BL_REASON" --expires "$BL_EXPIRES" 2>&1); WRC=$?
  case "$WRC" in
    0) echo "✅ 基準線を更新: $(printf '%s' "$WOUT" | sed -n 's/.*current=\([0-9]*\).*/\1/p') 件を記録（$BASELINE。$WOUT）" ;;
    1) echo "❌ 基準線の更新を拒否: 件数が増える方向（$WOUT）。直すか、除外の理由を保守者が判断する" ;;
    *) echo "❌ 基準線を書かない: 新しく載せる指摘には理由が要る（--reason。$WOUT）" ;;
  esac
  exit "$WRC"
fi
BL_STATUS=""   # 行ごとの区分（new / known / noreason / expired / low）。--baseline のときだけ使う
BL_SUMMARY=""
if [ -n "$BASELINE" ]; then
  BL_STATUS="$TMP/rows_classified.tsv"
  BL_SUMMARY=$(python3 "$BASELINE_PY" classify --baseline "$BASELINE" --rows "$ROWS" --root "$DIR" --out "$BL_STATUS" 2>/dev/null) || {
    echo "❌ 判定不能: 基準線 $BASELINE を読めない"
    exit 2
  }
fi
bl_get() { printf '%s' "$BL_SUMMARY" | tr ' ' '\n' | sed -n "s/^$1=//p"; }

# --- 集計・レポート出力 ------------------------------------------------------
N=$(wc -l < "$ROWS" | tr -d ' ')
sev_rank() {
  case "$1" in
    critical) echo 4 ;; high) echo 3 ;; medium|中) echo 2 ;; low|低) echo 1 ;; *) echo 0 ;;
  esac
}
HIGH_OR_ABOVE=0
if [ -n "$BASELINE" ]; then
  # 基準線あり: 新規と、理由なし・期限なし・期限切れの既知だけを数える
  HIGH_OR_ABOVE=$(( $(bl_get new) + $(bl_get noreason) + $(bl_get expired) ))
  ROWS_VIEW="$BL_STATUS"
else
  while IFS=$'\t' read -r tool rule loc sev summary; do
    [ -z "$tool" ] && continue
    [ "$(sev_rank "$sev")" -ge 2 ] && HIGH_OR_ABOVE=$((HIGH_OR_ABOVE+1))
  done < "$ROWS"
  ROWS_VIEW="$ROWS"
fi
bl_mark() {
  case "$1" in
    known) printf '［既知］' ;; noreason) printf '［基準線: 理由なし＝NG］' ;; expired) printf '［基準線: 期限なし・期限切れ＝NG］' ;;
  esac
}

{
  echo "# セキュリティ走査レポート"
  echo
  echo "- 対象: \`$DIR\`"
  if [ -n "$BASELINE" ]; then
    echo "- 指摘: $N 件（high/critical/中 以上のうち、新規と基準線で認めない既知: $HIGH_OR_ABOVE 件）"
  else
    echo "- 指摘: $N 件（high/critical/中 以上: $HIGH_OR_ABOVE 件）"
  fi
  echo "- 実行した走査器の指摘のみを合格に数える。**未検査は合格に数えない**"
  echo
  echo "## 指摘一覧"
  echo
  if [ "$N" -gt 0 ]; then
    echo "| ツール | 規則 | file:line | 重大度 | 要旨 |"
    echo "|---|---|---|---|---|"
    while IFS=$'\t' read -r tool rule loc sev summary st; do
      [ -z "$tool" ] && continue
      echo "| $tool | $rule | $loc | $sev | $(bl_mark "${st:-}")$summary |"
    done < "$ROWS_VIEW"
  else
    echo "なし。"
  fi
  if [ -n "$BASELINE" ]; then
    echo
    echo "## 基準線（\`$BASELINE\`。件数は減る方向だけ）"
    echo
    echo "- 既知 $(bl_get known) 件 ／ 新規 $(bl_get new) 件 ／ 理由なし $(bl_get noreason) 件 ／ 期限なし・期限切れ $(bl_get expired) 件"
    echo "- 件数の推移: 基準線 $(bl_get prev) 件 → 今回の該当 $(bl_get current) 件（解消して基準線から外せるもの $(bl_get resolved) 件）"
  fi
  echo
  echo "## 未検査（未導入・対象なし・解析失敗。合格に数えない）"
  echo
  if [ -s "$NOT_SCANNED" ]; then
    while IFS= read -r line; do echo "- $line"; done < "$NOT_SCANNED"
  else
    echo "なし。"
  fi
} > "$REPORT"

echo "=== セキュリティ走査: $DIR ==="
if [ "$SAST_RAN" -eq 0 ]; then
  if [ "$GREP_RAN" -eq 1 ]; then
    echo "⚠ SAST 未導入のため grep シグネチャで簡易代替（$(command -v semgrep >/dev/null 2>&1 && echo semgrep 規則未設定; command -v bandit >/dev/null 2>&1 || echo bandit 未導入)）"
  fi
fi
echo "対象: $N 件の指摘 ／ 未検査: $(wc -l < "$NOT_SCANNED" | tr -d ' ') 件"
if [ "$N" -gt 0 ]; then
  echo "  例（先頭5件）:"
  head -5 "$ROWS_VIEW" | while IFS=$'\t' read -r tool rule loc sev summary st; do
    echo "    [$sev] $loc ($tool $rule) $(bl_mark "${st:-}")$summary"
  done
fi
if [ -n "$BASELINE" ]; then
  echo "既知 $(bl_get known)（前回 $(bl_get prev)）／ 新規 $(bl_get new) ／ 解消 $(bl_get resolved)"
  NB=$(( $(bl_get noreason) + $(bl_get expired) ))
  [ "$NB" -gt 0 ] && echo "❌ 基準線の除外に理由なし $(bl_get noreason) 件・期限なし/期限切れ $(bl_get expired) 件（既知に数えない。理由と期限を書き直すか直す）"
fi
echo "詳細: $REPORT"

# 優先順位: 指摘（high/critical/中 以上）がある場合は 1 を最優先する（判定不能・解析失敗の 2 で覆さない）。
if [ "$HIGH_OR_ABOVE" -gt 0 ]; then
  echo "❌ NG（high/critical/中 以上）=$HIGH_OR_ABOVE"
  exit 1
fi
if [ "$TOOLS_FOUND" -eq 0 ] && [ "$GREP_RAN" -eq 0 ]; then
  echo "❌ 判定不能: 走査器が1つも無く、grep 代替の対象ファイルも無い"
  exit 2
fi
if [ "$PARSE_FAIL_ANY" -eq 1 ]; then
  echo "❌ 判定不能: 解析失敗した走査器がある（指摘なしと解析失敗は別。合格にしない）"
  exit 2
fi
echo "✅ 指摘なし（実行できた走査器の範囲内）"
exit 0
