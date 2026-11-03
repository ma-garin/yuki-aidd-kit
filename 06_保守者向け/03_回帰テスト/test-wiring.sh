#!/bin/bash
# test-wiring.sh — gen-wiring.py（hook 配線を真実源 .claude-plugin/hooks.json から生成・照合）の回帰テスト
#   (a) 現リポジトリで --check が exit 0（W1・W2 が hooks.json と一致。W4 の不一致は WARN）
#   (b) hooks.json から 1 本消した一時コピーでは exit 1。W4 だけの不一致は exit 0・--strict なら exit 1
#   (c) 全経路で constitution-gate pre が PreToolUse の先頭、stop が Stop にある
# 稼働中の .claude/ には書かない（W4 の形は --target local の標準出力で確かめる）。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GEN="$KIT_DIR/00_導入/01_インストール/gen-wiring.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
export PYTHONDONTWRITEBYTECODE=1

echo "=== gen-wiring 回帰テスト ==="
echo "[(a) 現リポジトリ]"
OUT=$(python3 "$GEN" --check 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "--check が exit 0" || ng "--check が exit 0" "rc=$RC: $(printf '%s' "$OUT" | grep '欠落\|余分' | head -3 | tr '\n' ' ')"

echo "[(b) 真実源から 1 本消す]"
K="$TMP/kit"; mkdir -p "$K/00_導入/02_プロジェクト配布" "$K/03_ClaudeCode/hooks" "$K/.claude" "$K/.claude-plugin"
cp "$KIT_DIR/.claude-plugin/hooks.json" "$K/.claude-plugin/"
cp "$KIT_DIR/03_ClaudeCode/hooks/settings.json" "$K/03_ClaudeCode/hooks/"
cp "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" "$K/00_導入/02_プロジェクト配布/"
python3 "$GEN" --root "$K" --target local > "$TMP/w4gen.json" && mv "$TMP/w4gen.json" "$K/.claude/settings.json"
OUT=$(python3 "$GEN" --root "$K" --check 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "写し（W4 を生成形にした）は exit 0" || ng "写しは exit 0" "rc=$RC"
python3 "$GEN" --root "$K" --check --strict >/dev/null 2>&1; RC=$?
[ "$RC" -eq 0 ] && ok "写しは --strict でも exit 0" || ng "写しは --strict でも exit 0" "rc=$RC"
cp "$K/.claude/settings.json" "$TMP/w4keep.json"
python3 - "$K/.claude/settings.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8"))
d["hooks"]["PreCompact"] = []
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
OUT=$(python3 "$GEN" --root "$K" --check 2>&1); RC=$?
[ "$RC" -eq 0 ] && ok "W4 だけ不一致なら exit 0（WARN）" || ng "W4 だけ不一致なら exit 0" "rc=$RC"
printf '%s' "$OUT" | grep -q "WARN 欠落 | PreCompact" && ok "W4 の差は WARN として表に出る" || ng "W4 の差は WARN" "$(printf '%s' "$OUT" | tail -2)"
python3 "$GEN" --root "$K" --check --strict >/dev/null 2>&1; RC=$?
[ "$RC" -eq 1 ] && ok "W4 だけ不一致でも --strict なら exit 1" || ng "--strict なら exit 1" "rc=$RC"
mv "$TMP/w4keep.json" "$K/.claude/settings.json"
python3 - "$K/.claude-plugin/hooks.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p, encoding="utf-8"))
d["hooks"]["PreCompact"] = []
json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY
OUT=$(python3 "$GEN" --root "$K" --check 2>&1); RC=$?
[ "$RC" -eq 1 ] && ok "1 本消すと exit 1" || ng "1 本消すと exit 1" "rc=$RC"
printf '%s' "$OUT" | grep -q "NG 余分 | PreCompact | - | pre-compact.py" && ok "差の表に消えた hook が出る" || ng "差の表" "$(printf '%s' "$OUT" | head -5)"

echo "[(c) constitution-gate の位置]"
first_check() {  # $1=経路名 $2=JSON ファイル
  python3 - "$2" <<'PY'
import json, sys
h = json.load(open(sys.argv[1], encoding="utf-8"))["hooks"]
pre = h["PreToolUse"][0]["hooks"][0]["command"]
stop = [x["command"] for g in h.get("Stop", []) for x in g["hooks"]]
ok = "constitution-gate.py" in pre and " pre" in pre and "matcher" not in h["PreToolUse"][0]
ok = ok and any("constitution-gate.py" in c and " stop" in c for c in stop)
sys.exit(0 if ok else 1)
PY
}
python3 "$GEN" --target global --stdout > "$TMP/w1.json"
python3 "$GEN" --target project --stdout > "$TMP/w2.json"
python3 "$GEN" --target local > "$TMP/w4.json"
cp "$KIT_DIR/.claude-plugin/hooks.json" "$TMP/w3.json"
for w in w1 w2 w3 w4; do
  first_check "$w" "$TMP/$w.json" && ok "$w: pre が PreToolUse の先頭・stop が Stop にある" || ng "$w: constitution-gate の位置" "$TMP/$w.json"
done
# 生成物と実物が一致する（W1・W2 は再生成済みであること）
python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); sys.exit(0 if a==b else 1)' \
  "$TMP/w1.json" "$KIT_DIR/03_ClaudeCode/hooks/settings.json" && ok "W1 は生成結果と一致" || ng "W1 は生成結果と一致" "gen-wiring.py --target global を実行"
grep -c constitution-gate "$KIT_DIR/00_導入/02_プロジェクト配布/export-project.sh" | grep -qx '[2-9]' && ok "W2 に constitution-gate pre/stop" || ng "W2 に constitution-gate" "2 件未満"
python3 "$GEN" --target local >/dev/null && git -C "$KIT_DIR" diff --quiet -- .claude/settings.json && ok "--target local は .claude/settings.json を書かない" || ng "--target local は書かない" "差分あり"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
