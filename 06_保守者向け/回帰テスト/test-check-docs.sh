#!/bin/bash
# test-check-docs.sh — check-docs.sh（check_docs.py）の回帰テスト
# リポジトリを一時ディレクトリへ複製し、各検査が「壊した箇所を検出できること」と
# 「壊していない状態（配布されるリポジトリ自身）が NG=0 で通ること」を両方確認する。
# BSD/GNU 共通のその場置換（macOS の sed -i は拡張子引数が必須で GNU と書き方が違う）
sedi() { local f="${@: -1}"; sed "${@:1:$#-1}" "$f" > "$f.sedi" && mv "$f.sedi" "$f"; }
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | head -3 | tr '\n' ' ')"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

# テスト実行の代替（各検査の突合に集中するため、実テストの再実行はしない）
export CHECK_DOCS_TEST_TOTALS="test-hooks.sh=110,test-trace-check.sh=15,test-quality-harness.sh=11,test-install.sh=108,test-git-gates.sh=27"

fresh() { # 複製を作り直してパスを返す
  rm -rf "$TMP/copy"; mkdir -p "$TMP/copy"
  (cd "$KIT_DIR" && tar --exclude=.git --exclude=check-docs-report.md -cf - .) | tar -xf - -C "$TMP/copy"
  echo "$TMP/copy"
}
run() { python3 "$KIT_DIR/06_保守者向け/回帰テスト/check_docs.py" --root "$1" -o "$TMP/report.md" "${@:2}" 2>&1; }

echo "=== check-docs.sh 回帰テスト ==="

echo "[ケース1: リポジトリ自身が NG=0]"
C=$(fresh); OUT=$(run "$C"); RC=$?
expect_exit "現状のリポジトリで exit 0" 0 "$RC"
expect_out  "結論に NG=0" "NG=0" "$OUT"
[ -f "$TMP/report.md" ] && grep -q "文書整合検査レポート" "$TMP/report.md" && ok "詳細レポートを書き出す" || ng "詳細レポートを書き出す" "無い"

echo "[ケース2: 参照コストのズレ]"
C=$(fresh); python3 - "$C/INDEX.md" <<'PY'
import re,sys,pathlib
p=pathlib.Path(sys.argv[1]); s=p.read_text(encoding="utf-8")
s=re.sub(r"(\| `retro` \|.*\| )(\d+)(行 \|)", lambda m: f"{m.group(1)}{int(m.group(2))+1}{m.group(3)}", s, count=1)
p.write_text(s, encoding="utf-8")
PY
OUT=$(run "$C"); RC=$?
expect_exit "INDEX の行数を +1 すると exit 1" 1 "$RC"
expect_out  "種別「参照コスト」で検出" "参照コスト" "$OUT"

echo "[ケース3: 掲載漏れ]"
C=$(fresh); sedi '/^| `retro` |/d' "$C/INDEX.md"
OUT=$(run "$C"); RC=$?
expect_exit "INDEX からスキル行を消すと exit 1" 1 "$RC"
grep -q "| 掲載漏れ | skills/retro |" "$TMP/report.md" && ok "種別「掲載漏れ」で skills/retro を検出（レポート）" || ng "種別「掲載漏れ」で skills/retro を検出（レポート）" "レポートに無い"

echo "[ケース4: ケース数のズレ]"
C=$(fresh)
OUT=$(CHECK_DOCS_TEST_TOTALS="test-hooks.sh=64,test-trace-check.sh=15,test-quality-harness.sh=11,test-install.sh=73,test-git-gates.sh=27" run "$C"); RC=$?
expect_exit "実測が記載と違えば exit 1" 1 "$RC"
expect_out  "種別「ケース数」で検出" "ケース数" "$OUT"
OUT=$(CHECK_DOCS_TEST_TOTALS= run "$C" --skip-tests); RC=$?
expect_exit "--skip-tests は exit 0" 0 "$RC"
expect_out  "--skip-tests は WARN で明示" "テスト未実行" "$OUT"

echo "[ケース5: 参照切れ]"
C=$(fresh); printf '\n参照: `skills/does-not-exist/SKILL.md` を見る\n' >> "$C/README.md"
OUT=$(run "$C"); RC=$?
expect_exit "存在しないキット内パスで exit 1" 1 "$RC"
expect_out  "種別「参照切れ」で検出" "参照切れ" "$OUT"
# 行数を変えない（06_保守者向け/内部仕様/01 の同期検査に引っかからない）よう 1 行目の末尾に追記する
C=$(fresh); sedi '1s/$/ ECC: `skills\/e2e-testing` と `docs\/lifecycle\/00-rfd.md` は除外/' "$C/README.md"
OUT=$(run "$C"); RC=$?
expect_exit "ECC スキル名と配布先の生成パスは参照切れにしない" 0 "$RC"

echo "[ケース6: frontmatter]"
C=$(fresh); sedi 's/^name: retro$/name: retrospective/' "$C/03_ClaudeCode/skills/retro/SKILL.md"
OUT=$(run "$C"); RC=$?
expect_exit "name がディレクトリ名と違えば exit 1" 1 "$RC"
expect_out  "種別「frontmatter」で検出" "frontmatter" "$OUT"

