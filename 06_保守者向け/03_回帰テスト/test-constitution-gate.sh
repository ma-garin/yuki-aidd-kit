#!/bin/bash
# test-constitution-gate.sh — constitution-gate.py（憲法ゲート: 見積・中間報告・番の終わり方）の回帰テスト
#
# transcript は mktemp に JSONL を自作し、時刻は AIDD_NOW_EPOCH で偽装する。各ケースは独立したプロジェクト
# ディレクトリ（停止 file・状態 file・学んだこと.md）で走らせ、稼働中セッションの .claude/ には触れない。
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$KIT_DIR/03_ClaudeCode/hooks/constitution-gate.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
ng() { echo "  ❌ $1（$2）"; FAIL=$((FAIL+1)); }
expect_out()  { printf '%s' "$3" | grep -qF -- "$2" && ok "$1" || ng "$1" "出力に '$2' が無い: ${3:0:160}"; }
expect_empty(){ [ -z "$2" ] && ok "$1" || ng "$1" "出力が空でない: ${2:0:160}"; }
expect_file() { [ -e "$2" ] && ok "$1" || ng "$1" "$2 が無い"; }
expect_nofile(){ [ -e "$2" ] && ng "$1" "$2 がある" || ok "$1"; }

unset AIDD_STOP_FILE CLAUDE_PROJECT_DIR AIDD_REPORT_INTERVAL_SEC
export AIDD_HOOK_LOG="$TMP/hook-decisions.log" AIDD_TOOL_TIME="$TMP/tool-time.json" AIDD_TRANSCRIPT_FLUSH_SEC=0
NOW=1790000000

# setmtime <file> <epoch>: macOS の BSD touch は -d @epoch を受け付けないので python で設定する
setmtime() { python3 -c 'import os,sys;os.utime(sys.argv[1],(int(sys.argv[2]),)*2)' "$1" "$2"; }
js() { python3 -c 'import json,sys;print(json.dumps(sys.argv[1],ensure_ascii=False))' "$1"; }
user() { echo "{\"type\":\"user\",\"uuid\":\"$1\",\"message\":{\"role\":\"user\",\"content\":$(js "$2")}}"; }
asst() { echo "{\"type\":\"assistant\",\"uuid\":\"$1\",\"message\":{\"role\":\"assistant\",\"content\":[{\"type\":\"text\",\"text\":$(js "$2")}]}}"; }
agent() { echo "{\"type\":\"assistant\",\"uuid\":\"$1\",\"message\":{\"role\":\"assistant\",\"content\":[{\"type\":\"tool_use\",\"id\":\"$2\",\"name\":\"Agent\",\"input\":{\"prompt\":\"x\",\"run_in_background\":$3}}]}}"; }
result() { echo "{\"type\":\"user\",\"uuid\":\"$1\",\"message\":{\"role\":\"user\",\"content\":[{\"type\":\"tool_result\",\"tool_use_id\":\"$2\",\"content\":$(js "$3")}]}}"; }

# newproj <名前>: プロジェクトを作り、学んだこと.md を NOW-1日 の mtime で置く。$P と $T（transcript）を設定
newproj() {
  P="$TMP/$1"; T="$P/transcript.jsonl"
  mkdir -p "$P/.claude" "$P/06_保守者向け"; : > "$T"
  echo "# 学んだこと" > "$P/06_保守者向け/学んだこと.md"; setmtime "$P/06_保守者向け/学んだこと.md" "$((NOW - 86400))"
}
# pre <tool> <tool_input JSON> <epoch> [追加フィールド]
pre() {
  printf '{"hook_event_name":"PreToolUse","tool_name":"%s","tool_input":%s,"transcript_path":"%s","cwd":"%s"%s}' \
    "$1" "$2" "$T" "$P" "${4:-}" | (cd "$P" && AIDD_NOW_EPOCH="$3" python3 "$HOOK" pre 2>&1)
}
stop() { printf '{"hook_event_name":"Stop","transcript_path":"%s","cwd":"%s"%s}' "$T" "$P" "${1:-}" \
           | (cd "$P" && AIDD_NOW_EPOCH="$NOW" python3 "$HOOK" stop 2>&1); }
RD='{"file_path":"/x/a.py"}'
WR='{"file_path":"/x/a.py","content":"x"}'

echo "■ (a) 停止 file"
newproj a; user u1 "README を読んで" >> "$T"
echo "2026-11-03T10:00:00+09:00	見積欠落	Write" > "$P/.claude/constitution-stop"
OUT=$(pre Read "$RD" $NOW)
expect_out "1. 停止 file があれば Read も deny" '"permissionDecision": "deny"' "$OUT"
expect_out "2. 理由に再開条件" "停止 file" "$OUT"

