#!/usr/bin/env python3
"""Block coding mutations until this turn has an assistant estimate."""
import json
from pathlib import Path
import re
import shlex
import sys

LIMIT = 262144
ESTIMATE = re.compile(r'^見積[:：]\s*[0-9０-９]+(?:[.．][0-9０-９]+)?\s*分\s*$', re.M)
SAFE_SUFFIXES = {'.md', '.toml', '.yaml', '.yml', '.json', '.ini', '.cfg'}
READ_TOOLS = {'read', 'read_file', 'glob', 'grep', 'search', 'view_image',
              'web_search', 'webfetch', 'websearch', 'list_files'}


def secret(path):
    return any(p.lower() in {'.env', '.ssh', '.aws', 'auth.json'}
               or p.lower().startswith(('.env.', 'credential', 'secrets'))
               or Path(p).suffix.lower() in {'.key', '.pem', '.p12', '.pfx'}
               for p in path.parts)


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(x.get('text', '') for x in content if isinstance(x, dict)
                         and x.get('type') in {'input_text', 'output_text', 'text'})
    return ''


def has_estimate(path):
    if not path:
        return False
    path = Path(path)
    if secret(path):
        return False
    try:
        target = path.resolve()
        if secret(target) or not target.is_file():
            return False
        with target.open('rb') as stream:
            stream.seek(0, 2)
            start = max(0, stream.tell() - LIMIT)
            stream.seek(start)
            raw = stream.read(LIMIT)
        if start:
            raw = raw.partition(b'\n')[2]
        found_user = False
        estimate = False
        for line in raw.decode('utf-8').splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            payload = item.get('payload', {})
            if not isinstance(payload, dict):
                continue
            # Rollout response_item messages carry role/channel/content.
            message = (item.get('type') == 'response_item'
                       and payload.get('type') == 'message')
            if message and payload.get('role') == 'user':
                found_user, estimate = True, False
            elif item.get('type') == 'event_msg' and payload.get('type') == 'user_message':
                found_user, estimate = True, False
            elif message and found_user and payload.get('role') == 'assistant' \
                    and payload.get('channel') == 'commentary':
                estimate = estimate or bool(ESTIMATE.search(text_of(payload.get('content'))))
        return found_user and estimate
    except (OSError, UnicodeError, RuntimeError):
        return False


def docs_only(paths):
    return bool(paths) and all(Path(p).suffix.lower() in SAFE_SUFFIXES
                               and not secret(Path(p)) for p in paths)


def classify(name, value):
    """Return coding, exempt, or read. Unknown executable input is coding."""
    name = name.lower().rsplit('.', 1)[-1]
    if name in READ_TOOLS:
        return 'read'
    if name in {'apply_patch', 'write', 'edit', 'multiedit', 'write_file'}:
        if isinstance(value, dict):
            patch = value.get('command', value.get('patch', value.get('input', '')))
            paths = [value[k] for k in ('file_path', 'path') if isinstance(value.get(k), str)]
        else:
            patch, paths = str(value), []
        if isinstance(patch, str):
            paths += re.findall(r'^\*\*\* (?:Add|Update|Delete) File: (.+)$', patch, re.M)
            paths += re.findall(r'^\*\*\* Move to: (.+)$', patch, re.M)
        return 'exempt' if docs_only(paths) else 'coding'
    if name not in {'bash', 'exec', 'exec_command', 'shell', 'shell_command', 'execute'}:
        return 'read'
    command = value.get('cmd', value.get('command', value.get('code', ''))) if isinstance(value, dict) else str(value)
    if not isinstance(command, str) or not command.strip():
        return 'coding'
    # Code-mode wrappers may hide arbitrary shell, Python, or patch execution.
    if name == 'exec' or any(x in command for x in ('$(', '`', '\n', ';', '&&', '||', '|')):
        return 'coding'
    try:
        tokens = shlex.split(command)
    except ValueError:
        return 'coding'
    if not tokens:
        return 'coding'
    binary = Path(tokens[0]).name
    if binary in {'cat', 'rg', 'grep', 'head', 'tail', 'wc', 'ls', 'pwd', 'find', 'stat', 'date'} \
            and not any('>' in t for t in tokens) \
            and not any(t.startswith(('--pre', '-exec', '-ok', '-delete', '-fprint', '-fprintf', '-fls')) for t in tokens):
        return 'read'
    if binary == 'git' and len(tokens) > 1 and tokens[1] in {'status', 'diff', 'show', 'log', 'ls-files', 'rev-parse'} \
            and not any(t.startswith(('--output', '--ext-diff', '--textconv')) for t in tokens):
        return 'read'
    # Only simple explicit shell redirections receive the document exemption.
    if binary in {'echo', 'printf', 'cat'} and re.search(r'\s>{1,2}\s*[^\s]+\s*$', command):
        target = re.split(r'>{1,2}', command)[-1].strip().strip("'\"")
        if docs_only([target]):
            return 'exempt'
    return 'coding'


def evaluate(event):
    if event.get('hook_event_name') == 'UserPromptSubmit':
        return {'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',
                'additionalContext': 'コーディング着手前に独立行「見積：N分」を commentary に表示してください。文書・設定のみは対象外。'}}
    if event.get('hook_event_name') != 'PreToolUse':
        return {}
    kind = classify(str(event.get('tool_name', '')), event.get('tool_input', {}))
    if kind != 'coding' or has_estimate(event.get('transcript_path')):
        return {}
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse',
            'permissionDecision': 'deny',
            'permissionDecisionReason': '現在の依頼に対する見積を確認できません。独立行「見積：N分」を commentary に表示してから再実行してください。'}}


def main():
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError('Hook input must be an object.')
        print(json.dumps(evaluate(event), ensure_ascii=False))
    except (ValueError, OSError, TypeError) as error:
        print('見積検査の入力を確認できません。入力と transcript を確認してください。', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
