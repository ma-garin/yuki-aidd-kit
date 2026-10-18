#!/usr/bin/env python3
"""Index all Git-visible kit files; machine reads never imply semantic review."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

SCOPE = {
    "source": "git ls-files -z --cached --others --exclude-standard",
    "includes": "tracked files and non-ignored untracked files",
    "excludes": "untracked ignored files and Git internals; secrets are metadata only",
    "review": "machine byte reads only; semantic review is not asserted",
}


def secret_path(path: Path) -> bool:
    """Check names only, before reading any content or resolving credentials."""
    for part in path.parts:
        name = part.lower()
        if (name in {'.env', '.envrc', '.ssh', '.aws', '.azure', '.kube'} or name.startswith('.env.')
                or name in {'.netrc', '.npmrc', '.pypirc', 'auth.json',
                            'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
                            'token.json', 'tokens.json', 'private-key', 'private_key'}
                or name.startswith(('credential', 'secrets.'))
                or name == 'secrets'
                or Path(name).suffix in {'.pem', '.key', '.p12', '.pfx', '.keystore', '.jks', '.kdbx'}):
            return True
    return False


def default_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if ((candidate / 'INDEX.md').is_file()
                and (candidate / '02_共通').is_dir()
                and (candidate / '04_Codex').is_dir()):
            return candidate
    raise ValueError('Cannot detect kit root; provide --root KIT.')


def safe_path(root: Path, name: str) -> tuple[Path, Path]:
    candidate = Path(name)
    if '..' in candidate.parts:
        raise ValueError('Parent traversal (..) is not allowed.')
    lexical = candidate if candidate.is_absolute() else root / candidate
    try:
        relative = lexical.relative_to(root)
    except ValueError:
        raise ValueError('Path is outside the kit root.') from None
    if '.git' in relative.parts:
        raise ValueError('Git internals are outside the read scope.')
    if secret_path(relative):
        raise ValueError('Secret path is excluded; content was not opened.')
    resolved = lexical.resolve()
    try:
        target_relative = resolved.relative_to(root)
    except ValueError:
        raise ValueError('Symlink target is outside the kit root.') from None
    if '.git' in target_relative.parts or secret_path(target_relative):
        raise ValueError('Resolved target is excluded; content was not opened.')
    return lexical, resolved


def paths_in_git(root: Path, ignored: bool = False) -> list[str]:
    command = ['git', '-C', str(root), 'ls-files', '-z', '--others', '--exclude-standard']
    command.append('--ignored' if ignored else '--cached')
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        raise ValueError('Cannot enumerate Git files: ' +
                         result.stderr.decode('utf-8', errors='replace').strip())
    return sorted(set(p.decode('utf-8', errors='surrogateescape')
                      for p in result.stdout.split(b'\0') if p))


def inspect_file(root: Path, name: str, output: Path | None = None,
                 include_ignored: bool = False) -> tuple[dict[str, Any], str | None]:
    entry: dict[str, Any] = {'path': name, 'semantic_review': 'not-asserted'}
    if secret_path(Path(name)):
        entry['status'] = 'excluded-secret'
        return entry, None
    try:
        lexical, target = safe_path(root, name)
        if output is not None and (lexical == output or target == output):
            entry['status'] = 'report-output'
            return entry, None
        entry['symlink'] = lexical.is_symlink()
        generated = {'node_modules', 'venv', '.venv', '__pycache__', '.pytest_cache',
                     '.mypy_cache', '.ruff_cache', '.cache', '.tox', '.next',
                     '.gradle', 'dist', 'build', 'target', 'coverage',
                     'test-results', 'playwright-report'}
        if include_ignored and ((set(Path(name).parts) | set(target.relative_to(root).parts)) & generated or
                                Path(name).name == '.DS_Store'):
            entry.update(status='excluded-dependency-cache',
                         bytes=lexical.lstat().st_size, machine_read='metadata-only')
            return entry, None
        entry['category'] = Path(name).parts[0] if '/' in name else 'root'
        if not target.is_file():
            entry['status'] = 'missing' if not target.exists() else 'non-file'
            return entry, None
        raw = target.read_bytes()
        entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                     machine_read='all-bytes')
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            entry.update(status='binary', utf8=False, lines=None, headings=[])
            return entry, None
        if '\0' in content:
            entry.update(status='binary', utf8=True, lines=None, headings=[])
            return entry, None
        entry.update(status='text', utf8=True,
                     lines=len(content.splitlines()),
                     headings=re.findall(r'^#{1,6}\s+(.+?)\s*#*\s*$', content, re.M))
        return entry, content
    except ValueError as error:
        entry.update(status='excluded-path', reason=str(error))
    except (OSError, RuntimeError) as error:
        entry.update(status='error', reason=str(error))
    return entry, None


def summarize(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = {}
    for entry in entries:
        key = entry['status']
        counts[key] = counts.get(key, 0) + 1
    return counts


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', help='Kit root; otherwise detect script ancestors.')
    commands = parser.add_subparsers(dest='command', required=True)
    inventory = commands.add_parser('inventory', help='Read every in-scope file once.')
    inventory.add_argument('--output', help='Write complete JSON ledger to this path.')
    inventory.add_argument('--include-ignored', action='store_true',
                           help='Include ignored paths; dependency/cache contents excluded.')
    search = commands.add_parser('search', help='Literal search through all text files.')
    search.add_argument('query')
    search.add_argument('--limit', type=int, default=20)
    reader = commands.add_parser('read', help='Read a full UTF-8 file or inclusive lines.')
    reader.add_argument('path')
    reader.add_argument('--start', type=int, default=1)
    reader.add_argument('--end', type=int)
    args = parser.parse_args()
    try:
        root = Path(args.root).expanduser().resolve() if args.root else default_root()
        if args.command == 'read':
            if args.start < 1 or (args.end is not None and args.end < args.start):
                raise ValueError('Use 1-based inclusive lines with end >= start.')
            _, target = safe_path(root, args.path)
            raw = target.read_bytes()
            content = raw.decode('utf-8')
            if '\0' in content:
                raise ValueError('Binary files cannot be read as text.')
            if args.start == 1 and args.end is None:
                sys.stdout.write(content)
            else:
                sys.stdout.write(''.join(content.splitlines(keepends=True)[
                    args.start - 1:args.end]))
            return 0
        if args.command == 'search' and (not args.query or args.limit < 0):
            raise ValueError('Search needs a nonempty query and a nonnegative limit.')
        names = paths_in_git(root)
        include_ignored = args.command == 'inventory' and args.include_ignored
        ignored_names = set(paths_in_git(root, ignored=True)) if include_ignored else set()
        names = sorted(set(names) | ignored_names)
        output = (Path(args.output).expanduser().absolute().resolve()
                  if args.command == 'inventory' and args.output else None)
        if output is not None:
            if secret_path(output):
                raise ValueError('Report output cannot be a secret path.')
            try:
                output_name = str(output.relative_to(root))
            except ValueError:
                pass
            else:
                if '.git' in Path(output_name).parts:
                    raise ValueError('Report output cannot be inside Git internals.')
                if output_name not in names:
                    names.append(output_name)
                    names.sort()
        entries = []
        matches = []
        matching_lines = occurrences = 0
        for name in names:
            entry, content = inspect_file(root, name, output, include_ignored)
            entry['git_ignored'] = name in ignored_names
            entries.append(entry)
            if args.command == 'search' and content is not None:
                for number, line in enumerate(content.splitlines(), 1):
                    count = line.count(args.query)
                    if count:
                        matching_lines += 1
                        occurrences += count
                        if len(matches) < args.limit:
                            matches.append({'path': name, 'line': number,
                                            'occurrences': count, 'text': line})
        scope = dict(SCOPE)
        if include_ignored:
            scope.update(source=SCOPE['source'] + ' plus git ls-files --others --ignored --exclude-standard -z',
                         includes='tracked, non-ignored untracked and ignored paths',
                         excludes='Git internals; dependency/cache and secret contents excluded',
                         ignored=True)
        result = {'root': str(root), 'scope': scope, 'files': len(entries),
                  'counts': summarize(entries)}
        if args.command == 'inventory':
            result['entries'] = entries
            if output is not None:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, ensure_ascii=True, indent=2)
                                  + '\n', encoding='utf-8')
                emit({'files': len(entries), 'counts': result['counts']})
            else:
                emit(result)
        else:
            result.update(query=args.query, matching_lines=matching_lines,
                          occurrences=occurrences, shown=len(matches), matches=matches)
            emit(result)
        return 1 if result['counts'].get('error') or result['counts'].get('missing') else 0
    except (ValueError, OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
