#!/bin/bash
# trace-check.sh — 工程文書のトレーサビリティを機械検証する
#
# 対象: docs/lifecycle/ 配下の工程文書（templates/lifecycle/ の雛形を前提とする）
# 規約: skills/dev-lifecycle/references/traceability.md
#
# 使い方:
#   ./scripts/trace-check.sh [対象ディレクトリ] [-o 詳細レポートの出力先]
#   （既定: 対象=docs/lifecycle / 詳細=./trace-check-report.md）
#
# 出力は context-compression の3層要約に従う。
# 会話・CI ログには「結論と根拠」だけを出し、全件は詳細レポートへ書き出す。
# 終了コード: NG=0 なら 0、NG>0 なら 1（CI でそのまま落とせる）

DIR="docs/lifecycle"
REPORT="./trace-check-report.md"

while [ $# -gt 0 ]; do
  case "$1" in
    -o) REPORT="$2"; shift 2 ;;
    -h|--help)
      echo "使い方: $0 [対象ディレクトリ] [-o 詳細レポート出力先]"; exit 0 ;;
    *) DIR="$1"; shift ;;
  esac
done

if [ ! -d "$DIR" ]; then
  echo "ℹ 対象ディレクトリが存在しないためスキップ: $DIR"
  echo "  （工程文書を作る場合: ./scripts/init-lifecycle.sh <対象プロジェクトのパス>）"
  exit 0
fi

# 走査対象。自身のレポートは除外する（レポート内の ID を定義と誤検出しないため）
FILES=$(find "$DIR" -maxdepth 1 -name '*.md' ! -name '*trace-check-report*' | sort)
if [ -z "$FILES" ]; then
  echo "ℹ 対象ディレクトリに工程文書(.md)がないためスキップ: $DIR"
  exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

ID_RE='^(REQ-F|REQ-N|RFD|UAT|OPS|DEF|BD|DD|UT|IT|ST|T)-[0-9][0-9][0-9]$'
export TMP

MATRIX=$(printf '%s\n' $FILES | grep -i 'traceability' | head -1)

# --- 定義と参照の抽出 -------------------------------------------------------
# 定義位置: ①見出し行の先頭トークン ②表の第1セル
#   ただし追跡表は「対応関係を突き合わせる表」であり定義の場ではないため、参照のみとして扱う
# 参照: 本文中に現れる全 ID（記号を空白に潰してトークン化するため、
#       "DD-001,DD-002" や "`T-001`" も正しく分解でき、"UAT-001" から "T-001" を誤検出しない）
awk -v idre="$ID_RE" -v matrix="$MATRIX" '
  function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
  {
    # 定義位置（追跡表は参照専用なので採らない）
    if (FILENAME == matrix) {
      # 何もしない
    } else if ($0 ~ /^#+[ \t]+/) {
      t = trim($2)
      if (t ~ idre) print t "\t" FILENAME > (ENVIRON["TMP"] "/defs.tsv")
    } else if ($0 ~ /^\|/) {
      n = split($0, cells, "|")
      if (n >= 2) {
        t = trim(cells[2])
        if (t ~ idre) print t "\t" FILENAME > (ENVIRON["TMP"] "/defs.tsv")
      }
    }
    # 参照
    line = $0
    gsub(/[^A-Za-z0-9_-]/, " ", line)
    m = split(line, toks, " ")
    for (i = 1; i <= m; i++)
      if (toks[i] ~ idre) print toks[i] "\t" FILENAME > (ENVIRON["TMP"] "/refs.tsv")
  }
' $FILES
touch "$TMP/defs.tsv" "$TMP/refs.tsv"

# --- 所有ファイルの解決 -----------------------------------------------------
owner_pattern() {
  case "$1" in
    RFD)   echo "rfd" ;;
    REQ-F|REQ-N) echo "requirement" ;;
    BD)    echo "basic-design" ;;
    DD)    echo "detailed-design" ;;
    T)     echo "implementation" ;;
    UT)    echo "unit-test" ;;
    IT)    echo "integration-test" ;;
    ST)    echo "system-test" ;;
    UAT)   echo "acceptance" ;;
    OPS)   echo "operations" ;;
    *)     echo "" ;;   # DEF は検出工程の文書内に置くため所有者を固定しない
  esac
}

# --- 検査 -------------------------------------------------------------------
: > "$TMP/ng.tsv"     # 種別 \t 対象 \t 内容
: > "$TMP/warn.tsv"