echo "■ (c) 見積ゲート"
newproj c; user u1 "constitution-gate.py を実装して" >> "$T"
for i in 1 2 3; do
  OUT=$(pre Read "$RD" $NOW); expect_empty "3.$i 見積なしでも読み取り $i 回目は許可" "$OUT"
done
OUT=$(pre Read "$RD" $NOW)
expect_out "4. 読み取り 4 回目は deny" "見積欠落" "$OUT"
expect_file "5. 違反で停止 file を即生成" "$P/.claude/constitution-stop"
expect_file "6. .last も生成" "$P/.claude/constitution-stop.last"
expect_out "7. 違反 JSONL に記録" '"kind": "見積欠落"' "$(cat "$P/.claude/constitution-violations.jsonl" 2>/dev/null)"
expect_out "8. hook-decisions.log に stop" '"hook": "constitution-gate", "decision": "stop"' "$(cat "$AIDD_HOOK_LOG")"

newproj c2; user u1 "バグを直して" >> "$T"
OUT=$(pre Write "$WR" $NOW)
expect_out "9. 見積なしの Write は 1 回目から deny" "見積欠落" "$OUT"

newproj c3; user u1 "a.py を修正して" >> "$T"; asst a1 "見積：5分
着手します" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "10. 見積行があれば Write を許可" "$OUT"
newproj c4; user u1 "a.py を修正して" >> "$T"; asst a1 "見積: 5分" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "11. 半角コロンの見積行も受理" "$OUT"
newproj c5; user u1 "今日の進捗を教えて" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "12. コーディングを含まない指示は見積ゲートの対象外" "$OUT"

echo "■ (d) 報告ゲート"
newproj d; user u1 "テストを追加して" >> "$T"; asst a1 "見積：10分" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "13. 見積行を確認（起点）" "$OUT"
# 上限＝最初の見積の分×60÷5 秒（2026-11-14 利用者指定。見積 10 分なら 120 秒。旧: 固定 180 秒）
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 110))); expect_empty "14. 110 秒は許可（見積 10 分→上限 120 秒）" "$OUT"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 121)))
expect_out "15. 120 秒超は deny" "無報告" "$OUT"
expect_out "16. 理由に中間行の書式" "中間行【進捗" "$OUT"
expect_file "17. 120 秒超で停止 file 生成" "$P/.claude/constitution-stop"
# 下限 60 秒（2026-11-14 利用者指定。見積 1 分は 12 秒でなく 60 秒が上限）
newproj dmin; user u1 "テストを追加して" >> "$T"; asst a1 "見積：1分" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "17a. 見積 1 分の見積行を確認（起点）" "$OUT"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 50))); expect_empty "17b. 50 秒は許可（下限 60 秒）" "$OUT"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 61)))
expect_out "17c. 60 秒超は deny" "無報告" "$OUT"
expect_out "17d. 理由に上限 60 秒" "上限 60 秒" "$OUT"

newproj d2; user u1 "テストを追加して" >> "$T"; asst a1 "見積：10分" >> "$T"
pre Write "$WR" $NOW >/dev/null
asst a2 "【進捗:順調 | 経過時間：2分 | 終了:10:10 | タスク数:1/3】" >> "$T"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 120))); expect_empty "18. 中間行を出した時点で許可" "$OUT"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 230))); expect_empty "19. 中間行から 110 秒なので許可（見積行からは 230 秒）" "$OUT"
expect_nofile "20. 停止 file は無い" "$P/.claude/constitution-stop"

newproj d3; user u1 "テストを追加して" >> "$T"; asst a1 "見積：10分" >> "$T"
pre Write "$WR" $NOW >/dev/null
asst a2 "完了。残作業はなし
【見積:10分 | 実測:8分 | 開始:10:00 | 終了:10:08 | 作業時間記録:成功】" >> "$T"
OUT=$(pre Bash '{"command":"ls"}' $((NOW + 1000))); expect_empty "21. 完了行の後は判定外" "$OUT"

newproj d4; user u1 "テストを追加して" >> "$T"; asst a1 "見積：10分" >> "$T"
user n1 "<task-notification><task-id>x</task-id><status>completed</status></task-notification>" >> "$T"
OUT=$(pre Write "$WR" $NOW); expect_empty "22. 機械の通知ではターンを区切らない（見積は有効）" "$OUT"

