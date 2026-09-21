#!/bin/bash
# test-hooks.sh — hooks の回帰テスト
# AUDIT-2026-07 A-01（hooks が入力を受け取れず無言で素通りしていた）の再発防止。
# stdin に Claude Code hooks 形式の JSON を流し、期待出力を検証する。
# BSD/GNU 共通のその場置換（macOS の sed -i は拡張子引数が必須で GNU と書き方が違う）
sedi() { local f="${@: -1}"; sed "${@:1:$#-1}" "$f" > "$f.sedi" && mv "$f.sedi" "$f"; }
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOKS="$KIT_DIR/03_ClaudeCode/hooks"
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
  echo "  ❌ セッション終了サマリ（exit=${RC}）"; FAIL=$((FAIL+1))
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

echo "[block-phase.py]"
# 工程承認ゲート。.claude/phase-gate がある時だけ発動し、前工程が未承認なら下流成果物への書き込みを deny する
PG="$TMP/proj-phase"; mkdir -p "$PG/scripts" "$PG/.claude"
"$KIT_DIR/00_導入/02_プロジェクト配布/init-lifecycle.sh" "$PG" >/dev/null
cp "$KIT_DIR/02_共通/ツール/check_approval.py" "$KIT_DIR/02_共通/ツール/phase-hash.py" "$PG/scripts/"
pj() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "${2:-Write}" "$PG/$1"; }
ph() { CLAUDE_PROJECT_DIR="$PG" python3 "$HOOKS/block-phase.py" 2>&1; }
reason() { printf '%s' "$1" | python3 -c 'import json,sys;print(json.load(sys.stdin)["hookSpecificOutput"]["permissionDecisionReason"])' 2>/dev/null; }

OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph); RC=$?
expect_empty "マーカー(.claude/phase-gate)が無ければ素通り" "$OUT" "$RC"

touch "$PG/.claude/phase-gate"
OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph); RC=$?
expect_empty "手前に着手済み工程が無ければ許可" "$OUT" "$RC"

sedi 's/YYYY-MM-DD/2026-09-19/' "$PG/docs/lifecycle/01-requirements.md"
OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph)
expect_contains "前工程が未承認なら deny" '"permissionDecision": "deny"' "$OUT"
expect_contains "deny 理由に前工程の状態を含む" "第1工程 要件定義: 未承認" "$(reason "$OUT")"
expect_contains "deny 理由に次の行動を含む" "/phase-review 1" "$(reason "$OUT")"

OUT=$(pj "docs/lifecycle/approvals/phase-1.md" | ph); RC=$?
expect_empty "承認記録そのものへの書き込みは常に許可" "$OUT" "$RC"
OUT=$(pj "docs/lifecycle/traceability-matrix.md" | ph); RC=$?
expect_empty "追跡表は工程成果物ではないので素通り" "$OUT" "$RC"
OUT=$(pj "src/app.py" | ph); RC=$?
expect_empty "工程文書以外は素通り" "$OUT" "$RC"

# 第1工程を承認する（承認は covers の版に縛られる）
python3 - "$PG" <<'FILL'
import re, subprocess, sys
from pathlib import Path
proj = Path(sys.argv[1]); p = proj / "docs/lifecycle/approvals/phase-1.md"; s = p.read_text(encoding="utf-8")
s = s.replace("判定: 未記入", "判定: 承認", 1)
for k, v in (("approver", "藤曲 雄基"), ("approved_at", "2026-09-19T10:00:00+09:00"), ("git_head", "deadbeef")):
    s = re.sub(rf"^\| {k} \| .*? \|$", f"| {k} | {v} |", s, count=1, flags=re.M)
s = s.replace("| 出口基準 | 確認方法・確認した対象 | 結果 |\n|---|---|---|",
              "| 出口基準 | 確認方法・確認した対象 | 結果 |\n|---|---|---|\n"
              "| 全 REQ-F に受入基準 | 01-requirements.md の REQ-F 8件を目視 | 充足 |", 1)
