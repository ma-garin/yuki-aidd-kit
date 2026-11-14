#!/usr/bin/env python3
"""Read-only, offline UI reference shared by Claude Code and Codex."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


class CatalogError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def load(directory):
    catalog = directory / 'ui-catalog.json'
    try:
        data = json.loads(catalog.read_text(encoding='utf-8'))
        if (data['schema_version'] != 1 or not isinstance(data['components'], list)
                or not data['components']):
            raise ValueError('仕様形式が違います')
        ids = set()
        for item in data['components']:
            for key in ('id', 'title', 'api', 'arguments', 'returns', 'example'):
                if not isinstance(item[key], str) or not item[key].strip():
                    raise ValueError('必須項目がありません: ' + key)
            for key in ('keywords', 'notes', 'sources', 'requires'):
                if not isinstance(item[key], list) or not item[key] or not all(
                        isinstance(v, str) and v.strip() for v in item[key]):
                    raise ValueError('必須リストがありません: ' + key)
            if item['id'] in ids:
                raise ValueError('部品IDが重複しています')
            ids.add(item['id'])
            for source in item['sources']:
                path = Path(source)
                resolved = (directory / path).resolve()
                if (path.suffix not in ('.js', '.css') or path.is_absolute()
                        or not resolved.is_relative_to(directory.parent.resolve())):
                    raise ValueError('参照先がテンプレート範囲外です')
                if not resolved.is_file():
                    raise ValueError('参照先がありません: ' + source)
        return data
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CatalogError('INVALID_CATALOG', '部品台帳を確認してください: ' + str(error)) from error


def reference(directory, data, items):
    sources = sorted({s for item in items for s in item['sources']})
    return {'schema_version': data['schema_version'],
            'catalog_sha256': hashlib.sha256((directory / 'ui-catalog.json').read_bytes()).hexdigest(),
            'sources': [{'path': s, 'sha256': hashlib.sha256(
                (directory / s).read_bytes()).hexdigest()} for s in sources]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('search', 'show', 'check'):
        command = commands.add_parser(name)
        command.add_argument('--json', action='store_true')
        if name == 'search':
            command.add_argument('query')
            command.add_argument('--limit', type=int, default=20)
        if name == 'show':
            command.add_argument('id')
            command.add_argument('--detail', choices=('compact', 'full'), default='full')
    args = parser.parse_args(argv)
    directory = Path(__file__).resolve().parent
    try:
        data = load(directory)
        all_items = data['components']
        items = all_items
        if args.command == 'search':
            query = args.query.strip().casefold()
            if not query or args.limit < 0:
                raise CatalogError('INVALID_QUERY', '検索語と0以上の表示件数を指定してください')
            items = [i for i in all_items if query in ' '.join(
                [i['id'], i['title'], i['api']] + i['keywords']).casefold()]
            count = len(items)
            items = items[:args.limit]
            payload = {'match_count': count, 'display_count': len(items), 'results': [
                {'id': i['id'], 'title': i['title'], 'api': i['api'],
                 'next': 'python3 ui_catalog.py show ' + i['id']} for i in items]}
        elif args.command == 'show':
            items = [i for i in all_items if args.id in (i['id'], i['api'])]
            if not items:
                raise CatalogError('UNKNOWN_COMPONENT', '部品が見つかりません。searchで用途を検索してください')
            payload = dict(items[0])
            if args.detail == 'compact':
                payload = {k: payload[k] for k in ('id', 'title', 'api', 'notes')}
        else:
            payload = {'specified_count': len(all_items), 'checked_count': len(all_items)}
        result = {'api_version': 1, 'type': args.command, 'data': payload,
                  'meta': reference(directory, data, items)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == 'show':
            print('\n'.join(f'{k}: ' + (v if isinstance(v, str) else json.dumps(
                v, ensure_ascii=False)) for k, v in payload.items()))
            print('参照元: ' + json.dumps(result['meta'], ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except CatalogError as error:
        print(json.dumps({'api_version': 1, 'code': error.code, 'error': str(error),
                          'action': '台帳と参照先を確認し、searchまたはcheckを再実行してください'},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
