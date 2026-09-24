#!/bin/bash
# test-pw-spec-lint.sh — pw-spec-lint.py（生成テストの locator 規約と静的検査。B29）の回帰テスト
#
# Playwright は入れない。合成の spec ファイルで、NG 5 種（固定待ち・sleep・.only・理由の無い skip・旧 API）、
# WARN 3 種（CSS/XPath/nth・弱いアサーション・spec: の ID 無し）、正当な書き方は 0 件、--json、exit 0/1/2 を確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TOOL="$KIT_DIR/02_共通/ツール/pw-spec-lint.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }
lint() { python3 "$TOOL" "$@" 2>&1; }
# --json の結果から、TS のファイル（cart.spec.ts）の規則 rule・行 line の件数を数える（line 0 はファイル単位。全ファイルなら 5 番目に ""）
count() { python3 -c 'import json,sys
d=json.loads(sys.argv[1]); lv, rule, line = sys.argv[2], sys.argv[3], int(sys.argv[4])
suf = sys.argv[5] if len(sys.argv) > 5 else ".spec.ts"
print(sum(1 for x in d[lv] if x["rule"] == rule and x["line"] == line and x["file"].endswith(suf)))' "$@"; }

echo "=== pw-spec-lint.py 回帰テスト ==="

G="$TMP/good"; mkdir -p "$G/e2e"
cat > "$G/e2e/login.spec.ts" <<'EOF'
// spec: ST-001, ST-002
import { test, expect } from '@playwright/test';
test.describe('ログイン', () => {
  test('正しいパスワードで入れる', async ({ page, browserName }) => {
    test.skip(browserName === 'webkit', 'WebKit は既知の不具合 #12 のため対象外');
    await page.goto('/login');
    await page.getByLabel('メールアドレス').fill('user@example.com');
    await page.getByRole('button', { name: 'ログイン' }).click();
    await expect(page.getByText('ようこそ')).toBeVisible();
    await expect(page.getByTestId('cart-count')).toHaveText('0');
    await page.locator('form >> text=送信').click();   // 複合の CSS は WARN にしない（#id・.class・タグ名だけのときだけ）
    // page.waitForTimeout(1000) や test.only( はコメントの中なら数えない
    const note = 'page.waitForTimeout(5) は文字列の中なら数えない';
  });
  // 決済の検証環境が 2026-10 まで止まっているため
  test.fixme('決済できる', async ({ page }) => {
    await page.goto('/pay');
  });
});
EOF
cat > "$G/e2e/test_smoke.py" <<'EOF'
"""spec: ST-003 — page.wait_for_timeout( は docstring の中なら数えない"""
from playwright.sync_api import Page, expect


def test_top(page: Page):
    page.goto("/")
    expect(page.get_by_role("heading", name="トップ")).to_be_visible()


@pytest.mark.skip(reason="印刷機能は次版で実装する")
def test_print(page: Page):
    page.goto("/print")
EOF
echo "[正当な書き方は NG・WARN とも 0]"
OUT=$(lint "$G/e2e"); RC=$?
expect_exit "正当な書き方だけなら exit 0" 0 "$RC"
expect_out  "NG=0 / WARN=0" "NG=0 / WARN=0" "$OUT"
expect_out  "対象 2 ファイル（TS と Playwright を使う Python）" "（2 ファイル）" "$OUT"
expect_out  "locator の内訳を修復順で出す" "getByRole 2 / getByLabel 1 / getByText 1 / getByTestId 1 / CSS/XPath 1" "$OUT"

B="$TMP/bad"; mkdir -p "$B/e2e/node_modules/pkg"
cat > "$B/e2e/cart.spec.ts" <<'EOF'
import { test, expect } from '@playwright/test';
test('カートに追加できる', async ({ page }) => {
  await page.waitForTimeout(1000);
  await sleep(500);
  await new Promise(r => setTimeout(r, 300));
  test.skip();
  const el = await page.$('#add');
  const all = await page.$$('.item');
  await page.locator('#add').click();
  await page.locator('xpath=//div[@id="x"]').click();
  await page.locator('li').nth(2).click();
  expect(await page.getByText('追加しました').isVisible()).toBeTruthy();
  await expect(page.getByRole('status')).not.toBeNull();
});
test.only('だけ走る', async ({ page }) => {});
test.skip('理由の無い宣言の skip', async ({ page }) => {});
EOF
echo 'await page.waitForTimeout(1)' > "$B/e2e/node_modules/pkg/x.spec.ts"
cat > "$B/e2e/test_bad.py" <<'EOF'
import time
from playwright.sync_api import Page


@pytest.mark.skip
def test_a(page: Page):
    time.sleep(1)
    page.wait_for_timeout(100)
    el = page.query_selector("#a")
    assert page.locator("#a").is_visible()
    pytest.skip()
EOF
echo "[NG 5 種・WARN 3 種]"
OUT=$(lint "$B/e2e"); RC=$?
expect_exit "NG があれば exit 1" 1 "$RC"
J=$(lint "$B/e2e" --json); RC=$?
expect_exit "--json でも NG があれば exit 1" 1 "$RC"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["files"] == 2 and d["summary"]["ng"] == len(d["ng"])' "$J" 2>/dev/null \
  && ok "--json が読める（files・summary・ng・warn）・node_modules を見ない（2 ファイル）" || ng "--json の形" "$(printf '%s' "$J" | head -c 200)"
[ "$(count "$J" ng fixed-wait 3)" -eq 1 ] && ok "NG 固定待ち: page.waitForTimeout(" || ng "NG 固定待ち" "3 行目で検出されない"
[ "$(count "$J" ng sleep 4)" -eq 1 ] && ok "NG sleep: sleep(" || ng "NG sleep" "4 行目"
[ "$(count "$J" ng sleep 5)" -eq 1 ] && ok "NG sleep: new Promise(… setTimeout(…) の手書きの待ち" || ng "NG setTimeout の待ち" "5 行目"
[ "$(count "$J" ng skip-no-reason 6)" -eq 1 ] && ok "NG 理由の無い skip: test.skip()" || ng "NG 理由の無い skip()" "6 行目"
[ "$(count "$J" ng legacy-api 7)" -eq 1 ] && ok "NG 旧 API: page.\$(" || ng "NG 旧 API \$(" "7 行目"
[ "$(count "$J" ng legacy-api 8)" -eq 1 ] && ok "NG 旧 API: page.\$\$(" || ng "NG 旧 API \$\$(" "8 行目"
[ "$(count "$J" ng only 15)" -eq 1 ] && ok "NG .only: test.only(" || ng "NG .only" "15 行目"
[ "$(count "$J" ng skip-no-reason 16)" -eq 1 ] && ok "NG 理由の無い skip: test.skip('題名', …) の宣言" || ng "NG 宣言の skip" "16 行目"
[ "$(count "$J" warn css-xpath-nth 9)" -eq 1 ] && ok "WARN CSS: locator('#add')（#id だけ）" || ng "WARN CSS #id" "9 行目"
[ "$(count "$J" warn css-xpath-nth 10)" -eq 1 ] && ok "WARN XPath: xpath=" || ng "WARN XPath" "10 行目"
[ "$(count "$J" warn css-xpath-nth 11)" -eq 1 ] && ok "WARN タグ名だけ＋nth(" || ng "WARN nth" "11 行目"
[ "$(count "$J" warn weak-assert 12)" -eq 1 ] && ok "WARN 弱いアサーション: toBeTruthy()" || ng "WARN toBeTruthy" "12 行目"
[ "$(count "$J" warn weak-assert 13)" -eq 1 ] && ok "WARN 弱いアサーション: not.toBeNull()" || ng "WARN not.toBeNull" "13 行目"
[ "$(count "$J" warn no-spec-id 0 "")" -eq 2 ] && ok "WARN spec: の ID が無いファイル（2 本とも）" || ng "WARN spec ID 無し" "$(count "$J" warn no-spec-id 0 "") 件"
echo "[Python（pytest-playwright）も同じ規則]"
PY=$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(" ".join(sorted({x["rule"] for x in d["ng"] + d["warn"] if x["file"].endswith(".py")})))' "$J")
for r in skip-no-reason sleep fixed-wait legacy-api css-xpath-nth weak-assert no-spec-id; do
  case " $PY " in *" $r "*) ok "Python: $r を検出" ;; *) ng "Python: $r を検出" "検出した規則: $PY" ;; esac