h = subprocess.run([sys.executable, str(proj / "scripts/phase-hash.py"), "docs/lifecycle/01-requirements.md"],
                   cwd=proj, capture_output=True, text=True).stdout.strip()
s = re.sub(r"^\| reviewed_hash \| .*? \|$", f"| reviewed_hash | {h} |", s, count=1, flags=re.M)
p.write_text(s, encoding="utf-8")
FILL
OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph); RC=$?
expect_empty "前工程が承認済みなら許可" "$OUT" "$RC"

OUT=$(pj "docs/lifecycle/01-requirements.md" | ph)
expect_contains "承認済み工程の成果物の書き換えは deny" '"permissionDecision": "deny"' "$OUT"
expect_contains "deny 理由に失効の警告を含む" "承認が失効します" "$(reason "$OUT")"
OUT=$(pj "docs/lifecycle/01-requirements.md" Edit | ph)
expect_contains "Edit でも同じく deny" '"permissionDecision": "deny"' "$OUT"

# 判定スクリプトが見つからないときは素通りさせず deny する（オプトインした以上、無言で緩めない）
mv "$PG/scripts/check_approval.py" "$PG/scripts/check_approval.py.off"
OUT=$(HOME="$TMP/nohome" pj "docs/lifecycle/02-basic-design.md" | HOME="$TMP/nohome" ph)
expect_contains "判定スクリプトが無ければ deny（導入手順を案内）" "check_approval.py が見つかりません" "$(reason "$OUT")"
mv "$PG/scripts/check_approval.py.off" "$PG/scripts/check_approval.py"

echo "[context-guard.py / pre-compact.py / log-instructions.py]"
# 会話の寿命: transcript の mtime でアイドル、サイズで肥大を判定（UserPromptSubmit・警告して通す）
CG="$TMP/cg"; mkdir -p "$CG"; TR="$CG/transcript.jsonl"
cgj() { printf '{"hook_event_name":"UserPromptSubmit","transcript_path":"%s","prompt":"x"}' "$1"; }
cg_ctx() { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d)["hookSpecificOutput"].get("additionalContext","") if d.strip() else "")' 2>/dev/null; }
echo '{}' > "$TR"; python3 -c 'import os,sys,time;t=time.time()-4200;os.utime(sys.argv[1],(t,t))' "$TR"
OUT=$(cgj "$TR" | python3 "$HOOKS/context-guard.py")
expect_contains "70 分空いたら /clear か要約再開を注入" "/clear" "$(cg_ctx "$OUT")"
expect_contains "経過分数を含む" "70 分" "$(cg_ctx "$OUT")"
python3 -c 'import os,sys,time;t=time.time()-600;os.utime(sys.argv[1],(t,t))' "$TR"
OUT=$(cgj "$TR" | python3 "$HOOKS/context-guard.py"); RC=$?
expect_empty "10 分なら何も注入しない" "$OUT" "$RC"
truncate -s 5M "$TR"; touch "$TR"
OUT=$(cgj "$TR" | python3 "$HOOKS/context-guard.py")
expect_contains "5 MB 超なら /compact を注入" "/compact" "$(cg_ctx "$OUT")"
OUT=$(cgj "$CG/none.jsonl" | python3 "$HOOKS/context-guard.py"); RC=$?
expect_empty "transcript が無ければ何もしない（初回）" "$OUT" "$RC"
OUT=$(printf '{"hook_event_name":"PreCompact","trigger":"auto"}' | python3 "$HOOKS/pre-compact.py")
expect_contains "PreCompact に「残す／捨てる」の指示を注入" "決定事項" "$(cg_ctx "$OUT")"
PL="$TMP/proj-log"; mkdir -p "$PL/.claude"
printf '{"hook_event_name":"InstructionsLoaded","file_path":"/x/CLAUDE.md","load_reason":"session_start"}' | CLAUDE_PROJECT_DIR="$PL" python3 "$HOOKS/log-instructions.py"; RC=$?
if [ "$RC" -eq 0 ] && grep -q '"/x/CLAUDE.md"' "$PL/.claude/instructions-loaded.log" 2>/dev/null; then
  echo "  ✅ InstructionsLoaded を .claude/instructions-loaded.log に追記（Claude には何も返さない）"; PASS=$((PASS+1))
