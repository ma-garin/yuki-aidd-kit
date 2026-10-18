#!/usr/bin/env python3
"""Claude Code 用 hook を Codex CLI の hook から呼ぶ薄いアダプタ（原本は複製しない）。

使い方（hooks.json の command）:
  python3 codex_hook_adapter.py pretool <原本 hook のパス> [--explore]
  python3 codex_hook_adapter.py passthrough <原本 hook のパス>

Codex 0.163.0 の入出力（同梱 JSON スキーマ `pre-tool-use.command.input/output` で確認）:
- stdin: hook_event_name / tool_name / tool_input / cwd / transcript_path / turn_id 等
- deny: {"hookSpecificOutput": {"hookEventName": "PreToolUse",
         "permissionDecision": "deny", "permissionDecisionReason": "<非空>"}}
- PreToolUse の permissionDecision は allow / ask を受け付けない（"unsupported" として扱われる）。

pretool の変換:
- シェル系ツール（tool_name が Bash / shell / exec_command 等、または tool_input に
  command・cmd の文字列／配列がある）を Claude 形式 {"tool_name": "Bash",
  "tool_input": {"command": "..."}} に直して原本へ渡す。`["bash", "-lc", "<cmd>"]` は <cmd> を取り出す。
- `--explore`: 実装モード（<cwd>/.claude/mode）で読取系コマンド（cat / grep / rg / find 等）を
  Read / Grep / Glob として block-explore.sh に渡す。
- 原本の deny・exit 2 は Codex の deny に、原本の ask は deny に変える（Codex は ask 非対応。安全側）。
  allow・追加文脈・updatedInput は捨てる（Codex の PreToolUse は allow / updatedInput を拒否する）。
- stdin が読めない・原本を起動できないときは deny（fail-closed）。

passthrough: 出力形式が同じ hook（UserPromptSubmit / SubagentStart の additionalContext）を
そのまま実行し、stdout を返す。失敗しても止めない（注入のみの hook のため）。

AIDD_CODEX_HOOK_LOG=<ファイル> を設定すると、受け取った tool_name と tool_input のキーだけを追記する
（中身は書かない。Codex のツール名の実測用）。
"""
import json
import os
import shlex
import subprocess
import sys

SHELL_TOOLS = {'bash', 'shell', 'shell_command', 'exec_command', 'local_shell', 'exec', 'execute'}
WRITE_TOOLS = {'apply_patch', 'write', 'edit', 'multiedit', 'write_file'}
READ_BINS = {'cat': 'Read', 'head': 'Read', 'tail': 'Read', 'less': 'Read', 'sed': 'Read',
             'nl': 'Read', 'bat': 'Read', 'grep': 'Grep', 'rg': 'Grep', 'ag': 'Grep',
             'egrep': 'Grep', 'fgrep': 'Grep', 'git-grep': 'Grep', 'find': 'Glob',
             'fd': 'Glob', 'ls': 'Glob', 'tree': 'Glob'}
TIMEOUT = 10


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': reason.strip() or 'AIDD hook が拒否しました'}},
        ensure_ascii=False))
    return 0


def shell_command(name, value):
    """シェル実行なら文字列のコマンドを返す。シェルでなければ None。"""
    short = name.lower().rsplit('.', 1)[-1]
    if short in WRITE_TOOLS or not isinstance(value, dict):
        return None
    cmd = value.get('command', value.get('cmd'))
    if isinstance(cmd, list) and all(isinstance(x, str) for x in cmd):
        if len(cmd) >= 3 and os.path.basename(cmd[0]) in {'bash', 'sh', 'zsh'} \
                and cmd[1] in {'-c', '-lc', '-ic'}:
            cmd = cmd[2]
        else:
            cmd = shlex.join(cmd)
    if isinstance(cmd, str) and (short in SHELL_TOOLS or cmd.strip()):
        return cmd
    return None


