#!/bin/bash
# test-token-audit.sh — token-audit.sh（token_audit.py）の回帰テスト
# 「キット自身が NG=0 で通ること」と「配線漏れ・床の超過・MCP 過多を検出できること」を確認する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_exit() { [ "$2" -eq "$3" ] && ok "$1" || ng "$1" "期待 exit=$2 / 実際 exit=$3"; }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: $(printf '%s' "$3" | tr '\n' ' ' | cut -c1-160)"; }
run() { HOME="$TMP/nohome" python3 "$KIT_DIR/00_導入/token_audit.py" --root "$1" -o "$TMP/report.md" 2>&1; }

echo "=== token-audit.sh 回帰テスト ==="

echo "[ケース1: キット自身]"
OUT=$(run "$KIT_DIR"); RC=$?
expect_exit "キット自身は exit 0" 0 "$RC"
expect_out  "床の推定 tok を出す" "床（常時読み込み・推定）≒" "$OUT"
expect_out  "配線済みの結論" "NG=0" "$OUT"
grep -q "手元でしか測れないもの" "$TMP/report.md" && ok "レポートに /context /usage /doctor の案内" || ng "レポートに /context /usage /doctor の案内" "無い"

echo "[ケース2: 配布先（export-project.sh 直後）]"
P="$TMP/proj"; mkdir -p "$P"; bash "$KIT_DIR/00_導入/export-project.sh" "$P" >/dev/null 2>&1
OUT=$(run "$P"); RC=$?
expect_exit "配布直後も exit 0（.claude/settings.json と .claude/rules を見る）" 0 "$RC"
grep -q "settings: .*\.claude/settings.json" "$TMP/report.md" && ok "配布先の .claude/settings.json を読む（レポートに明記）" || ng "配布先の .claude/settings.json を読む" "$(grep 'settings:' "$TMP/report.md")"

echo "[ケース3: 配線漏れ]"
python3 - "$P/.claude/settings.json" <<'PY'
import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.pop("effortLevel",None)
for grp in d["hooks"]["PreToolUse"]:
    grp["hooks"]=[h for h in grp["hooks"] if "filter-output" not in h["command"]]
json.dump(d,open(p,"w"),ensure_ascii=False,indent=2)
PY
OUT=$(run "$P"); RC=$?
expect_exit "effortLevel と filter-output.py を外すと exit 1" 1 "$RC"
expect_out  "種別「配線」で検出" "配線" "$OUT"
grep -q "filter-output.py が hooks に配線されていない" "$TMP/report.md" && ok "欠けた hook 名を出す" || ng "欠けた hook 名を出す" "無い"

echo "[ケース4: 実測ログの集計]"
P2="$TMP/proj2"; mkdir -p "$P2"; bash "$KIT_DIR/00_導入/export-project.sh" "$P2" >/dev/null 2>&1
for i in 1 2 3; do printf '2026-09-19T10:00:00+0900\t{"file_path":"/x/CLAUDE.md"}\n' >> "$P2/.claude/instructions-loaded.log"; done
printf '2026-09-19T10:00:00+0900\t{"file_path":"/x/rules/speed-harness.md"}\n' >> "$P2/.claude/instructions-loaded.log"
run "$P2" >/dev/null
grep -q "CLAUDE.md×3" "$TMP/report.md" && ok "ログをファイル別に集計する（CLAUDE.md×3）" || ng "ログをファイル別に集計する" "$(grep '実測ログ' "$TMP/report.md")"

echo "[ケース5: MCP 過多は WARN（exit 0）]"
printf '{"mcpServers":{"a":{},"b":{},"c":{},"d":{}}}' > "$P2/.mcp.json"
OUT=$(run "$P2"); RC=$?
expect_exit "MCP 4 個でも exit 0（WARN）" 0 "$RC"
expect_out  "警告に MCP" "MCP" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ] && { echo "✅ 全て正常"; exit 0; } || { echo "⚠ 失敗あり"; exit 1; }
