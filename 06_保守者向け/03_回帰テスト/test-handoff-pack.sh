#!/bin/bash
# test-handoff-pack.sh — check-handoff.py（REPORT.md の返却時の状態 4 行）と pack-context.py（文脈パック）の回帰テスト（G3）
#
# check-handoff: 4 行が揃えば exit 0、欠落・順序違い・空欄・置き場所のまま・語彙外・証跡の不在/絶対パス/root の外は exit 1、
#   unknown・全角コロン・フェンス囲み・Windows 区切りは通す、停止/ブロックで「未達・要判断」が無いと WARN、読めなければ exit 2。
# pack-context: ファイル全体・見出し指定（: と #）の抜粋と sha256、見出しの 0 件/複数一致・ファイル無しで exit 1、
#   --verify は一致で 0・改変/削除で 1、抜粋内の ``` を壊さないこと、ファイルを書かない（-o 以外）ことを確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HANDOFF="$KIT_DIR/02_共通/ツール/check-handoff.py"
PACK="$KIT_DIR/02_共通/ツール/pack-context.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
export PYTHONDONTWRITEBYTECODE=1

echo "=== check-handoff.py / pack-context.py 回帰テスト ==="

R="$TMP/zip"; mkdir -p "$R/logs"
echo "ALL GREEN" > "$R/logs/test-tail.txt"
hc() { python3 "$HANDOFF" "$R/REPORT.md" "$@" 2>&1; }
report() { printf '%s\n' "$@" > "$R/REPORT.md"; }

echo "[check-handoff: 揃っている（通る）]"
report "状態: 完了" "閉じる条件: python scripts/verify.py の末尾が ALL GREEN" "次の担当: Claude" "証跡: logs/test-tail.txt" "" "## 変更ファイル"
OUT=$(hc); RC=$?
expect_exit "4 行が揃えば exit 0" 0 "$RC"
expect_out  "OK と NG=0 を出す" "NG=0" "$OUT"
report '```' "状態：停止" "閉じる条件：unknown" "次の担当：Codex（再依頼）" "証跡：logs\\test-tail.txt" '```' "## 未達・要判断" "- 入力待ち"
OUT=$(hc); RC=$?
expect_exit "フェンス囲み・全角コロン・Windows 区切り・unknown は通る" 0 "$RC"
expect_noout "未達・要判断があれば W1 を出さない" "W1" "$OUT"
report "" "状態: unknown" "閉じる条件: unknown" "次の担当: unknown" "証跡: unknown"
OUT=$(hc); RC=$?
expect_exit "全項目 unknown は通る（空欄にしない約束を守っている）" 0 "$RC"
report "状態: 完了" "閉じる条件: x" "次の担当: 保守者" "証跡: \`logs/test-tail.txt\`"
OUT=$(hc); RC=$?
expect_exit "バッククォートで囲んだ証跡も通る" 0 "$RC"
OUT=$(hc --json); RC=$?
expect_out  "--json に ok: true" '"ok": true' "$OUT"

echo "[check-handoff: NG]"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude"
OUT=$(hc); RC=$?
expect_exit "3 行しか無いと exit 1" 1 "$RC"
expect_out  "4 行目の欠落を H1 で出す" "H1 先頭 4 行目に \`証跡:\` が無い" "$OUT"
report "閉じる条件: x" "状態: 完了" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "順序違いは exit 1" 1 "$RC"
expect_out  "1 行目は状態のはずと出す" "\`状態:\` で始まるはず" "$OUT"
report "# 報告" "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "先頭に見出しがあると exit 1（先頭 4 行の約束）" 1 "$RC"
report "状態: 完了" "閉じる条件:" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "空欄は exit 1" 1 "$RC"
expect_out  "空欄を H2 で出す（unknown を促す）" "H2 \`閉じる条件\` が空" "$OUT"
report "状態: 完了" "閉じる条件: <この作業を完了とみなす条件>" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "置き場所 <…> のままは exit 1" 1 "$RC"
report "状態: 完了 | 停止 | ブロック" "閉じる条件: x" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "状態の選択肢をそのまま写すと exit 1" 1 "$RC"
expect_out  "H3 を出す" "H3 状態は" "$OUT"
report "状態: done" "閉じる条件: x" "次の担当: Claude" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "語彙外の状態は exit 1" 1 "$RC"
report "状態: 完了" "閉じる条件: x" "次の担当: 誰か" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "語彙外の次の担当は exit 1" 1 "$RC"
expect_out  "H4 を出す" "H4 次の担当は" "$OUT"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: logs/none.txt"
OUT=$(hc); RC=$?
expect_exit "証跡のファイルが無いと exit 1" 1 "$RC"
expect_out  "H5 を出す" "H5 証跡のファイルが無い: logs/none.txt" "$OUT"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: $R/logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "証跡の絶対パスは exit 1" 1 "$RC"
expect_out  "相対パスで書くよう出す" "相対パスで書く" "$OUT"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: C:\\work\\tail.txt"
OUT=$(hc); RC=$?
expect_exit "証跡の Windows 絶対パスも exit 1" 1 "$RC"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: ../outside.txt"
touch "$TMP/outside.txt"
OUT=$(hc); RC=$?
expect_exit "root の外を指す証跡は（実在しても）exit 1" 1 "$RC"
expect_out  "root の外と出す" "root の外" "$OUT"
report "状態: 完了" "閉じる条件: x" "次の担当: Claude" "証跡: test-tail.txt"
OUT=$(hc --root "$R/logs"); RC=$?
expect_exit "--root で証跡の起点を変えられる" 0 "$RC"

