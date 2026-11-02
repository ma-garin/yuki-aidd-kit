#!/bin/bash
# test-oracle-tools.sh — oracle-lint.py ・mutate-quick.py ・passk.py（AI が書いたテストを信じる前の 3 つの確認）の回帰テスト
#
# SUT は図書館の延滞判定（期限当日は貸出可・翌日は不可）。境目を確かめない弱いテストと、確かめる強いテストを mktemp に作る。
# 確かめること: 実装依存の期待値を NG・要求ID 無しと境界値漏れを WARN・正常なテストは指摘なし、
# 弱いテストは境界ミュータントを「見逃し」・強いテストは全検出、変異後に対象が元どおり、pass^k の全成功と一部失敗。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
T="$KIT_DIR/02_共通/ツール"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-240)"; }
expect_noout(){ printf '%s' "$3" | grep -qF -- "$2" && ng "$1" "出力に '$2' が出た" || ok "$1"; }

mkdir -p "$TMP/lib" "$TMP/bad" "$TMP/good"
cat > "$TMP/lib/library.py" <<'PY'
def can_borrow(days_after_due):
    """期限からの経過日数。当日（0）は貸出可、翌日（1）以降は不可。"""
    if days_after_due <= 0:
        return True
    return False
PY
cat > "$TMP/lib/test_weak.py" <<'PY'
from library import can_borrow
def test_r1_overdue():  # R1
    assert can_borrow(-3) is True
    assert can_borrow(5) is False
PY
cat > "$TMP/lib/test_strong.py" <<'PY'
from library import can_borrow
def test_r1_boundary():  # R1 期限当日は可・翌日は不可
    assert can_borrow(-1) is True
    assert can_borrow(0) is True
    assert can_borrow(1) is False
PY
cat > "$TMP/bad/test_oracle.py" <<'PY'
from library import can_borrow
def test_r2_same():  # R2
    assert can_borrow(3) == can_borrow(3)
PY
cat > "$TMP/bad/test_noreq.py" <<'PY'
from library import can_borrow
def test_overdue():
    days = 7
    assert days > 5
    assert can_borrow(days) is False
PY
cp "$TMP/lib/test_strong.py" "$TMP/good/test_ok.py"

echo "■ oracle-lint"
out=$(python3 "$T/oracle-lint.py" "$TMP/bad/test_oracle.py" 2>&1); rc=$?
expect_exit "期待値を SUT から作るテストは exit 1" 1 $rc
expect_out  "NG 実装依存の期待値を出す" "NG 実装依存の期待値" "$out"
out=$(python3 "$T/oracle-lint.py" "$TMP/bad/test_noreq.py" 2>&1); rc=$?
expect_out  "要求ID の無いテストを WARN" "WARN 要求IDが無い" "$out"
expect_out  "5 の前後が無い比較を WARN 境界値" "WARN 境界値が無い" "$out"
expect_exit "WARN だけなら exit 0" 0 $rc
out=$(python3 "$T/oracle-lint.py" "$TMP/good" 2>&1); rc=$?
expect_exit "正常なテストは exit 0" 0 $rc
expect_out  "正常なテストは指摘 0 件" "NG 0 / WARN 0" "$out"
python3 "$T/oracle-lint.py" "$TMP/bad/test_oracle.py" > "$TMP/bl.txt" 2>&1
python3 "$T/oracle-lint.py" "$TMP/bad/test_oracle.py" --baseline "$TMP/bl.txt" >/dev/null 2>&1
expect_exit "--baseline に載った NG は数えない" 0 $?

echo "■ mutate-quick"
cp "$TMP/lib/library.py" "$TMP/orig.py"
out=$(cd "$TMP/lib" && python3 "$T/mutate-quick.py" library.py --test "python3 -m pytest -q -p no:cacheprovider test_weak.py" --only boundary --timeout 30 2>&1); rc=$?
expect_out  "弱いテストは <= → < を見逃す" "3:<= → < → 見逃し" "$out"
expect_exit "見逃しありは exit 1" 1 $rc
cmp -s "$TMP/orig.py" "$TMP/lib/library.py" && ok "変異後に対象が元どおり" || ng "変異後に対象が元どおり" "差分あり"
out=$(cd "$TMP/lib" && python3 "$T/mutate-quick.py" library.py --test "python3 -m pytest -q -p no:cacheprovider test_strong.py" --timeout 30 2>&1); rc=$?
expect_out  "強いテストは境界ミュータントを検出" "3:<= → < → 検出" "$out"
expect_exit "強いテストは全検出で exit 0" 0 $rc
expect_out  "スコア行を出す" "ミューテーションスコア: 検出" "$out"
cmp -s "$TMP/orig.py" "$TMP/lib/library.py" && ok "全変異の後も元どおり" || ng "全変異の後も元どおり" "差分あり"

echo "■ passk"
out=$(python3 "$T/passk.py" -k 3 -- true 2>&1); rc=$?
expect_out  "全成功は pass^3 が 1.00" "pass^3: 1.00" "$out"
expect_exit "全成功は exit 0" 0 $rc
cat > "$TMP/flip.sh" <<SH
#!/bin/bash
n=\$(cat "$TMP/cnt" 2>/dev/null || echo 0); n=\$((n+1)); echo \$n > "$TMP/cnt"
r=\$([ \$((n % 2)) -eq 0 ] && echo '<failure/>' || echo '')
echo "<testsuite><testcase classname=\"c\" name=\"flaky\">\$r</testcase><testcase classname=\"c\" name=\"stable\"/></testsuite>" > "$TMP/junit.xml"
[ -z "\$r" ]
SH
chmod +x "$TMP/flip.sh"
out=$(python3 "$T/passk.py" -k 4 --junit "$TMP/junit.xml" -- "$TMP/flip.sh" 2>&1); rc=$?
expect_out  "一部失敗は pass@4 が 1.00" "pass@4: 1.00" "$out"
expect_out  "一部失敗は pass^4 が 0.00" "pass^4: 0.00" "$out"
expect_exit "一部失敗は exit 1" 1 $rc
expect_out  "揺れたテストを JUnit から一覧" "c::flaky: 合格 2 / 不合格 2" "$out"
expect_noout "揺れていないテストは出さない" "c::stable" "$out"

echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
