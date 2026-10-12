#!/bin/bash
# pre-commit フォールバック（gitleaks なし）の回帰テスト: 値の形で判定する
HERE="$(cd "$(dirname "$0")" && pwd)"
HOOK="$HERE/../../02_共通/ツール/pre-commit"
GL="$(command -v gitleaks)"; [ -n "$GL" ] && PATH="$(echo "$PATH" | tr ':' '\n' | grep -vxF "$(dirname "$GL")" | paste -sd: -)"
PASS=0; FAIL=0
run() { # name expect(0|1) file content
  local d; d=$(mktemp -d); (cd "$d" && git init -q && printf '%s\n' "$4" > "$3" && git add "$3" && bash "$HOOK" >/dev/null 2>&1); local rc=$?
  if [ "$rc" -eq "$2" ]; then PASS=$((PASS+1)); echo "PASS $1"; else FAIL=$((FAIL+1)); echo "FAIL $1 (rc=$rc)"; fi
}
run "説明文の token/secret/ANTHROPIC_API_KEY は通る" 0 a.md 'ANTHROPIC_API_KEY を環境変数に置く。token と secret の説明。'
run "api_key に sk-ant 形は止まる" 1 a.py 'api_key = "sk-ant-abcdefghijklmnopqrstuvwxyz123"'
run "password: changeme は通る" 0 a.yml 'password: "changeme"'
run ".env は止まる" 1 .env 'A=1'
run "AKIA 形は止まる" 1 a.txt 'id AKIAABCDEFGHIJKLMNOP'
echo "PASS=$PASS / FAIL=$FAIL"; [ "$FAIL" -eq 0 ]
