#!/usr/bin/env python3
"""Codex のグローバル規約を Claude Code と共有する。既存ファイルは退避する。"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


def sync(home: Path) -> Path | None:
    source = home / ".claude" / "AGENTS.md"
    target = home / ".codex" / "AGENTS.md"
    if not source.is_file():
        raise FileNotFoundError(f"共通規約がありません: {source}")
    if target.is_symlink() and target.resolve() == source.resolve():
        return None
    if target.is_dir():
        raise IsADirectoryError(f"ファイルではありません: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if target.exists() or target.is_symlink():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = target.with_name(f"AGENTS.md.bak-{stamp}")
        target.rename(backup)
    try:
        target.symlink_to("../.claude/AGENTS.md")
    except OSError:
        if backup is not None:
            backup.rename(target)
        raise
    return backup


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    args = parser.parse_args()
    backup = sync(args.home.expanduser().resolve())
    print("共通規約: ~/.codex/AGENTS.md → ~/.claude/AGENTS.md")
    if backup:
        print(f"既存規約の退避先: {backup}")


if __name__ == "__main__":
    main()
