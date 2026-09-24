#!/bin/bash
# test-cite-check.sh — cite-check.py（ADR・rules・lessons の引用先の消失・変更の検知）の回帰テスト
# ファイル無し・見出し無しは NG、版の無い引用は版を書き足して WARN、版の違う引用は stale の WARN、--refresh で記録し直せること、
# skills は対象外であること、引用でないバッククォート（MIME 型・メソッド名・glob・コマンド）を NG にしないことを確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CITE="$KIT_DIR/02_共通/ツール/cite-check.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
sedi() { local f="${@: -1}"; sed "${@:1:$#-1}" "$f" > "$f.sedi" && mv "$f.sedi" "$f"; }
run() { python3 "$CITE" "$@" 2>&1; }

echo "=== cite-check.py 回帰テスト ==="
R="$TMP/proj"; mkdir -p "$R/docs/adr" "$R/src" "$R/.claude/rules" "$R/.claude/skills/x/adr"
printf '# 仕様\n## 認証方式\nJWT を使う。\n### 期限\n1 時間。\n## 保存\nIndexedDB に保存する。\n' > "$R/docs/spec.md"
printf 'TIMEOUT = 30\nRETRY = 3\n' > "$R/src/app.py"
cat > "$R/docs/adr/ADR-001-auth.md" <<'EOF'
# ADR-001: 認証方式

## 背景
根拠は `docs/spec.md#認証方式` と `src/app.py:1`。
引用でない: `application/json`・`requests.get`・`src/**/*.py`・`python3 scripts/cite-check.py .`・`docs/`
<!-- `docs/commented-out.md` は HTML コメントの中なので読まない -->
EOF
printf -- '- 再試行は `src/app.py:2` の回数に合わせる\n' > "$R/.claude/rules/api.md"
printf '## 2026-09-24 横断\n**Keep**\n- 保存先は `docs/spec.md#保存` を先に読む\n' > "$R/lessons.md"
printf -- '- `docs/skill-only.md` を見る\n' > "$R/.claude/skills/x/adr/ADR-001-example.md"   # スキル内の ADR の記入例

echo "[ケース1: 通常の実行は書き込まない。--record で版の無い引用に @版 を書き足す]"
cp -r "$R" "$TMP/before"
OUT=$(run "$R"); RC=$?
expect_exit "NG が無ければ exit 0" 0 "$RC"
expect_out  "版の無い引用は WARN にせず件数だけ出す" "NG=0 / WARN=0（対象 3 ファイル・引用 5 件・版の記録なし 4 件" "$OUT"
diff -r "$TMP/before" "$R" >/dev/null && ok "通常の実行はファイルに一切書き込まない" || ng "通常の実行はファイルに一切書き込まない" "$(diff -r "$TMP/before" "$R" | head -3 | tr '\n' ' ')"
OUT=$(run "$R" --record); RC=$?
expect_exit "--record は exit 0" 0 "$RC"
expect_out  "--record で記録した場所を出す（ADR）" "記録 docs/adr/ADR-001-auth.md:4" "$OUT"
expect_out  "rules も対象" "記録 .claude/rules/api.md:1" "$OUT"
expect_out  "lessons も対象" "記録 lessons.md:3" "$OUT"
expect_out  "保守者の記録だと出す（AI は打たない）" "AI は --record・--refresh を打たない" "$OUT"
grep -Eq '`docs/spec.md#認証方式@[0-9a-f]{7}`' "$R/docs/adr/ADR-001-auth.md" && ok "引用に @版 を書き足す（見出し）" || ng "引用に @版 を書き足す（見出し）" "$(sed -n 4p "$R/docs/adr/ADR-001-auth.md")"
grep -Eq '`src/app.py:1@[0-9a-f]{7}`' "$R/docs/adr/ADR-001-auth.md" && ok "引用に @版 を書き足す（行）" || ng "引用に @版 を書き足す（行）" "$(sed -n 4p "$R/docs/adr/ADR-001-auth.md")"
expect_noout "skills は対象外（skills 内の存在しない引用を NG にしない）" "skill-only.md" "$OUT"
expect_noout "HTML コメントの中の引用は読まない" "commented-out.md" "$OUT"
for w in application/json requests.get 'src/**/*.py' 'python3 scripts'; do
  expect_noout "引用でないバッククォート（$w）を NG にしない" "$w" "$OUT"
done
OUT=$(run "$R"); RC=$?
expect_exit "2 回目は版が一致して exit 0" 0 "$RC"
expect_out  "2 回目は WARN=0" "NG=0 / WARN=0" "$OUT"