# C1: 重複定義（異なるファイルで同一 ID が定義位置に現れる）
sort -u "$TMP/defs.tsv" | cut -f1 | sort | uniq -d | while read -r id; do
  [ -z "$id" ] && continue
  files=$(awk -F'\t' -v i="$id" '$1==i{print $2}' "$TMP/defs.tsv" | sort -u | tr '\n' ' ')
  printf '重複定義\t%s\t%s\n' "$id" "複数ファイルで定義: $files" >> "$TMP/ng.tsv"
done

# C2: 未定義参照（参照されているが、どこにも定義されていない）
cut -f1 "$TMP/refs.tsv" | sort -u | while read -r id; do
  [ -z "$id" ] && continue
  if ! awk -F'\t' -v i="$id" '$1==i{f=1} END{exit !f}' "$TMP/defs.tsv"; then
    refin=$(awk -F'\t' -v i="$id" '$1==i{print $2}' "$TMP/refs.tsv" | sort -u | tr '\n' ' ')
    printf '未定義参照\t%s\t%s\n' "$id" "定義が無いまま参照: $refin" >> "$TMP/ng.tsv"
  fi
done

# C3: 所有ファイル違反（所有ファイル以外に定義位置で書かれている＝対応表の複製）
sort -u "$TMP/defs.tsv" | while IFS="$(printf '\t')" read -r id file; do
  [ -z "$id" ] && continue
  prefix="${id%-*}"
  pat=$(owner_pattern "$prefix")
  [ -z "$pat" ] && continue
  ownerfile=$(printf '%s\n' $FILES | grep -i -- "$pat" | head -1)
  if [ -z "$ownerfile" ]; then
    printf '所有ファイル不在\t%s\t%s\n' "$prefix" "工程文書 *${pat}*.md が見つからない（該当工程が未着手なら無視してよい）" >> "$TMP/warn.tsv"
    continue
  fi
  [ "$file" = "$ownerfile" ] || \
    printf '所有ファイル違反\t%s\t%s\n' "$id" "定義先=$file ／ 所有ファイル=$ownerfile" >> "$TMP/ng.tsv"
done

