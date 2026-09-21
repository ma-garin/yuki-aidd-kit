#!/usr/bin/env python3
"""工程成果物のコンテンツハッシュを計算する（工程承認を版に縛るため）。

承認記録 `docs/lifecycle/approvals/phase-<n>.md` の `reviewed_hash` に貼る値を出す。
承認後に成果物が1文字でも変われば値が変わり、`check-approval.sh` が承認を失効と判定する。

使い方:
    python3 scripts/phase-hash.py <パス> [<パス> ...]      # ファイルまたはディレクトリ
    python3 scripts/phase-hash.py --staged <パス> ...       # git stage 済みのものだけを対象にする

出力: sha256 先頭16桁。**対象ファイルが1件も無いときは `empty`**
（対象なしを「一致」にしないため。`empty` 同士は一致するが、承認記録側で covers が
空になっていれば `check-approval.sh` が別途 NG にする）。

作法は scripts/ui-hash.py（UI 検証マーカー `.ui-verified` 用）と同一。
ui-hash.py は UI 拡張子に限定した専用版で、そちらは据え置く。
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {".git", "venv", "node_modules", "__pycache__", "dist", "output", "test-results"}


def _expand(args: list[str]) -> list[str]:
    """引数をファイルのリストに展開する。存在しないパスは stderr に出して飛ばす。"""
    files: set[str] = set()
    for a in args:
        p = Path(a)
        if p.is_file():
            files.add(p.as_posix())
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file() and not set(f.parts) & EXCLUDE_DIRS and not f.name.startswith("."):
                    files.add(f.as_posix())
        else:
            print(f"[WARN] 対象が存在しません（無視）: {a}", file=sys.stderr)
    return sorted(files)


def _staged() -> set[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    )
    return {line for line in out.stdout.splitlines() if line}


def main() -> int:
    args = sys.argv[1:]
    staged_only = False
    if args and args[0] == "--staged":
        staged_only, args = True, args[1:]
    if not args or args[0] in ("-h", "--help"):
        print("使い方: phase-hash.py [--staged] <パス> [<パス> ...]", file=sys.stderr)
        return 2

    files = _expand(args)
    if staged_only:
        s = _staged()
        files = [f for f in files if f in s]

    if not files:
        print("empty")
        return 0

    h = hashlib.sha256()
    for f in files:
        h.update(f.encode())
        h.update(Path(f).read_bytes())
    print(h.hexdigest()[:16])
    return 0


if __name__ == "__main__":
    sys.exit(main())
