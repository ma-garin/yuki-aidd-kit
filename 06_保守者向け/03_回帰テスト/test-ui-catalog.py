#!/usr/bin/env python3
"""REQ-UI-001..004: commands, provenance, rejection and portable distribution."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '02_共通/ひな形/components'


class CatalogAcceptance(unittest.TestCase):
    def run_cli(self, *args, directory=SOURCE, code=0):
        result = subprocess.run(['python3', str(directory / 'ui_catalog.py'), *args, '--json'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return json.loads(result.stdout if code == 0 else result.stderr)

    def test_five_intents_and_examples(self):
        for query, identifier in [('保存完了', 'success'), ('保存失敗', 'error'),
                                  ('読み込み中', 'busy'), ('検索結果なし', 'empty'),
                                  ('削除確認', 'confirm')]:
            with self.subTest(query=query):
                found = self.run_cli('search', query)['data']['results']
                self.assertIn(identifier, [item['id'] for item in found])
                item = self.run_cli('show', identifier)['data']
                self.assertIn(item['api'] + '(', item['example'])
                self.assertTrue(item['requires'] and item['returns'])

    def test_zero_limit_and_unknown(self):
        self.assertEqual(self.run_cli('search', '存在しない用途')['data']['match_count'], 0)
        result = self.run_cli('search', '確認', '--limit', '0')['data']
        self.assertGreater(result['match_count'], 0)
        self.assertEqual(result['display_count'], 0)
        self.assertEqual(self.run_cli('show', 'missing', code=1)['code'], 'UNKNOWN_COMPONENT')
        self.assertEqual(self.run_cli('search', ' ', code=1)['code'], 'INVALID_QUERY')

    def test_compact_and_hashes(self):
        full = self.run_cli('show', 'Feedback.confirm')
        compact = self.run_cli('show', 'confirm', '--detail', 'compact')
        self.assertNotIn('example', compact['data'])
        for source in full['meta']['sources']:
            self.assertEqual(source['sha256'], hashlib.sha256(
                (SOURCE / source['path']).read_bytes()).hexdigest())

    def test_portable_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / '.claude/templates/components'
            shutil.copytree(SOURCE, directory)
            shutil.copyfile(SOURCE.parent / 'tokens.css', directory.parent / 'tokens.css')
            before = {p: p.read_bytes() for p in directory.rglob('*') if p.is_file()}
            self.assertEqual(self.run_cli('show', 'confirm', directory=directory),
                             self.run_cli('show', 'confirm'))
            self.assertEqual(self.run_cli('check', directory=directory)['data'],
                             {'specified_count': 5, 'checked_count': 5})
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_invalid_catalogs(self):
        for fault in ('duplicate', 'required', 'missing', 'escape', 'absolute', 'secret'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp) / 'templates/components'
                shutil.copytree(SOURCE, directory)
                shutil.copyfile(SOURCE.parent / 'tokens.css', directory.parent / 'tokens.css')
                target = directory / 'ui-catalog.json'
                data = json.loads(target.read_text())
                item = data['components'][0]
                if fault == 'duplicate':
                    data['components'].append(item)
                elif fault == 'required':
                    del item['example']
                else:
                    item['sources'] = [{'missing': 'missing.js', 'escape': '../../escape.js',
                                       'absolute': '/tmp/source.js', 'secret': '../.env'}[fault]]
                target.write_text(json.dumps(data))
                self.assertEqual(self.run_cli('check', directory=directory, code=1)['code'],
                                 'INVALID_CATALOG')


if __name__ == '__main__':
    unittest.main()
