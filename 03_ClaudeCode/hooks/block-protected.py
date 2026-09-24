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

パッチ・コミットの中身で書き先が決まるコマンドは、中身から書き先を求めて同じ判定をする（`bash -c`・`sudo`・`env` 越しも同じ）:
  - `git apply`・`git am`・`patch`: パッチの入力（引数のファイル・`-i <file>`・`< <file>`）を読み、`diff --git`・`+++`・`---`・
    `***`・`rename to` 等・`Index:` のパスを集める（-p で外す成分・`--directory` の前置き・`patch -d` の基点も試す。
    git am は MIME の base64 等も解く）。入力がパイプ・プロセス置換・ヒアドキュメント・読めないファイルなら deny
    （パッチをファイルに書いてから当てる）。`git apply --check / --stat / --numstat / --summary`・`patch --dry-run` は通す。
    `git am --continue / --skip` は rebase-apply/ の残りのパッチを読む
  - `git cherry-pick`・`git revert`: hook の中で `git rev-list`・`git diff-tree`（読み取り専用）を動かし、コミットが触る
    ファイルを見る。範囲（a..b）は各コミット（上限 50。超えたら deny）。解決できないコミットは deny。
    `--continue / --skip` は sequencer/todo の残りを見る
  - `git checkout <rev> -- <path>`・`git restore [--source=<rev>] <path>`: パスそのものと、`git diff --name-only` で実際に
    書き換わるファイル（`.` のようなディレクトリ指定も）を見る。`git restore --staged`（--source 無し）は索引だけなので通す
  - git の別名（`-c alias.x=…`・設定済みの alias）は 1 段だけ解いて同じ判定をする
  - 同じコマンドの中で先に作業ツリー・ref を変えうる断片（`>` 等の書き込み・`git fetch` 等）があれば、中身が実行時には
    変わりうるので deny（分けて実行する）。hook の中の git は合計 3.5 秒まで（timeout 5 秒で素通りにならないよう超えたら deny）
限界（見ない）: `git merge`・`git pull`・`git rebase`・`git stash pop`・ブランチの切り替え（`git switch`・`git checkout <branch>`）・
`git reset`・`git rm` / `git mv` など、上に挙げていない git の書き込みで入る変更は見ない。

判定不能は deny（fail-closed。block-destructive.py と同じ）: 入力の JSON が読めない・パスが解決できない・
変数（`$X`）が残ったまま `.claude` / `.git` / `hooks` / `settings` を含む書き先・
`03_ClaudeCode/hooks/secret_patterns.py` が hook と同じ場所に無い（同梱物の欠落に最初の呼び出しで気づかせる）。
入力が JSON として読めない・オブジェクトでない（`[1]`・`null`・空）は deny。`{}`・書き先（file_path / command）が無いものは通す。