echo "[ケース2: 引用先の節・行が変わると stale の WARN]"
sedi 's/JWT を使う。/セッション Cookie を使う。/' "$R/docs/spec.md"
OUT=$(run "$R"); RC=$?
expect_exit "stale は WARN（exit 0）" 0 "$RC"
expect_out  "見出しの節の変更を stale にする" "WARN stale: docs/adr/ADR-001-auth.md:4 — \`docs/spec.md#認証方式\` が変わった" "$OUT"
expect_noout "別の節（## 保存）を引用した lessons は stale にしない" "WARN stale: lessons.md" "$OUT"
run "$R" --refresh >/dev/null                      # いったん記録し直してから子節だけを変える
sedi 's/1 時間。/2 時間。/' "$R/docs/spec.md"
OUT=$(run "$R")
expect_out  "子節（### 期限）の変更も親の見出しの引用を stale にする" "WARN stale: docs/adr/ADR-001-auth.md:4 — \`docs/spec.md#認証方式\` が変わった" "$OUT"
sedi 's/RETRY = 3/RETRY = 5/' "$R/src/app.py"
OUT=$(run "$R")
expect_out  "引用した行の変更を stale にする" "WARN stale: .claude/rules/api.md:1" "$OUT"
expect_noout "別の行（:1）の引用は stale にしない" "\`src/app.py:1\` が変わった" "$OUT"

echo "[ケース3: --refresh で記録を現在の版に書き換える]"
OUT=$(run "$R" --refresh); RC=$?
expect_exit "--refresh は exit 0" 0 "$RC"
expect_out  "書き換えた記録を出す" "版を書いた（2 件）" "$OUT"
expect_out  "保守者の再確認の記録だと出す（AI は打たない）" "AI は --record・--refresh を打たない" "$OUT"
OUT=$(run "$R"); RC=$?
expect_out  "--refresh の後は stale が消える" "NG=0 / WARN=0" "$OUT"

echo "[ケース4: ファイル無し・見出し無し・行が無い・版の書式不正は NG]"
printf '消えた根拠: `docs/removed.md`\n見出し違い: `docs/spec.md#認可方式`\n行が無い: `src/app.py:9`\n壊れた版: `src/app.py@zz`\n' >> "$R/docs/adr/ADR-001-auth.md"
OUT=$(run "$R"); RC=$?
expect_exit "NG があれば exit 1" 1 "$RC"
expect_out  "ファイル無しを NG" "ファイル無し（docs/removed.md）" "$OUT"
expect_out  "見出し無しを NG" "見出し無し（docs/spec.md に「認可方式」が無い）" "$OUT"
expect_out  "行が無いを NG" "行が無い（src/app.py は 2 行。引用は 9）" "$OUT"
expect_out  "版の書式不正を NG" "NG   版の書式不正: docs/adr/ADR-001-auth.md:10" "$OUT"
grep -q '`docs/removed.md`' "$R/docs/adr/ADR-001-auth.md" && ok "NG の引用には版を書き足さない" || ng "NG の引用には版を書き足さない" "書き換わった"
rm "$R/src/app.py"
OUT=$(run "$R")
expect_out  "版を記録済みの引用でも、引用先が消えたら NG" "\`src/app.py:1@" "$OUT"

echo "[ケース5: 配布先の .claude/rules/（キット参照・ファイル名だけ・キットの配置・未作成の参照）]"
K="$TMP/kproj"; KR="$TMP/kproj/.claude/rules"; mkdir -p "$KR" "$K/.claude/skills/t/references" "$K/docs/adr" "$K/src"
printf 'x = 1\n' > "$K/src/app.py"; printf '# 参考\n' > "$K/.claude/skills/t/references/ref.md"
printf '%s\n' '根拠: `06_保守者向け/02_設計判断の根拠/kit.md`・`./00_導入/03_点検/token-audit.sh`。hook は `prompt-priority.py`。' \
  '詳細は `skills/t/references/ref.md`、記録は `docs/lessons.md` に残す。' > "$TMP/kit.md"
cp "$TMP/kit.md" "$KR/"
OUT=$(run "$K"); RC=$?
expect_exit ".claude/rules/ のキット参照・未作成の参照だけなら exit 0" 0 "$RC"
expect_out  "対象外の件数を出す（キット参照 2・未作成 1）" "対象外 3 件" "$OUT"
expect_noout "ファイル名だけ（prompt-priority.py）は引用にしない" "prompt-priority.py" "$OUT"
expect_noout "skills/… はキットの配置（.claude/skills/）で見つける" "ref.md" "$OUT"
OUT=$(run "$K" --strict); RC=$?
expect_exit "--strict でも WARN だけ（exit 0）" 0 "$RC"
expect_out  "--strict でキット参照を WARN" "WARN キット参照（対象外）: .claude/rules/kit.md:1" "$OUT"
expect_out  "--strict で未作成の参照を WARN" "WARN 未作成の参照（対象外）: .claude/rules/kit.md:2" "$OUT"
printf -- '- 根拠 `06_保守者向け/02_設計判断の根拠/kit.md`\n' > "$K/docs/adr/ADR-002.md"
OUT=$(run "$K"); RC=$?
expect_exit "ADR（.claude/rules/ の外）のキット参照は NG（exit 1）" 1 "$RC"
rm "$K/docs/adr/ADR-002.md"
printf -- '- `src/app.py`\n' > "$TMP/own.md"; cp "$TMP/own.md" "$KR/"
run "$K" --record >/dev/null; rm "$K/src/app.py"
OUT=$(run "$K"); RC=$?
expect_exit ".claude/rules/ でも版を記録した引用の引用先が消えたら NG（exit 1）" 1 "$RC"
expect_out  "消えた引用を NG で出す" "NG   引用先が無い: .claude/rules/own.md:1" "$OUT"

