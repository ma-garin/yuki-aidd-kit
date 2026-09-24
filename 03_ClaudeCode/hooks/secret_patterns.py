#!/usr/bin/env python3
"""秘密情報とコマンド分解の判定を 1 か所に持つ共通部品（hook ではない。hook から import する）。

B-19。秘密ファイルの規則が 5 か所（pre-write-check.sh・settings.sandbox.json・init-project.sh・
pre-commit・文書）に散って食い違っていた。判定はここだけに書き、他の 4 か所は `--check-consistency` で
ここと食い違っていないかを検査する（自動生成はしない）。

  (a) is_secret_path(path, cwd) / is_secret_glob(pattern, cwd) / glob_may_match_secret(pattern)
        秘密ファイル名の判定。realpath と元のパスの両方を小文字化して見る（シンボリックリンク越しも止める）。
        名前のドット区切りの成分に example / sample / template / dist がある雛形は秘密扱いしない（.envrc は秘密のまま）。
        glob（* ? [）は候補名（GLOB_CANDIDATES）に 1 つでも当たりうれば秘密扱い（`.en?`・`.e*`・`*.pem`）
  (b) SECRET_VALUE_PATTERNS / find_secret_values(text) -> [(名前, 行番号)]
        既知形式の秘密値の検出。値そのものは返さない（伏字は describe_hits が型の接頭辞だけで作る）。
        プレースホルダの語（your- / your_ / example / placeholder / xxx / XXX。小文字の example だけを見る）を含む行は除く
  (c) unwrap_command(cmd) -> [文字列...] / analyze_command(cmd)
        先に正規化する（`$'…'` の展開・`${IFS}` → 空白。引用の連結 `g"it"` は字句解析で、`{a,b}` は断片ごとに 1 段展開）。
        Bash のラッパー（bash/sh/zsh/dash -c・sudo・env・xargs・timeout・nohup・command・eval・$( )・` `・
        `find -exec …`・`sh <<< …`）を剥がし、&& ; | || & 改行で分割する。2 段まで再帰。元の文字列も含めて返す。
        剥がした `K=V`（env 形の前置き）は Analysis.assigns に残す（GIT_CONFIG_* 等の差し替えを呼び出し側が止める）
  (d) CLI
        python3 secret_patterns.py --check-consistency [キットのルート]   他 4 か所との一致（exit 0/1）
        python3 secret_patterns.py --self-test                             自分の例を通す（exit 0/1）
        python3 secret_patterns.py --pre-write                             pre-write-check.sh から呼ぶ（stdin に hook の JSON）
        python3 secret_patterns.py --log-decision HOOK DECISION 理由 [ツール] [要約]   sh の hook から (e) を呼ぶ（常に exit 0）
  (e) mask_secrets(text) / log_decision(hook, decision, reason, tool, summary, cwd=None, env=None)
        hook の deny・block・warn・override（AIDD_ALLOW_*・AIDD_*_OK で通した）を `.claude/hook-decisions.log` に
        JSONL で 1 行追記する（B12。時刻・hook・decision・理由 40 字・ツール・コマンドやパスの要約 60 字・解除に使った変数）。
        置き場は injection-guard.log とそろえる（`$CLAUDE_PROJECT_DIR/.claude/`、無ければ呼び出し側の cwd・
        カレントの `.claude/`、どれも無ければ `~/.claude/`）。環境変数 AIDD_HOOK_LOG でファイルを直に指定できる（テスト用）。
        秘密値は伏字にしてから切り詰める（(b) の値パターンに当たる部分と `password=…` 形の値を `***`）。
        書けなくても例外を出さない（記録のために止めない。deny の動作は変えない）。集計は `token_report.py --hooks`
      一致検査は片方向（4 か所に書かれた名前 ⊂ (a)）。pre-write-check.sh に独自の拡張子一覧が残っていれば
      `=~ \.(env|pem|…)$` の形だけを読む（別の書き方にすると検査から漏れる）

標準ライブラリのみ。
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import sys
from pathlib import Path

# ---------------------------------------------------------------- (a) 秘密ファイル名
SECRET_EXTS = (".env", ".pem", ".key", ".p12", ".pfx", ".secret")
SECRET_NAMES = frozenset({".npmrc", ".pypirc", ".netrc", "credentials", "secret", "secrets"})
SECRET_PREFIXES = ("id_rsa", "id_ed25519", "id_ecdsa", "secrets.")
TEMPLATE_MARKERS = frozenset({"example", "sample", "template", "dist"})   # ドット区切りの成分として一致したら雛形（読める）
SECRET_DIRS = frozenset({".aws", ".ssh", ".gnupg"})            # この名前のディレクトリ配下はすべて
SECRET_TAILS = ("/.config/gh/hosts.yml",)                      # gh の OAuth トークン
_HOME_VAR = re.compile(r"\$\{?HOME\}?(?=/|$)")

SECRET_READ_REASON = ("秘密情報のファイル（{path}）は読まない・表示しない。値が要るなら保守者に聞く。"
                      "`.env.example` は読める")


def _name_is_secret(name: str) -> bool:
    n = name.lower()
    if TEMPLATE_MARKERS.intersection(n.split(".")):      # x.example.yml・.env.sample・settings.dist.json（www.distance.jp.key は違う）
        return False
    if n.startswith(".env"):
        return True                                   # .envrc も含む（direnv は export を持つ）
    if n in SECRET_NAMES or n.startswith(SECRET_PREFIXES) or n.endswith(SECRET_EXTS):
        return True
    return n.endswith(".json") and ("credentials" in n or n.startswith("client_secret"))


def expand_path(path: str, cwd: str | None = None) -> str:
    """~ と $HOME を展開し、相対パスは cwd（無ければプロセスの cwd）から絶対パスにする。"""
    p = os.path.expanduser(_HOME_VAR.sub("~", path.strip()))
    if not os.path.isabs(p):
        p = os.path.join(cwd or os.getcwd(), p)
    return p


def is_secret_path(path: str, cwd: str | None = None) -> bool:
    """秘密ファイル（またはその置き場）なら True。判定できない（パスが壊れている等）ときも True（deny 側）。"""
    if not isinstance(path, str) or not path.strip():
        return False
    try:
        p = expand_path(path, cwd)
        cands = {os.path.normpath(p), os.path.realpath(p)}
    except (OSError, ValueError):
        return True
    for c in cands:
        low = c.replace("\\", "/").lower()
        parts = [x for x in low.split("/") if x]
        if not parts:
            continue
        if _name_is_secret(parts[-1]) or SECRET_DIRS.intersection(parts) or low.endswith(SECRET_TAILS):
            return True
    return False


def _expand_braces(p: str, limit: int = 32) -> list[str]:
    m = re.search(r"\{([^{}]*,[^{}]*)\}", p)
    if not m:
        return [p]
    out: list[str] = []
    for alt in m.group(1).split(","):
        out.extend(_expand_braces(p[:m.start()] + alt + p[m.end():], limit))
        if len(out) >= limit:
            break
    return out[:limit]


def glob_literal(pattern: str) -> str:
    """glob から * ? [...] を除いた字面（`**/.env*` → `/.env`、`*.pem` → `.pem`）。"""
    return re.sub(r"\[[^\]]*\]", "", pattern).replace("*", "").replace("?", "")


# glob の当たり判定に使う候補名。_BY_EXT は拡張子で秘密になるもの（`*.pem` で当たる）。
# それ以外は名前の本体が秘密なので、拡張子だけの glob（`*.json`・`*.yml`）では当たりとしない
GLOB_CANDIDATES = (".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials.json",
                   "secrets.yml", "x.pem", "x.key", "x.p12", "x.pfx", "x.env", ".npmrc", ".netrc")
_BY_EXT = frozenset({"x.pem", "x.key", "x.p12", "x.pfx", "x.env"})
_GLOB_CHARS = re.compile(r"[*?\[]")


def _component_may_match(comp: str, shell: bool) -> bool:
    if not _GLOB_CHARS.search(comp) or set(comp) <= {"*"}:
        return False          # glob でない／`*`・`**` だけ（ディレクトリ全体を読むのと同じ。限界として文書化）
    pat, lit = comp.lower(), glob_literal(comp).lower()
    for c in GLOB_CANDIDATES:
        if shell and c.startswith(".") and not pat.startswith("."):
            continue          # シェルの glob は先頭の . に当たらない
        if fnmatch.fnmatchcase(c, pat) and (c in _BY_EXT or lit not in ("", os.path.splitext(c)[1])):
            return True
    return False


def glob_may_match_secret(pattern: str, shell: bool = False) -> bool:
    """glob（* ? [ を含む）が秘密ファイルに当たりうるなら True。`.en?`・`**/.e*`・`*.pem`・`~/.ss*/config`。"""
    if not isinstance(pattern, str) or not _GLOB_CHARS.search(pattern):
        return False
    for alt in _expand_braces(pattern):
        parts = [x for x in alt.replace("\\", "/").split("/") if x]
        if parts and _component_may_match(parts[-1], shell):
            return True
        for comp in parts[:-1]:
            if _GLOB_CHARS.search(comp) and set(comp) > {"*"} and any(
                    fnmatch.fnmatchcase(d, comp.lower()) for d in SECRET_DIRS):
                return True
    return False


def is_secret_glob(pattern: str, cwd: str | None = None) -> bool:
    """glob が秘密ファイルを指しうるなら True（`**/.env*`・`**/.en?` は True、`**/*.py`・`**/*` は False）。"""
    if not isinstance(pattern, str) or not pattern.strip():
        return False
    if glob_may_match_secret(pattern):
        return True
    for alt in _expand_braces(pattern):
        lit = glob_literal(alt)
        if lit.strip("/") and is_secret_path(lit, cwd):
            return True
    return False


# ---------------------------------------------------------------- (b) 秘密値
# (名前, 接頭辞（--check-consistency で pre-commit の語と突き合わせる）, 伏字, 正規表現)
# 接頭辞だけの言及（文書の「AKfycb で始まる」等）で止めないよう、各形式に最低の長さを持たせる
SECRET_VALUE_PATTERNS: tuple[tuple[str, tuple[str, ...], str, re.Pattern[str]], ...] = (
    ("AWS アクセスキー", ("AKIA",), "AKIA****", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub トークン", ("ghp_", "gho_", "ghs_", "ghu_", "ghr_"), "gh*_****",
     re.compile(r"\bgh[posur]_[A-Za-z0-9]{36}\b")),
    ("GitHub トークン", ("github_pat_",), "gh*_****", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("Slack トークン", ("xoxa-", "xoxb-", "xoxp-", "xoxr-", "xoxs-"), "xox?-****",
     re.compile(r"\bxox[abprs]-[0-9]{8,13}-[0-9]{8,13}-[A-Za-z0-9-]{20,}")),
    ("Anthropic API キー", ("sk-ant-",), "sk-ant-****", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API キー", ("sk-",), "sk-****", re.compile(r"\bsk-(?:[A-Za-z0-9]{20,}|proj-[A-Za-z0-9_-]{20,})")),
    ("秘密鍵", ("-----BEGIN",), "-----BEGIN … PRIVATE KEY-----", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("JWT", ("eyJ",), "eyJ****.eyJ****", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ")),
    ("Google API キー", ("AIza",), "AIza****", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("GAS デプロイ ID", ("AKfycb",), "AKfycb****", re.compile(r"\bAKfycb[A-Za-z0-9_-]{20,}")),
)
_MASK = {name: mask for name, _kw, mask, _rx in SECRET_VALUE_PATTERNS}
# pre-commit の簡易規則にある汎用語。誤検知が多いので deny には使わないが、一致検査では既知として扱う
KNOWN_BODY_WORDS = frozenset({"api[_-]?key", "secret", "password", "token"})
# 雛形・文書の行（`SLACK_BOT_TOKEN=xoxb-your-token-here`・`sk-xxxxxxxx…`）。大文字の EXAMPLE は見ない
# （AWS 公式の偽キー AKIAIOSFODNN7EXAMPLE は実物と同じ形なので、検出器の確認用に当たるままにする）
PLACEHOLDER_WORDS = ("your-", "your_", "example", "placeholder", "xxx", "XXX")


def find_secret_values(text: str) -> list[tuple[str, int]]:
    """既知形式の秘密値を探す。[(名前, 行番号)]。値そのものは返さない。"""
    if not isinstance(text, str) or not text:
        return []
    hits: list[tuple[str, int]] = []
    for no, line in enumerate(text.splitlines(), 1):
        if any(w in line for w in PLACEHOLDER_WORDS):
            continue
        for name, _kw, _mask, rx in SECRET_VALUE_PATTERNS:
            if (name, no) not in hits and rx.search(line):
                hits.append((name, no))
    return hits


def describe_hits(hits: list[tuple[str, int]], where: str = "") -> str:
    """理由文用。値は出さず、型の名前・型の接頭辞の伏字・行番号だけを書く。"""
    return "、".join(f"{name}（{_MASK.get(name, '****')}）{where}{no} 行目" for name, no in hits)


# ---------------------------------------------------------------- (e) hook の判定の記録（B12）
# 値パターンに当たった所から、続く英数字・記号（JWT の残り・鍵の続き）までを伏字にする
_MASK_RX = tuple(re.compile(rf"(?:{rx.pattern})[A-Za-z0-9_\-.+/=]*") for _n, _kw, _m, rx in SECRET_VALUE_PATTERNS)
# 既知形式でない値も、名前が秘密らしい代入（password=…・API_KEY: …・Bearer …）は値を伏せる（安全側）
_MASK_KV = re.compile(r"(?i)\b([A-Za-z0-9_.-]*(?:passw(?:or)?d|secret|token|api[_-]?key|credential)[A-Za-z0-9_.-]*"
                      r"[\"']?\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s;&|]+)")
_MASK_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-.+/=]+")
LOG_NAME = "hook-decisions.log"
DECISIONS = ("deny", "block", "warn", "override")


def mask_secrets(text: str) -> str:
    """秘密値らしい部分を *** にする。プレースホルダの行も伏せる（記録は安全側に倒す）。"""
    if not isinstance(text, str):
        return ""
    for rx in _MASK_RX:
        text = rx.sub("***", text)
    text = _MASK_KV.sub(lambda m: m.group(1) + "***", text)
    return _MASK_BEARER.sub(lambda m: m.group(1) + "***", text)


def _short(text: str, n: int) -> str:
    t = " ".join(mask_secrets(text if isinstance(text, str) else str(text or "")).split())
    return t if len(t) <= n else t[:n - 1] + "…"


def decision_log_path(cwd: str | None = None) -> Path:
    explicit = os.environ.get("AIDD_HOOK_LOG")
    if explicit:
        return Path(explicit)
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), cwd, os.getcwd()):
        if base and (Path(base) / ".claude").is_dir():
            return Path(base) / ".claude" / LOG_NAME
    return Path.home() / ".claude" / LOG_NAME


def log_decision(hook: str, decision: str, reason: str, tool: str = "", summary: str = "",
                 cwd: str | None = None, env: str | None = None) -> None:
    """hook の判定を 1 行追記する。秘密値は伏字。失敗しても何もしない（呼び出し側の判定を変えない）。"""
    try:
        import time
        rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "hook": str(hook), "decision": str(decision),
               "reason": _short(reason, 40), "tool": _short(tool, 20), "summary": _short(summary, 60)}
        if env:
            rec["env"] = str(env)
        path = decision_log_path(cwd)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:    # 記録は付け足し。書けない・壊れた入力でも hook を止めない
        pass


def input_summary(tool_input) -> str:
    """ツール入力から要約の元（コマンド・パス・パターン）を取る。"""
    if not isinstance(tool_input, dict):
        return ""
    for k in ("command", "file_path", "notebook_path", "pattern", "path", "url", "query"):
        v = tool_input.get(k)
        if isinstance(v, str) and v:
            return v
    return ""


# ---------------------------------------------------------------- (c) コマンドの分解
MAX_DEPTH = 2
_SHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh"})
_CONTROL = frozenset({"then", "do", "else", "elif", "if", "while", "until", "!", "{", "}", "(", ")"})
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_SUDO_ARG = frozenset({"-u", "-g", "-C", "-D", "-h", "-p", "-U", "-r", "-t", "-T", "--user", "--group",
                       "--chdir", "--host", "--prompt", "--other-user", "--role", "--type", "--close-from",
                       "--command-timeout"})
_ENV_ARG = frozenset({"-u", "--unset", "-C", "--chdir"})
_XARGS_ARG = frozenset({"-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s", "--arg-file", "--delimiter",
                        "--max-args", "--max-procs", "--max-chars", "--max-lines", "--process-slot-var"})
_TIMEOUT_ARG = frozenset({"-s", "-k", "--signal", "--kill-after"})
_SIMPLE_WRAPPERS = frozenset({"nohup", "exec", "time", "builtin", "command", "nice", "stdbuf", "setsid", "ionice",
                              "unbuffer", "caffeinate"})
# exec -a / nice -n / stdbuf -i -o -e / ionice -c -n -p / caffeinate -t -w
_SIMPLE_ARG = frozenset({"-a", "-n", "--adjustment", "-i", "-o", "-e", "-c", "--class", "--classdata", "-p", "--pid",
                         "-P", "--pgid", "-u", "--uid", "-t", "-w"})
_FLOCK_ARG = frozenset({"-w", "--wait", "--timeout", "-E", "--conflict-exit-code"})
_HEREDOC = re.compile(r"(<<-?[ \t]*(['\"]?)(\w+)\2)([^\n]*)\n(.*?)\n[ \t]*\3[ \t]*(?=\n|$)", re.DOTALL)
_SHELL_BEFORE = re.compile(r"(?:^|[\s;&|(])(?:sudo\s+(?:-\S+\s+)*)?(?:ba|z|da|k)?sh(?:\s+-\S+)*\s*$")


_ANSI_C = re.compile(r"\$'((?:[^'\\]|\\.)*)'")
_ANSI_ESC = re.compile(r"\\(x[0-9A-Fa-f]{1,2}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|[0-7]{1,3}|.)", re.DOTALL)
_ESC = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "v": "\v",
        "\\": "\\", "'": "'", '"': '"', "?": "?"}
_IFS = re.compile(r"\$\{IFS\}|\$IFS\b")
_LOCALE_Q = re.compile(r'(?<!\\)\$(?=")')          # $"…"（ロケール引用）は "…" と同じ


def _ansi_c(body: str) -> str:
    def rep(m: re.Match[str]) -> str:
        e = m.group(1)
        try:
            if e[0] in "xuU":
                return chr(int(e[1:], 16))
            if e[0] in "01234567":
                return chr(int(e, 8) & 0xFF)
        except ValueError:
            return m.group(0)
        return _ESC.get(e, "\\" + e)
    return _ANSI_ESC.sub(rep, body)


def normalize(cmd: str) -> str:
    """字句解析の前の正規化: `$'…'` を展開して単引用に直す・`$"…"` を `"…"` に・`${IFS}` / `$IFS` を空白にする。"""
    s = _ANSI_C.sub(lambda m: "'" + _ansi_c(m.group(1)).replace("'", "'\\''") + "'", cmd)
    return _IFS.sub(" ", _LOCALE_Q.sub("", s))


class Analysis:
    """analyze_command の結果。strings: 照合用の文字列（元の文字列・正規化後・入れ子の中身・剥がした各断片）、
    segments: 剥がした各断片のトークン列（{a,b} は展開済み）、assigns: 剥がした `K=V`、
    too_deep: MAX_DEPTH を超えて入れ子が残った。"""

    def __init__(self) -> None:
        self.strings: list[str] = []
        self.segments: list[list[str]] = []
        self.pipe_out: list[bool] = []          # segments と同じ並び。その断片の出力が | で次へ流れるか
        self.assigns: list[str] = []
        self.too_deep = False

    def add(self, s: str) -> None:
        if s and s not in self.strings:
            self.strings.append(s)


def tokens(s: str) -> list[str]:
    """シェルの字句に分ける（引用は外す。リダイレクト記号 > >> < 等は独立したトークンになる）。"""
    try:
        lx = shlex.shlex(s, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        lx.commenters = ""
        return list(lx)
    except ValueError:
        return s.split()


def _join(toks: list[str]) -> str:
    # 空白・引用符を含むトークンだけ引用し直す（照合側の strip_noise が引用の中身を語として扱わないように）
    return " ".join(shlex.quote(t) if (not t or re.search(r"[\s'\"\\]", t)) else t for t in toks)


def _match_paren(s: str, i: int) -> int:
    depth, q, n = 1, None, len(s)
    while i < n:
        c = s[i]
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == "\\":
            i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return n


def _scan(s: str) -> tuple[list[tuple[str, bool]], list[str]]:
    """トップレベルの && || ; | & 改行と、グループ・関数本体の { } ( ) で分割する。戻り値の各断片には
    「出力が | で次へ流れるか」を添える。$( )・` `・<( )・>( ) の中身（単引用の外）は入れ子として集める。"""
    segs: list[tuple[str, bool]] = []
    nested: list[str] = []
    buf: list[str] = []

    def flush(pipe: bool = False) -> None:
        seg = "".join(buf).strip()
        if seg:
            segs.append((seg, pipe))
        buf.clear()

    i, n, q = 0, len(s), None
    while i < n:
        c = s[i]
        if q == "'":
            buf.append(c)
            q = None if c == "'" else q
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            buf.append(s[i:i + 2])
            i += 2
            continue
        if s.startswith("$(", i) or (q is None and (s.startswith("<(", i) or s.startswith(">(", i))):
            j = _match_paren(s, i + 2)
            nested.append(s[i + 2:j])
            buf.append(s[i:j + 1])
            i = j + 1
            continue
        if c == "`":
            j = s.find("`", i + 1)
            j = n if j < 0 else j
            nested.append(s[i + 1:j])
            buf.append(s[i:j + 1])
            i = j + 1
            continue
        if q == '"':
            buf.append(c)
            q = None if c == '"' else q
            i += 1
            continue
        if c in "'\"":
            q = c
            buf.append(c)
            i += 1
            continue
        prev = s[i - 1] if i else " "
        nxt = s[i + 1] if i + 1 < n else " "
        if c in "\n;()":                                            # ( ) はサブシェル・関数定義 f()
            flush()
            i += 1
            continue
        if (c == "{" and prev in " \t\n;&|" and nxt in " \t\n") or (c == "}" and prev in " \t\n;" and nxt in " \t\n;&|)"):
            flush()                                                   # { …; } のグループ（{a,b}・${x}・{} は分けない）
            i += 1
            continue
        if c == "&":
            if s.startswith("&&", i):
                flush()
                i += 2
            elif prev in "<>" or s.startswith("&>", i):              # >&  &>  はリダイレクト
                buf.append(c)
                i += 1
            else:
                flush()
                i += 1
            continue
        if c == "|":
            if s.startswith("||", i):
                flush()
                i += 2
            elif prev == ">":                                         # >| はリダイレクト
                buf.append(c)
                i += 1
            else:
                flush(pipe=True)
                i += 2 if s.startswith("|&", i) else 1
            continue
        buf.append(c)
        i += 1
    flush()
    return segs, nested


def _skip_opts(toks: list[str], i: int, with_arg: frozenset[str]) -> int:
    while i < len(toks) and toks[i].startswith("-") and toks[i] != "-":
        o = toks[i]
        i += 1
        if o == "--":
            break
        if o in with_arg:
            i += 1
    return i


def _peel(toks: list[str]) -> tuple[list[str], list[str], list[str]]:
    """先頭のラッパーを剥がす。戻り値: (剥がした後のトークン列, 入れ子のコマンド文字列, 剥がした K=V)。"""
    nested: list[str] = []
    assigns: list[str] = []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        b = t.rsplit("/", 1)[-1]
        if _ASSIGN.match(t):
            assigns.append(t)
            i += 1
            continue
        if t in _CONTROL:
            i += 1
            continue
        if b in ("sudo", "doas"):
            i = _skip_opts(toks, i + 1, _SUDO_ARG)
            continue
        if b == "flock":                                  # flock [opts] <file> (-c '<cmd>' | <cmd> …)
            i = _skip_opts(toks, i + 1, _FLOCK_ARG) + 1
            if i < n and toks[i] in ("-c", "--command"):
                if i + 1 < n:
                    nested.append(toks[i + 1])
                return [], nested, assigns
            continue
        if b == "env":
            env_at = i
            i += 1
            while i < n:
                o = toks[i]
                if o == "--":
                    i += 1
                    break
                if o in ("-S", "--split-string") and i + 1 < n:
                    nested.append(toks[i + 1])
                    i += 2
                    continue
                if o in _ENV_ARG:
                    i += 2
                    continue
                if _ASSIGN.match(o):
                    assigns.append(o)
                if o.startswith("-") or _ASSIGN.match(o):
                    i += 1
                    continue
                break
            if i >= n:                                   # 素の env は環境を表示するコマンドとして残す
                return toks[env_at:], nested, assigns
            continue
        if b == "xargs":
            i = _skip_opts(toks, i + 1, _XARGS_ARG)
            continue
        if b == "timeout":
            i = _skip_opts(toks, i + 1, _TIMEOUT_ARG) + 1    # + 秒数
            continue
        if b in _SIMPLE_WRAPPERS:
            i = _skip_opts(toks, i + 1, _SIMPLE_ARG)
            continue
        if b in _SHELLS:
            j, has_c = i + 1, False
            while j < n and toks[j].startswith(("-", "+")) and toks[j] not in ("-", "--"):
                o = toks[j]
                j += 1
                if o in ("-o", "+o", "-O", "+O", "--rcfile", "--init-file"):
                    j += 1
                elif not o.startswith("--") and "c" in o[1:]:
                    has_c = True
                    break
            if has_c and j < n:
                nested.append(toks[j])
            nested += [toks[k + 1] for k in range(i, n - 1) if toks[k] == "<<<"]   # sh <<< '…' の中身
            break
        if b == "eval":
            if i + 1 < n:
                nested.append(" ".join(toks[i + 1:]))
            break
        break
    return toks[i:], nested, assigns


def _find_exec(toks: list[str]) -> list[str]:
    """`find … -exec <cmd> … {} ;|+` の <cmd> 部分（-execdir / -ok / -okdir も）。"""
    out: list[str] = []
    i = 0
    while i < len(toks):
        if toks[i] in ("-exec", "-execdir", "-ok", "-okdir"):
            j = i + 1
            while j < len(toks) and toks[j] not in (";", "+"):
                j += 1
            if j > i + 1:
                out.append(_join(toks[i + 1:j]))
            i = j
        i += 1
    return out


def _strip_heredocs(s: str) -> tuple[str, list[str]]:
    """ヒアドキュメント本文を外す（本文の行を別コマンドと誤読しない）。シェルに流す本文だけは入れ子として返す。"""
    nested: list[str] = []

    def rep(m: re.Match[str]) -> str:
        line_start = s.rfind("\n", 0, m.start()) + 1
        if _SHELL_BEFORE.search(s[line_start:m.start()]):
            nested.append(m.group(5))
        return m.group(1) + m.group(4)

    return _HEREDOC.sub(rep, s), nested


def _analyze(cmd: str, depth: int, out: Analysis) -> None:
    norm = normalize(cmd)
    out.add(norm)
    text, nested = _strip_heredocs(norm)
    segs, inner = _scan(text)
    nested += inner
    for seg, pipe in segs:
        # {a,b} を 1 段展開し、空の選択肢（{git,}）から出た空トークンは捨てる
        toks, sub, assigns = _peel([x for t in tokens(seg) for x in _expand_braces(t) if x or x == t])
        nested += sub
        out.assigns += assigns
        if toks and toks[0].rsplit("/", 1)[-1] == "find":
            nested += _find_exec(toks)
        if toks:
            out.segments.append(toks)
            out.pipe_out.append(pipe)
            out.add(_join(toks))
            if "/" in toks[0]:           # /usr/bin/git → git（規則はコマンド名で書く）
                out.add(_join([toks[0].rsplit("/", 1)[-1]] + toks[1:]))
    for sub in nested:
        if not sub.strip():
            continue
        out.add(sub)
        if depth <= 0:
            out.too_deep = True
            continue
        _analyze(sub, depth - 1, out)


def analyze_command(cmd: str, depth: int = MAX_DEPTH) -> Analysis:
    out = Analysis()
    if isinstance(cmd, str) and cmd.strip():
        out.add(cmd)
        _analyze(cmd, depth, out)
    return out


def unwrap_command(cmd: str, depth: int = MAX_DEPTH) -> list[str]:
    """元の文字列＋入れ子の中身＋剥がした各断片。照合はこの全部に対して行う。"""
    return analyze_command(cmd, depth).strings


# ---------------------------------------------------------------- pre-write（pre-write-check.sh から呼ぶ）
def _write_texts(tool_input: dict) -> list[tuple[str, str]]:
    out = []
    for key in ("content", "new_string", "new_source"):
        v = tool_input.get(key)
        if isinstance(v, str):
            out.append((key, v))
    for k, e in enumerate(tool_input.get("edits") or []):
        if isinstance(e, dict) and isinstance(e.get("new_string"), str):
            out.append((f"edits[{k}].new_string", e["new_string"]))
    return out


def pre_write(stdin_text: str) -> int:
    """deny なら hook の JSON を 1 つだけ出す。警告なら 1 行ずつ出す。何も無ければ無言。入力が読めなければ exit 3。"""
    try:
        data = json.loads(stdin_text)
        if not isinstance(data, dict):
            raise ValueError("JSON の最上位がオブジェクトでない")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            raise ValueError("tool_input がオブジェクトでない")
    except ValueError:
        log_decision("pre-write-check", "deny", "hook の入力が読めない（fail-closed）")
        return 3     # 入力が読めない（pre-write-check.sh が deny にする。2 は python3 がファイルを開けないときの値）
    fp = ti.get("file_path") or ti.get("notebook_path") or ""
    tool = data.get("tool_name") if isinstance(data.get("tool_name"), str) else ""
    cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else None
    found = []
    for where, text in _write_texts(ti):
        hits = find_secret_values(text)
        if hits:
            found.append(describe_hits(hits, f"{where} "))
    lines = []
    if found:
        what = "、".join(found)
        if os.environ.get("AIDD_SECRET_OK") != "1":
            reason = (f"[pre-write-check] 書き込む本文に秘密情報らしき値がある: {what}。"
                      "値はファイルに書かない（環境変数や .env から読む形にし、.env 自体は保守者が用意する）。"
                      "テスト用の偽値など意図したものなら、保守者が AIDD_SECRET_OK=1 を付けて起動する")
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
            }}, ensure_ascii=False))
            log_decision("pre-write-check", "deny", f"本文に秘密値: {what}", tool, fp, cwd)
            return 0
        lines.append(f"⚠ 秘密情報らしき値を書き込む（AIDD_SECRET_OK=1 のため通す）: {what}")
        log_decision("pre-write-check", "override", f"本文に秘密値: {what}", tool, fp, cwd, env="AIDD_SECRET_OK")
    if fp and is_secret_path(fp, data.get("cwd")):
        lines.append(f"⚠ 秘密情報ファイルへの書き込み: {fp}")
        log_decision("pre-write-check", "warn", "秘密情報ファイルへの書き込み", tool, fp, cwd)
    if lines:
        print("\n".join(lines))
    return 0


# ---------------------------------------------------------------- (d) 他 4 か所との一致検査
_NEUTRAL_CWD = "/aidd-consistency-check"


def _alternatives(rx: str) -> list[str]:
    """最上位の | で分ける（[] と () の中は分けない）。"""
    out, buf, depth, cls = [], [], 0, False
    i = 0
    while i < len(rx):
        c = rx[i]
        if c == "\\" and i + 1 < len(rx):
            buf.append(rx[i:i + 2])
            i += 2
            continue
        if cls:
            cls = c != "]"
        elif c == "[":
            cls = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "|" and depth == 0:
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    out.append("".join(buf))
    return [a for a in out if a]


def _literal_prefix(rx: str) -> str:
    m = re.match(r"[^\[\](){}?*+.|^$\\]*", rx)
    return m.group(0) if m else ""


def _check_names(label: str, names: list[str], ng: list[str]) -> None:
    if not names:
        ng.append(f"{label}: 秘密ファイルの規則が見つからない（判定不能は不一致として扱う）")
    for nm in names:
        lit = glob_literal(nm.replace("**/", "")).removeprefix("./")
        if not lit.strip("/") or not is_secret_path(lit, _NEUTRAL_CWD):
            ng.append(f"{label}: `{nm}` が secret_patterns.py の is_secret_path で秘密と判定されない")


def check_consistency(root: Path) -> list[str]:
    ng: list[str] = []
    hooks = root / "03_ClaudeCode/hooks"
    # 1. pre-write-check.sh: 判定を secret_patterns.py に委ねていること。独自の拡張子一覧が残っていればそれも照合
    f = hooks / "pre-write-check.sh"
    try:
        body = f.read_text(encoding="utf-8")
        exts = [e for m in re.finditer(r"\\\.\(([\w|]+)\)\$", body) for e in m.group(1).split("|")]
        if "secret_patterns.py" not in body:
            ng.append(f"{f.name}: secret_patterns.py を呼んでいない（判定が二重になる）")
        if exts:
            _check_names(f.name, [f"x.{e}" for e in exts], ng)
    except OSError as e:
        ng.append(f"{f.name}: 読めない（{e}）")
    # 2. settings.sandbox.json: sandbox.filesystem.denyRead と permissions.deny の Read(...)
    f = root / "02_共通/ひな形/settings.sandbox.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        names = list((d.get("sandbox") or {}).get("filesystem", {}).get("denyRead") or [])
        names += [m.group(1) for r in (d.get("permissions") or {}).get("deny") or []
                  if (m := re.fullmatch(r"Read\((.*)\)", r))]
        _check_names(f.name, names, ng)
    except (OSError, ValueError, AttributeError) as e:
        ng.append(f"{f.name}: 読めない（{e}）")
    # 3. init-project.sh: 生成する .gitignore の「# 秘密情報」の段
    f = root / "00_導入/02_プロジェクト配布/init-project.sh"
    try:
        m = re.search(r"^# 秘密情報\n(.*?)^#", f.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL)
        names = [ln.strip() for ln in (m.group(1).splitlines() if m else []) if ln.strip()]
        _check_names(f.name, names, ng)
    except OSError as e:
        ng.append(f"{f.name}: 読めない（{e}）")
    # 4. pre-commit: 本文規則 PATTERNS の各語が (b) の接頭辞か既知の汎用語
    f = root / "02_共通/ツール/pre-commit"
    try:
        m = re.search(r"PATTERNS=(['\"])\((.*)\)\1", f.read_text(encoding="utf-8"))
        if not m:
            ng.append(f"{f.name}: PATTERNS が見つからない（判定不能は不一致として扱う）")
        else:
            kws = [k.lower() for _n, ks, _m, _r in SECRET_VALUE_PATTERNS for k in ks]
            for alt in _alternatives(m.group(2)):
                lit = _literal_prefix(alt).lower()
                if alt.lower() in KNOWN_BODY_WORDS or (lit and any(lit.startswith(k) for k in kws)):
                    continue
                ng.append(f"{f.name}: 本文規則の語 `{alt}` が SECRET_VALUE_PATTERNS にも既知語にも無い")
    except OSError as e:
        ng.append(f"{f.name}: 読めない（{e}）")
    return ng


# ---------------------------------------------------------------- self-test
def self_test() -> list[str]:
    bad: list[str] = []
    cwd = "/work/proj"
    for p in (".env", ".env.local", "config/.env.production", "prod.env", "server.pem", "tls.key", "a.p12",
              "b.pfx", "id_rsa", "id_ed25519.pub", "id_ecdsa", "gcp-credentials.json", "client_secret_1.json",
              ".npmrc", ".pypirc", ".netrc", "secrets.yml", "credentials", "~/.aws/config", "~/.ssh/known_hosts",
              "~/.gnupg/", "$HOME/.ssh/id_rsa", "~/.config/gh/hosts.yml", "/work/PROJ/.ENV", ".envrc"):
        if not is_secret_path(p, cwd):
            bad.append(f"is_secret_path({p!r}) が False")
    if not is_secret_path("certs/www.distance.jp.key", cwd) or is_secret_path("settings.dist.json", cwd):
        bad.append("雛形の印をドット区切りの成分で見ていない（www.distance.jp.key は秘密、settings.dist.json は雛形）")
    for p in (".env.example", ".env.sample", ".env.template", ".env.dist", "config/secrets.example.yml",
              "README.md", "src/app.py", "secret_patterns.py", "docs/credentials.md", "env.py", "keys.py", ""):
        if is_secret_path(p, cwd):
            bad.append(f"is_secret_path({p!r}) が True")
    for g, want in (("**/.env*", True), ("*.pem", True), ("{.env,x}", True), ("**/.en?", True), (".e*", True),
                    ("id_*", True), ("~/.ss*/config", True), ("**/*.py", False), ("*", False), ("**/*", False),
                    ("**/.env.example", False), ("*.json", False), ("*.yml", False)):
        if is_secret_glob(g, cwd) != want:
            bad.append(f"is_secret_glob({g!r}) が {not want}")
    if glob_may_match_secret("*.local", shell=True) or not glob_may_match_secret(".*", shell=True):
        bad.append("シェルの glob で先頭の . の扱いが違う（*.local は .env.local に当たらない、.* は当たる）")
    # 偽の値は連結で作る（このファイル自体が秘密値の検査に掛からないように）
    fakes = {"AWS アクセスキー": "AKIA" + "IOSFODNN7EXAMPLE", "GitHub トークン": "ghp_" + "FAKE" * 9,
             "Slack トークン": "xoxb-" + "1" * 12 + "-" + "2" * 13 + "-" + "Fake" * 6, "OpenAI API キー": "sk-" + "a" * 24,
             "Anthropic API キー": "sk-ant-" + "b" * 24, "秘密鍵": "-----BEGIN RSA " + "PRIVATE KEY-----",
             "JWT": "eyJ" + "h" * 12 + ".eyJ" + "p" * 8, "Google API キー": "AIza" + "c" * 35,
             "GAS デプロイ ID": "AKfycb" + "d" * 30}
    for name, val in fakes.items():
        hits = find_secret_values(f"x = 1\nKEY={val}\n")
        if (name, 2) not in hits:
            bad.append(f"find_secret_values が {name} を 2 行目に見つけない（{hits}）")
        if val in describe_hits(hits):
            bad.append(f"describe_hits が {name} の値を出している")
        if val in mask_secrets(f"curl -H 'X: {val}' https://a.test") or val[4:] in mask_secrets(f"k={val}"):
            bad.append(f"mask_secrets が {name} の値を伏せていない")
    for raw, want in (("DB_PASSWORD=hunter2 ./run", "DB_PASSWORD=*** ./run"),
                      ("curl -H 'Authorization: Bearer abc.def' x", "curl -H 'Authorization: Bearer ***' x"),
                      ("git status && ls -la", "git status && ls -la")):
        if mask_secrets(raw) != want:
            bad.append(f"mask_secrets({raw!r}) = {mask_secrets(raw)!r}（期待 {want!r}）")
    for text in ("API_KEY=your-key-here", "AKfycb で始まる ID", "ghp_ で始まるトークン", "task-abcdefghijklmnopqrstuvwxyz",
                 "SLACK_BOT_TOKEN=xoxb-your-token-here", "OPENAI_API_KEY=sk-" + "x" * 30,
                 "# example: AKIA" + "IOSFODNN7EXAMPLE"):
        if find_secret_values(text):
            bad.append(f"find_secret_values({text!r}) が誤検知")
    for cmd, want in (("bash -c 'git reset --hard'", "git reset --hard"),
                      ("sudo -u root rm -rf /tmp/x", "rm -rf /tmp/x"),
                      ("env A=1 B=2 git push --force", "git push --force"),
                      ("find . | xargs -n 1 rm -rf", "rm -rf"),
                      ("timeout 5 nohup git clean -fd", "git clean -fd"),
                      ("echo \"$(git stash drop)\"", "git stash drop"),
                      ("echo `git add -A`", "git add -A"),
                      ("git status && git reset --hard; ls", "git reset --hard"),
                      ("sh -c \"bash -c 'git branch -D x'\"", "git branch -D x"),
                      ("bash <<'EOF'\ngit reset --hard\nEOF", "git reset --hard"),
                      ("git $'reset' --hard", "git reset --hard"),
                      ("git $'\\x72eset' --hard", "git reset --hard"),
                      ("git${IFS}reset${IFS}--hard", "git reset --hard"),
                      ("g\"it\" re's'et --hard", "git reset --hard"),
                      ("git {reset,x} --hard", "git reset x --hard"),
                      ("find . -name x -exec rm -rf {} +", "rm -rf {}"),
                      ("find . -exec git clean -fd \\;", "git clean -fd"),
                      ("bash <<< 'git reset --hard'", "git reset --hard"),
                      ("{git,} reset --hard", "git reset --hard"),
                      ('$"git" reset --hard', "git reset --hard"),
                      ("f() { git reset --hard; }; f", "git reset --hard"),
                      ("( cd x && git clean -fd )", "git clean -fd"),
                      ("setsid nice -n 5 git clean -fd", "git clean -fd"),
                      ("flock /tmp/l git stash drop", "git stash drop"),
                      ("flock /tmp/l -c 'git stash drop'", "git stash drop")):
        if want not in unwrap_command(cmd):
            bad.append(f"unwrap_command({cmd!r}) に {want!r} が無い: {unwrap_command(cmd)}")
    s = unwrap_command("git commit -m \"$(cat <<'EOF'\ngit add -A を禁止\nEOF\n)\"")
    if "git add -A を禁止" in s or any(x.startswith("git add") for x in s):
        bad.append(f"ヒアドキュメント本文をコマンドとして扱った: {s}")
    s = unwrap_command("echo 'bash -c \"git reset --hard\"'")
    if any(x.startswith(("git", "bash")) for x in s):
        bad.append(f"単引用の中の bash -c を剥がした: {s}")
    if analyze_command("echo .env | xargs cat; ls").pipe_out != [True, False, False]:
        bad.append("パイプで流す断片の印（pipe_out）が違う")
    a = analyze_command("GIT_DIR=/x env GIT_CONFIG_COUNT=1 git status")
    if a.assigns != ["GIT_DIR=/x", "GIT_CONFIG_COUNT=1"]:
        bad.append(f"剥がした K=V が assigns に残らない: {a.assigns}")
    if not analyze_command("bash -c \"sh -c 'bash -c \\\"sh -c x\\\"'\"").too_deep:
        bad.append("3 段の入れ子で too_deep が立たない")
    return bad


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--self-test":
        bad = self_test()
        for b in bad:
            print(f"❌ {b}")
        print("✅ self-test: 全件一致" if not bad else f"❌ self-test: {len(bad)} 件不一致")
        return 1 if bad else 0
    if len(argv) >= 2 and argv[1] == "--check-consistency":
        root = Path(argv[2]) if len(argv) >= 3 else Path(__file__).resolve().parents[2]
        ng = check_consistency(root)
        for x in ng:
            print(f"❌ {x}")
        print("✅ 秘密情報の規則: 4 か所とも secret_patterns.py と一致" if not ng
              else f"❌ 秘密情報の規則: {len(ng)} 件の不一致（secret_patterns.py に足すか、その箇所を直す）")
        return 1 if ng else 0
    if len(argv) >= 2 and argv[1] == "--pre-write":
        try:
            return pre_write(sys.stdin.read())
        except Exception as e:   # RecursionError（深い入れ子の JSON）等。Traceback を出さず deny
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": f"[pre-write-check] hook 内部エラー: {type(e).__name__}（判定不能なので止めた）",
            }}, ensure_ascii=False))
            log_decision("pre-write-check", "deny", f"hook 内部エラー: {type(e).__name__}")
            return 0
    if len(argv) >= 5 and argv[1] == "--log-decision":
        log_decision(argv[2], argv[3], argv[4], *(argv[5:7]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