echo "[ケース7: 常時読み込み層の上限]"
C=$(fresh); seq 1 300 | sed 's/^/- 行 /' >> "$C/02_共通/rules/speed-harness.md"
OUT=$(run "$C"); RC=$?
expect_exit "既定で exit 1（M16 で NG に昇格済み）" 1 "$RC"
expect_out  "種別「常時読込」で検出" "常時読込" "$OUT"
C=$(fresh); { printf -- '---\npaths:\n  - "src/**/*.py"\n---\n'; seq 1 300 | sed 's/^/- 行 /'; } > "$C/02_共通/rules/zz-scoped.md"
# INDEX 掲載漏れにならないよう表へ1行足す
printf '| `zz-scoped` | テスト用 | #test | 304行 |\n' >> "$C/INDEX.md"
OUT=$(run "$C" --strict); RC=$?
if grep "| 常時読込 |" "$TMP/report.md" | grep -q "zz-scoped"; then ng "paths 付きの rules は常時読込に数えない" "常時読込の内訳に zz-scoped が出た"; else ok "paths 付きの rules は常時読込に数えない"; fi
grep -q "rules/zz-scoped.md.*目録に無い" "$TMP/report.md" && ok "新規ファイルが 06_保守者向け/内部仕様/01 に無いことを検出（網羅性）" || ng "新規ファイルが 06_保守者向け/内部仕様/01 に無いことを検出（網羅性）" "検出されない"

echo "[ケース8: 行数目安]"
C=$(fresh); seq 1 250 | sed 's/^/- 行 /' >> "$C/03_ClaudeCode/skills/retro/SKILL.md"
sedi 's/^\(| `retro` |.*| \)[0-9]*\(行 |\)$/\1288\2/' "$C/INDEX.md"   # 参照コストは合わせておく
OUT=$(run "$C"); RC=$?
expect_exit "SKILL.md が 200 行を超えると exit 1（M17 で NG に昇格）" 1 "$RC"
expect_out  "種別「行数目安」で検出" "行数目安" "$OUT"
OUT=$(run "$C" --strict); RC=$?
expect_exit "--strict でも exit 1" 1 "$RC"

echo "[ケース9: spec 同期]"
C=$(fresh); sedi 's/^| `verify.sh` | [0-9]* |/| `verify.sh` | 1 |/' "$C/06_保守者向け/内部仕様/01-inventory.md"
OUT=$(run "$C"); RC=$?
expect_exit "06_保守者向け/内部仕様/01 の行数がズレると exit 1" 1 "$RC"
expect_out  "種別「spec同期」で検出" "spec同期" "$OUT"

echo "[ケース10: 03_ClaudeCode/CLAUDE.md.template ＋ 04_Codex/AGENTS.md.template の合計 ≦ 200 行]"
C=$(fresh); for i in $(seq 1 120); do echo "- 水増し $i" >> "$C/04_Codex/AGENTS.md.template"; done
OUT=$(run "$C" --skip-tests); RC=$?
expect_exit "合計が 200 行を超えると exit 1" 1 "$RC"
expect_out  "種別「常時読込」で検出" "03_ClaudeCode/CLAUDE.md.template + 04_Codex/AGENTS.md.template" "$OUT"

echo "[ケース11: 件数の直値（検査10・WARN）]"
C=$(fresh); sedi '1,/スキル: 20個/s/スキル: 20個/スキル: 19個/' "$C/01_利用者向け資料/利用ガイド.html"
OUT=$(run "$C" --skip-tests); RC=$?
expect_exit "件数のズレは WARN なので exit 0" 0 "$RC"
grep -q "| 件数 | 01_利用者向け資料/利用ガイド.html" "$TMP/report.md" && ok "種別「件数」で skills 19 / 実数 20 を検出（レポート）" || ng "種別「件数」で検出" "レポートに無い"

echo "[ケース12: 絶対パス（検査11・WARN）]"
C=$(fresh); sedi 's|^- 1. <作業>.*|- 1. /Users/you/work/app を開く|' "$C/02_共通/ひな形/CURRENT_STATE.md"   # 行数を変えない（spec 同期を崩さない）
OUT=$(run "$C" --skip-tests); RC=$?
expect_exit "絶対パスは WARN なので exit 0" 0 "$RC"
grep -q "| 絶対パス | 02_共通/ひな形/CURRENT_STATE.md" "$TMP/report.md" && ok "種別「絶対パス」で /Users/ を検出（レポート）" || ng "種別「絶対パス」で検出" "レポートに無い"
C=$(fresh); OUT=$(run "$C" --skip-tests)
grep -q "| 絶対パス |" "$TMP/report.md" && ng "元の状態では検出されない" "残っている: $(grep '| 絶対パス |' "$TMP/report.md" | head -2)" || ok "元の状態では検出されない（配布雛形・README・userguide に絶対パスなし）"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