echo "[ケース6: adr-to-rules.py が生成した rules は飛ばす・引数の誤り]"
printf '<!-- adr-to-rules.py が生成 -->\n- `docs/generated-missing.md`\n' > "$R/.claude/rules/decisions-adr-001.md"
OUT=$(run "$R")
expect_noout "生成物（decisions-*.md）は元の ADR を見るので飛ばす" "generated-missing.md" "$OUT"
OUT=$(run "$TMP/none"); RC=$?
expect_exit "root が無い → exit 2" 2 "$RC"
S="$TMP/solo"; mkdir -p "$S"; cp "$CITE" "$S/"
OUT=$(python3 "$S/cite-check.py" "$R" 2>&1); RC=$?
expect_exit "隣に section_hash.py が無い → exit 2（版を計算できない）" 2 "$RC"

echo "[検証: 塊I] 見出し・行の境界、--refresh の書き換え範囲"
V="$TMP/vI"; mkdir -p "$V/docs/adr" "$V/src" "$V/rules" "$V/skills/s"
printf '# 仕様\n## a\nA\n### b\nB\n## 手順\n1\n## 手順\n2\n## c\nC\n' > "$V/docs/spec.md"
printf 'x = 1\ny = 2\n' > "$V/src/app.py"
printf '# ADR-009\n- `docs/spec.md#a#b`\n- `docs/spec.md#手順`\n- `src/app.py:3`\n- [リンク](docs/nothere.md#h)\n' > "$V/docs/adr/ADR-009.md"
printf -- '- `docs/nothere-skill.md`\n' > "$V/skills/s/lessons.md"
OUT=$(run "$V"); RC=$?
expect_exit "NG があれば exit 1" 1 "$RC"
expect_out  "path#a#b（# が 2 つ）は NG（見出し無し）" "docs/adr/ADR-009.md:2" "$OUT"
expect_out  "見出しの重複は NG（曖昧）" "見出しが曖昧（docs/spec.md で 2 個" "$OUT"
expect_out  "path:行 で行が範囲外は NG" "行が無い（src/app.py は 2 行。引用は 3）" "$OUT"
expect_noout "Markdown リンク [x](path#h) は読まない（事実）" "nothere.md" "$OUT"
expect_noout "skills 配下の lessons.md は対象外" "nothere-skill.md" "$OUT"
printf '# ADR-010\r\n- `docs/spec.md#a` と `docs/spec.md#c`\r\n' > "$V/docs/adr/ADR-010.md"
printf -- '- `docs/spec.md#c`\n' > "$V/rules/r.md"
printf -- '- `docs/spec.md#a`\n' > "$V/README.md"
rm "$V/docs/adr/ADR-009.md"; run "$V" --record >/dev/null   # 通常の実行は書き込まない（差し戻しの決定 7）。版は --record で記録する
cp "$V/docs/adr/ADR-010.md" "$V/adr.before"; cp "$V/rules/r.md" "$V/r.before"
sedi 's/^B$/B2/' "$V/docs/spec.md"
OUT=$(run "$V")
expect_out  "@版 の記録後に子節を変える → 親の見出しの引用が stale" "WARN stale: docs/adr/ADR-010.md:2 — \`docs/spec.md#a\`" "$OUT"
cmp -s "$V/docs/adr/ADR-010.md" "$V/adr.before" && ok "--refresh 無しでは stale の記録を書き換えない" || ng "--refresh 無しでは stale の記録を書き換えない" "書き換わった"
run "$V" --refresh >/dev/null
[ "$(diff "$V/adr.before" "$V/docs/adr/ADR-010.md" | grep -c '^>')" -eq 1 ] && ok "--refresh は stale の行だけ書き換える（1 行）" || ng "--refresh は stale の行だけ書き換える" "$(diff "$V/adr.before" "$V/docs/adr/ADR-010.md" | tr '\n' ' ')"
grep -qF '`docs/spec.md#c@' "$V/docs/adr/ADR-010.md" && grep -q $'\r$' "$V/docs/adr/ADR-010.md" && ok "--refresh は同じ行の stale でない引用と CRLF を保つ" || ng "--refresh は同じ行の他の引用・CRLF を保つ" "崩れた"
cmp -s "$V/rules/r.md" "$V/r.before" && ok "--refresh は stale の無い rules を書き換えない" || ng "--refresh は stale の無い rules を書き換えない" "書き換わった"
grep -qxF -- '- `docs/spec.md#a`' "$V/README.md" && ok "対象外（README.md）は書き換えない" || ng "対象外（README.md）は書き換えない" "書き換わった"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