解除: キット自身の checkout で設定や hook を意図して保守するときは、保守者が `AIDD_ALLOW_CONFIG_EDIT=1` を付けて
Claude Code を起動する。キットの `03_ClaudeCode/hooks/` は `.claude/hooks/` ではないので既定でも書ける。
対象外: `00_導入/02_プロジェクト配布/install-git-hooks.sh`（人が打つ前提。`.git/hooks/` を配線するのはこのスクリプトで、
中で行う書き込みは hook からは見えない）。
"""
import codecs
import email
import fnmatch
import glob
import json
import os
import re
import shlex
import subprocess
import sys
import time

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
    elif cmd == "git":                  # git 自身の書き込み（--output・format-patch / archive -o・mailsplit -o・bundle create）
        k, gopts = git_split(toks)
        sub, rest = (toks[k], toks[k:]) if k < len(toks) else ("", [])
        found = [(v, False) for v in _opt_values(rest, "", ("--output",))]
        found += [(v, sub == "format-patch") for v in _opt_values(rest, "o", ("--output-directory",))
                  if sub in ("format-patch", "archive")]
        found += [(t[2:], True) for t in rest[1:] if sub == "mailsplit" and t.startswith("-o") and len(t) > 2]
        found += [(t, False) for t in [t for t in rest[2:] if not t.startswith("-")][:1] if rest[1:2] == ["create"]
                  and sub == "bundle"]
        cdirs = [v for n, v in gopts if n == "-C"]
        out += [(os.path.join(*cdirs, p) if cdirs else p, w) for p, w in found]
    return out


# ---------------------------------------------------------------- 中身で書き先が決まるコマンド（パッチ・コミット・git の設定）
class Unverifiable(Exception):
    """書き先がパッチ・コミットの中身で決まり、それを確かめられない。メッセージがそのまま deny 理由になる。"""


class _GitFail(Exception):
    def __init__(self, msg: str, code: int = -1) -> None:
        super().__init__(msg)
        self.code = code


def _cannot(what: str, instead: str) -> Unverifiable:
    return Unverifiable(f"{what}ので止めた（判定不能）。代わりに: {instead}。"
                        f"意図した設定の保守なら、保守者が {ENV_ALLOW}=1 を付けて起動する")


def _no_patch(what: str) -> Unverifiable:
    return _cannot(f"パッチの中身を確かめられない（{what}）", "パッチをファイルに書いてから、別のコマンドで "
                   "`git apply <ファイル>` のように当てる（hook が中身の書き先を読んで確かめる）")


def _no_rev(what: str) -> Unverifiable:
    return _cannot(f"コミット・別名が書き換えるファイルを確かめられない（{what}）",
                   "`git log --oneline` で確かめ、別名を使わず具体的なコミット名で 1 つずつ別のコマンドとして指定する")


_MAX_COMMITS, _MAX_PATCH, _MAX_ALIAS = 50, 16 << 20, 3
_BUDGET = 3.5                    # 秒。hook の timeout（5 秒）で素通りにならないよう、超えたら deny する
_T0 = time.monotonic()
_GIT_GLOBAL_ARG = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"})
_CONTENT = frozenset({"apply", "am", "cherry-pick", "revert", "checkout", "restore"})
_GIT_RO = frozenset({"status", "log", "diff", "show", "rev-parse", "rev-list", "ls-files", "ls-tree", "cat-file",
                     "describe", "shortlog", "blame", "grep", "diff-tree", "merge-base", "name-rev", "show-ref",
                     "for-each-ref"})
_GIT_BUILTIN = _CONTENT | _GIT_RO | frozenset({     # 別名を引かない（git は組み込みを別名で上書きできない）
    "add", "archive", "bisect", "branch", "bundle", "check-ignore", "cherry", "clean", "clone", "commit", "config",
    "count-objects", "diff-files", "diff-index", "fetch", "format-patch", "fsck", "gc", "hash-object", "help", "init",
    "ls-remote", "mailinfo", "mailsplit", "maintenance", "merge", "mv", "notes", "prune", "pull", "push", "range-diff",
    "rebase", "reflog", "remote", "repack", "replace", "rerere", "reset", "rm", "show-branch", "sparse-checkout",
    "stash", "submodule", "switch", "symbolic-ref", "tag", "update-index", "update-ref", "var", "version", "worktree"})
# 作業ツリー・ref を変えない断片（同じコマンドの前にあっても、後ろのパッチ・コミットの中身を変えない）
_READ_ONLY = frozenset({"cd", "pushd", "popd", "ls", "cat", "echo", "printf", "pwd", "true", "false", "test", "[",
                        "head", "tail", "wc", "grep", "stat", "diff", "sleep", ":", "mkdir", "export", "unset", "set",
                        "which", "type", "date"})
_SHELL_NAMES = frozenset({"bash", "sh", "zsh", "dash", "ksh", "eval"})       # -c の中身は別の断片として見る
_CFG_READ = frozenset({"--get", "--get-all", "--get-regexp", "--get-urlmatch", "--get-color", "--get-colorbool",
                       "--list", "-l", "--show-origin"})
_CFG_WRITE = frozenset({"--unset", "--unset-all", "--add", "--replace-all", "--rename-section", "--remove-section",
                        "--edit", "-e"})
# (値を取る長いオプション, 意味を見る値なしの長いオプション, 値を取る短いオプション, 値を付けたときだけ取る短いオプション)。
# 長い方は一意な省略形（`--dir=`）を正式名に直す。git・getopt は曖昧な省略形を拒むので、見ない値なしは並べない
_Spec = tuple[frozenset[str], frozenset[str], str, str]
_APPLY: _Spec = (frozenset({"--exclude", "--include", "--directory", "--whitespace", "--build-fake-ancestor"}),
                 frozenset({"--check", "--stat", "--numstat", "--summary", "--apply"}), "pC", "")
_AM: _Spec = (frozenset({"--quoted-cr", "--whitespace", "--directory", "--exclude", "--include", "--patch-format",
                         "--resolvemsg", "--empty"}),
              frozenset({"--continue", "--resolved", "--skip", "--abort", "--quit", "--show-current-patch",
                         "--allow-empty"}), "Cp", "S")
_PATCH: _Spec = (frozenset({"--prefix", "--basename-prefix", "--ifdef", "--fuzz", "--get", "--input", "--output",
                            "--directory", "--strip", "--reject-file", "--suffix", "--version-control", "--quoting-style",
                            "--reject-format", "--read-only", "--debug"}), frozenset({"--dry-run", "--version"}),
                 "BDFVYdgioprxz", "")
_PICK: _Spec = (frozenset({"--cleanup", "--mainline", "--strategy", "--strategy-option", "--empty"}),
                frozenset({"--quit", "--continue", "--abort", "--skip", "--no-commit", "--commit", "--edit", "--signoff",
                           "--rerere-autoupdate", "--ff", "--allow-empty", "--allow-empty-message",
                           "--keep-redundant-commits", "--gpg-sign", "--reference", "--stdin"}), "mX", "S")
_PICK_SHORT = frozenset("nesxrSmX")                # cherry-pick / revert は知らないオプションを deny（--all 等で対象が増える）
_CHECKOUT: _Spec = (frozenset({"--orphan", "--conflict", "--pathspec-from-file"}), frozenset({"--pathspec-file-nul"}),
                    "bB", "t")
_RESTORE: _Spec = (frozenset({"--source", "--conflict", "--pathspec-from-file"}),
                   frozenset({"--staged", "--worktree", "--pathspec-file-nul"}), "s", "")
_CONFIG: _Spec = (frozenset({"--file", "--blob", "--type", "--default", "--comment", "--value", "--url"}),
                  _CFG_READ | _CFG_WRITE, "f", "")


def _canon(name: str, known: frozenset[str]) -> str:
    """長いオプションの省略形・否定形（`--dir`・`--no-chec`）を正式名にする。一意に決まらなければそのまま。"""
    if name in known:
        return name
    neg = name.startswith("--no-")
    hits = [k for k in known if k.startswith("--" + name[5:] if neg else name)]
    return name if len(hits) != 1 else ("--no-" + hits[0][2:] if neg else hits[0])


def _parse(args: list[str], spec: _Spec) -> tuple[list[str], int | None, list[tuple[str, str | None]]]:
    """(位置引数, `--` の前にあった位置引数の数（`--` が無ければ None）, [(正式名, 値)])。"""
    longs, flags, shorts, attached = spec
    pos: list[str] = []
    opts: list[tuple[str, str | None]] = []
    dd: int | None = None
    i, n = 0, len(args)
    while i < n:
        t = args[i]
        if dd is not None or t == "-" or not t.startswith("-"):
            pos.append(t)
        elif t == "--":
            dd = len(pos)
        elif t.startswith("--"):
            name, eq, val = t.partition("=")
            name = _canon(name, longs | flags)
            take = not eq and name in longs and i + 1 < n
            opts.append((name, val if eq else args[i + 1] if take else None))
            i += take
        else:
            for k, ch in enumerate(t[1:], 1):
                rest = t[k + 1:]
                if ch in attached or ch in shorts:
                    take = ch in shorts and not rest and i + 1 < n
                    opts.append(("-" + ch, rest or (args[i + 1] if take else None)))
                    i += take
                    break
                opts.append(("-" + ch, None))
        i += 1
    return pos, dd, opts


def _vals(opts: list[tuple[str, str | None]], *names: str) -> list[str]:
    return [v for o, v in opts if o in names and v]


def git_split(toks: list[str]) -> tuple[int, list[tuple[str, str]]]:
    """git のグローバルオプションを読み飛ばす。(サブコマンドの位置, [(名前, 値)])。"""
    i, n, out = 1, len(toks), []
    while i < n and toks[i].startswith("-"):
        name, eq, val = toks[i].partition("=")
        if name in _GIT_GLOBAL_ARG and not eq:
            val, i = (toks[i + 1] if i + 1 < n else ""), i + 1
        out.append((name, val))
        i += 1
    return i, out


def _strip_redirs(toks: list[str]) -> tuple[list[str], tuple[str, str] | None, bool]:
    """リダイレクトを除いたトークン列・標準入力（("file", パス) か ("bad", 説明)）・プロセス置換 <( ) があるか。"""
    out: list[str] = []
    stdin: tuple[str, str] | None = None
    i, n = 0, len(toks)
    while i < n:
        t, fd = toks[i], None
        if t.isdigit() and i + 1 < n and toks[i + 1] in _REDIR_ALL:
            fd, i = t, i + 1
            t = toks[i]
        if t not in _REDIR_ALL:
            out.append(t)
            i += 1
            continue
        if fd in (None, "0") and t in ("<", "<>"):
            stdin = ("file", toks[i + 1] if i + 1 < n else "")
        elif fd in (None, "0") and t in ("<<", "<<<", "<&"):
            stdin = ("bad", "ヒアドキュメント・ヒア文字列")
        i += 2
    return out, stdin, any(t.startswith(("<(", ">(")) for t in toks)


def _read_file(p: str) -> bytes:
    if not os.path.isfile(p):                        # FIFO・デバイスは読まない（読むと止まる）
        raise _no_patch(f"{p} が通常のファイルでない")
    if os.path.getsize(p) > _MAX_PATCH:
        raise _no_patch(f"{p} が大きすぎる")
    with open(p, "rb") as f:
        return f.read()


def _read_inputs(name: str, bases: list[str], allow_dir: bool = False) -> list[tuple[str, bytes]]:
    """パッチのファイルを読む。相対パスは bases のどれから見ても読み、見つかった全部を返す。読めなければ deny。"""
    if name in ("", "-") or name.startswith(("/dev/", "/proc/")) or re.search(r"\$|`", name):
        raise _no_patch(f"標準入力・特殊ファイル・変数（{name or '空'}）")
    out: list[tuple[str, bytes]] = []
    try:
        for b in dict.fromkeys(bases):
            full = expand_path(name, b)
            for c in (sorted(glob.glob(full)) if _GLOB.search(name) else [full]):
                if allow_dir and os.path.isdir(c):       # git am の Maildir
                    out += [(name, _read_file(os.path.join(r, f))) for r, _d, fs in os.walk(c) for f in sorted(fs)]
                elif os.path.exists(c):
                    out.append((name if c == full else os.path.relpath(c, b), _read_file(c)))
    except OSError as e:
        raise _no_patch(f"{name} を読めない（{type(e).__name__}）") from e
    if not out:
        raise _no_patch(f"{name} が見つからない")
    return out


def _mail_texts(data: bytes) -> list[str]:
    """git am の入力: 生の本文に加えて、MIME（base64・quoted-printable）を解いた本文も返す。"""
    out = [data.decode("utf-8", "surrogateescape")]
    for k, chunk in enumerate(re.split(rb"(?m)^From ", data)):
        chunk = chunk.partition(b"\n")[2] if k else chunk      # mbox の区切り行（From <id> <日付>）の残り
        try:
            for part in email.message_from_bytes(chunk).walk() if chunk.strip() else ():
                body = None if part.is_multipart() else part.get_payload(decode=True)
                if isinstance(body, bytes):
                    out.append(body.decode("utf-8", "surrogateescape"))
        except Exception as e:                          # 壊れたメール
            raise _no_patch(f"メールを解釈できない（{type(e).__name__}）") from e
    if any(t.lstrip().startswith("# This series applies on GIT commit") for t in out):
        raise _no_patch("StGit の series ファイル（別のファイルを当てる）")
    return out


_QUOTED = re.compile(r'"((?:[^"\\]|\\.)*)"(.*)', re.DOTALL)
_HDR = ("+++ ", "--- ", "*** ", "+++\t", "---\t", "***\t")
_NAMED = ("rename from ", "rename to ", "rename old ", "rename new ", "copy to ", "Index: ")
_STAMP = re.compile(r"\s+(?:\d{4}-\d\d-\d\d[ T]\d\d:\d\d|\w{3} \w{3} [ \d]\d \d\d:\d\d:\d\d).*$")


def _cunquote(s: str) -> tuple[str, str]:
    """先頭の git の C 風の引用 "…"（\\ooo・\\t 等）を外す。(中身, 残り)。"""
    m = _QUOTED.match(s)
    if not m:
        return s, ""
    raw = codecs.escape_decode(m.group(1).encode("utf-8", "surrogateescape"))[0]
    return raw.decode("utf-8", "surrogateescape"), m.group(2)


def _names(v: str) -> set[str]:
    v = v.strip()
    if v.startswith('"'):
        return {_cunquote(v)[0]}
    head = v.split("\t", 1)[0].rstrip()
    return {head, head.split(" ", 1)[0], _STAMP.sub("", head)}


def patch_paths(text: str) -> set[str]:
    """パッチの本文から書き先の候補を集める（`diff --git`・`+++`・`---`・`***`・`rename to` 等・`Index:`）。
    本文の行（`--- ` で始まる削除行等）も拾うが、余分に拾うのは deny 側なのでそのままにする。"""
    out: set[str] = set()
    for line in text.splitlines():
        line = line.rstrip("\r")
        if line.startswith("diff --git "):
            rest = line[11:]
            if rest.startswith('"'):
                a, b = _cunquote(rest)
                out |= {a} | _names(b)
            else:                                        # 引用されない a/ b/ の境目は空白のどれか
                out.add(rest)
                for m in re.finditer(" ", rest) if rest.count(" ") <= 8 else ():
                    out |= {rest[:m.start()]} | _names(rest[m.end():])
        elif line.startswith(_HDR):
            out |= _names(line[4:])
        elif line.startswith(_NAMED):
            out |= _names(line[7:] if line.startswith("Index: ") else line.split(" ", 2)[-1])
    return out - {"", "/dev/null"}


def _left() -> float:
    return _BUDGET - (time.monotonic() - _T0)


def _texts_hit(texts: list[tuple[str, str]], bases: list[str], variants: list) -> str | None:
    """texts: [(どこから読んだか, 本文)]。パスの先頭の成分を何個外しても（-p）・どの基点から見ても・前置き付きでも見る。"""
    for label, text in texts:
        for name in sorted(patch_paths(text)):
            if _left() <= 0:
                raise _no_patch("時間内に確かめきれない")
            comps = [c for c in name.replace("\\", "/").split("/") if c]
            for k in range(len(comps)):
                tail = ("/" if k == 0 and name.startswith("/") else "") + "/".join(comps[k:])
                if any(protected(c, b) for c in {tail, *(f(tail) for f in variants)} for b in dict.fromkeys(bases)):
                    return f"{name}（{label} の中）"
    return None


def _git(args: list[str], cwd: str, gl: list[str], stdin: str | None = None) -> str:
    """読み取り専用の git を hook の中で動かす（ロックを取らない・fsmonitor を動かさない）。失敗は _GitFail。"""
    if _left() <= 0.1:
        raise _GitFail("時間内に確かめきれない")
    try:
        r = subprocess.run(["git", *gl, "-c", "core.fsmonitor=false", *args], cwd=cwd, capture_output=True,
                           env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0"),
                           input=None if stdin is None else stdin.encode(), timeout=_left())
    except (OSError, subprocess.SubprocessError) as e:
        raise _GitFail(type(e).__name__) from e
    if r.returncode:
        err = r.stderr.decode("utf-8", "replace").strip().splitlines() or [f"exit {r.returncode}"]
        raise _GitFail(err[-1], r.returncode)
    return r.stdout.decode("utf-8", "surrogateescape")


def _state(rel: str, cwd: str, gl: list[str]) -> str | None:
    """git am / cherry-pick の途中の状態（rebase-apply/・sequencer/todo）の絶対パス。無ければ None。"""
    try:
        p = expand_path(_git(["rev-parse", "--git-path", rel], cwd, gl).strip(), cwd)
    except _GitFail as e:
        raise _no_rev(f"途中の状態を読めない（{e}）") from e
    return p if os.path.exists(p) else None


def _no_write(sub: str, rest: list[str]) -> bool:
    """当てずに調べるだけの形（git apply --check / --stat / --numstat / --summary・patch --dry-run）。"""
    if sub not in ("apply", "patch"):
        return False
    names = {o for o, _v in _parse(rest, _APPLY if sub == "apply" else _PATCH)[2]}
    if sub == "patch":
        return "--dry-run" in names
    return bool(names & {"--check", "--stat", "--numstat", "--summary"}) and "--apply" not in names


def _patch_cmd(args: list[str], cwd: str, stdin: tuple[str, str] | None) -> str | None:
    """GNU patch: patch [opts] [元のファイル [パッチ]]。-i / < / 2 つ目の位置引数がパッチ。-d は基点に足す。"""
    pos, _dd, opts = _parse(args, _PATCH)
    if _no_write("patch", args):
        return None
    bases = [cwd] + [expand_path(d, cwd) for d in _vals(opts, "-d", "--directory")]
    for t in pos[:1] + _vals(opts, "-o", "--output", "-r", "--reject-file"):
        if any(protected(t, b) for b in bases):
            return t
    inputs = _vals(opts, "-i", "--input") or pos[1:2]
    if inputs:
        data = [d for name in inputs for d in _read_inputs(name, bases)]
    elif stdin and stdin[0] == "file":
        data = _read_inputs(stdin[1], [cwd])
    else:
        raise _no_patch(stdin[1] if stdin else "パイプ・標準入力から読む")
    variants = [lambda p, x=x: x + p for x in _vals(opts, "-B", "--prefix")]
    variants += [lambda p, x=x: os.path.join(os.path.dirname(p), x + os.path.basename(p))
                 for x in _vals(opts, "-Y", "--basename-prefix")]
    variants += [lambda p, x=x: p + x for x in _vals(opts, "-z", "--suffix")]
    return _texts_hit([(k, d.decode("utf-8", "surrogateescape")) for k, d in data], bases, variants)


def _git_apply(sub: str, args: list[str], cwd: str, gl: list[str], bases: list[str],
               stdin: tuple[str, str] | None) -> str | None:
    pos, _dd, opts = _parse(args, _APPLY if sub == "apply" else _AM)
    names = {o for o, _v in opts}
    if _no_write(sub, args) or names & {"--abort", "--quit", "--show-current-patch"}:
        return None
    for t in _vals(opts, "--build-fake-ancestor"):
        if protected(t, cwd):
            return t
    variants = [lambda p, r=r: r.rstrip("/") + "/" + p for r in _vals(opts, "--directory")]
    if any("series" in v for v in _vals(opts, "--patch-format")):
        raise _no_patch("StGit の series 形式（別のファイルを当てる）")
    if sub == "am" and names & {"--continue", "--resolved", "-r", "--skip", "--allow-empty"}:
        d = _state("rebase-apply", cwd, gl)                # 続けて当てる next〜last 番と、当て途中の patch
        if d is None:
            return None
        try:
            with open(os.path.join(d, "next")) as f1, open(os.path.join(d, "last")) as f2:
                nxt, last = int(f1.read()), int(f2.read())
        except (OSError, ValueError) as e:
            raise _no_patch("rebase-apply/ の next・last を読めない") from e
        if last - nxt > 10000:
            raise _no_patch("rebase-apply/ のパッチが多すぎる")
        data = [(f"git am の途中のパッチ {x}", _read_file(os.path.join(d, x)))
                for x in [f"{k:04d}" for k in range(nxt, last + 1)] + ["patch"] if os.path.isfile(os.path.join(d, x))]
    elif pos:
        data = [d for p in pos for d in _read_inputs(p, [cwd], allow_dir=sub == "am")]
    elif stdin and stdin[0] == "file":
        data = _read_inputs(stdin[1], [cwd])
    else:
        raise _no_patch(stdin[1] if stdin else "パイプ・標準入力から読む")
    texts = [(k, t) for k, d in data for t in (_mail_texts(d) if sub == "am" else [d.decode("utf-8", "surrogateescape")])]
    return _texts_hit(texts, bases, variants)


def _git_pick(sub: str, args: list[str], cwd: str, gl: list[str], bases: list[str]) -> str | None:
    """cherry-pick / revert: git rev-list・diff-tree でコミットが触るファイルを出す（範囲は各コミット。上限あり）。"""
    pos, _dd, opts = _parse(args, _PICK)
    names = {o for o, _v in opts}
    for o in names:
        if not ({o, "--" + o[5:]} & (_PICK[0] | _PICK[1]) or (len(o) == 2 and o[1] in _PICK_SHORT)):
            raise _no_rev(f"解釈できないオプション {o}")
    if "--stdin" in names:
        raise _no_rev("コミットを標準入力から読む")
    if names & {"--abort", "--quit"} or not (pos or names & {"--continue", "--skip"}):
        return None
    revs, walk = pos, True
    if names & {"--continue", "--skip"}:                   # 続けて当てる sequencer/todo の残り
        p, revs, walk = _state("sequencer/todo", cwd, gl), [], False
        with open(p or os.devnull, encoding="utf-8", errors="surrogateescape") as f:
            lines = f.read().splitlines()
        for s in lines:
            m = re.match(r"\s*(?:(?:pick|p|revert|r)\s+([0-9A-Fa-f]{4,64})\b|#|$)", s)
            if not m:
                raise _no_rev(f"sequencer/todo の行を解釈できない: {s[:40]}")
            revs += [m.group(1)] if m.group(1) else []
        if not revs:
            return None
    try:                                   # --max-count は --no-walk より前に置く（後ろだと祖先をたどってしまう）
        shas = _git(["rev-list", f"--max-count={_MAX_COMMITS + 1}", "--no-walk", *revs, "--"], cwd, gl).split() \
            if walk else revs
        if len(shas) > _MAX_COMMITS:
            raise _no_rev(f"コミットが {_MAX_COMMITS} を超える")
        out = _git(["diff-tree", "--no-commit-id", "--name-only", "-r", "-m", "--root", "-z", "--stdin"], cwd, gl,
                   stdin="\n".join(shas) + "\n")
    except _GitFail as e:
        raise _no_rev(f"{' '.join(revs)} を解決できない: {e}") from e
    for f in (x for x in out.split("\0") if x.strip()):
        if any(protected(f, b) for b in bases):
            return f"{f}（git {sub} するコミットが触る）"
    return None


def _pathspecs_from_file(opts: list[tuple[str, str | None]], cwd: str) -> list[str]:
    out: list[str] = []
    for f in _vals(opts, "--pathspec-from-file"):
        try:
            if f == "-" or f.startswith(("/dev/", "/proc/")):
                raise _no_patch("標準入力")
            data = _read_file(expand_path(f, cwd)).decode("utf-8", "surrogateescape")
        except (OSError, Unverifiable) as e:
            raise _cannot(f"パスの一覧（--pathspec-from-file {f}）を読めない", "パスを引数に並べる") from e
        out += [x for x in data.split("\0" if ("--pathspec-file-nul", None) in opts else "\n") if x.strip()]
    return out


def _diff_names(rev: str | None, paths: list[str], cwd: str, gl: list[str], cached: bool = False) -> list[str]:
    if rev and rev.startswith("-"):
        raise _GitFail(f"リビジョンが - で始まる（{rev}）")
    out = _git(["diff", "--name-only", "-z", "--no-ext-diff", "--no-textconv", "--no-renames",
                *(["--cached"] if cached else []), *([rev] if rev else []), "--", *paths], cwd, gl)
    return [x for x in out.split("\0") if x.strip()]


def _resolves(rev: str, cwd: str, gl: list[str]) -> bool:
    """<rev> がコミット・ツリーとして解決できるか。解決できない（exit 1）以外の失敗は _GitFail のまま上げる。"""
    try:
        return rev.startswith("-") or bool(_git(["rev-parse", "--verify", "--quiet", rev + "^{tree}"], cwd, gl))
    except _GitFail as e:
        if e.code == 1:
            return False
        raise


def _git_checkout(sub: str, args: list[str], cwd: str, gl: list[str], bases: list[str], dirty: str | None) -> str | None:
    """git checkout [<rev>] [--] <path> / git restore [-s <rev>] <path>: パスそのもの（静的）と、git diff --name-only で
    実際に書き換わるファイル（`.`・ディレクトリ・glob も展開される）を見る。<rev> が解決できなければ通す（git も失敗する）。"""
    pos, dd, opts = _parse(args, _CHECKOUT if sub == "checkout" else _RESTORE)
    names = {o for o, _v in opts}
    staged = sub == "restore" and bool(names & {"-S", "--staged"})
    worktree = not staged or bool(names & {"-W", "--worktree"})
    if sub == "checkout":
        paths = pos[dd:] if dd is not None else pos
        rev = pos[0] if (dd if dd is not None else len(pos) >= 2) else None
    else:
        paths, rev = pos, (_vals(opts, "-s", "--source") or [None])[-1]
    if not worktree and not rev:
        return None                                    # 索引を HEAD に戻すだけ（作業ツリーは変えない）
    guessed = sub == "checkout" and dd is None and rev is not None      # `--` 無し: 先頭がリビジョンかは git が決める
    paths = paths + _pathspecs_from_file(opts, cwd)
    for p in paths:
        if any(protected(re.sub(r"^:(?:\([^)]*\)|[/!^]*)", "", p) or p, b, whole_dir=True) for b in [cwd, *bases]):
            return p
    if not paths:
        return None                                    # ブランチの切り替え（対象外。docstring の限界）
    if dirty and not (sub == "checkout" and dd is None and len(pos) == 1):
        raise _cannot(f"同じコマンドの中で先に `{dirty}` が動く（git {sub} で書き換わるファイルが実行時には変わりうる）",
                      f"先のコマンドを別に実行してから、git {sub} を単独で実行する")
    rev = "@{-1}" if rev == "-" else rev
    src = rev or ("HEAD" if staged else None)
    try:
        try:
            files = _diff_names(src, paths[1:] if guessed else paths, cwd, gl, cached=not worktree)
            files += _diff_names(src, paths, cwd, gl, cached=True) if staged and worktree else []
        except _GitFail:
            if not rev or _resolves(rev, cwd, gl):
                raise
            if not guessed:
                return None                            # <rev> が解決できない（git も失敗する）
            files = _diff_names(None, paths, cwd, gl)  # 先頭はリビジョンでなかった（全部が索引から戻すパス）
    except _GitFail as e:
        raise _no_rev(f"git {sub} で書き換わるファイルを求められない: {e}") from e
    for f in files:
        if any(protected(f, b) for b in bases):
            return f"{f}（git {sub} で書き換わる）"
    return None


def _config_write(args: list[str]) -> bool:
    """git config が書き込む形か（--get・--list 等と、キー 1 つだけの読み出し・`git config get|list` 以外）。"""
    pos, _dd, opts = _parse(args, _CONFIG)
    names = {o for o, _v in opts}
    if names & _CFG_READ or pos[:1] in (["get"], ["list"]):
        return False
    return bool(names & _CFG_WRITE) or len(pos) >= 2 or pos[:1] in (["set"], ["unset"], ["edit"],
                                                                   ["rename-section"], ["remove-section"])


def _unalias(sub: str, rest: list[str], cwd: str, gl: list[str]) -> tuple[str, list[str]]:
    """git の別名を組み込みに当たるまで 3 段まで解く。シェルの別名（!）・解けない・3 段超は deny。"""
    for depth in range(_MAX_ALIAS + 1):
        if sub in _GIT_BUILTIN:
            return sub, rest
        if depth == _MAX_ALIAS:
            break
        try:
            al = _git(["config", "--get", f"alias.{sub}"], cwd, gl).strip()
        except _GitFail as e:
            if e.code == 1:
                return sub, rest                       # 別名ではない（git lfs 等の外部コマンド。対象外）
            raise _no_rev(f"git の別名 {sub} を解けない: {e}") from e
        if al.startswith("!"):
            raise _cannot(f"git の別名 {sub} がシェルのコマンド（{al[:40]}）で、動く中身を確かめられない",
                          "別名を使わず元のコマンドを打つ")
        try:
            words = shlex.split(al)
        except ValueError:
            words = []
        while words[:1] and words[0] in ("-p", "-P", "--paginate", "--no-pager"):
            words.pop(0)
        if not words or words[0].startswith("-"):
            raise _no_rev(f"git の別名 {sub}（{al[:40]}）を解釈できない")
        sub, rest = words[0], words[1:] + rest
    raise _no_rev(f"git の別名が {_MAX_ALIAS} 段を超える")


def content_hit(toks: list[str], cur: str | None, dirty: str | None, env: dict[str, str]) -> str | None:
    """中身で書き先が決まるコマンド（git apply / am / cherry-pick / revert / checkout / restore・patch）と git config の
    書き込みを見る。dirty: 同じコマンドの前の断片が作業ツリーや ref を変えうるなら、その断片。env: コマンド中の GIT_*=…。"""
    base = toks[0].rsplit("/", 1)[-1]
    if base not in ("git", "patch", "gpatch"):
        return None
    args, stdin, procsub = _strip_redirs(toks)
    cwd = cur or os.getcwd()
    sub, rest, gl, bases = "patch", args[1:], [], [cwd]
    if base == "git":
        k, gopts = git_split(args)
        if k >= len(args):
            return None
        sub, rest = args[k], args[k + 1:]
        gd, wt = env.get("GIT_DIR"), env.get("GIT_WORK_TREE")
        inject = any(re.fullmatch(r"GIT_CONFIG\w*", x) for x in env)
        for n, v in gopts:
            cwd = expand_path(v, cwd) if n == "-C" else cwd
            gd, wt = (v if n == "--git-dir" else gd), (v if n == "--work-tree" else wt)
            inject = inject or n == "--config-env" or (n == "-c" and v.lower().startswith("alias."))
        if inject and (sub in _CONTENT | {"config"} or sub not in _GIT_BUILTIN):
            raise _cannot(f"git の設定（alias 等）を環境変数・`-c`・`--config-env` で差し替えたまま git {sub} を動かす"
                          "（実際に動くコマンドを確かめられない）", "前置きを外して実行する")
        gl = [f"{o}={expand_path(v, cwd)}" for o, v in (("--git-dir", gd), ("--work-tree", wt)) if v]
        sub, rest = _unalias(sub, rest, cwd, gl)
        if sub == "config":
            return "git config の書き込み（.git/config・~/.gitconfig。hooksPath・alias を書ける）" if _config_write(rest) else None
        if sub not in _CONTENT:
            return None
        for kind, v in (("GIT_DIR / --git-dir", gd), ("GIT_WORK_TREE / --work-tree", wt)):
            p = os.path.realpath(expand_path(v, cwd)) if v and v.strip() and not re.search(r"\$|`", v) else ""
            if v is not None and not os.path.isdir(p):
                raise _cannot(f"{kind}（{v}）の指す先を解決できない", "既存のディレクトリを具体的なパスで書くか、前置きを外す")
            if v is not None and protected(p, cwd, whole_dir=kind.startswith("GIT_W")):
                return f"{v}（{kind} の指す先）"
            bases = [p, cwd] if v is not None and kind.startswith("GIT_W") else bases
    if procsub:
        raise _no_patch("プロセス置換 <( ) から読む") if sub in ("patch", "apply", "am") else _no_rev("プロセス置換 <( )")
    if sub in ("checkout", "restore"):
        return _git_checkout(sub, rest, cwd, gl, bases, dirty)
    if dirty and not _no_write(sub, rest):
        raise _cannot(f"同じコマンドの中で先に `{dirty}` が動く（パッチ・コミットの中身が実行時には変わりうる）",
                      "書き込み・取得を先に別のコマンドで済ませてから、当てるコマンドを単独で実行する")
    if sub == "patch":
        return _patch_cmd(rest, cwd, stdin)
    return _git_apply(sub, rest, cwd, gl, bases, stdin) if sub in ("apply", "am") else _git_pick(sub, rest, cwd, gl, bases)


def _changes_state(toks: list[str]) -> bool:
    """この断片が作業ツリー・ref・パッチのファイルを変えうるか（後ろのパッチ・コミットの判定を信用できなくなる）。"""
    base = toks[0].rsplit("/", 1)[-1]
    if targets(toks):
        return True
    if base in _READ_ONLY or base in _SHELL_NAMES or base not in ("git", "patch", "gpatch"):
        return base not in _READ_ONLY and base not in _SHELL_NAMES
    k = git_split(toks)[0] if base == "git" else 0
    sub = (toks[k] if k < len(toks) else "") if base == "git" else "patch"
    return not (not sub or sub in _GIT_RO or _no_write(sub, _strip_redirs(toks[k + 1:])[0]))


def bash_hit(cmd: str, cwd: str | None) -> str | None:
    a = analyze_command(cmd)
    env = dict(kv.split("=", 1) for kv in a.assigns + [t for toks in a.segments
                                                       if toks[0] in ("export", "declare", "typeset") for t in toks[1:]]
               if kv.startswith("GIT_") and "=" in kv)
    cur, dirty = cwd, None
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
        hit = content_hit(toks, cur, dirty, env)
        if hit:
            return hit
        if dirty is None and _changes_state(toks):
            dirty = " ".join(toks)[:60]
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
    except Unverifiable as e:
        return deny(str(e))
    except Unresolvable as e:
        return deny(f"書き先が解決できない（{e}）ので止めた（判定不能）。書き先を具体的なパスで書き直す。"
                    f"意図した設定の保守なら、保守者が {ENV_ALLOW}=1 を付けて起動する")
    except Exception as e:   # 判定の不具合で素通りさせない
        return deny(f"判定中に例外（{type(e).__name__}）が起きたので止めた（判定不能）。保守者に hook の不具合として報告する")
    return deny(_why(hit)) if hit else 0


if __name__ == "__main__":
    sys.exit(main())
