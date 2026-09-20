#!/bin/bash
# test-json-envelope.sh — 検査スクリプトの --json（エージェント向け出力契約）の回帰テスト
# 対象: check_docs.py / check_approval.py / check_design.py / quality_harness.py / test_metrics.py / floor-guard.py
# 契約: 1 行の JSON {"ok", "exit", "data", "meta", "error": {"type", "message", "hint", "retry_argv"}}。
# 出所: WeKnora CLI の AGENTS.md「エラー文は AI の判断入力になる」。hint は次の一手、retry_argv は直した後の再実行。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
# 出力が 1 行の JSON で、期待するキー/値を持つか
# 使い方: check "<名前>" "<JSON>" ok=<true|false> exit=<n> [type=<error.type>] [hint] [retry] [data=<key>]
CHECK_PY="$TMP/check.py"
cat > "$CHECK_PY" <<'PY'
import json, sys
raw = sys.stdin.read().strip()
lines = [l for l in raw.splitlines() if l.strip()]
if len(lines) != 1:
    print(f"JSON が 1 行でない（{len(lines)} 行）"); sys.exit(1)
try:
    d = json.loads(lines[0])
except ValueError as e:
    print(f"JSON でない: {e}"); sys.exit(1)
for k in ("ok", "exit", "data", "meta"):
    if k not in d:
        print(f"キー {k} が無い"); sys.exit(1)
for cond in sys.argv[1:]:
    if cond == "hint":
        if not d.get("error", {}).get("hint"): print("error.hint が空"); sys.exit(1)
    elif cond == "retry":
        if not isinstance(d.get("error", {}).get("retry_argv"), list) or not d["error"]["retry_argv"]: print("error.retry_argv が無い"); sys.exit(1)
    else:
        k, v = cond.split("=", 1)
        if k == "ok":
            if d["ok"] != (v == "true"): print(f"ok={d['ok']} 期待 {v}"); sys.exit(1)
        elif k == "exit":
            if d["exit"] != int(v): print(f"exit={d['exit']} 期待 {v}"); sys.exit(1)
        elif k == "type":
            if d.get("error", {}).get("type") != v: print(f"error.type={d.get('error', {}).get('type')} 期待 {v}"); sys.exit(1)
        elif k == "data":
            if v not in d["data"]: print(f"data.{v} が無い"); sys.exit(1)
if d["ok"] and "error" in d: print("ok なのに error がある"); sys.exit(1)
if not d["ok"] and "error" not in d: print("ok=false なのに error が無い"); sys.exit(1)
print("ok")
PY
check() {
  local name="$1" out="$2"; shift 2
  local res
  res=$(printf '%s' "$out" | python3 "$CHECK_PY" "$@")
  if [ "$res" = "ok" ]; then ok "$name"; else ng "$name" "$res"; fi
}

echo "=== --json 出力契約 回帰テスト ==="
unset CHECK_DOCS_TEST_TOTALS   # check_docs は --skip-tests で回す（実テストは再実行しない）

echo "[check_docs.py]"
OUT=$(python3 "$KIT_DIR/scripts/check_docs.py" --root "$KIT_DIR" --skip-tests --json -o "$TMP/r.md" 2>/dev/null)
check "リポジトリ自身: ok=true exit=0、data に ng/warn/report" "$OUT" ok=true exit=0 data=ng data=report
C="$TMP/copy"; mkdir -p "$C"; (cd "$KIT_DIR" && tar --exclude=.git -cf - INDEX.md README.md skills rules claude-code scripts templates spec docs AGENTS.md.template CLAUDE.md.template VERSION) | tar -xf - -C "$C"
sed -i '/^| `retro` |/d' "$C/INDEX.md"
OUT=$(python3 "$KIT_DIR/scripts/check_docs.py" --root "$C" --skip-tests --json -o "$TMP/r.md" 2>/dev/null)
check "掲載漏れ: ok=false exit=1 type=docs.inconsistent、hint と retry_argv がある" "$OUT" ok=false exit=1 type=docs.inconsistent hint retry