def explore_tool(cmd):
    """読取系コマンドなら Read / Grep / Glob を返す。"""
    try:
        tokens = shlex.split(cmd)
    except ValueError:
        return None
    while tokens and '=' in tokens[0] and not tokens[0].startswith('-'):
        tokens = tokens[1:]
    if not tokens:
        return None
    first = os.path.basename(tokens[0])
    if first == 'git' and len(tokens) > 1 and tokens[1] == 'grep':
        first = 'git-grep'
    if first == 'sed' and any(t.startswith(('-i', '--in-place')) for t in tokens[1:]):
        return None  # sed -i は書き込み。探索ではない
    return READ_BINS.get(first)


def log_shape(data):
    path = os.environ.get('AIDD_CODEX_HOOK_LOG')
    if not path:
        return
    ti = data.get('tool_input')
    row = {'event': data.get('hook_event_name'), 'tool_name': data.get('tool_name'),
           'input_keys': sorted(ti) if isinstance(ti, dict) else type(ti).__name__}
    try:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except OSError:
        pass


def run_hook(hook, payload, cwd):
    argv = ['bash', hook] if hook.endswith('.sh') else [sys.executable, hook]
    env = dict(os.environ)
    if cwd and os.path.isdir(cwd):
        env.setdefault('CLAUDE_PROJECT_DIR', cwd)
    return subprocess.run(argv, input=json.dumps(payload, ensure_ascii=False), text=True,
                          capture_output=True, timeout=TIMEOUT, env=env,
                          cwd=cwd if cwd and os.path.isdir(cwd) else None)


def to_codex(proc, label):
    if proc.returncode == 2:
        return deny(proc.stderr or f'{label} が拒否しました')
    try:
        out = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except ValueError:
        return 0
    spec = out.get('hookSpecificOutput') or {}
    decision = spec.get('permissionDecision')
    reason = spec.get('permissionDecisionReason') or out.get('reason') or ''
    if decision == 'deny' or out.get('decision') == 'block':
        return deny(reason or f'{label} が拒否しました')
    if decision == 'ask':
        return deny('Codex は確認（ask）に対応しないため拒否しました。必要なら利用者が手で実行してください。\n'
                    + reason)
    return 0


def pretool(hook, explore):
    label = os.path.basename(hook)
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError('object でない')
    except ValueError:
        return deny(f'{label}: hook の入力が読めないため拒否しました（fail-closed）')
    log_shape(data)
    cmd = shell_command(str(data.get('tool_name', '')), data.get('tool_input'))
    payload = dict(data)
    if cmd is not None:
        payload['tool_name'] = 'Bash'
        payload['tool_input'] = {'command': cmd}
        if explore:
            tool = explore_tool(cmd)
            if tool is None:
                return 0
            payload['tool_name'] = tool
    elif explore:
        return 0
    try:
        proc = run_hook(hook, payload, data.get('cwd'))
    except (OSError, subprocess.SubprocessError) as exc:
        return deny(f'{label} を起動できないため拒否しました（{type(exc).__name__}）。'
                    '04_Codex/hooks/install.sh を再実行してください')
    return to_codex(proc, label)


def passthrough(hook):
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        cwd = data.get('cwd') if isinstance(data, dict) else None
        proc = run_hook(hook, data, cwd)
    except (ValueError, OSError, subprocess.SubprocessError):
        return 0
    if proc.returncode == 0 and proc.stdout.strip():
        sys.stdout.write(proc.stdout)
    return 0


def main(argv):
    if len(argv) < 3 or argv[1] not in {'pretool', 'passthrough'}:
        print('usage: codex_hook_adapter.py pretool|passthrough <hook> [--explore]', file=sys.stderr)
        return 1
    if argv[1] == 'pretool':
        return pretool(argv[2], '--explore' in argv[3:])
    return passthrough(argv[2])


if __name__ == '__main__':
    sys.exit(main(sys.argv))