# C4/C5: 追跡表の突合（追跡表がある場合のみ）
if [ -n "$MATRIX" ]; then
  # 追跡表に現れる ID
  awk -F'\t' -v f="$MATRIX" '$2==f{print $1}' "$TMP/refs.tsv" | sort -u > "$TMP/in_matrix.txt"

  # C4: 定義済み REQ-* が追跡表に無い
  awk -F'\t' '$1 ~ /^REQ-[FN]-/{print $1}' "$TMP/defs.tsv" | sort -u | while read -r id; do
    grep -qx "$id" "$TMP/in_matrix.txt" || \
      printf '追跡表に未記載\t%s\t%s\n' "$id" "要件が $MATRIX に載っていない" >> "$TMP/ng.tsv"
  done

  # C5: 追跡表のカバー漏れ（必須セルの空欄・必須列の未割当）
  awk -v out="$TMP/ng.tsv" '
    function trim(s) { gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
    /^\|/ {
      n = split($0, c, "|")
      for (i = 1; i <= n; i++) c[i] = trim(c[i])
      if (c[2] ~ /REQ-ID/) {                      # ヘッダ行: 列位置を学習する
        delete col
        for (i = 2; i < n; i++) {
          if (c[i] == "BD") col["BD"] = i
          else if (c[i] == "DD") col["DD"] = i
          else if (c[i] ~ /UAT/) col["UAT"] = i
          else if (c[i] == "UT") col["UT"] = i
          else if (c[i] == "IT") col["IT"] = i
          else if (c[i] == "ST") col["ST"] = i
          else if (c[i] ~ /実装/) col["T"] = i
        }
        hdr = 1; next
      }
      if (!hdr) next
      if (c[2] !~ /^REQ-[FN]-[0-9][0-9][0-9]$/) next
      id = c[2]
      # 空欄チェック（"-" や "—" は「非該当」として許容する）
      split("BD DD T UT IT ST UAT", need, " ")
      for (k = 1; k <= 7; k++) {
        nm = need[k]
        if (!(nm in col)) continue
        v = c[col[nm]]
        if (v == "") printf "カバー漏れ\t%s\t追跡表の %s 列が空欄（非該当なら - を入れる）\n", id, nm >> out
      }
      # V字の必須割当
      if ("BD" in col && c[col["BD"]] !~ /BD-[0-9][0-9][0-9]/)
        printf "カバー漏れ\t%s\t設計未割当（BD 列に BD-xxx が無い）\n", id >> out
      if (id ~ /^REQ-F-/ && "UAT" in col && c[col["UAT"]] !~ /UAT-[0-9][0-9][0-9]/)
        printf "カバー漏れ\t%s\t受け入れテスト未割当（REQ-F は UAT 必須）\n", id >> out
      if (id ~ /^REQ-N-/ && "ST" in col && c[col["ST"]] !~ /ST-[0-9][0-9][0-9]/)
        printf "カバー漏れ\t%s\tシステムテスト未割当（REQ-N は ST 必須）\n", id >> out
    }
  ' "$MATRIX"

  # C6: 孤立テスト（定義済みだが追跡表から参照されていない）
  awk -F'\t' '$1 ~ /^(UT|IT|ST|UAT)-/{print $1}' "$TMP/defs.tsv" | sort -u | while read -r id; do
    grep -qx "$id" "$TMP/in_matrix.txt" || \
      printf '孤立テスト\t%s\t%s\n' "$id" "追跡表から参照されていない（検証対象の要件が不明）" >> "$TMP/ng.tsv"
  done
else
  printf '追跡表なし\t-\t%s\n' "*traceability*.md が $DIR に無い。要件とテストの突合ができない" >> "$TMP/warn.tsv"
fi

sort -u "$TMP/ng.tsv" -o "$TMP/ng.tsv"
sort -u "$TMP/warn.tsv" -o "$TMP/warn.tsv"
NG=$(wc -l < "$TMP/ng.tsv" | tr -d ' ')
WARN=$(wc -l < "$TMP/warn.tsv" | tr -d ' ')
DEFS=$(cut -f1 "$TMP/defs.tsv" | sort -u | wc -l | tr -d ' ')

# --- 詳細レポート（全件はファイルへ） ---------------------------------------
{
  echo "# トレーサビリティ検査レポート"
  echo ""
  echo "- 対象: \`$DIR\`（$(printf '%s\n' $FILES | wc -l | tr -d ' ') ファイル）"
  echo "- 定義済み ID: $DEFS 件 ／ NG: $NG 件 ／ 警告: $WARN 件"
  echo "- 規約: \`skills/dev-lifecycle/references/traceability.md\`"
  echo ""
  echo "## NG 一覧"
  echo ""
  if [ "$NG" -eq 0 ]; then
    echo "なし。"
  else
    echo "| 種別 | 対象 | 内容 |"
    echo "|---|---|---|"
    awk -F'\t' '{printf "| %s | %s | %s |\n", $1, $2, $3}' "$TMP/ng.tsv"
  fi
  echo ""
  echo "## 警告"
  echo ""
  if [ "$WARN" -eq 0 ]; then
    echo "なし。"
  else
    echo "| 種別 | 対象 | 内容 |"
    echo "|---|---|---|"
    awk -F'\t' '{printf "| %s | %s | %s |\n", $1, $2, $3}' "$TMP/warn.tsv"
  fi
  echo ""
  echo "## 定義済み ID（工程別）"
  echo ""
  echo "| ID | 定義ファイル |"
  echo "|---|---|"
  sort -u "$TMP/defs.tsv" | awk -F'\t' '{printf "| %s | %s |\n", $1, $2}'
} > "$REPORT"

# --- 結論と根拠（会話・CI ログに出すのはここまで） --------------------------
echo "=== トレーサビリティ検査: $DIR ==="
if [ "$NG" -eq 0 ]; then
  echo "✅ NG=0（定義済み ID: $DEFS 件）"
else
  echo "❌ NG=$NG（定義済み ID: $DEFS 件）"
  cut -f1 "$TMP/ng.tsv" | sort | uniq -c | sort -rn | while read -r n kind; do
    echo "  - $kind: $n 件"
  done
  echo "  例（先頭5件）:"
  head -5 "$TMP/ng.tsv" | awk -F'\t' '{printf "    %s: %s — %s\n", $1, $2, $3}'
fi
[ "$WARN" -gt 0 ] && awk -F'\t' '{printf "⚠ %s: %s\n", $1, $3}' "$TMP/warn.tsv"
echo "詳細: $REPORT"

[ "$NG" -eq 0 ] && exit 0 || exit 1