done
[ "$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(sum(1 for x in d["ng"] if x["file"].endswith(".py") and x["rule"]=="skip-no-reason"))' "$J")" -eq 2 ] \
  && ok "Python: reason の無い @pytest.mark.skip と引数の無い pytest.skip() の 2 件" || ng "Python の skip" "2 件でない"
echo "[表示]"
expect_out  "テキスト出力に NG の件数（TS 8・Python 5）" "NG=13 / WARN=9" "$OUT"
expect_out  "WARN に修復順（getByRole → getByLabel → getByText → getByTestId → CSS）を出す" "getByRole → getByLabel → getByText → getByTestId → CSS" "$OUT"
expect_noout "node_modules の中は見ない" "node_modules" "$OUT"

echo "[理由のコメントで skip を許す・コメントと文字列は照合しない]"
S="$TMP/skip"; mkdir -p "$S"
cat > "$S/a.spec.ts" <<'EOF'
// spec: ST-010
test('a', async () => {
  test.skip(); // 外部 API の契約が未確定のため
});
/*
 * await page.waitForTimeout(1000) ── ブロックコメントの中は数えない
 */
EOF
OUT=$(lint "$S"); RC=$?
expect_exit "同じ行の理由コメント付き skip・ブロックコメントの中の固定待ちは exit 0" 0 "$RC"

echo "[入力の誤り]"
OUT=$(lint "$TMP/nothing"); RC=$?
expect_exit "パスが無ければ exit 2" 2 "$RC"
mkdir -p "$TMP/empty"; echo 'x' > "$TMP/empty/readme.md"
OUT=$(lint "$TMP/empty"); RC=$?
expect_exit "テストファイルが 0 本なら exit 2（判定不能）" 2 "$RC"
expect_out  "0 本は判定不能と出す" "判定不能" "$OUT"
OUT=$(lint "$B/e2e/cart.spec.ts"); RC=$?
expect_exit "ファイル 1 本を渡しても検査する（exit 1）" 1 "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