echo "[check-handoff: WARN・判定不能]"
report "状態: ブロック" "閉じる条件: x" "次の担当: 保守者" "証跡: logs/test-tail.txt"
OUT=$(hc); RC=$?
expect_exit "ブロックで理由が無いのは WARN だけ（exit 0）" 0 "$RC"
expect_out  "W1 を出す" "W1" "$OUT"
OUT=$(python3 "$HANDOFF" "$TMP/none/REPORT.md" 2>&1); RC=$?
expect_exit "REPORT.md が無ければ exit 2" 2 "$RC"

echo "[pack-context: 生成]"
D="$TMP/docs"; mkdir -p "$D"
cat > "$D/spec.md" <<'EOF'
# 仕様
## 1. 目的
貸出を Web にする。
## 2. 画面
### 2.1 一覧
一覧を出す。
```bash
echo "フェンス内の # 見出しではない"
```
### 2.2 詳細
詳細を出す。
## 3. 非機能
速い。
EOF
printf 'line1\nline2\n' > "$D/plain.txt"
pk() { (cd "$D" && python3 "$PACK" "$@" 2>&1); }
OUT=$(pk "spec.md:画面" plain.txt -o "$TMP/pack.md"); RC=$?
expect_exit "見出し指定とファイル全体で exit 0" 0 "$RC"
P=$(cat "$TMP/pack.md")
expect_out  "節の抜粋（子節を含む）を入れる" "詳細を出す。" "$P"
expect_noout "節の外（次の同レベル見出し以降）は入れない" "速い。" "$P"
expect_out  "行範囲を表に出す" "| 4-11 |" "$P"
SHA=$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$D/spec.md")
expect_out  "ファイル全体の sha256 を刻む" "sha256=$SHA" "$P"
expect_out  "ファイル全体の指定は（全体）" "| \`plain.txt\` | （全体） |" "$P"
expect_out  "抜粋内の \`\`\` を壊さない長いフェンスで囲む" '````markdown' "$P"
OUT=$(pk "spec.md#一覧"); RC=$?
expect_exit "# 区切りも使える（標準出力）" 0 "$RC"
expect_out  "標準出力に抜粋を出す" "一覧を出す。" "$OUT"
VER=$(cd "$KIT_DIR/02_共通/ツール" && python3 -c 'import sys,hashlib;sys.dont_write_bytecode=True;import section_hash as s;t=open(sys.argv[1],encoding="utf-8").read().splitlines();print(hashlib.sha256(s.normalize("\n".join(t[4:9])).encode()).hexdigest()[:7])' "$D/spec.md")
expect_out  "節の版は section_hash.normalize の sha256 先頭 7 桁" "\`$VER\`" "$OUT"

echo "[pack-context: NG]"
OUT=$(pk "spec.md:存在しない"); RC=$?
expect_exit "見出しが 0 件なら exit 1" 1 "$RC"
expect_out  "見つからないと出す" "見出しが見つかりません" "$OUT"
OUT=$(pk "spec.md:2."); RC=$?
expect_exit "見出しが複数一致なら exit 1" 1 "$RC"
expect_out  "候補を出す" "複数一致" "$OUT"
OUT=$(pk "none.md:目的"); RC=$?
expect_exit "ファイルが無ければ exit 1" 1 "$RC"
OUT=$(pk); RC=$?
expect_exit "指定が無ければ exit 2" 2 "$RC"

echo "[pack-context: --verify]"
OUT=$(pk --verify "$TMP/pack.md"); RC=$?
expect_exit "変わっていなければ exit 0" 0 "$RC"
expect_out  "2 件中 0 件と出す" "2 件中 0 件" "$OUT"
echo "追記" >> "$D/spec.md"
OUT=$(pk --verify "$TMP/pack.md"); RC=$?
expect_exit "元のファイルが変わると exit 1" 1 "$RC"
expect_out  "変わったファイルを出す" "変わった: spec.md" "$OUT"
rm "$D/plain.txt"
OUT=$(pk --verify "$TMP/pack.md"); RC=$?
expect_out  "消えたファイルを出す" "消えた: plain.txt" "$OUT"
printf '# 空\n' > "$TMP/empty-pack.md"
OUT=$(pk --verify "$TMP/empty-pack.md"); RC=$?
expect_exit "記録の無いパックは exit 1" 1 "$RC"
BEFORE=$(find "$D" "$KIT_DIR/02_共通/ツール" -newer "$TMP/pack.md" -type f | grep -v __pycache__ | sort)
pk "spec.md:目的" >/dev/null
AFTER=$(find "$D" "$KIT_DIR/02_共通/ツール" -newer "$TMP/pack.md" -type f | grep -v __pycache__ | sort)
[ "$BEFORE" = "$AFTER" ] && ok "-o なしではファイルを書かない" || ng "-o なしではファイルを書かない" "書かれた: $AFTER"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
