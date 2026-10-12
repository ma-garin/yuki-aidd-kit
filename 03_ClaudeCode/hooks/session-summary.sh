#!/bin/bash
# session-summary.sh
# セッション終了時: コミット忘れ防止・implement.md更新リマインド・要約の型（G2）
# 要約の型は 依頼／調べた事／学び／完了／次手 の 5 項目。LLM は呼ばない。
# 調べた事・完了の欄には .claude/observations.jsonl（observe.py）の最新セッション分から件数と変更したファイル名を下書きとして入れる
# （観測が無い・python3 が無いときは空欄のまま。常に exit 0）

UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l)

echo "=== [AIDD Hook: session-end] ==="

if [ "$UNCOMMITTED" -gt 0 ]; then
  echo "⚠ 未コミットファイル: ${UNCOMMITTED}件"
  git status --short 2>/dev/null | head -10
  echo "→ git add / git commit を忘れずに"
fi

# implement.mdの最終更新確認
if [ -f "implement.md" ]; then
  LAST=$(date -r implement.md "+%Y-%m-%d" 2>/dev/null || stat -c "%y" implement.md 2>/dev/null | cut -d' ' -f1)
  TODAY=$(date "+%Y-%m-%d")
  if [ "$LAST" != "$TODAY" ]; then
    echo "📝 implement.md が今日未更新 → 作業内容を記録してください"
  fi
fi

# 要約の型（CURRENT_STATE.md・implement.md・retro に残すときはこの 5 項目で書く）
OBS="${AIDD_OBSERVATIONS:-${CLAUDE_PROJECT_DIR:-.}/.claude/observations.jsonl}"
HINTS=""
if [ -f "$OBS" ] && command -v python3 >/dev/null 2>&1; then
  HINTS=$(python3 - "$OBS" 2>/dev/null <<'PY'
import json, sys
recs = []
for line in open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines()[-500:]:
    try:
        d = json.loads(line)
    except ValueError:
        continue
    if isinstance(d, dict):
        recs.append(d)
if recs:
    sid = recs[-1].get("sid")
    recs = [d for d in recs if d.get("sid") == sid]
reads = sum(1 for d in recs if d.get("op") in ("read", "search", "fetch"))
changed = []
for d in recs:
    p = str(d.get("path") or "")
    if d.get("op") in ("write", "edit") and p and p not in changed:
        changed.append(p)
print(f"（観測: 読む・探す {reads} 件）" if reads else "")
print((f"（観測: 変更 {len(changed)} 件: " + "、".join(changed[-3:]) + "）") if changed else "")
PY
)
fi
READ_HINT=$(printf '%s\n' "$HINTS" | sed -n 1p)
DONE_HINT=$(printf '%s\n' "$HINTS" | sed -n 2p)
echo "--- 要約の型（依頼／調べた事／学び／完了／次手）---"
echo "依頼: "
echo "調べた事: ${READ_HINT}"
echo "学び: "
echo "完了: ${DONE_HINT}"
echo "次手: "
echo "================================="
exit 0
