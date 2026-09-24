#!/usr/bin/env python3
"""Claude Code の設定・hook と git hook の書き換えを止める PreToolUse フック（Write / Edit / MultiEdit と Bash）。

B-19。安全装置（settings の hooks 配線・hook の実体・git hook）を AI が書き換えると、以後の判定がすべて効かなくなる。
書き先を realpath で解決してから（シンボリックリンク越しも）、次に当たれば deny する。大文字小文字は区別しない:
  - `.claude/settings*.json`（`~/.claude/` も `<cwd>/.claude/` も。どのディレクトリの `.claude/` でも同じに扱う）
  - `.claude/hooks/` の配下
  - `.git/hooks/`・`.git/info/` の配下と `.git/config`（hooksPath・alias を書き込めるため。Write/Edit も止める）
Bash は `secret_patterns.py` の `analyze_command` でラッパー（bash -c・sudo・env・xargs・$( ) 等）を剥がし、
正規化（`$'…'`・引用の連結・`{a,b}` の展開）して分割してから、`>` `>>` `&>`・`tee`・`cp` `install`（書き先）・
`mv` `ln`（全引数）・`sed -i` `perl -i`・`rm` `truncate`・`chmod` `chattr` `chown`・`dd of=`・
`curl -o` `wget -O` / `-P`・`-t`（`-o<path>`・`--output=<path>` のように値が付いた形も）・`rsync`（最後の引数）・
`tar -C` / `--directory=`・`unzip -d`・`awk -i inplace`・`find <DIR> … -exec|-delete`（DIR）の書き先を見る。
glob（`.cl*/settings.json`）の書き先は、展開したら保護パスに当たりうるなら deny。`cd` は同じコマンドの中でだけ追う。
読むだけ（cat / ls / stat / diff / grep / head / tail / less）は止めない。

判定不能は deny（fail-closed。block-destructive.py と同じ）: 入力の JSON が読めない・パスが解決できない・
変数（`$X`）が残ったまま `.claude` / `.git` / `hooks` / `settings` を含む書き先・
`03_ClaudeCode/hooks/secret_patterns.py` が hook と同じ場所に無い（同梱物の欠落に最初の呼び出しで気づかせる）。
入力が JSON として読めない・オブジェクトでない（`[1]`・`null`・空）は deny。`{}`・書き先（file_path / command）が無いものは通す。

解除: キット自身の checkout で設定や hook を意図して保守するときは、保守者が `AIDD_ALLOW_CONFIG_EDIT=1` を付けて
Claude Code を起動する。キットの `03_ClaudeCode/hooks/` は `.claude/hooks/` ではないので既定でも書ける。
対象外: `00_導入/02_プロジェクト配布/install-git-hooks.sh`（人が打つ前提。`.git/hooks/` を配線するのはこのスクリプトで、
中で行う書き込みは hook からは見えない）。
"""
import fnmatch
import json
import os
import re
import sys

_GLOB = re.compile(r"[*?\[]")

try:
    from secret_patterns import analyze_command, expand_path
except ImportError:          # 部品が欠けた導入。判定できないので main で deny する
    analyze_command = None

ENV_ALLOW = "AIDD_ALLOW_CONFIG_EDIT"
_KEYWORDS = (".claude", ".git", "hooks", "settings")
_REDIR_OUT = frozenset({">", ">>", ">|", "&>", "&>>", "<>"})
_REDIR_ALL = _REDIR_OUT | {"<", "<<", "<<<", ">&", "<&"}


class Unresolvable(Exception):
    pass


def protected(path: str, cwd: str | None, whole_dir: bool = False) -> bool:
    """書き先が保護対象なら True。解決できなければ Unresolvable。whole_dir: `.claude` / `.git` そのものも対象にする。"""
    if not isinstance(path, str) or not path.strip():
        return False
    p = os.path.expandvars(path)
    if re.search(r"\$|`", p):
        if any(k in p.lower() for k in _KEYWORDS):
            raise Unresolvable(path)
        return False
    try:
        full = expand_path(p, cwd)
        cands = (os.path.normpath(full),) if _GLOB.search(full) else (os.path.normpath(full), os.path.realpath(full))
    except (OSError, ValueError) as e:
        raise Unresolvable(path) from e
    return any(_protected_parts([x for x in c.replace("\\", "/").lower().split("/") if x], whole_dir) for c in cands)


def _protected_parts(parts: list[str], whole_dir: bool) -> bool:
    """各成分を glob として保護パスに当てる（glob でない成分は完全一致になる）。"""
    def m(name: str, pat: str) -> bool:
        return fnmatch.fnmatchcase(name, pat)
    for i in range(len(parts) - 1):
        if (m(".claude", parts[i]) or m(".git", parts[i])) and m("hooks", parts[i + 1]):
            return True
        if m(".git", parts[i]) and m("info", parts[i + 1]):
            return True
    if len(parts) >= 2:
        if m(".claude", parts[-2]) and (fnmatch.fnmatchcase(parts[-1], "settings*.json") or any(
                m(x, parts[-1]) for x in ("settings.json", "settings.local.json"))):
            return True
        if m(".git", parts[-2]) and m("config", parts[-1]):
            return True
    return bool(whole_dir and parts and (m(".claude", parts[-1]) or m(".git", parts[-1])))


