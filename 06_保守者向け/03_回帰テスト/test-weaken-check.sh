#!/bin/bash
# test-weaken-check.sh — test-weaken-check.py（テストの弱体化の検知。B38）の回帰テスト
#
# 一時 git リポジトリで、assert の削除・書き換え、skip/only の追加、弱いアサーションへの置換、retries の増加を NG にし、
# weaken-ok: <理由（8 字以上）> で許可できること、テスト以外のファイルは対象外であること、--staged・--base・既定の差分、
# 判定不能（git でない・rev が無い）を exit 2 にすることを確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$KIT_DIR/02_共通/ツール/test-weaken-check.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
export GIT_AUTHOR_NAME=T GIT_AUTHOR_EMAIL=t@example.com GIT_COMMITTER_NAME=T GIT_COMMITTER_EMAIL=t@example.com
R="$TMP/repo"
chk() { python3 "$TOOL" --root "$R" "$@" 2>&1; }
g() { git -C "$R" "$@"; }
# 置換: ファイル 旧 新（Python で行う。sed の方言差を避ける）
subst() { python3 -c 'import sys; p,o,n=sys.argv[1:4]; s=open(p).read(); assert o in s, o; open(p,"w").write(s.replace(o,n,1))' "$@"; }
fresh() {   # 基準のコミットを作り直す
  rm -rf "$R"; mkdir -p "$R/e2e" "$R/tests" "$R/src"; g init -q -b main
  cat > "$R/e2e/cart.spec.ts" <<'EOF'
// spec: ST-001
import { test, expect } from '@playwright/test';
test('カートに追加できる', async ({ page }) => {
  await page.goto('/cart');
  await page.getByRole('button', { name: '追加' }).click();
  await expect(page.getByTestId('cart-count')).toHaveText('1');
  expect(total).toBe(1200);
});
test('retries 3 times on network error', async ({ page }) => {
  await page.goto('/retry');
});
EOF
  cat > "$R/tests/test_price.py" <<'EOF'
from app import price


def test_price():
    assert price(100) == 110
    assert price(0) == 0
EOF
  printf 'def price(x):\n    assert x >= 0\n    return int(x * 1.1)\n' > "$R/src/app.py"
  printf 'import { defineConfig } from "@playwright/test";\nexport default defineConfig({\n  retries: 0,\n});\n' > "$R/playwright.config.ts"
  printf 'test("old", () => { expect(1).toBe(1); });\n' > "$R/e2e/old.spec.ts"
  g add -A && g commit -qm base
}

echo "=== test-weaken-check.py 回帰テスト ==="

echo "[変更なし・テストを足すだけは通る]"
fresh
OUT=$(chk --staged); RC=$?
expect_exit "staged が空なら exit 0" 0 "$RC"
printf 'test("new", async ({ page }) => {\n  await expect(page.getByText("ok")).toBeVisible();\n});\n' >> "$R/e2e/cart.spec.ts"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "アサーションを足すだけなら exit 0" 0 "$RC"
expect_out  "NG=0 と出す" "NG=0" "$OUT"

echo "[NG: アサーションの削除・書き換え]"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" ""
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "assert（expect）の削除は exit 1" 1 "$RC"
expect_out  "削除を NG に出す（ファイルと行）" "アサーションの削除・書き換え: e2e/cart.spec.ts:7" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "toBe(1200)" "toBe(1000)"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "期待値の書き換えも exit 1（理由が要る）" 1 "$RC"
fresh
subst "$R/tests/test_price.py" "    assert price(0) == 0
" ""
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "Python の assert 文の削除は exit 1" 1 "$RC"
expect_out  "Python のテストファイル（test_*.py）も対象" "tests/test_price.py" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);" "  // expect(total).toBe(1200);"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "アサーションのコメントアウトは exit 1" 1 "$RC"

