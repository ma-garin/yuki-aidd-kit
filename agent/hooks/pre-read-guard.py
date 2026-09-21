#!/usr/bin/env python3
"""読む価値の無いファイルを止め、大きすぎるファイルは先頭だけに絞る PreToolUse フック（Read）。

`context-compression` 原則 2「大きいファイルは行範囲指定で部分読みする」を散文から機械に移したもの。

  - deny: ロックファイル・minified・source map・node_modules / dist / build / .git 配下・キットの生成レポート
          （読んでも判断材料にならない。必要なら grep で該当行だけ取る）
  - 切り詰め: READ_GUARD_MAX_LINES（既定 800）行超のファイルを offset も limit も無しに読む
          → updatedInput で limit=READ_GUARD_LIMIT（既定 300）。systemMessage で全体の行数と続きの読み方を伝える
  - それ以外・バイナリ（画像/PDF は Read が自前で扱う）は素通り

逃がし口は offset / limit の明示（既に Read が持っている）。環境変数のバイパスは作らない。
`block-explore.sh`（実装モードの探索ブロック）と同じ matcher に前段として並べる。deny が 1 つでもあれば deny が勝つ。
"""
import json
import os
import re
import sys
from pathlib import Path

LOCK_FILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock",
              "Gemfile.lock", "composer.lock", "Pipfile.lock", "uv.lock"}
GENERATED_SUFFIX = (".min.js", ".min.css", ".map", ".bundle.js")
GENERATED_DIRS = {"node_modules", "dist", "build", ".git", "__pycache__", ".venv", "venv", "coverage", ".next"}
REPORT_RE = re.compile(r"^(?:check-[a-z-]+|trace-check|token-audit|test-metrics)-report\.md$")
MAX_LINES = int(os.environ.get("READ_GUARD_MAX_LINES", "800"))
LIMIT = int(os.environ.get("READ_GUARD_LIMIT", "300"))


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    return 0


def worthless(p: Path) -> str | None:
    if p.name in LOCK_FILES:
        return f"ロックファイルは読まない（{p.name}）。依存の確認は package.json / pyproject.toml を読むか `grep -n \"<pkg>\" {p.name}` で該当行だけ取る"
    if p.name.endswith(GENERATED_SUFFIX):
        return f"minified / 生成物は読まない（{p.name}）。元ソースを読む"
    hit = set(p.parts) & GENERATED_DIRS
    if hit:
        return f"{'/'.join(sorted(hit))} 配下は読まない（{p.as_posix()}）。依存の中身が要るなら `grep -rn` で該当行だけ取る"
    if REPORT_RE.match(p.name):
        return f"生成レポート（{p.name}）は全件表なので読まない。結論は生成元スクリプトの標準出力（3 層要約）にある。特定の行が要るなら grep する"
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Read":
        return 0
    tool_input = data.get("tool_input", {}) or {}
    fp = tool_input.get("file_path", "")
    if not fp:
        return 0
    p = Path(fp)

    reason = worthless(p)
    if reason:
        return deny(reason + "（pre-read-guard.py）")

    if tool_input.get("offset") is not None or tool_input.get("limit") is not None:
        return 0
    if not p.is_file():
        return 0
    try:
        with p.open("rb") as f:
            head = f.read(8192)
            if b"\0" in head:
                return 0                    # バイナリ（画像・PDF 等）は Read に任せる
            n = head.count(b"\n") + sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1 << 20), b""))
    except OSError:
        return 0
    if n <= MAX_LINES:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**tool_input, "limit": LIMIT},
        },
        "systemMessage": (
            f"{p.name} は {n} 行あるため先頭 {LIMIT} 行だけ読みました（pre-read-guard.py）。"
            f"続きは offset={LIMIT + 1} を指定する。全部が要ることは稀なので、先に `grep -n` で当たりを付けてから"
            "範囲指定で読むのが安い。"
        ),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
