import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).with_name('estimate_guard.py'))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def message(role, text, channel=None):
    return {'type': 'response_item', 'payload': {'type': 'message', 'role': role,
            'channel': channel, 'content': [{'type': 'output_text', 'text': text}]}}


class EstimateGuard(unittest.TestCase):
    def transcript(self, rows):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'rollout.jsonl'
        path.write_text('\n'.join(json.dumps(row, ensure_ascii=False) for row in rows))
        return str(path)

    def denied(self, path):
        result = guard.evaluate({'hook_event_name': 'PreToolUse', 'tool_name': 'apply_patch',
                                'tool_input': {'command': '*** Update File: app.py\n+x'},
                                'transcript_path': path})
        return result.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'

    def test_current_assistant_estimate_allows_code(self):
        path = self.transcript([message('user', '修正して'), message('assistant', '見積：3分\n実装します', 'commentary')])
        self.assertFalse(self.denied(path))

    def test_old_estimate_does_not_authorize_new_request(self):
        path = self.transcript([message('user', '古い依頼'), message('assistant', '見積：3分', 'commentary'), message('user', '新しい修正')])
        self.assertTrue(self.denied(path))

    def test_user_quote_or_analysis_is_not_assistant_estimate(self):
        path = self.transcript([message('user', '見積：3分'), message('assistant', '見積：3分', 'analysis')])
        self.assertTrue(self.denied(path))

    def test_event_user_boundary_and_missing_boundary(self):
        path = self.transcript([{'type': 'event_msg', 'payload': {'type': 'user_message', 'message': '修正'}}, message('assistant', '見積:2分', 'commentary')])
        self.assertFalse(self.denied(path))
        self.assertTrue(self.denied(self.transcript([message('assistant', '見積:2分', 'commentary')])))

    def test_document_patch_and_read_only_are_exempt(self):
        self.assertEqual(guard.classify('apply_patch', {'command': '*** Update File: README.md\n+x'}), 'exempt')
        self.assertEqual(guard.classify('Bash', {'command': 'rg estimate README.md'}), 'read')
        self.assertEqual(guard.classify('apply_patch', {'command': '*** Update File: README.md\n+x\n*** Update File: app.py\n+y'}), 'coding')

    def test_exec_wrapping_and_command_injection_fail_closed(self):
        self.assertEqual(guard.classify('functions.exec', 'text(await tools.exec_command({cmd:"python3 edit.py"}))'), 'coding')
        self.assertEqual(guard.classify('Bash', {'command': 'cat README.md; python3 edit.py'}), 'coding')
        self.assertEqual(guard.classify('Bash', {'command': 'rg --pre=edit.py search README.md'}), 'coding')

    def test_missing_transcript_and_secret_path_deny(self):
        self.assertTrue(self.denied(None))
        self.assertFalse(guard.has_estimate('/tmp/.env'))

    def test_tail_without_user_boundary_fails_closed(self):
        path = self.transcript([message('user', '修正'), message('assistant', 'x' * (guard.LIMIT + 100)), message('assistant', '見積：2分', 'commentary')])
        self.assertTrue(self.denied(path))

    def test_read_named_commands_with_write_options_are_coding(self):
        self.assertEqual(guard.classify('Bash', {'command': 'find . -fprint app.py'}), 'coding')
        self.assertEqual(guard.classify('Bash', {'command': 'git diff --output=app.py'}), 'coding')


if __name__ == '__main__':
    unittest.main()
