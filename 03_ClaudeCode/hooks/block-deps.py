#!/usr/bin/env python3
"""新規依存パッケージの追加を人の承認待ちにする PreToolUse フック（Bash / Write / Edit）。

根拠: AI が提案する依存パッケージは実在しない名前を含むことがある（研究で商用モデル平均 5.2% 以上）。
新規依存の追加は人の承認を条件にする（AIDD-QA 5/5 §7「制御」）。
- deny: `pip|pip3 install <pkg>`・`python -m pip install <pkg>`・`uv add`・`poetry add`・`npm install|i <pkg>`・
  `pnpm add`・`yarn add`・`cargo add`・`go get` のうちパッケージ名を伴うもの。
  通す: `pip install -r <file>`・`pip install -e .`・`npm install`（引数なし）・`npm ci`。
- deny: Write/Edit で `requirements*.txt`・`pyproject.toml`・`package.json` に既存に無い依存名を足す変更。
- WARN（止めない）: AIDD_DEPS_OK=1 で通したとき、名前がローカルのロックファイルのどれにも無い（初出）なら知らせる。
- 解除: 承認後に AIDD_DEPS_OK=1 で再実行。log_decision に override を残す。
- 読めない入力は deny（block-destructive と同じ fail-closed）。
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secret_patterns import input_summary, log_decision
except ImportError:          # 記録は付け足し。部品が無くても deny の動作は変えない
    def log_decision(*_a, **_k) -> None:
        pass

    def input_summary(_t) -> str:
        return ""

_CTX: dict = {}
REASON = ("新規依存の追加は人の承認が要る（AIDD-QA 5/5 §7）: {names}。"
          "実在・配布元・版・既存で足りないかを確認し、承認後に AIDD_DEPS_OK=1 で再実行")
_LOCKS = ("package-lock.json", "poetry.lock", "uv.lock")
_VALUE_OPTS = {"-r", "--requirement", "-c", "--constraint", "-e", "--editable", "-i", "--index-url",
               "--extra-index-url", "-f", "--find-links", "-t", "--target", "--prefix", "--registry", "-w",
               "--filter", "--group", "-G", "--features", "--optional"}
_PY_KEYS = {"name", "version", "description", "readme", "requires-python", "python", "license", "authors",
            "keywords", "classifiers", "homepage", "repository", "documentation", "packages", "build-backend",
            "requires", "scripts", "dependencies", "optional-dependencies", "include", "exclude"}
_JSON_KEYS = {"name", "version", "description", "main", "type", "license", "private", "node", "npm", "module",
              "types", "author", "homepage"}


def _segments(cmd: str) -> list[list[str]]:
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    segs, cur = [], []
    for t in lex:
        if t and set(t) <= set(";&|"):
            segs.append(cur)
            cur = []
        else:
            cur.append(t)
    segs.append(cur)
    return [s for s in segs if s]


def _pkgs(args: list[str]) -> list[str]:
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a in _VALUE_OPTS:
            skip = True
            continue
        if a.startswith("-") or a in (".", "..") or a.startswith(("./", "../", "/")):
            continue
        out.append(a)
    return out


def bash_pkgs(cmd: str) -> list[str]:
    names: list[str] = []
    for toks in _segments(cmd):
        while toks and (re.match(r"^\w+=", toks[0]) or toks[0] in ("sudo", "env", "command", "exec")):
            toks = toks[1:]
        if len(toks) >= 3 and re.match(r"^python[\d.]*$", toks[0]) and toks[1:3] == ["-m", "pip"]:
            toks = ["pip"] + toks[3:]
        if len(toks) < 2:
            continue
        tool, sub = Path(toks[0]).name, toks[1]
        if (tool in ("pip", "pip3") and sub == "install") or (tool == "npm" and sub in ("install", "i", "add")) \
                or (tool in ("uv", "poetry", "pnpm", "yarn", "cargo") and sub == "add") \
                or (tool == "go" and sub == "get") or (tool == "uv" and toks[1:3] == ["pip", "install"]):
            names += _pkgs(toks[3:] if toks[1:3] == ["pip", "install"] else toks[2:])
    return names


def dep_names(text: str, fname: str) -> set[str]:
    names: set[str] = set()
    if fname.startswith("requirements") and fname.endswith(".txt"):
        for line in text.splitlines():
            m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)", line.split("#", 1)[0])
            if m:
                names.add(m.group(1).lower())
    elif fname == "package.json":
        for k in re.findall(r'"([@A-Za-z0-9][\w@./-]*)"\s*:\s*"[^"]*"', text):
            if k not in _JSON_KEYS:
                names.add(k.lower())
    elif fname == "pyproject.toml":
        for line in text.splitlines():
            m = re.match(r'^\s*"([A-Za-z0-9][A-Za-z0-9_.-]*)\s*[<>=~!\[;@",]', line) \
                or re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)\s*=\s*[\"{]", line)
            if m and m.group(1).lower() not in _PY_KEYS:
                names.add(m.group(1).lower())
    return names


def file_pkgs(tool: str, ti: dict) -> list[str]:
    path = str(ti.get("file_path") or "")
    fname = Path(path).name
    if not (fname == "package.json" or fname == "pyproject.toml"
            or (fname.startswith("requirements") and fname.endswith(".txt"))):
        return []
    if tool == "Edit":
        old, new = str(ti.get("old_string") or ""), str(ti.get("new_string") or "")
    else:
        try:
            old = Path(path).read_text(encoding="utf-8")
        except OSError:
            old = ""
        new = str(ti.get("content") or "")
    return sorted(dep_names(new, fname) - dep_names(old, fname))


def first_seen(names: list[str], cwd: str) -> list[str]:
    base = Path(cwd)
    texts = []
    for p in [base / n for n in _LOCKS] + sorted(base.glob("requirements*.txt")):
        try:
            texts.append(p.read_text(encoding="utf-8", errors="replace").lower())
        except OSError:
            pass
    def bare(n: str) -> str:              # 版指定を外す（`requests==2`・`@scope/pkg@1`）
        m = re.match(r"^(@?[^@<>=~!\[\s]+)", n)
        return m.group(1) if m else n
    return [n for n in names if not any(bare(n).lower() in t for t in texts)]


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"[block-deps] {reason}"}}, ensure_ascii=False))
    log_decision("block-deps", "deny", reason, _CTX.get("tool", ""), _CTX.get("summary", ""), _CTX.get("cwd"))
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
        assert isinstance(data, dict), "not an object"
        tool, ti = data.get("tool_name", ""), data.get("tool_input") or {}
        cwd = data.get("cwd") or os.getcwd()
        _CTX.update(tool=tool, summary=input_summary(ti), cwd=cwd)
        if tool == "Bash":
            names = bash_pkgs(str(ti.get("command") or ""))
        elif tool in ("Write", "Edit"):
            names = file_pkgs(tool, ti)
        else:
            return 0
    except Exception as e:
        return deny(f"hook の入力が読めない（{type(e).__name__}）ので止めた（fail-closed）")
    if not names:
        return 0
    new = first_seen(names, cwd)
    if os.environ.get("AIDD_DEPS_OK") == "1":
        log_decision("block-deps", "override", "AIDD_DEPS_OK=1", tool, _CTX["summary"], cwd, "AIDD_DEPS_OK")
        if new:
            msg = f"[block-deps] WARN: ロックファイルに無い初出の依存: {', '.join(new)}（実在・綴りを再確認）"
            print(json.dumps({"systemMessage": msg}, ensure_ascii=False))
            log_decision("block-deps", "warn", msg, tool, _CTX["summary"], cwd)
        return 0
    extra = f"（うちロックファイルに無い初出: {', '.join(new)}）" if new else ""
    return deny(REASON.format(names=", ".join(names)) + extra)


if __name__ == "__main__":
    sys.exit(main())
