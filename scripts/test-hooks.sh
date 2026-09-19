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

echo "[block-phase.py]"
# 工程承認ゲート。.claude/phase-gate がある時だけ発動し、前工程が未承認なら下流成果物への書き込みを deny する
PG="$TMP/proj-phase"; mkdir -p "$PG/scripts" "$PG/.claude"
"$KIT_DIR/scripts/init-lifecycle.sh" "$PG" >/dev/null
cp "$KIT_DIR/scripts/check_approval.py" "$KIT_DIR/scripts/phase-hash.py" "$PG/scripts/"
pj() { printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "${2:-Write}" "$PG/$1"; }
ph() { CLAUDE_PROJECT_DIR="$PG" python3 "$HOOKS/block-phase.py" 2>&1; }
reason() { printf '%s' "$1" | python3 -c 'import json,sys;print(json.load(sys.stdin)["hookSpecificOutput"]["permissionDecisionReason"])' 2>/dev/null; }

OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph); RC=$?
expect_empty "マーカー(.claude/phase-gate)が無ければ素通り" "$OUT" "$RC"

touch "$PG/.claude/phase-gate"
OUT=$(pj "docs/lifecycle/02-basic-design.md" | ph); RC=$?
expect_empty "手前に着手済み工程が無ければ許可" "$OUT" "$RC"

sed -i 's/YYYY-MM-DD/2026-09-19/' "$PG/docs/lifecycle/01-requirements.md"
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
OUT=$(bash_json "bash scripts/test-hooks.sh" | fo); RC=$?
expect_empty "キット自身の回帰テスト（bash scripts/test-*.sh）は絞らない" "$OUT" "$RC"
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

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"
  exit 0
else
  echo "⚠ 失敗あり。claude-code/hooks/ と docs/AUDIT-2026-07.md A-01 を確認してください"
  exit 1
fi