echo "[NG: 弱いアサーションへの置換・skip/only の追加・retries の増加・ファイルの削除]"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);" "  expect(total).toBeTruthy();"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "toBeTruthy() への置換は exit 1" 1 "$RC"
expect_out  "弱いアサーションへの置換として出す" "弱いアサーションへの置換" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "test('カートに追加できる'" "test.skip('カートに追加できる'"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "test.skip( の追加は exit 1" 1 "$RC"
expect_out  "skip の追加として出す" "skip・only の追加: e2e/cart.spec.ts:3" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "test('retries 3 times" "test.only('retries 3 times"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "test.only( の追加は exit 1" 1 "$RC"
expect_noout "テスト名の「retries 3 times」を retries の設定と取り違えない" "retries の増加" "$OUT"
fresh
subst "$R/tests/test_price.py" "def test_price():" "@pytest.mark.skip(reason=\"later\")
def test_price():"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "@pytest.mark.skip の追加は exit 1" 1 "$RC"
fresh
subst "$R/playwright.config.ts" "retries: 0," "retries: process.env.CI ? 3 : 0,"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "playwright.config.ts の retries の増加は exit 1" 1 "$RC"
expect_out  "増加の前後を出す" "retries の増加（0 → 3）" "$OUT"
fresh
subst "$R/playwright.config.ts" "retries: 0," "retries: 0, // 変えない"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "retries が増えない書き換えは exit 0" 0 "$RC"
fresh
g rm -q e2e/old.spec.ts
OUT=$(chk --staged); RC=$?
expect_exit "テストファイルの削除は exit 1" 1 "$RC"
expect_out  "削除をファイル単位で出す" "テストファイルの削除（アサーション 1 件）: e2e/old.spec.ts" "$OUT"

echo "[weaken-ok: <理由> で許可]"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" "  // weaken-ok: 合計の表示は仕様変更 REQ-F-012 で廃止した
"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "近く（±3 行）に理由 8 字以上の weaken-ok があれば exit 0" 0 "$RC"
expect_out  "許可した件と理由を出す" "許可 アサーションの削除・書き換え: e2e/cart.spec.ts:7 — weaken-ok: 合計の表示は仕様変更 REQ-F-012 で廃止した" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" "  // weaken-ok: 廃止
"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "理由が 8 字未満の weaken-ok では許可しない（exit 1）" 1 "$RC"
expect_out  "理由が短い旨を出す" "8 字未満" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "test('retries 3 times" "// weaken-ok: 合計の表示は仕様変更 REQ-F-012 で廃止した
test('retries 3 times"
g add -A && g commit -qm "前からある weaken-ok"
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" ""
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "前からあった weaken-ok（この差分で足していない）では許可しない" 1 "$RC"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" ""
printf '\n\n\n\n\n// weaken-ok: 遠すぎる位置に書いた理由の説明文\n' >> "$R/e2e/cart.spec.ts"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "±3 行より遠い weaken-ok では許可しない" 1 "$RC"
fresh
g rm -q e2e/old.spec.ts
printf '// weaken-ok: old.spec.ts は機能 X の廃止（REQ-F-009）で不要\n' >> "$R/e2e/cart.spec.ts"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "テストファイルの削除は、差分のどこかの weaken-ok: <ファイル名> <理由> で許可" 0 "$RC"

echo "[対象外: テスト以外のファイル・移動]"
fresh
subst "$R/src/app.py" "    assert x >= 0
" ""
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "テスト以外のファイル（src/app.py）の assert 削除は対象外（exit 0）" 0 "$RC"
fresh
python3 - "$R/tests/test_price.py" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
s = s.replace("    assert price(100) == 110\n    assert price(0) == 0\n", "    assert price(0) == 0\n    assert price(100) == 110\n")
open(p, "w").write(s)
PY
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "アサーションの並べ替え（同じ行の移動）は exit 0" 0 "$RC"

echo "[--base・既定の差分・--json・判定不能]"
fresh
g checkout -q -b feature
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" ""
g add -A && g commit -qm "assert を消す"
OUT=$(chk --staged); RC=$?
expect_exit "コミット済みの弱体化は --staged には出ない（exit 0）" 0 "$RC"
OUT=$(chk --base main); RC=$?
expect_exit "--base main は分岐点からの弱体化を拾う（exit 1）" 1 "$RC"
expect_out  "--base の分岐点を表示する" "--base main（分岐点" "$OUT"
g checkout -q main
printf 'test("main 側で足した", () => { expect(2).toBe(2); });\n' > "$R/e2e/main.spec.ts"
g add -A && g commit -qm "main 側"
g checkout -q feature
OUT=$(chk --base main); RC=$?
expect_noout "main 側で後から足したテストを「削除」と取り違えない（分岐点と比べる）" "main.spec.ts" "$OUT"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);
" ""
OUT=$(chk); RC=$?
expect_exit "既定（HEAD から作業ツリー）は未 stage の弱体化も拾う（exit 1）" 1 "$RC"
OUT=$(chk --json); RC=$?
expect_exit "--json でも exit 1" 1 "$RC"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["summary"]["ng"]==1 and d["ng"][0]["file"]=="e2e/cart.spec.ts" and d["ng"][0]["line"]==7' "$OUT" 2>/dev/null \
  && ok "--json が読める（summary・ng の file・line）" || ng "--json の形" "$(printf '%s' "$OUT" | head -c 200)"
