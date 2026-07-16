#!/bin/bash
# test-hooks.sh — hooks の回帰テスト
# AUDIT-2026-07 A-01（hooks が入力を受け取れず無言で素通りしていた）の再発防止。
# stdin に Claude Code hooks 形式の JSON を流し、期待出力を検証する。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS="$KIT_DIR/claude-code/hooks"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

json() { printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$1"; }
json_tool() { printf '{"tool_name":"%s","tool_input":{}}' "$1"; }

expect_contains() { # 名前, 期待部分文字列, 実出力
  if printf '%s' "$3" | grep -qF "$2"; then
    echo "  ✅ $1"; PASS=$((PASS+1))
  else
    echo "  ❌ $1（期待: '$2' を含む / 実際: $(printf '%s' "$3" | head -1)）"; FAIL=$((FAIL+1))
  fi
}

expect_empty() { # 名前, 実出力, 終了コード
  if [ "$3" -eq 0 ] && [ -z "$2" ]; then
    echo "  ✅ $1"; PASS=$((PASS+1))
  else
    echo "  ❌ $1（exit=$3 / 出力: $(printf '%s' "$2" | head -1)）"; FAIL=$((FAIL+1))
  fi
}

echo "=== AIDD Kit hooks 回帰テスト ==="

echo "[pre-write-check.sh]"
OUT=$(json "/tmp/example/.env" | bash "$HOOKS/pre-write-check.sh")
expect_contains "秘密情報ファイル(.env)で警告" "秘密情報ファイル" "$OUT"

touch "$TMP/page.html"
OUT=$(json "$TMP/style.css" | bash "$HOOKS/pre-write-check.sh")
expect_contains "HTML隣接のCSSで分割警告" "CSS/JS外部分割" "$OUT"

OUT=$(json "$TMP/notes.md" | bash "$HOOKS/pre-write-check.sh"); RC=$?
expect_empty "通常ファイルは無言終了" "$OUT" "$RC"

OUT=$(printf '' | bash "$HOOKS/pre-write-check.sh"); RC=$?
expect_empty "空入力は無害終了" "$OUT" "$RC"

echo "[post-write-html.sh]"
printf '<html><body>test</body></html>\n' > "$TMP/page.html"
OUT=$(json "$TMP/page.html" | bash "$HOOKS/post-write-html.sh")
expect_contains "HTML保存後にレポート出力" "post-write HTML" "$OUT"

seq 1 501 | sed 's/.*/<div>&<\/div>/' > "$TMP/big.html"
OUT=$(json "$TMP/big.html" | bash "$HOOKS/post-write-html.sh")
expect_contains "500行超で部分編集を推奨" "500行超" "$OUT"

OUT=$(json "$TMP/style.css" | bash "$HOOKS/post-write-html.sh"); RC=$?
expect_empty "非HTMLは無言終了" "$OUT" "$RC"

echo "[session-summary.sh]"
OUT=$(cd "$TMP" && bash "$HOOKS/session-summary.sh"); RC=$?
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -qF "session-end"; then
  echo "  ✅ セッション終了サマリが出力され exit 0"; PASS=$((PASS+1))
else
  echo "  ❌ セッション終了サマリ（exit=$RC）"; FAIL=$((FAIL+1))
fi

echo "[block-explore.sh]"
# 実装モード OFF（.claude/mode なし）→ 探索は素通り
PROJ_OFF="$TMP/proj-off"; mkdir -p "$PROJ_OFF"
OUT=$(json_tool "Read" | CLAUDE_PROJECT_DIR="$PROJ_OFF" bash "$HOOKS/block-explore.sh" 2>&1); RC=$?
expect_empty "モードOFFではReadを許可（無言 exit 0）" "$OUT" "$RC"

# 実装モード ON（.claude/mode あり）→ 探索をブロック（exit 2 ＋ 警告）
PROJ_ON="$TMP/proj-on"; mkdir -p "$PROJ_ON/.claude"; echo "implement" > "$PROJ_ON/.claude/mode"
OUT=$(json_tool "Read" | CLAUDE_PROJECT_DIR="$PROJ_ON" bash "$HOOKS/block-explore.sh" 2>&1); RC=$?
if [ "$RC" -eq 2 ] && printf '%s' "$OUT" | grep -qF "実装モード"; then
  echo "  ✅ モードONでReadをブロック（exit 2 ＋ 警告）"; PASS=$((PASS+1))
else
  echo "  ❌ モードONでReadをブロック（exit=$RC / 出力: $(printf '%s' "$OUT" | head -1)）"; FAIL=$((FAIL+1))
fi

# 実装モード ON でも Write 系（非探索）は素通り（matcher 想定外の tool_name）
OUT=$(json_tool "Write" | CLAUDE_PROJECT_DIR="$PROJ_ON" bash "$HOOKS/block-explore.sh" 2>&1); RC=$?
expect_empty "モードONでもWriteは素通り（無言 exit 0）" "$OUT" "$RC"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"
  exit 0
else
  echo "⚠ 失敗あり。claude-code/hooks/ と docs/AUDIT-2026-07.md A-01 を確認してください"
  exit 1
fi