else
  echo "  ❌ InstructionsLoaded を .claude/instructions-loaded.log に追記"; FAIL=$((FAIL+1))
fi

echo "[instruction-guard.py / reply-language.py / prompt-priority.py]"
# 保守者の指示に応答するまでツールを呼ばせない（PreToolUse 全ツール）／最後の応答の言語（Stop）／優先の注入（UserPromptSubmit）
IG="$TMP/ig"; mkdir -p "$IG"; TRJ="$IG/t.jsonl"
igj() { printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{},"transcript_path":"%s"}' "$1"; }
ig_reason() { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d)["hookSpecificOutput"].get("additionalContext","") if d.strip() else "")' 2>/dev/null; }
u_text()  { printf '{"type":"user","message":{"role":"user","content":"%s"}}\n' "$1"; }
u_tool()  { printf '{"type":"user","message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"x","content":"ok"}]}}\n'; }
a_text()  { printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"text","text":"%s"}]}}\n' "$1"; }
a_tool()  { printf '{"type":"assistant","message":{"role":"assistant","content":[{"type":"tool_use","id":"x","name":"Bash","input":{}}]}}\n'; }
queued()  { printf '{"type":"attachment","attachment":{"type":"queued_command","prompt":"%s","humanTurn":true}}\n' "$1"; }
enqueue() { printf '{"type":"queue-operation","operation":"enqueue","content":"%s"}\n' "$1"; }
{ u_text "日本語で報告しなさい"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "指示の直後にツールを呼ぶと deny（未応答）" "未応答" "$(ig_reason "$OUT")"
expect_contains "deny 理由に指示の先頭を載せる（読み飛ばし防止）" "日本語で報告しなさい" "$(ig_reason "$OUT")"
{ u_text "日本語で報告しなさい"; a_text "目的: 報告します。 見積: 1分（00:01 完了予定）"; a_tool; u_tool; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "日本語で応答済みなら許可（ツール結果が続いても素通り）" "$OUT" "$RC"
{ u_text "日本語で報告しなさい"; a_tool; } > "$TRJ"
IGS="test-ig-$$"; rm -f "${TMPDIR:-/tmp}/instruction-guard-$IGS"
igs() { printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{},"session_id":"%s","transcript_path":"%s"}' "$IGS" "$1"; }
OUT=$(igs "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "同じ指示の 1 回目は deny" "未応答" "$(ig_reason "$OUT")"
OUT=$(igs "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "同じ指示の 2 回目は許可（応答が transcript に未反映でも閉じ込めない）" "$OUT" "$RC"
rm -f "${TMPDIR:-/tmp}/instruction-guard-$IGS"
{ u_text "作業して"; a_text "目的: 作業。 見積: 1分（00:01 完了予定）"; a_tool; u_tool; queued "中間報告をしなさい。今すぐに。"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "途中で届いた発言（queued_command）に未応答なら deny" "中間報告をしなさい" "$(ig_reason "$OUT")"
{ u_text "作業して"; a_text "目的: 作業。 見積: 1分（00:01 完了予定）"; a_tool; enqueue "止めなさい"; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "キュー投入（enqueue）の時点で deny（配達前でも理由に載る）" "止めなさい" "$(ig_reason "$OUT")"
{ u_text "作業して"; a_text "目的: 作業。 見積: 1分（00:01 完了予定）"; a_tool; u_tool; queued "中間報告をしなさい。"; a_text "中間報告です。 見積: 1分（00:01 完了予定）"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "途中の発言に日本語で応答済みなら許可" "$OUT" "$RC"
{ u_text "日本語で報告しなさい"; a_text "Reflections are in place. Now updating."; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "日本語の指示に英語で応答したら通知" "日本語で応答し直す" "$(ig_reason "$OUT")"
{ u_text "Please fix the test"; a_text "Fixing the test now. 見積: 1分（00:01 完了予定）"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "英語の指示に英語で応答は許可（言語は指示に合わせる）" "$OUT" "$RC"
{ u_text "<command-name>/plan</command-name><command-args>x</command-args>"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "機械由来のタグだけの発言（スラッシュコマンド）は対象外" "$OUT" "$RC"
{ printf '{"type":"user","isSidechain":true,"message":{"role":"user","content":"調べて"}}\n'; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "サブエージェント（isSidechain）は対象外" "$OUT" "$RC"
{ u_text "日本語で報告しなさい"; a_tool; } > "$TRJ"
OUT=$(printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{},"agent_id":"sub1","transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "サブエージェント内（agent_id あり）は親の発言で止めない" "$OUT" "$RC"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_empty "deny しない（permissionDecision を返さず画面にエラーを出さない）" "$(printf '%s' "$OUT" | grep -o permissionDecision)" 0
OUT=$(igj "$IG/none.jsonl" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "transcript が無ければ許可（fail-open）" "$OUT" "$RC"
# 機械が書いた本文を指示と誤認すると、応答しても新しいエラー文が湧いて解除されない自己参照ループになる
{ u_text "構成案を出して"; a_text "案は以下です。 見積: 1分（00:01 完了予定）"; a_tool; u_text "Error: [instruction-guard] 保守者の指示に未応答: 「構成案を出して」。"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "フック自身のエラー文を指示として読み直さない（自己参照ループ防止）" "$OUT" "$RC"
{ u_text "調査して"; a_text "調査します。 見積: 1分（00:01 完了予定）"; a_tool; u_text "<agent-message from=\\\"abc123\\\">[Subagent hand-back] The text below is the final report.</agent-message>"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "サブエージェントの報告（属性付きタグ）は対象外" "$OUT" "$RC"
{ u_text "調査して"; a_text "調査します。 見積: 1分（00:01 完了予定）"; a_tool; u_text "<task-notification><status>completed</status></task-notification>"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "バックグラウンド完了通知は対象外" "$OUT" "$RC"
{ u_text "やって"; a_text "やります。 見積: 1分（00:01 完了予定）"; a_tool; u_text "Stop hook feedback:[reply-language] 日本語で応答してから終える（A-13）"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "Stop フックの差し戻し文は対象外" "$OUT" "$RC"
{ u_text "日本語で報告しなさい"; a_text "Done."; } > "$TRJ"
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"Done.","transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py")
expect_contains "Stop: 最後の応答に日本語が無ければ block で続行させる" '"decision": "block"' "$OUT"
# transcript の最後は 1 つ前の英語の途中報告でも、実際の最後の応答（last_assistant_message）が日本語なら通す
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"報告します。","transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py"); RC=$?
expect_empty "Stop: 最後の応答が日本語なら transcript が古くても止めない" "$OUT" "$RC"
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py"); RC=$?
expect_empty "Stop: last_assistant_message が無ければ判定せず通す" "$OUT" "$RC"
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":true,"transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py"); RC=$?
expect_empty "Stop: stop_hook_active なら何もしない（無限ループ防止）" "$OUT" "$RC"
# 最後の assistant エントリは Stop フックの後に transcript へ書かれる。未応答か未書込かを
# 区別できないため、Stop では未応答を理由に止めない（毎ターンの誤検知を防ぐ）
{ u_text "構成案を出して"; } > "$TRJ"
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py"); RC=$?
expect_empty "Stop: 応答が未書込でも止めない（未応答の検出は PreToolUse 側の担当）" "$OUT" "$RC"
{ u_text "日本語で報告しなさい"; a_text "報告します。"; } > "$TRJ"
OUT=$(printf '{"hook_event_name":"Stop","stop_hook_active":false,"transcript_path":"%s"}' "$TRJ" | python3 "$HOOKS/reply-language.py"); RC=$?
expect_empty "Stop: 日本語で応答していれば何もしない" "$OUT" "$RC"
OUT=$(printf '{"hook_event_name":"UserPromptSubmit","prompt":"中間報告をしなさい。今すぐに。"}' | python3 "$HOOKS/prompt-priority.py")
expect_contains "UserPromptSubmit: 「今すぐ」「報告」を含む発言に優先の注入" "作業より優先" "$(cg_ctx "$OUT")"
OUT=$(printf '{"hook_event_name":"UserPromptSubmit","prompt":"次は S3 を進めて"}' | python3 "$HOOKS/prompt-priority.py"); RC=$?
expect_contains "UserPromptSubmit: 通常の発言にも見積もりの提示を注入（A-2 例外なし）" "見積: N分" "$(cg_ctx "$OUT")"
{ u_text "構成を直して"; a_text "直します。"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py")
expect_contains "応答に見積もり行が無いままツールを呼んだら通知（A-2）" "見積もりが無い" "$(ig_reason "$OUT")"
{ u_text "構成を直して"; a_text "見積: 3分（21:30 完了予定）"; a_tool; } > "$TRJ"
OUT=$(igj "$TRJ" | python3 "$HOOKS/instruction-guard.py"); RC=$?
expect_empty "見積もり行があれば通知しない" "$OUT" "$RC"

echo "[pre-read-guard.py]"
# 読む価値の無いファイルを deny、大きすぎるファイルは先頭だけに絞る（PreToolUse Read）
rg() { python3 "$HOOKS/pre-read-guard.py"; }
rj() { printf '{"tool_name":"Read","tool_input":{"file_path":"%s"%s}}' "$1" "${2:-}"; }
rg_reason() { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d)["hookSpecificOutput"].get("permissionDecisionReason","") if d.strip() else "")' 2>/dev/null; }
rg_limit()  { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d)["hookSpecificOutput"]["updatedInput"].get("limit","") if d.strip() else "")' 2>/dev/null; }
RG="$TMP/proj-read"; mkdir -p "$RG/node_modules/x" "$RG/src"
echo '{}' > "$RG/package-lock.json"; echo 'x' > "$RG/node_modules/x/index.js"; echo '# r' > "$RG/check-docs-report.md"
seq 1 900 > "$RG/src/big.py"; seq 1 300 > "$RG/src/small.py"; printf 'PNG\0\0\0' > "$RG/src/img.png"
OUT=$(rj "$RG/package-lock.json" | rg)
expect_contains "ロックファイルは deny" '"permissionDecision": "deny"' "$OUT"
expect_contains "deny 理由に代替（grep）を示す" "grep" "$(rg_reason "$OUT")"
OUT=$(rj "$RG/node_modules/x/index.js" | rg)
expect_contains "node_modules 配下は deny" '"permissionDecision": "deny"' "$OUT"
OUT=$(rj "$RG/check-docs-report.md" | rg)
expect_contains "生成レポートは deny" '"permissionDecision": "deny"' "$OUT"
OUT=$(rj "$RG/src/big.py" | rg)
expect_contains "900 行のファイルは limit 300 に絞る" "300" "$(rg_limit "$OUT")"
expect_contains "systemMessage に全体の行数と続きの読み方" "900 行" "$OUT"
OUT=$(rj "$RG/src/big.py" ',"limit":50' | rg); RC=$?
expect_empty "limit 指定ありは触らない" "$OUT" "$RC"
OUT=$(rj "$RG/src/big.py" ',"offset":400' | rg); RC=$?
expect_empty "offset 指定ありは触らない" "$OUT" "$RC"
OUT=$(rj "$RG/src/small.py" | rg); RC=$?
expect_empty "300 行のファイルは触らない" "$OUT" "$RC"
OUT=$(rj "$RG/src/img.png" | rg); RC=$?
expect_empty "バイナリは触らない（Read に任せる）" "$OUT" "$RC"
OUT=$(printf '{"tool_name":"Grep","tool_input":{"pattern":"x","path":"%s"}}' "$RG/package-lock.json" | rg); RC=$?
expect_empty "Grep は対象外（Read だけ）" "$OUT" "$RC"

bash_json() { printf '{"tool_name":"Bash","tool_input":{"command":"%s"}}' "$1"; }
echo "[filter-output.py]"
# 冗長な出力を Claude が読む前に絞る（PreToolUse Bash・updatedInput）。終了コードは元のコマンドのまま
fo() { python3 "$HOOKS/filter-output.py"; }
fo_cmd() { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d)["hookSpecificOutput"]["updatedInput"]["command"] if d.strip() else "")' 2>/dev/null; }
fo_msg() { printf '%s' "$1" | python3 -c 'import json,sys;d=sys.stdin.read();print(json.loads(d).get("systemMessage","") if d.strip() else "")' 2>/dev/null; }

OUT=$(bash_json "GATES_REQUESTED=1 pytest tests/" | fo)
expect_contains "pytest を失敗行＋末尾に絞る（updatedInput）" "grep -A 5 -E" "$(fo_cmd "$OUT")"
expect_contains "元の終了コードで終える" 'exit $__rc' "$(fo_cmd "$OUT")"
expect_contains "systemMessage で全量の取り方を伝える" "FULL_OUTPUT=1" "$(fo_msg "$OUT")"
OUT=$(bash_json "FULL_OUTPUT=1 GATES_REQUESTED=1 pytest tests/" | fo); RC=$?
expect_empty "FULL_OUTPUT=1 なら触らない" "$OUT" "$RC"
OUT=$(bash_json "bash 06_保守者向け/03_回帰テスト/test-hooks.sh" | fo); RC=$?
expect_empty "キット自身の回帰テスト（bash ci/test-*.sh）は絞らない" "$OUT" "$RC"
OUT=$(printf '{"tool_name":"Bash","tool_input":{"command":"cat <<EOF > a.md\\npytest を実行する手順\\nEOF"}}' | fo); RC=$?
expect_empty "ヒアドキュメント内の pytest は触らない" "$OUT" "$RC"
OUT=$(bash_json "git log" | fo)
expect_contains "git log に件数が無ければ --oneline -20 を補う" "git log --oneline -20" "$(fo_cmd "$OUT")"
OUT=$(bash_json "git log -n 5" | fo); RC=$?
expect_empty "git log -n 5 は触らない" "$OUT" "$RC"
OUT=$(bash_json "git diff" | fo)
expect_contains "git diff（対象なし）は --stat に" "git diff --stat" "$(fo_cmd "$OUT")"
OUT=$(bash_json "git diff -- README.md" | fo); RC=$?
expect_empty "git diff -- <path> は触らない" "$OUT" "$RC"
OUT=$(bash_json "npm install" | fo)
expect_contains "npm install は末尾 40 行に" "tail -40" "$(fo_cmd "$OUT")"
# block-gates.py と共存: GATES_REQUESTED=1 が無ければ block-gates が deny（filter の allow より deny が勝つ）
OUT=$(bash_json "pytest tests/" | python3 "$HOOKS/block-gates.py")
expect_contains "GATES_REQUESTED=1 無しは block-gates.py が deny のまま" '"permissionDecision": "deny"' "$OUT"
# 書き換えたコマンドを実際に実行: 偽の pytest（100 行出力・1 行 FAIL・exit 1）で出力が絞られ終了コードが保たれる
FB="$TMP/fakebin"; mkdir -p "$FB"
printf '#!/bin/bash\nfor i in $(seq 1 100); do echo "test_$i PASSED"; done\necho "FAILED test_x - assert 1 == 2"\necho "=== 1 failed, 100 passed ==="\nexit 1\n' > "$FB/pytest"; chmod +x "$FB/pytest"
NEWCMD=$(fo_cmd "$(bash_json "GATES_REQUESTED=1 pytest tests/" | fo)")
RUN=$(PATH="$FB:$PATH" bash -c "$NEWCMD" 2>&1); RC=$?
if [ "$RC" -eq 1 ] && printf '%s' "$RUN" | grep -qF "FAILED test_x" && ! printf '%s' "$RUN" | grep -qF "test_50 PASSED" && printf '%s' "$RUN" | grep -qF "1 failed, 100 passed"; then
  echo "  ✅ 実行すると失敗行と集計だけが残り exit 1 が保たれる（$(printf '%s' "$RUN" | wc -l | tr -d ' ') 行 / 元 102 行）"; PASS=$((PASS+1))
else
  echo "  ❌ 実行すると失敗行と集計だけが残り exit 1 が保たれる（exit=$RC / $(printf '%s' "$RUN" | head -3 | tr '\n' ' ')）"; FAIL=$((FAIL+1))
fi

echo "[block-gates.py]"
OUT=$(bash_json "pytest tests/" | python3 "$HOOKS/block-gates.py")
expect_contains "pytest を deny" '"permissionDecision": "deny"' "$OUT"

OUT=$(bash_json "cd /tmp && make test" | python3 "$HOOKS/block-gates.py")
expect_contains "&& 直後の make test を deny" '"permissionDecision": "deny"' "$OUT"

OUT=$(bash_json "GATES_REQUESTED=1 pytest tests/" | python3 "$HOOKS/block-gates.py"); RC=$?
expect_empty "GATES_REQUESTED=1 で素通り" "$OUT" "$RC"

OUT=$(bash_json "git commit -m 'add make test target'" | python3 "$HOOKS/block-gates.py"); RC=$?
expect_empty "引用文字列内の make test は素通り（誤検知なし）" "$OUT" "$RC"

OUT=$(json_tool "Read" | python3 "$HOOKS/block-gates.py"); RC=$?
expect_empty "Bash 以外は素通り" "$OUT" "$RC"

echo "[progress.py / statusline.py]"
PH="$TMP/proj-prog/.claude/hooks"; mkdir -p "$PH"; cp "$HOOKS/progress.py" "$HOOKS/statusline.py" "$PH/"
python3 "$PH/progress.py" start "テスト" 120 && python3 "$PH/progress.py" step "2/3 配線"
if [ -f "$TMP/proj-prog/.claude/progress.json" ] && grep -qF '2/3' "$TMP/proj-prog/.claude/progress.json"; then
  echo "  ✅ start/step で progress.json を更新"; PASS=$((PASS+1))
else
  echo "  ❌ start/step で progress.json を更新"; FAIL=$((FAIL+1))
fi
OUT=$(printf '{}' | python3 "$PH/statusline.py")
expect_contains "進行中はステータスラインに ⏱ と経過/見積を表示" "⏱ テスト [2/3 配線]" "$OUT"
python3 "$PH/progress.py" done
if [ ! -e "$TMP/proj-prog/.claude/progress.json" ]; then
  echo "  ✅ done で progress.json を削除"; PASS=$((PASS+1))
else
  echo "  ❌ done で progress.json を削除"; FAIL=$((FAIL+1))
fi

echo "[.claude/settings.json 配線]"
# 2026-09-20 の事故の再発防止: 実体に届かない環境（リモートセッション／ディレクトリ移動の途中）で
# hook の起動に失敗すると、UserPromptSubmit はプロンプト投入ごとブロックされる。無言で飛ぶことを検証する。
DEV_SETTINGS="$KIT_DIR/.claude/settings.json"
if [ -f "$DEV_SETTINGS" ]; then
  EMPTY="$TMP/no-hooks"; mkdir -p "$EMPTY"
  CMDS=$(python3 -c 'import json,sys
d = json.load(open(sys.argv[1]))
for entries in d.get("hooks", {}).values():
    for e in entries:
        for h in e.get("hooks", []):
            print(h.get("command", ""))' "$DEV_SETTINGS")
  while IFS= read -r CMD; do
    [ -n "$CMD" ] || continue
    NAME=$(printf '%s' "$CMD" | grep -o '[a-z-]*\.py' | head -1)
    OUT=$(printf '{"hook_event_name":"UserPromptSubmit","prompt":"報告して"}' | CLAUDE_PROJECT_DIR="$EMPTY" sh -c "$CMD" 2>&1); RC=$?
    expect_empty "実体が無くても無言で exit 0: $NAME" "$OUT" "$RC"
  done <<< "$CMDS"
  PP=$(printf '%s' "$CMDS" | grep prompt-priority)
  OUT=$(printf '{"hook_event_name":"UserPromptSubmit","prompt":"いますぐ報告して"}' | CLAUDE_PROJECT_DIR="$KIT_DIR" sh -c "$PP" 2>&1)
  expect_contains "実体があれば prompt-priority は従来どおり注入する" "prompt-priority" "$OUT"
else
  echo "  ❌ .claude/settings.json が無い"; FAIL=$((FAIL+1))
fi

echo "[block-ci.py]"
for T in ScheduleWakeup CronCreate RemoteTrigger mcp__x__send_later mcp__github__subscribe_pr_activity; do
  OUT=$(json_tool "$T" | python3 "$HOOKS/block-ci.py")
  expect_contains "$T を deny" '"permissionDecision": "deny"' "$OUT"
done
OUT=$(printf '{"tool_name":"Skill","tool_input":{"skill":"loop"}}' | python3 "$HOOKS/block-ci.py")
expect_contains "Skill loop を deny" '"permissionDecision": "deny"' "$OUT"
OUT=$(bash_json "git push && gh run watch 123" | python3 "$HOOKS/block-ci.py")
expect_contains "gh run watch を deny" '"permissionDecision": "deny"' "$OUT"
OUT=$(bash_json "gh pr checks 5 --watch" | python3 "$HOOKS/block-ci.py")
expect_contains "gh pr checks --watch を deny" '"permissionDecision": "deny"' "$OUT"
OUT=$(bash_json "CI_REQUESTED=1 gh workflow run ci.yml" | python3 "$HOOKS/block-ci.py"); RC=$?
expect_empty "CI_REQUESTED=1 なら素通り" "$OUT" "$RC"
OUT=$(bash_json "gh pr checks 5" | python3 "$HOOKS/block-ci.py"); RC=$?
expect_empty "gh pr checks（待機なし）は素通り" "$OUT" "$RC"
OUT=$(bash_json "git commit -m 'gh run watch を禁止'" | python3 "$HOOKS/block-ci.py"); RC=$?
expect_empty "引用文字列内の gh run watch は素通り" "$OUT" "$RC"
OUT=$(json_tool "Read" | python3 "$HOOKS/block-ci.py"); RC=$?
expect_empty "無関係なツールは素通り" "$OUT" "$RC"
expect_contains "配布用 settings.json に block-ci.py が配線されている" "block-ci.py" "$(cat "$HOOKS/settings.json")"

echo "[statusline.py トークン表示]"
TJ="$TMP/t.jsonl"
printf '%s\n' '{"type":"assistant","message":{"id":"m1","usage":{"input_tokens":10,"cache_read_input_tokens":1000,"output_tokens":200}}}' \
  '{"type":"assistant","message":{"id":"m1","usage":{"input_tokens":10,"cache_read_input_tokens":1000,"output_tokens":200}}}' \
  '{"type":"assistant","message":{"id":"m2","usage":{"cache_read_input_tokens":2000,"output_tokens":400}}}' > "$TJ"
OUT=$(printf '{"transcript_path":"%s"}' "$TJ" | HOME="$TMP" python3 "$HOOKS/statusline.py")
expect_contains "同一 id を 1 回と数え累計・1 応答あたり出力・応答数を出す" "Σ4k 出力300/t 2t" "$OUT"
printf '%s\n' '{"type":"assistant","message":{"id":"m3","usage":{"output_tokens":2600}}}' >> "$TJ"
OUT=$(printf '{"transcript_path":"%s"}' "$TJ" | HOME="$TMP" python3 "$HOOKS/statusline.py")
expect_contains "差分だけ読み足し、1 応答 1000 超で ⚠" "⚠ Σ6k 出力1,066/t 3t" "$OUT"
OUT=$(python3 "$KIT_DIR/00_導入/03_点検/token_report.py" "$TJ")
expect_contains "token_report.py が区分別の表を出す" "| cache_read | 3,000 |" "$OUT"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"
  exit 0
else
  echo "⚠ 失敗あり。03_ClaudeCode/hooks/ と 06_保守者向け/04_監査記録/AUDIT-2026-07.md A-01 を確認してください"
  exit 1
fi