OUT=$(chk --base no-such-branch); RC=$?
expect_exit "存在しない --base は判定不能（exit 2）" 2 "$RC"
mkdir -p "$TMP/notgit"
OUT=$(python3 "$TOOL" --root "$TMP/notgit" --staged 2>&1); RC=$?
expect_exit "git リポジトリでなければ判定不能（exit 2）" 2 "$RC"
expect_out  "判定不能を合格に数えない旨を出す" "合格に数えない" "$OUT"

echo "[差し戻し: 複数行のアサーション・無効化する文・テストファイルの判定]"
mfresh() {   # 複数行の toMatchObject を持つ基準
  fresh
  printf '%s\n' "test('obj', async () => {" "  const r = load();" "  expect(r).toMatchObject({" "    x: 1," "    y: 2," "  });" "  done();" "});" > "$R/e2e/obj.spec.ts"
  g add -A && g commit -qm obj
}
mfresh
subst "$R/e2e/obj.spec.ts" "    y: 2," "    y: 3,"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "複数行の期待値の書き換え（y: 2 → 3）は exit 1" 1 "$RC"
expect_out  "複数行のアサーションの内側として出す" "複数行の期待値" "$OUT"
mfresh
subst "$R/e2e/obj.spec.ts" "  done();" "  done(); // 後片付け"
subst "$R/e2e/obj.spec.ts" "  const r = load();" "  const r = load('v2');"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "複数行のアサーションの外の行の書き換えは exit 0" 0 "$RC"
mfresh
subst "$R/e2e/obj.spec.ts" "    y: 2,
" "    // weaken-ok: y は仕様変更 REQ-F-020 で返さなくなった
"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "複数行の期待値の削除も weaken-ok: <理由> で許可（exit 0）" 0 "$RC"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);" "  if (flag) {
    expect(total).toBe(1200);
  }"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "条件の if (flag) で包むのは無効化の語に当たらない（exit 0）" 0 "$RC"
