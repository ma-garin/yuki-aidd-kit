#!/usr/bin/env bash
# Codex CLI に AIDD の hook（block-destructive / block-gates / block-ci / block-explore ほか）を配線する。
# - 原本の hook は ~/.claude/hooks（無ければこのリポジトリの 03_ClaudeCode/hooks）を参照する。複製しない
# - アダプタだけを ~/.codex/aidd-hooks/ に置く（worktree が消えても動くように）
# - 既存の ~/.codex/hooks.json は hooks.json.bak-<日時> に退避してから、既存定義を残してマージする
# 使い方: ./04_Codex/hooks/install.sh   （CODEX_HOME・AIDD_CLAUDE_HOOKS_DIR で上書き可）
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_HOOKS="$(cd "$HERE/../../03_ClaudeCode/hooks" && pwd)"
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
HOOKS_DIR="${AIDD_CLAUDE_HOOKS_DIR:-$HOME/.claude/hooks}"
if [ ! -f "$HOOKS_DIR/block-destructive.py" ] || [ ! -f "$HOOKS_DIR/secret_patterns.py" ]; then
  HOOKS_DIR="$REPO_HOOKS"
fi

mkdir -p "$CODEX_DIR/aidd-hooks"
cp "$HERE/codex_hook_adapter.py" "$CODEX_DIR/aidd-hooks/codex_hook_adapter.py"
ADAPTER="$CODEX_DIR/aidd-hooks/codex_hook_adapter.py"
TARGET="$CODEX_DIR/hooks.json"

if [ -f "$TARGET" ]; then
  BAK="$TARGET.bak-$(date +%Y%m%d%H%M%S)"
  cp "$TARGET" "$BAK"
  echo "退避: $BAK"
fi

python3 - "$HERE/hooks.json.template" "$TARGET" "$ADAPTER" "$HOOKS_DIR" <<'PY'
import json, os, sys
tmpl, target, adapter, hooks = sys.argv[1:5]
new = json.loads(open(tmpl, encoding='utf-8').read()
                 .replace('__ADAPTER__', adapter).replace('__HOOKS__', hooks))
cur = {'hooks': {}}
if os.path.exists(target):
    with open(target, encoding='utf-8') as f:
        cur = json.load(f)  # 壊れていれば失敗して止める（退避は済んでいる）
cur.setdefault('hooks', {})
for event, groups in cur['hooks'].items():  # 前回の AIDD 定義を外す（冪等）
    for g in groups:
        g['hooks'] = [h for h in g.get('hooks', []) if 'codex_hook_adapter.py' not in h.get('command', '')]
    cur['hooks'][event] = [g for g in groups if g.get('hooks')]
for event, groups in new['hooks'].items():
    cur['hooks'].setdefault(event, []).extend(groups)
tmp = target + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(cur, f, ensure_ascii=False, indent=2)
    f.write('\n')
os.replace(tmp, target)
print(f'書き込み: {target}（原本 hook: {hooks}）')
PY
echo "次の行動: Codex を再起動し /hooks で AIDD の hook を確認・信頼してください。"
