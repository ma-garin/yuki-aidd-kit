#!/bin/bash
# test-config-deps.sh — 03_ClaudeCode/hooks/config-snapshot.py と block-deps.py の回帰テスト
# 構成の変化の記録（初回は無出力・変化で項目名・無変化で無出力・report の表）と、
# 新規依存の追加ゲート（deny / 通す / AIDD_DEPS_OK / Edit / 壊れた JSON）を確かめる。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SNAP="$KIT_DIR/03_ClaudeCode/hooks/config-snapshot.py"
DEPS="$KIT_DIR/03_ClaudeCode/hooks/block-deps.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0

ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_empty() { [ -z "$2" ] && ok "$1" || ng "$1" "出力があってはいけない: $2"; }
expect_out()   { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い"; }
expect_noout() { ! printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' があってはいけない"; }

P="$TMP/proj"; mkdir -p "$P/.claude/rules"
export HOME="$TMP/home"; mkdir -p "$HOME"     # 利用者の ~/.claude を巻き込まない
unset AIDD_CONFIG_LOG AIDD_DEPS_OK
echo "# 指示" > "$P/CLAUDE.md"
echo "- 規則" > "$P/.claude/rules/a.md"
snap() { (cd "$P" && printf '{"cwd":"%s","hook_event_name":"%s","model":"%s"}' "$P" "${1:-SessionStart}" "${2:-m-1}" \
          | python3 "$SNAP" snapshot 2>&1); }
deps() { (cd "$P" && printf '%s' "$1" | python3 "$DEPS" 2>&1); }
bash_in() { python3 -c 'import json,sys; print(json.dumps({"tool_name":"Bash","cwd":sys.argv[2],"tool_input":{"command":sys.argv[1]}}))' "$1" "$P"; }

echo "=== config-snapshot.py ==="
out=$(snap); expect_empty "snapshot 初回は無出力" "$out"
[ -s "$P/.claude/ai-config-log.jsonl" ] && ok "初回でも記録は残る" || ng "初回でも記録は残る" "jsonl が無い"
out=$(snap UserPromptSubmit); expect_empty "変えなければ無出力（UserPromptSubmit）" "$out"
echo "# 指示（改）" > "$P/CLAUDE.md"
out=$(snap UserPromptSubmit)
expect_out "CLAUDE.md の変更が additionalContext に出る" "AI の構成が変わった: CLAUDE.md" "$out"
expect_out "確認セットの再実行を促す" "quality-decision" "$out"
out=$(snap UserPromptSubmit m-2); expect_out "モデルの変更を拾う" "model" "$out"
out=$(ANTHROPIC_MODEL=x snap UserPromptSubmit m-2); expect_out "環境変数のキー名を拾う" "env_keys" "$out"
expect_noout "環境変数の値は記録しない（キー名だけ）" '"env_keys": "x"' "$(cat "$P/.claude/ai-config-log.jsonl")"
out=$(AIDD_CONFIG_LOG="$TMP/alt.jsonl" snap); [ -s "$TMP/alt.jsonl" ] && ok "AIDD_CONFIG_LOG で保存先を差し替え" || ng "AIDD_CONFIG_LOG で保存先を差し替え" "無い"
out=$(cd "$P" && python3 "$SNAP" report 5)
expect_out "report が表を出す" "| 日時 | 契機 | 変わった項目 | モデル |" "$out"
expect_out "report に変更項目が載る" "CLAUDE.md" "$out"
out=$(cd "$P" && echo '{壊れ' | python3 "$SNAP" snapshot; echo "exit=$?"); expect_out "壊れた入力でも止めない（fail-open）" "exit=0" "$out"

echo "=== block-deps.py ==="
echo "requests==2.31.0" > "$P/requirements.txt"
out=$(deps "$(bash_in 'pip install requests')"); expect_out "pip install requests は deny" '"deny"' "$out"
expect_out "deny 理由に承認と解除方法" "AIDD_DEPS_OK=1" "$out"
out=$(deps "$(bash_in 'pip install -r requirements.txt')"); expect_empty "pip install -r requirements.txt は通す" "$out"
out=$(deps "$(bash_in 'npm ci')"); expect_empty "npm ci は通す" "$out"
out=$(deps "$(bash_in 'npm install')"); expect_empty "npm install（引数なし）は通す" "$out"
out=$(deps "$(bash_in 'npm install left-pad')"); expect_out "npm install left-pad は deny" '"deny"' "$out"
expect_out "初出（ロックに無い）を deny 理由に添える" "初出: left-pad" "$out"
out=$(deps "$(bash_in 'cd x && uv add httpx')"); expect_out "連結した uv add も deny" '"deny"' "$out"
out=$(deps "$(bash_in 'python3 -m pip install flask')"); expect_out "python -m pip install も deny" '"deny"' "$out"
out=$(AIDD_DEPS_OK=1 deps "$(bash_in 'pip install requests')"); expect_noout "AIDD_DEPS_OK=1 で通る" '"deny"' "$out"
expect_empty "ロックにある名前は WARN も出さない" "$out"
out=$(AIDD_DEPS_OK=1 deps "$(bash_in 'npm i left-pad')"); expect_out "AIDD_DEPS_OK=1 でも初出は WARN" "WARN" "$out"
EDIT=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[1]+"/package.json",
  "old_string":"\"dependencies\": {\n    \"express\": \"^4.18.0\"\n  }","new_string":"\"dependencies\": {\n    \"express\": \"^4.18.0\",\n    \"lodahs\": \"^4.17.0\"\n  }"}}))' "$P")
out=$(deps "$EDIT"); expect_out "Edit で package.json に依存追加は deny" "lodahs" "$out"
EDIT2=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Edit","cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[1]+"/package.json",
  "old_string":"\"express\": \"^4.18.0\"","new_string":"\"express\": \"^4.19.2\""}}))' "$P")
out=$(deps "$EDIT2"); expect_empty "版だけ上げる Edit は通す" "$out"
WR=$(python3 -c 'import json,sys; print(json.dumps({"tool_name":"Write","cwd":sys.argv[1],"tool_input":{"file_path":sys.argv[1]+"/requirements.txt","content":"requests==2.31.0\nreqeusts\n"}}))' "$P")
out=$(deps "$WR"); expect_out "Write で requirements.txt に新しい名前は deny" "reqeusts" "$out"
out=$(deps '{壊れたJSON'); expect_out "壊れた JSON は deny（fail-closed）" '"deny"' "$out"
out=$(deps '{"tool_name":"Read","tool_input":{"file_path":"x"}}'); expect_empty "対象外のツールは無出力" "$out"

echo ""
if [ "$FAIL" -ne 0 ]; then
  echo "⚠ 失敗あり。03_ClaudeCode/hooks/config-snapshot.py・block-deps.py を確認してください"
fi
echo "結果: PASS=$PASS / FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
