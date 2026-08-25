#!/usr/bin/env python3
"""UI ファイル（.html/.js/.css）のコンテンツハッシュを計算する（クロスプラットフォーム）。

使い方:
    python3 scripts/ui-hash.py disk    # git 管理対象の UI ファイル全体
    python3 scripts/ui-hash.py staged  # git staged の UI ファイル
環境変数 UI_HASH_EXCLUDE_PREFIXES（カンマ区切り。既定 "docs/"）で対象外の接頭辞を指定する
（docs/ 配下の HTML/JS/CSS は設計モックであり実 UI ではない）。
.ui-verified マーカーとの照合は scripts/pre-commit-ui-gate.sh。
出所: WebSpec2Doc scripts/ui-hash.py。
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

UI_EXTENSIONS = {".html", ".js", ".css"}
EXCLUDE_DIRS = {".git", "venv", "node_modules", "output", "__pycache__", "dist", "test-results"}
EXCLUDE_PREFIXES = tuple(
    p for p in os.environ.get("UI_HASH_EXCLUDE_PREFIXES", "docs/").split(",") if p
)


def _filter(lines: list[str]) -> list[str]:
    return sorted(
        f
        for f in lines
        if Path(f).suffix in UI_EXTENSIONS
        and not set(Path(f).parts) & EXCLUDE_DIRS
        and not f.startswith(EXCLUDE_PREFIXES)
    )


def _ui_files_on_disk() -> list[str]:
    # git 管理対象（追跡済み＋未追跡だが無視されないもの）のみ。rglob だと per-run 生成物が混入し hash が揺れる。
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True
    )
    return _filter(out.stdout.splitlines())


def _ui_files_staged() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"], capture_output=True, text=True
    )
    return _filter(out.stdout.splitlines())


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "disk"
    files = _ui_files_staged() if mode == "staged" else _ui_files_on_disk()
    h = hashlib.sha256()
    for f in files:
        p = Path(f)
        if p.is_file():
            h.update(f.encode())
            h.update(p.read_bytes())
    print(h.hexdigest()[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