echo "■ (C) 停止 file の保護"
newproj p; user u1 "README を読んで" >> "$T"
OUT=$(pre Bash '{"command":"rm -f .claude/constitution-stop"}' $NOW)
expect_out "23. 停止 file への rm を deny" "停止 file の改ざん" "$OUT"
newproj p2; user u1 "README を読んで" >> "$T"
OUT=$(pre Write "{\"file_path\":\"$P/.claude/constitution-stop.last\",\"content\":\"\"}" $NOW)
expect_out "24. Write で .last を deny" "停止 file の改ざん" "$OUT"
newproj p3; user u1 "README を読んで" >> "$T"
OUT=$(pre Edit '{"file_path":".claude/constitution-state.json","old_string":"a","new_string":"b"}' $NOW)
expect_out "25. Edit で状態 file（相対 path）を deny" "停止 file の改ざん" "$OUT"
newproj p4; user u1 "README を読んで" >> "$T"
OUT=$(pre Bash '{"command":"cat .claude/constitution-stop.last"}' $NOW); expect_empty "26. 停止 file の読み取りは許可" "$OUT"

echo "■ (C2) Bash の読み書き判別（保護名を含むコマンドは読み取り専用と確定したときだけ許可）"
# 各ケースは mktemp 配下の偽プロジェクトで hook に判定させるだけで、コマンド自体は実行しない
CASES=("rm -f .claude/constitution-stop" "cat .claude/constitution-stop.last"); FPS=()
bash_case() {   # bash_case <番号> <allow|deny|fp> <command>（fp = origin/main の誤検知を今回許可にしたもの）
  newproj "bc$1"; user u1 "README を読んで" >> "$T"
  if [ "$2" = fp ]; then FPS+=("$3"); else CASES+=("$3"); fi
  OUT=$(pre Bash "{\"command\":$(js "$3")}" $NOW)
  if [ "$2" != deny ]; then
    [ -z "$OUT" ] && [ ! -e "$P/.claude/constitution-stop" ] && ok "C$1. 許可: $3" || ng "C$1. 許可: $3" "${OUT:0:160}"
  else
    expect_out "C$1. deny: $3" "停止 file の改ざん" "$OUT"
  fi
}
bash_case 1 deny 'echo "constitution-stop を確認した" > notes.txt'
bash_case 2 allow 'grep -n constitution-state hooks/x.py | head -5'
bash_case 3 allow 'ls -la .claude/ # constitution-stop は消さない'
bash_case 4 deny 'head -3 .claude/constitution-stop.last 2>/dev/null'
bash_case 5 deny 'test -f .claude/constitution-stop && echo yes >&2'
bash_case 6 allow 'git commit -m "fix: constitution-stop の誤検知"'
bash_case 7 deny 'printf "constitution-violations\n" | wc -l > /tmp/count.txt'
bash_case 8 deny 'rm -f /tmp/x.tmp; cat .claude/constitution-state.json'
bash_case 9 allow 'cp .claude/settings.json /tmp/settings.bak'
bash_case 31 allow 'find .claude -name constitution-stop -print'
bash_case 32 allow 'rg -n constitution-state 03_ClaudeCode && git log --oneline -3'
bash_case 33 allow 'test -f .claude/constitution-stop || echo none'
bash_case 34 deny 'cat x;</dev/null rm .claude/constitution-stop'
bash_case 35 deny 'cat x;>/dev/null rm .claude/constitution-stop'
bash_case 36 deny 'cat x&&</dev/null rm .claude/constitution-stop'
bash_case 37 deny 'cat x
</dev/null rm .claude/constitution-stop'
bash_case 38 deny "echo '{}' >! .claude/constitution-state.json"
bash_case 39 deny "echo '{}' >>! .claude/constitution-state.json"
bash_case 40 deny 'echo x >| .claude/constitution-stop'
bash_case 41 deny 'echo x &> .claude/constitution-stop'
bash_case 42 deny 'cat <> .claude/constitution-stop'
bash_case 43 deny 'rg --pre rm x .claude/constitution-stop'
bash_case 44 deny 'git diff --output=.claude/constitution-state.json'
bash_case 45 deny 'git log -0 --output=.claude/constitution-state.json'
bash_case 46 deny 'find . -maxdepth 0 -fprint0 .claude/constitution-stop'
bash_case 47 deny 'find . -name constitution-stop -fprintf x y'
bash_case 48 deny 'cat .claude/constitution-stop & rm x'
bash_case 49 deny 'sudo cat .claude/constitution-stop'
bash_case 50 deny "rm \$'.claude/constitution-stop'"
bash_case 51 deny 'rm .claude/constitution-stop{,}'
bash_case 52 deny 'cat $(echo .claude/constitution-stop)'
bash_case 53 deny 'git -c core.pager=rm log .claude/constitution-stop'
bash_case 54 deny 'sed -n 1p .claude/constitution-stop.last'
bash_case 55 deny 'awk 1 .claude/constitution-state.json'
bash_case 56 fp 'ls -ln .claude/constitution-stop.last'
bash_case 57 fp 'git commit -m "fix: constitution-stop を rm で消させない"'
bash_case 58 fp 'grep -c cp .claude/constitution-violations.jsonl'
bash_case 10 deny 'echo x > .claude/constitution-stop.last'
bash_case 11 deny 'echo x >> .claude/constitution-violations.jsonl'
bash_case 12 deny 'cat a | tee .claude/constitution-state.json'
bash_case 13 deny "sed -i '' 1d .claude/constitution-stop.last"
bash_case 14 deny 'truncate -s 0 .claude/constitution-stop'
bash_case 15 deny 'cp /dev/null .claude/constitution-stop'
bash_case 16 deny 'mv .claude/constitution-stop /tmp/x'
bash_case 17 deny 'rm .claude/constitution-stop*'
bash_case 19 deny 'F=.claude/constitution-stop; rm "$F"'
bash_case 20 deny 'eval "rm .claude/constitution-stop"'
bash_case 21 deny "bash -c 'rm .claude/constitution-stop'"
bash_case 22 deny "python3 -c 'import os; os.remove(\".claude/constitution-stop\")'"
bash_case 23 deny 'echo .claude/constitution-stop | xargs rm'
bash_case 24 deny 'echo rm .claude/constitution-stop | sh'
bash_case 25 deny 'rm .claude/constitution\-stop'
bash_case 26 deny 'touch .claude/constitution-stop'
bash_case 27 deny 'find .claude -name constitution-stop -delete'
bash_case 28 deny 'cat <<EOF > x
constitution-stop
EOF'
bash_case 29 deny 'ls # c
rm .claude/constitution-stop'
bash_case 30 deny 'cp /tmp/constitution-stop .claude/'

