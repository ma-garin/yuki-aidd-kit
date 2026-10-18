"""Codex 形式の stdin を入れ、アダプタ経由で原本 hook の deny が Codex 形式で返ることを確かめる。

実行: python3 -m unittest discover -s 04_Codex/hooks -p 'test_codex_hook_adapter.py'
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ADAPTER = HERE / 'codex_hook_adapter.py'
HOOKS = HERE.parent.parent / '03_ClaudeCode' / 'hooks'


def codex_event(tool_name, tool_input, cwd):
    """Codex 0.163.0 の pre-tool-use.command.input の必須項目を満たす入力。"""
    return {'session_id': 's', 'turn_id': 't', 'tool_use_id': 'u', 'transcript_path': None,
            'cwd': cwd, 'hook_event_name': 'PreToolUse', 'model': 'gpt-5',
            'permission_mode': 'default', 'tool_name': tool_name, 'tool_input': tool_input}


class Adapter(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.cwd = tmp.name

    def run_adapter(self, hook, stdin, *extra):
        proc = subprocess.run([sys.executable, str(ADAPTER), 'pretool', str(HOOKS / hook), *extra],
                              input=stdin, text=True, capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    def decision(self, hook, tool_name, tool_input, *extra):
        out = self.run_adapter(hook, json.dumps(codex_event(tool_name, tool_input, self.cwd)), *extra)
        spec = out.get('hookSpecificOutput', {})
        if spec.get('permissionDecision') == 'deny':
            self.assertEqual(spec.get('hookEventName'), 'PreToolUse')
            self.assertTrue(spec.get('permissionDecisionReason', '').strip())
        return spec.get('permissionDecision')

    def test_git_add_all_is_denied_for_each_shell_shape(self):
        for name, value in [('Bash', {'command': 'git add -A'}),
                            ('shell', {'command': ['bash', '-lc', 'git add -A']}),
                            ('exec_command', {'cmd': 'git add -A'})]:
            with self.subTest(name=name):
                self.assertEqual(self.decision('block-destructive.py', name, value), 'deny')

    def test_reset_hard_is_denied(self):
        self.assertEqual(self.decision('block-destructive.py', 'shell',
                                       {'command': ['bash', '-lc', 'git reset --hard HEAD']}), 'deny')

    def test_harmless_command_passes_destructive(self):
        self.assertIsNone(self.decision('block-destructive.py', 'shell', {'command': 'git status --short'}))

    def test_gate_without_request_is_denied(self):
        self.assertEqual(self.decision('block-gates.py', 'shell', {'command': 'pytest -q'}), 'deny')

    def test_gate_with_request_passes(self):
        self.assertIsNone(self.decision('block-gates.py', 'shell', {'command': 'GATES_REQUESTED=1 pytest -q'}))

    def test_patch_tool_is_not_treated_as_shell(self):
        self.assertIsNone(self.decision('block-gates.py', 'apply_patch', {'command': '*** pytest'}))

    def test_explore_denied_only_in_implement_mode(self):
        self.assertIsNone(self.decision('block-explore.sh', 'shell', {'command': 'cat a.py'}, '--explore'))
        (Path(self.cwd) / '.claude').mkdir()
        (Path(self.cwd) / '.claude' / 'mode').write_text('implement')
        self.assertEqual(self.decision('block-explore.sh', 'shell', {'command': 'rg foo'}, '--explore'), 'deny')
        self.assertIsNone(self.decision('block-explore.sh', 'shell', {'command': 'sed -i s/a/b/ x'}, '--explore'))
        self.assertIsNone(self.decision('block-explore.sh', 'shell', {'command': 'python3 x.py'}, '--explore'))

    def test_unreadable_stdin_fails_closed(self):
        out = self.run_adapter('block-destructive.py', 'not json')
        self.assertEqual(out['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_missing_hook_fails_closed(self):
        proc = subprocess.run([sys.executable, str(ADAPTER), 'pretool', str(HOOKS / 'nope.py')],
                              input=json.dumps(codex_event('shell', {'command': 'ls'}, self.cwd)),
                              text=True, capture_output=True, timeout=30)
        # 原本が無い → python が exit 2 で落ちる → deny
        self.assertEqual(json.loads(proc.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_template_is_valid_json(self):
        data = json.loads((HERE / 'hooks.json.template').read_text(encoding='utf-8'))
        self.assertIn('PreToolUse', data['hooks'])


if __name__ == '__main__':
    unittest.main()
