#!/bin/bash
# pre-write-check.sh
# 書き込み前にスコープ違反・秘密情報混入を検出
# Claude Code hooks はツール入力を stdin の JSON で渡す（tool_input.file_path / content / new_string / edits）
# 秘密情報の判定は secret_patterns.py に 1 か所で持つ（B-19。規則を他所に書き足さない）:
#   - 書き込む本文（Write の content・Edit の new_string・MultiEdit の各 new_string）に既知形式の秘密値 → deny
#     （理由文には型の名前と行番号だけ。値は出さない）。テスト用の偽値など意図したものは AIDD_SECRET_OK=1 で警告に落とす
#   - ファイル名だけの一致（.env 等）→ 警告のみ（.env.example に API_KEY=your-key-here を書くのは止めない）
#   - 入力が JSON として読めない・オブジェクトでない（[1]・null・空）→ deny（fail-closed）。{} は通す
#   - 03_ClaudeCode/hooks/secret_patterns.py が hook と同じ場所に無い・判定に失敗した → deny（判定不能は不合格）
# deny・警告・AIDD_SECRET_OK での通過は .claude/hook-decisions.log に 1 行ずつ記録する（B12。secret_patterns.py の
#   log_decision。秘密値は伏字。書けなくても止めない。secret_patterns.py が無いときは記録できない）

INPUT=$(cat)
deny() { printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"; exit 0; }

# 秘密情報（本文の値 → deny ／ ファイル名 → 警告）。入力の検査も secret_patterns.py が行う
SP="$(dirname "${BASH_SOURCE[0]}")/secret_patterns.py"
SP_OUT=$(printf '%s' "$INPUT" | python3 "$SP" --pre-write 2>/dev/null); SP_RC=$?
case "$SP_RC" in
  0) ;;
  3) deny "[pre-write-check] hook の入力が読めない（JSON のオブジェクトでない）ので止めた（fail-closed）。続けて起きるなら Claude Code と hook の版の組み合わせを保守者に確認してもらう" ;;
  2) deny "[pre-write-check] 判定不能で止めた: 03_ClaudeCode/hooks/secret_patterns.py が無い。hook と同じ場所に置く（保守者に install.sh / export-project.sh での入れ直しを依頼する）" ;;
  *) python3 "$SP" --log-decision pre-write-check deny "秘密情報の検査に失敗（exit ${SP_RC}）" >/dev/null 2>&1
     deny "[pre-write-check] 秘密情報の検査に失敗した（secret_patterns.py が exit ${SP_RC}）ので止めた（判定不能）。保守者に hook の不具合として報告する" ;;
esac
case "$SP_OUT" in
  "{"*) printf '%s\n' "$SP_OUT"; exit 0 ;;   # deny の JSON はそのまま返す（警告の文字列と混ぜると JSON として読まれない）
esac

if command -v jq >/dev/null 2>&1; then
  FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
else
  FILE=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))' 2>/dev/null)
fi
if [ -z "$FILE" ]; then exit 0; fi

ERRORS=()
if [ -n "$SP_OUT" ]; then
  while IFS= read -r line; do ERRORS+=("$line"); done <<< "$SP_OUT"
fi

# 単一HTMLツールへの外部ファイル分割検出
if [[ "$FILE" =~ \.css$|\.js$ ]]; then
  PARENT=$(dirname "$FILE")
  if ls "$PARENT"/*.html &>/dev/null 2>&1; then
    ERRORS+=("⚠ 同階層にHTMLあり: 単一HTMLツールのプロジェクトならCSS/JS外部分割は規約違反です（通常のWebプロジェクトなら無視してよい）。意図的ですか？ ($FILE)")
    TOOLN=$(printf '%s' "$INPUT" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("tool_name",""))' 2>/dev/null)
    python3 "$SP" --log-decision pre-write-check warn "HTML 隣の CSS/JS 分割" "$TOOLN" "$FILE" >/dev/null 2>&1
  fi
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "=== [AIDD Hook: pre-write] ==="
  for e in "${ERRORS[@]}"; do echo "$e"; done
  echo "=============================="
fi

exit 0  # ここまで来たら警告のみ（deny は上で JSON を返して終えている）