echo "■ (C3) 差分検査: 読み書き判別を入れる前の版（55a855b）で deny の入力は今回も deny（逆転 0 件）"
# 比較基準は fixtures に固定した 55a855b 版。origin/main から取ると、マージ後は基準が今回の版そのものになり
# D3 が必ず落ちる（2026-11-10）。浅い clone の CI でも取れるよう、git の履歴にも頼らない。
# 両版を import し、判定関数に同じ入力群を流す（判定のみ・実行しない）
OLD="$TMP/old"; mkdir -p "$OLD" "$TMP/fakeroot"
BASELINE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fixtures/constitution-gate.baseline-55a855b.py"
printf '%s\0' "${CASES[@]}" > "$TMP/cases.bin"; printf '%s\0' "${FPS[@]}" > "$TMP/fps.bin"
if cp "$BASELINE" "$OLD/constitution-gate.py" 2>/dev/null; then
  DIFF=$(python3 - "$OLD/constitution-gate.py" "$HOOK" "$TMP/cases.bin" "$TMP/fps.bin" "$TMP/fakeroot" <<'PY' 2>&1
import importlib.util, sys
from pathlib import Path
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
old, new = load(sys.argv[1], "gate_old"), load(sys.argv[2], "gate_new")
root = Path(sys.argv[5])
def denied(mod, c):
    return bool(mod.tampers("Bash", {"command": c}, mod.paths(root), root))
def items(p):
    return [c for c in open(p, encoding="utf-8").read().split("\0") if c]
cases, fps = items(sys.argv[3]), items(sys.argv[4])
inv = [c for c in cases if denied(old, c) and not denied(new, c)]
fixed = [c for c in fps if denied(old, c) and not denied(new, c)]
print(f"inputs={len(cases)} inversions={len(inv)} fp_fixed={len(fixed)}/{len(fps)}")
for c in inv:
    print("INV", repr(c))
PY
)
  echo "  $DIFF" | head -5
  expect_out "D1. 差分検査: 逆転 0 件" "inversions=0" "$DIFF"
  expect_out "D2. 入力数が登録数と一致（飛ばしていない）" "inputs=${#CASES[@]} " "$DIFF"
  expect_out "D3. 意図した誤検知の解消は 55a855b 版で deny・今回 allow" "fp_fixed=${#FPS[@]}/${#FPS[@]}" "$DIFF"
else
  ng "D1. 差分検査" "比較基準の fixtures/constitution-gate.baseline-55a855b.py が無い"