def _split_args(toks: list[str], with_arg: frozenset[str] = frozenset()) -> tuple[list[str], list[tuple[str, str | None]]]:
    """(位置引数, [(オプション, 値)])。リダイレクトとその先・リダイレクト前の fd 番号は除く。"""
    pos: list[str] = []
    opts: list[tuple[str, str | None]] = []
    i, n, end = 1, len(toks), False
    while i < n:
        t = toks[i]
        if t in _REDIR_ALL:
            i += 2
            continue
        if t.isdigit() and i + 1 < n and toks[i + 1] in _REDIR_ALL:
            i += 1
            continue
        if not end and t == "--":
            end = True
        elif not end and t.startswith("-") and t != "-":
            if t in with_arg and i + 1 < n:
                opts.append((t, toks[i + 1]))
                i += 1
            else:
                opts.append((t, None))
        else:
            pos.append(t)
        i += 1
    return pos, opts


def _short_has(opts: list[tuple[str, str | None]], letter: str) -> bool:
    return any(o.startswith("-") and not o.startswith("--") and letter in o[1:] for o, _v in opts)


def _opt_values(toks: list[str], shorts: str, longs: tuple[str, ...]) -> list[str]:
    """値を取るオプションの値を全部の書き方で拾う: `-o x`・`-ox`・`-sSo x`・`--output=x`・`--output x`。"""
    out: list[str] = []
    i, n = 1, len(toks)
    while i < n:
        t = toks[i]
        if t == "--":
            break
        if t.startswith("--"):
            name, eq, val = t.partition("=")
            if name in longs:
                if eq:
                    out.append(val)
                elif i + 1 < n:
                    out.append(toks[i + 1])
                    i += 1
        elif t.startswith("-") and len(t) > 1:
            for k, ch in enumerate(t[1:], 1):
                if ch in shorts:
                    rest = t[k + 1:]
                    if rest:
                        out.append(rest)
                    elif i + 1 < n:
                        out.append(toks[i + 1])
                        i += 1
                    break
        i += 1
    return [v for v in out if v and v != "-"]


def targets(toks: list[str]) -> list[tuple[str, bool]]:
    """1 つの断片が書き換えうるパス [(パス, ディレクトリそのものも対象か)]。"""
    out: list[tuple[str, bool]] = []
    for k, t in enumerate(toks[:-1]):
        if t in _REDIR_OUT or (t == ">&" and not re.fullmatch(r"\d+|-", toks[k + 1])):
            out.append((toks[k + 1], False))
    cmd = toks[0].rsplit("/", 1)[-1] if toks else ""
    if cmd == "tee":
        out += [(p, False) for p in _split_args(toks)[0]]
    elif cmd in ("cp", "install", "mv", "ln"):
        pos, opts = _split_args(toks, frozenset({"-t", "--target-directory", "-S", "--suffix", "-m", "--mode",
                                                 "-o", "--owner", "-g", "--group"}))
        tdir = _opt_values(toks, "t", ("--target-directory",))
        if cmd in ("mv", "ln") or (cmd == "install" and _short_has(opts, "d")):
            dests = pos                                  # mv は元も消える・ln は元への経路を作る
        else:
            dests = [] if tdir else pos[-1:]
        out += [(p, True) for p in dests + tdir]
    elif cmd in ("sed", "perl"):
        pos, opts = _split_args(toks, frozenset({"-e", "-f", "-E", "-l", "-M", "-I", "--expression", "--file"}))
        if _short_has(opts, "i") or any(o == "--in-place" or o.startswith("--in-place=") for o, _v in opts):
            out += [(p, False) for p in pos]
    elif cmd in ("rm", "rmdir", "unlink", "shred", "truncate", "chmod", "chattr", "chown", "chgrp", "setfacl"):
        with_arg = frozenset({"-s", "--size", "-r", "--reference"}) if cmd == "truncate" else frozenset()
        out += [(p, True) for p in _split_args(toks, with_arg)[0]]     # rm -r・chmod -x の -r / -x は値を取らない
    elif cmd in ("awk", "gawk"):
        if any(t == "-iinplace" or t == "--include=inplace" or (t in ("-i", "--include") and k + 2 < len(toks)
                                                                    and toks[k + 2] == "inplace")
               for k, t in enumerate(toks[1:])):
            out += [(p, False) for p in _split_args(toks, frozenset({"-i", "--include", "-f", "--file", "-v", "--assign",
                                                                     "-F", "--field-separator"}))[0]]
    elif cmd == "rsync":
        pos = _split_args(toks, frozenset({"-e", "--rsh", "--exclude", "--include", "--filter", "-f", "--files-from",
                                           "--exclude-from", "--include-from", "--password-file", "--port", "--chmod",
                                           "--log-file", "--temp-dir", "-T", "--partial-dir", "--backup-dir"}))[0]
        out += [(p, True) for p in pos[-1:]]
    elif cmd in ("tar", "gtar", "bsdtar"):
        out += [(v, True) for v in _opt_values(toks, "C", ("--directory",))]
    elif cmd == "unzip":
        out += [(v, True) for v in _opt_values(toks, "d", ())]
    elif cmd == "find":
        if any(t in ("-exec", "-execdir", "-ok", "-okdir", "-delete") for t in toks[1:]):
            for t in toks[1:]:
                if t.startswith(("-", "(", "!")):
                    break
                out.append((t, True))
    elif cmd == "dd":
        out += [(t[3:], False) for t in toks[1:] if t.startswith("of=")]
    elif cmd == "curl":
        out += [(v, False) for v in _opt_values(toks, "o", ("--output",))]
        out += [(v, True) for v in _opt_values(toks, "", ("--output-dir",))]
    elif cmd == "wget":
        out += [(v, False) for v in _opt_values(toks, "O", ("--output-document",))]
        out += [(v, True) for v in _opt_values(toks, "P", ("--directory-prefix",))]
    return out


