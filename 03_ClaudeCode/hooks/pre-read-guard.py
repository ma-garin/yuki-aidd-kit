#!/usr/bin/env python3
"""秘密ファイルと読む価値の無いファイルを止め、大きすぎるファイルは先頭だけに絞る PreToolUse フック（Read / Grep / Glob）。

`context-compression` 原則 2「大きいファイルは行範囲指定で部分読みする」を散文から機械に移したもの。

  - deny（Read / Grep / Glob）: 秘密ファイル（`.env`・鍵・`~/.ssh/` 等。判定は `secret_patterns.py` の
          `is_secret_path` / `is_secret_glob`。Grep は `path`・`glob`、Glob は `pattern`・`path` を見る。B-19）。
          `.env.example` 等の雛形は読める。glob（`**/.en?`）は候補名に当たりうれば deny（`*`・`**` だけは対象外）。
          `03_ClaudeCode/hooks/secret_patterns.py` が hook と同じ場所に無ければ、判定不能として Read/Grep/Glob を deny する
  - deny（Read のみ）: ロックファイル・minified・source map・node_modules / dist / build / .git 配下・キットの生成レポート
          （読んでも判断材料にならない。必要なら grep で該当行だけ取る）
  - 切り詰め: READ_GUARD_MAX_LINES（既定 800）行超のファイルを offset も limit も無しに読む
          → updatedInput で limit=READ_GUARD_LIMIT（既定 300）。systemMessage で全体の行数と続きの読み方を伝える
  - それ以外・バイナリ（画像/PDF は Read が自前で扱う）は素通り

逃がし口は offset / limit の明示（既に Read が持っている）。環境変数のバイパスは作らない。
入力が JSON として読めない・オブジェクトでない（`[1]`・`null`・空）ときは deny する（fail-closed）。`{}` は判定するものが無いので通す。

限界（止めない。テストにもしない）: Grep をディレクトリに掛けたとき（`path: .`）に中に入っている `.env` の中身、
Bash 経由の読み出し（block-destructive.py の担当。`python3 -c` 等は構文解析しないので抜ける）。
秘密ファイルは `02_共通/ひな形/settings.sandbox.json` の denyRead（OS のサンドボックス）と併用する。
`block-explore.sh`（実装モードの探索ブロック）と同じ matcher に前段として並べる。deny が 1 つでもあれば deny が勝つ。
"""
import json
import os
import re
import sys
from pathlib import Path

try:
    from secret_patterns import SECRET_READ_REASON, is_secret_glob, is_secret_path
except ImportError:          # 部品が欠けた導入。判定できないので deny する
    is_secret_path = None

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


def secret_target(tool: str, tool_input: dict, cwd: str | None) -> str | None:
    """秘密ファイルを読む・探す呼び出しなら、その対象（パスか glob）を返す。"""
    paths = [tool_input.get("file_path")] if tool == "Read" else [tool_input.get("path")]
    globs = [tool_input.get("glob")] if tool == "Grep" else [tool_input.get("pattern")] if tool == "Glob" else []
    for p in paths:
        if isinstance(p, str) and is_secret_path(p, cwd):
            return p
    for g in globs:
        if isinstance(g, str) and is_secret_glob(g, cwd):
            return g
    return None


def main() -> int:
    try:
        return _main()
    except Exception as e:   # RecursionError（深い入れ子の JSON）等。Traceback を出さず止める
        return deny(f"hook 内部エラー: {type(e).__name__}（判定不能なので止めた。pre-read-guard.py）")


def _main() -> int:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("JSON の最上位がオブジェクトでない")
        tool_input = data.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            raise ValueError("tool_input がオブジェクトでない")
    except ValueError as e:     # JSONDecodeError・UnicodeDecodeError も含む
        return deny(f"hook の入力が読めない（{type(e).__name__}）ので止めた（fail-closed）。"
                    "続けて起きるなら Claude Code と hook の版の組み合わせを保守者に確認してもらう（pre-read-guard.py）")
    tool = data.get("tool_name")
    if tool in ("Read", "Grep", "Glob"):
        if is_secret_path is None:
            return deny("判定不能で止めた: `03_ClaudeCode/hooks/secret_patterns.py` が無い。hook と同じ場所に置く"
                        "（保守者に install.sh / export-project.sh での入れ直しを依頼する。pre-read-guard.py）")
        cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else None
        hit = secret_target(tool, tool_input, cwd)
        if hit:
            return deny(SECRET_READ_REASON.format(path=hit) + "（pre-read-guard.py）")
    if tool != "Read":
        return 0
    fp = tool_input.get("file_path", "")
    if not fp or not isinstance(fp, str):
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
