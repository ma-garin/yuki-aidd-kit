#!/bin/bash
# run-all.sh — 回帰テスト（同ディレクトリの test-*.sh）を全本実行する。CI はこの 1 本だけを呼ぶ。
# 本数を CI の yml に手で並べない（掲載漏れの再発防止）。RUN≠FOUND または FAIL>0 で exit 1。
# ゲートなので GATES_REQUESTED=1 が無ければ実行しない（exit 2）。
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${GATES_REQUESTED:-}" ]; then
  echo "回帰テストの全本実行はゲートです。実行するなら GATES_REQUESTED=1 bash $0 を使ってください。" >&2
  exit 2
fi
LOGDIR=$(mktemp -d)
trap 'find "$LOGDIR" -delete 2>/dev/null' EXIT
FOUND=0; RUN=0; PASS=0; FAIL=0
for t in "$DIR"/test-*.sh; do
  [ -f "$t" ] || continue
  FOUND=$((FOUND+1))
  name=$(basename "$t"); log="$LOGDIR/$name.log"
  RUN=$((RUN+1))
  if bash "$t" >"$log" 2>&1; then
    PASS=$((PASS+1)); echo "OK   $name"
  else
    # 失敗したケースの行（❌）を先に出す。末尾 20 行だけでは、途中で落ちたケースの名前が見えない（2026-11-10）
    FAIL=$((FAIL+1)); echo "FAIL $name"; grep -F '❌' "$log" | head -n 20 | sed 's/^/     ! /'; tail -n 20 "$log" | sed 's/^/     | /'
  fi
done
echo "RUN=$RUN FOUND=$FOUND PASS=$PASS FAIL=$FAIL"
[ "$RUN" -eq "$FOUND" ] && [ "$FAIL" -eq 0 ] && exit 0
exit 1