echo "[check_approval.py]"
OUT=$(python3 "$KIT_DIR/scripts/check_approval.py" --root "$TMP" --json 2>/dev/null)
check "工程文書が無ければ ok=true exit=0（スキップ）" "$OUT" ok=true exit=0
mkdir -p "$TMP/appr/docs/lifecycle"
OUT=$(python3 "$KIT_DIR/scripts/check_approval.py" --root "$TMP/appr" --phase 99 --json 2>/dev/null)
check "工程番号が範囲外: ok=false exit=2 type=approval.undetermined" "$OUT" ok=false exit=2 type=approval.undetermined hint

echo "[check_design.py]"
D="$TMP/design"; mkdir -p "$D"; cp "$KIT_DIR/templates/tokens.css" "$D/"
printf '@import url("tokens.css");\n.x { color: var(--color-text); }\n' > "$D/ok.css"
OUT=$(python3 "$KIT_DIR/scripts/check_design.py" --root "$D" --tokens tokens.css --json -o "$TMP/d.md" ok.css 2>/dev/null)
check "直値なし: ok=true exit=0" "$OUT" ok=true exit=0 data=ng
printf '@import url("tokens.css");\n.x { color: #ff0000; }\n' > "$D/bad.css"
OUT=$(python3 "$KIT_DIR/scripts/check_design.py" --root "$D" --tokens tokens.css --json -o "$TMP/d.md" bad.css 2>/dev/null)
check "直値あり: ok=false exit=1 type=design.literal_values" "$OUT" ok=false exit=1 type=design.literal_values hint retry

echo "[quality_harness.py]"
Q="$TMP/q"; mkdir -p "$Q/.claude/rules"; cp "$KIT_DIR/rules/functional-integrity.md" "$Q/.claude/rules/"; bash "$KIT_DIR/scripts/init-test-docs.sh" "$Q" >/dev/null 2>&1
OUT=$(python3 "$KIT_DIR/scripts/quality_harness.py" --root "$Q" --json 2>/dev/null)
check "雛形直後: ok=true exit=0、data.errors が空" "$OUT" ok=true exit=0 data=errors
OUT=$(python3 "$KIT_DIR/scripts/quality_harness.py" --root "$TMP" --json 2>/dev/null)
check "契約が無い: ok=false exit=1 type=contract.failed" "$OUT" ok=false exit=1 type=contract.failed hint retry

echo "[test_metrics.py]"
OUT=$(python3 "$KIT_DIR/scripts/test_metrics.py" --root "$TMP" --json -o "$TMP/m.md" 2>/dev/null)
check "記録なし（status）: ok=true exit=0" "$OUT" ok=true exit=0
OUT=$(python3 "$KIT_DIR/scripts/test_metrics.py" --root "$TMP" --gate --json -o "$TMP/m.md" 2>/dev/null)
check "記録なし（--gate）: ok=false exit=2 type=gate.undetermined" "$OUT" ok=false exit=2 type=gate.undetermined hint retry

echo "[floor-guard.py --check]"
G="$TMP/g"; mkdir -p "$G/tests"; printf 'def test_a():\n    assert 1\n' > "$G/tests/test_a.py"
(cd "$G" && git init -q && git -c user.name=t -c user.email=t@t add -A && git -c user.name=t -c user.email=t@t commit -q -m i)
OUT=$(python3 "$KIT_DIR/claude-code/hooks/floor-guard.py" --check --root "$G" --json)
check "差分なし: ok=true exit=0、data.findings が空" "$OUT" ok=true exit=0 data=findings
printf 'import pytest\n@pytest.mark.skip\ndef test_b():\n    assert 1\n' >> "$G/tests/test_a.py"
OUT=$(python3 "$KIT_DIR/claude-code/hooks/floor-guard.py" --check --root "$G" --json)
check "skip 追加: ok=false exit=1 type=floor.lowered" "$OUT" ok=false exit=1 type=floor.lowered hint retry
OUT=$(python3 "$KIT_DIR/claude-code/hooks/floor-guard.py" --check --root "$TMP" --json)
check "git の外: ok=false exit=2 type=floor.undetermined" "$OUT" ok=false exit=2 type=floor.undetermined

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