def bash_hit(cmd: str, cwd: str | None) -> str | None:
    a = analyze_command(cmd)
    cur = cwd
    for toks in a.segments:
        base = toks[0].rsplit("/", 1)[-1]
        if base in ("cd", "pushd"):
            pos = _split_args(toks)[0]
            try:
                cur = expand_path(os.path.expandvars(pos[0]), cur) if pos and pos[0] != "-" else (
                    os.path.expanduser("~") if not pos else cur)
            except (OSError, ValueError):
                pass
            continue
        for path, whole in targets(toks):
            if protected(path, cur, whole):
                return path
    if a.too_deep and any(k in cmd.lower() for k in _KEYWORDS):
        raise Unresolvable("入れ子（bash -c・$( ) 等）が 3 段以上")
    return None


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"[block-protected] {reason}",
    }}, ensure_ascii=False))
    return 0


def _why(path: str) -> str:
    return (f"安全装置の書き換えを止めた（{path}）。Claude Code の設定（.claude/settings*.json）・hook（.claude/hooks/）・"
            "git hook と git の設定（.git/hooks/・.git/info/・.git/config）を AI が変えると、以後の判定が効かなくなる。代わりに: 変更案（差分）を示して保守者に依頼する。"
            f"キットの保守で意図して変えるときは、保守者が {ENV_ALLOW}=1 を付けて Claude Code を起動する"
            "（キットの 03_ClaudeCode/hooks/ は対象外で、既定でも書ける）")


def main() -> int:
    try:
        return _main()
    except Exception as e:   # RecursionError（深い入れ子の JSON）・判定の不具合。Traceback を出さず止める
        return deny(f"hook 内部エラー: {type(e).__name__}（判定不能なので止めた。続けて起きるなら保守者に hook の不具合として報告する）")


def _main() -> int:
    try:
        raw = sys.stdin.read()
    except (OSError, ValueError):
        raw = ""
    if os.environ.get(ENV_ALLOW) == "1":
        return 0
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON の最上位がオブジェクトでない")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            raise ValueError("tool_input がオブジェクトでない")
    except ValueError as e:
        return deny(f"hook の入力が読めない（{type(e).__name__}）ので止めた（fail-closed）。"
                    "続けて起きるなら Claude Code と hook の版の組み合わせを保守者に確認してもらう")
    tool = data.get("tool_name")
    cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        fp = ti.get("file_path") or ti.get("notebook_path")
        if not isinstance(fp, str) or not fp.strip():
            return 0
    elif tool == "Bash":
        cmd = ti.get("command")
        if not isinstance(cmd, str) or not cmd.strip():
            return 0
    else:
        return 0
    if analyze_command is None:
        return deny("判定不能で止めた: `03_ClaudeCode/hooks/secret_patterns.py` が無い。hook と同じ場所に置く"
                    "（保守者に install.sh / export-project.sh での入れ直しを依頼する）")
    try:
        hit = (fp if protected(fp, cwd) else None) if tool != "Bash" else bash_hit(cmd, cwd)
    except Unresolvable as e:
        return deny(f"書き先が解決できない（{e}）ので止めた（判定不能）。書き先を具体的なパスで書き直す。"
                    f"意図した設定の保守なら、保守者が {ENV_ALLOW}=1 を付けて起動する")
    except Exception as e:   # 判定の不具合で素通りさせない
        return deny(f"判定中に例外（{type(e).__name__}）が起きたので止めた（判定不能）。保守者に hook の不具合として報告する")
    return deny(_why(hit)) if hit else 0


if __name__ == "__main__":
    sys.exit(main())