fresh
subst "$R/e2e/cart.spec.ts" "  expect(total).toBe(1200);" "  expect.soft(total).toBe(1200);"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "expect.soft( への置換は exit 1" 1 "$RC"
expect_out  "無効化する文の追加として出す" "アサーションを無効化する文の追加" "$OUT"
fresh
subst "$R/tests/test_price.py" "    assert price(100) == 110" "    pytest.xfail('later')
    assert price(100) == 110"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "pytest.xfail( の追加は exit 1" 1 "$RC"
fresh
printf 'def check(x):\n    assert x > 0\n' > "$R/tests/helpers.py"
g add -A && g commit -qm helpers
printf 'def check(x):\n    return x\n' > "$R/tests/helpers.py"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "tests/ 配下の .py（test_ で始まらない）も対象（exit 1）" 1 "$RC"
fresh
printf 'def f():\n    return 1\n\n\ndef g():\n    return\n' > "$R/src/app.py"
g add -A
OUT=$(chk --staged); RC=$?
expect_exit "テスト以外のファイルの return 単独は対象外（exit 0）" 0 "$RC"

echo ""
echo "[検証: 塊L]"
# 1 件ずつ一時リポジトリで: 基準をコミット → 書き換えて stage → --staged の exit を見る
VL="$TMP/vl"
vcase() {   # 名前 期待exit ファイル 旧 新
  rm -rf "$VL"; mkdir -p "$VL/$(dirname "$3")"; git -C "$VL" init -q
  printf '%s\n' "$4" > "$VL/$3"; git -C "$VL" add -A; git -C "$VL" commit -qm base
  printf '%s\n' "$5" > "$VL/$3"; git -C "$VL" add -A
  OUT=$(python3 "$TOOL" --root "$VL" --staged 2>&1); RC=$?
  expect_exit "$1" "$2" "$RC"
}
VB='test("a", async () => {
  const a = 1;
  expect(a).toBe(1);
  expect(a).toBe(2);
  const b = 2;
});'
# 正当（通る）
vcase "移動: 同じ assert を別の行へ（通る）" 0 e2e/a.spec.ts "$VB" 'test("a", async () => {
  expect(a).toBe(2);
  const a = 1;
  expect(a).toBe(1);
  const b = 2;
});'
# バイパス（止まるべき）
vcase "if (false) { を別の行に足して assert を包む（NG）" 1 e2e/a.spec.ts "$VB" 'test("a", async () => {
  const a = 1;
  if (false) {
    expect(a).toBe(1);
    expect(a).toBe(2);
  }
  const b = 2;
});'
vcase "assert の前に return; を足す（NG）" 1 e2e/a.spec.ts "$VB" 'test("a", async () => {
  const a = 1;
  return;
  expect(a).toBe(1);
  expect(a).toBe(2);
  const b = 2;
});'
vcase "test.fail() を足す（失敗を期待に反転。NG）" 1 e2e/a.spec.ts "$VB" 'test("a", async () => {
  test.fail();
  const a = 1;
  expect(a).toBe(1);
  expect(a).toBe(2);
  const b = 2;
});'
vcase "@pytest.mark.xfail を足す（NG）" 1 tests/test_a.py 'def test_a():
    assert f() == 1' '@pytest.mark.xfail
def test_a():
    assert f() == 1'
vcase "複数行の期待値から項目を消す（toMatchObject の y: 2。NG）" 1 e2e/a.spec.ts 'test("a", () => {
  expect(r).toMatchObject({
    x: 1,
    y: 2,
  });
});' 'test("a", () => {
  expect(r).toMatchObject({
    x: 1,
  });
});'
vcase "同じ assert 2 行を 1 行に減らす（件数を見ない。NG）" 1 e2e/a.spec.ts 'test("a", () => {
  expect(ok()).toBe(true);
  go();
  expect(ok()).toBe(true);
});' 'test("a", () => {
  go();
  expect(ok()).toBe(true);
});'
vcase "__tests__/ 配下（Jest の既定）の assert 削除（NG）" 1 __tests__/cart.js 'test("a", () => { expect(1).toBe(1); });' 'test("a", () => {});'
# rename は git mv で作る（上の vcase は同名のため、ここで別名にする）
rm -rf "$VL"; mkdir -p "$VL/e2e"; git -C "$VL" init -q; printf '%s\n' "$VB" > "$VL/e2e/a.spec.ts"; git -C "$VL" add -A; git -C "$VL" commit -qm base
git -C "$VL" mv e2e/a.spec.ts e2e/b.spec.ts
OUT=$(python3 "$TOOL" --root "$VL" --staged 2>&1); RC=$?
expect_exit "git mv で別名にしただけは通る（--staged）" 0 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
