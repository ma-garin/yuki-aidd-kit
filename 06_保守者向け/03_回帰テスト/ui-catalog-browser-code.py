#!/usr/bin/env python3
"""Print code for Playwright browser_run_code_unsafe; no server or dependencies needed."""
import json
from pathlib import Path
root = Path(__file__).resolve().parents[2]
directory = root / '02_共通/ひな形/components'
assets = {'items': json.loads((directory / 'ui-catalog.json').read_text())['components'],
          'css': (directory.parent / 'tokens.css').read_text(),
          'js': (directory / 'feedback.js').read_text()}
fn = Path(__file__).with_name('ui-catalog-browser.cjs').read_text()
print('async page => (' + fn + ')(page,' + json.dumps(assets) + ')')