fi

echo "■ (b) 事後分析の必須化"
newproj b; user u1 "README を読んで" >> "$T"
printf '%s\t2026-11-03T10:00:00+09:00\t見積欠落\n' "$NOW" > "$P/.claude/constitution-stop.last"
OUT=$(pre Read "$RD" $((NOW + 60)))
expect_out "27. .last より古い学んだこと.md なら deny" "インシデント記録が無い" "$OUT"
expect_nofile "28. 事後分析待ちでは停止 file を書かない" "$P/.claude/constitution-stop"
setmtime "$P/06_保守者向け/学んだこと.md" "$((NOW + 30))"
OUT=$(pre Read "$RD" $((NOW + 60))); expect_empty "29. 新しい学んだこと.md なら許可" "$OUT"
rm "$P/06_保守者向け/学んだこと.md"; mkdir -p "$P/docs"; echo x > "$P/docs/lessons.md"; setmtime "$P/docs/lessons.md" "$((NOW + 30))"
OUT=$(pre Read "$RD" $((NOW + 60))); expect_empty "30. docs/lessons.md へのフォールバック" "$OUT"

echo "■ B. Stop"
newproj s; user u1 "調べて" >> "$T"; agent a1 t1 false >> "$T"
OUT=$(stop); expect_out "31. Agent 走行中（結果なし）は block" '"decision": "block"' "$OUT"
newproj s2; user u1 "調べて" >> "$T"; agent a1 t1 true >> "$T"
result r1 t1 "Async agent launched successfully. agentId: ag-1" >> "$T"
OUT=$(stop); expect_out "32. 背景 Agent の完了通知なしは block" "委譲先が走行中" "$OUT"
user n1 "<task-notification><task-id>ag-1</task-id><status>completed</status></task-notification>" >> "$T"
OUT=$(stop); expect_empty "33. 完了通知が届けば通す" "$OUT"
newproj s3; user u1 "a.py を修正して" >> "$T"; asst a1 "見積：5分" >> "$T"
OUT=$(stop); expect_out "34. 完了行なしは block" "計測区間が未了" "$OUT"
asst a2 "完了。残作業はなし
【見積:5分 | 実測:4分 | 開始:10:00 | 終了:10:04 | 作業時間記録:成功】" >> "$T"
OUT=$(stop); expect_empty "35. 完了行があれば通す" "$OUT"
newproj s4; user u1 "a.py を修正して" >> "$T"; asst a1 "見積：5分" >> "$T"
OUT=$(stop ',"stop_hook_active":true'); expect_empty "36. stop_hook_active は無言" "$OUT"

echo "■ D. fail-closed"
newproj f
OUT=$(cd "$P" && echo '{壊れた' | python3 "$HOOK" pre 2>&1)
expect_out "37. 壊れた JSON は deny" "hook 内部エラー" "$OUT"
OUT=$(cd "$P" && echo '{壊れた' | python3 "$HOOK" stop 2>&1)
expect_out "38. Stop でも壊れた JSON は block" '"decision": "block"' "$OUT"
T="$P/none.jsonl"; OUT=$(pre Read "$RD" $NOW)
expect_out "39. transcript が読めなければ deny（原因を理由に）" "transcript が読めない" "$OUT"
expect_out "40. 読み取り系の deny には注記" "読み取り系も止まる" "$OUT"

echo "■ その他"
newproj o; user u1 "a.py を修正して" >> "$T"
OUT=$(pre Write "$WR" $NOW ',"agent_id":"sub-1"'); expect_empty "41. 委譲先の中では見積ゲートを掛けない" "$OUT"
echo "x	見積欠落	Write" > "$P/.claude/constitution-stop"
OUT=$(pre Read "$RD" $NOW ',"agent_id":"sub-1"'); expect_out "42. 委譲先でも停止中は deny" "停止中" "$OUT"
OUT=$(cd "$P" && python3 "$HOOK" report 2>&1)
expect_out "43. report に停止中の内容" "| 停止中 | x 見積欠落 Write |" "$OUT"
expect_out "44. report に hook-decisions.log の件数" "| hook-decisions.log |" "$OUT"
expect_out "45. AIDD_NOW_EPOCH の使用を log に残す" '"decision": "test-clock"' "$(cat "$AIDD_HOOK_LOG")"

echo ""
echo "結果: PASS=$PASS / FAIL=$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo "✅ 全て正常"; exit 0
else
  echo "⚠ 失敗あり。03_ClaudeCode/hooks/constitution-gate.py を確認してください"; exit 1
fi
