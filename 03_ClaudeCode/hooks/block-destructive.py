#!/usr/bin/env python3
"""取り返しのつかない操作・安全装置の迂回・秘密情報の読み出しを止める PreToolUse フック（Bash 対象）。

根拠: `rules/speed-harness.md` H-2 の禁止操作（`git add -A` / `stash` / `checkout` / `reset` / `clean`）と
`06_保守者向け/保守者の傾向.md` #12。散文で禁じても守られなかったので機械で止める
（2026-09-22。外部事例: Claude Code Safety Net・Dippy。`06_保守者向け/04_監査記録/EXTERNAL-REF-awesome-2026-09.md` §1-3）。
B-19（2026-09-24）: `bash -c '…'`・`sudo`・`env`・`xargs`・`$( )` 越しに素通りしていたので、照合の前に
`secret_patterns.py` の `unwrap_command` でラッパーを剥がし、分割した各断片に同じ規則を当てる。

**止めるのは「やり直しが効かない」操作と「安全装置を外す」操作だけ**にする。止めすぎると回避策を覚えさせるだけで逆効果。
- 未コミットの変更を消す git 操作（reset --hard / checkout -- / checkout . / checkout -f / restore（`--staged` だけは可）/
  clean / stash drop|clear）・`find … -delete`
- 履歴を壊す push（--force・`+<refspec>`。`--force-with-lease` は他人の作業を消さないので許可）・未マージのブランチ削除（branch -D）
- 再帰削除（`rm -rf` / `rm -r -f` / `--recursive --force`。対象を問わずすべて。`find -exec rm -rf` も）
- `git add -A` / `git add .`（意図しないファイルの混入。H-2 はパス明示を要求する）
- git hook・設定の迂回（commit/push の `--no-verify`、commit の `-n`、`-c core.hooksPath=…`、`git config core.hooksPath …`、
  `-c alias.<名前>=…`・`git config … alias.<名前> …`（別名で偽装できるので値を問わず）、
  前置きの `GIT_CONFIG_*=`・`GIT_DIR=`・`GIT_WORK_TREE=`）
- シェルへ流す形（入口を問わず `… | sh`・`sh <<< …`・`sh -s`・`source <(…)`・`bash <(…)`。`curl … | python` 等も）
- 秘密ファイル（`.env` や鍵。判定は `secret_patterns.py`）が引数に現れる断片すべて。例外は ls/stat/test/[/rm/touch/
  chmod/file/du/mkdir/echo/printf（中身を読まない。出力をパイプで流す断片では例外にしない）、cp/mv/ln/install の書き先
  （最後の引数か `-t <DIR>`）、`>` 等の書き先、メッセージ・検索語の値（コマンド別: git commit/tag/merge/stash の -m、
  git log/shortlog の --grep/-S/-G/--format、gh の --title/--body、grep 系の -e と最初の位置引数）、表示せずに消費する形（限定する）:
    `direnv allow|deny|reload|status`・`docker compose --env-file <f> up|down|ps|build|pull|restart|stop|start|logs`・
    `dotenv|dotenvx run|env-cmd … [--] <実行>`（-p・get・config・--print があれば不可）・`uv run --env-file <f> [--] <実行|module>`。
    <実行> は npm|pnpm|yarn の test/run <名前>/start/build/ci/install/lint・npx playwright|vitest|jest|tsx <file>|ts-node <file>・
    pytest・インタプリタ + スクリプトファイル。インタプリタに -c/-e/-r/-E/-p/-m/eval が付く形・sh/bash は不可・
    `kubectl create secret … --from-env-file=<f>`（--dry-run・-o があれば不可）・git add/rm/check-ignore/ls-files/status。
  例外の断片の出力がパイプ・出力リダイレクトで流れるとき、同じ行に表示系（git diff/show/log -p・cat・printenv・env・
  docker exec・docker compose exec|run・kubectl exec 等）があるときは例外にしない。`docker run … --env-file <秘密>` は常に止める（image の後ろで何でも表示できる）。
  `--mount type=bind,src=<f>` はカンマと = で、`-v <f>:<dst>` は : で分けてから判定する。`< .env` の入力リダイレクトは常に判定する
  glob（`cat .en?`）は候補名に当たりうれば秘密扱い
git のグローバルオプション（`-c k=v`・`-C <dir>`・`--git-dir=`・`--work-tree=`）は読み飛ばしてサブコマンドを見る。
照合の前に `$'…'`・`$"…"`・`${IFS}`・引用の連結（`g"it"`）・`{a,b}`（空の選択肢は捨てる）を正規化し、関数定義・
`{ …; }`・`( … )` の中身も断片として取り出す（secret_patterns.py の normalize / tokens / _scan）。
ラッパー（sudo・doas・env・xargs・timeout・nohup・setsid・flock・nice・ionice・stdbuf・unbuffer・time・caffeinate・
bash -c・eval・find -exec）は剥がしてから照合する。hook の内部エラー（深い入れ子の JSON の RecursionError 等）も deny する。

Bash を構文解析しない限界（止めない。テストにもしない）: `python3 -c` / `python3 - <<EOF` の中身、変数を介した呼び出し
（`g=git; $g reset --hard`）、実行時に決まる引数（`cat "$(echo .env)"`）、ディレクトリを丸ごと読むコマンド
（`grep -r KEY .`）。秘密ファイルは `02_共通/ひな形/settings.sandbox.json` の denyRead（OS のサンドボックス）と併用する。

解除は環境変数ではなく、**人間が同じコマンドを自分で叩く**。安全装置に抜け道を作らない
（`rules/speed-harness.md`「安全フックに止められたら、安全装置が正しく働いた結果として受け入れる」）。
ヒアドキュメント本文と引用文字列は照合前に除去する（文書やコミットメッセージの中の語で止めない）。
deny のたびに `.claude/hook-decisions.log` へ 1 行記録する（B12。`secret_patterns.log_decision`。秘密値は伏字。書けなくても止めない）。
**入力が読めなければ deny する（fail-closed）**。ただし `tool_input.command` が無い・空なら何もしない。
入れ子が 2 段を超えて判定しきれないときも deny する（判定不能は不合格）。
`03_ClaudeCode/hooks/secret_patterns.py` が hook と同じ場所に無ければ、すべての Bash を deny する（同梱物の欠落に最初のコマンドで気づかせる）。
"""
import json
import re
import sys

try:
    from secret_patterns import SECRET_READ_REASON, analyze_command, glob_may_match_secret, is_secret_path
except ImportError:          # 部品が欠けた導入。判定できないので main で deny する
    analyze_command = None
try:
    from secret_patterns import input_summary, log_decision
except ImportError:          # 記録は付け足し（B12）。部品が無くても deny の動作は変えない
    def log_decision(*_a, **_k) -> None:
        return None

    def input_summary(_ti) -> str:
        return ""
_CTX: dict = {}              # deny の記録に使う（ツール名・コマンドの要約・cwd）

_HEREDOC = re.compile(r"<<-?\s*'?\"?(\w+)'?\"?.*?\n.*?\n\1\s*$", re.DOTALL | re.MULTILINE)
_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")
_START = r"(?:^|&&|\|\||;|\||\n)\s*"
# git のグローバルオプション（サブコマンドの前に来るもの）を読み飛ばす
_GIT = (r"git(?:\s+(?:-[Cc]\s+\S+|--(?:git-dir|work-tree|namespace|exec-path|config-env)(?:=|\s+)\S+"
        r"|--no-pager|--paginate|-[pP]|--bare|--no-replace-objects|--no-optional-locks"
        r"|--(?:literal|glob|noglob|icase)-pathspecs))*\s+")
_ARGS = r"[^\n;&|]*"      # 同じ断片の中の残りの引数
_SH = r"(?:ba|z|da|k)?sh"

# (正規表現, 理由, 代替手段)
_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(_START + _GIT + r"reset\s+(?:\S+\s+)*--hard\b"),
     "未コミットの変更が消える", "変更を残すなら `git stash push -m <名前>` ではなく、まず `git status --short` で対象を確認して個別に戻す"),
    (re.compile(_START + _GIT + r"clean\s+-\S*[fd]"),
     "追跡外のファイルが消える（空ディレクトリ込み。過去にテストを壊した）", "`git clean -n` で対象を出してから、必要なものだけ手で消す"),
    (re.compile(_START + _GIT + r"stash\s+(?:drop|clear)\b"),
     "退避した変更が消える", "`git stash list` で中身を確かめ、必要なら `git stash show -p` で内容を残す"),
    (re.compile(_START + _GIT + r"checkout\s+(?:\S+\s+)*(?:--\s+\S|\.(?:\s|$))"),
     "作業ツリーの変更が消える", "戻す前に `git diff -- <path>` を残し、戻すのは保守者に依頼する"),
    (re.compile(_START + _GIT + r"checkout\s+(?:\S+\s+)*(?:--force|-[a-zA-Z]*f[a-zA-Z]*)(?:\s|$)"),
     "作業ツリーの変更が消える（`checkout -f`）", "`git status --short` で変更を確かめ、`git stash push -m <名前>` ではなく保守者に切り替えを依頼する"),
    (re.compile(_START + _GIT + r"restore\b(?!" + _ARGS + r"\s(?:--staged|-[a-zA-Z]*S[a-zA-Z]*)(?:\s|$))"),
     "作業ツリーの変更が消える（`git restore <path>`）", "索引から外すだけなら `git restore --staged <path>`。作業ツリーを戻すのは `git diff -- <path>` を残して保守者に依頼する"),
    (re.compile(_START + _GIT + r"restore\b(?=" + _ARGS + r"\s(?:--worktree|-[a-zA-Z]*W[a-zA-Z]*)(?:\s|$))"),
     "作業ツリーの変更が消える（`--worktree`）", "索引から外すだけなら `git restore --staged <path>`"),
    (re.compile(_START + _GIT + r"push\s+(?:\S+\s+)*(?:--force|-f|\+\S+)(?:\s|$)"),
     "他人の作業を消す可能性がある", "`--force-with-lease` を使う（リモートが進んでいたら失敗して気づける）"),
    (re.compile(_START + _GIT + r"branch\b" + _ARGS + r"\s-[a-zA-Z]*D"),
     "未マージのコミットごとブランチが消える", "`git branch -d <名前>`（マージ済みだけ消える）。未マージなら保守者に確認する"),
    (re.compile(_START + _GIT + r"branch\b(?=" + _ARGS + r"\s(?:--delete|-[a-zA-Z]*d[a-zA-Z]*)(?:\s|$))(?="
                + _ARGS + r"\s(?:--force|-[a-zA-Z]*f[a-zA-Z]*)(?:\s|$))"),
     "未マージのコミットごとブランチが消える", "`git branch -d <名前>`（マージ済みだけ消える）。未マージなら保守者に確認する"),
    (re.compile(_START + _GIT + r"add\s+(?:-A|--all|\.)(?:\s|$)"),
     "意図しないファイルが混入する（H-2 はパス明示を要求している）", "`git status --short` で確認し `git add <path>...` とパスを並べる"),
    (re.compile(_START + _GIT + r"(?:commit|push)\b" + _ARGS + r"\s--no-veri\w*"),
     "git hook（秘密情報・UI ゲート）を飛ばす", "hook が止めた原因を直す。飛ばす必要があるかは保守者が判断する"),
    (re.compile(_START + _GIT + r"commit\b" + _ARGS + r"\s-[apzseiovq]*n[a-zA-Z]*(?=\s|$)"),
     "git hook（秘密情報・UI ゲート）を飛ばす（`commit -n` は `--no-verify`）", "hook が止めた原因を直す。飛ばす必要があるかは保守者が判断する"),
    (re.compile(_START + r"git\s+(?:\S+\s+)*?(?:-c\s+|--config-env[=\s])(?i:core\.hookspath)\s*="),
     "git hook の置き場を差し替えて hook を飛ばす", "hook が止めた原因を直す。飛ばす必要があるかは保守者が判断する"),
    (re.compile(_START + _GIT + r"config\b(?!" + _ARGS + r"\s--(?:get|unset)\S*)" + _ARGS + r"\s(?i:alias\.)\S"),
     "git の永続の別名（alias）を定義する（既存の規則を別名で迂回できる）", "別名を使わず元のコマンドを打つ。別名が要るなら保守者が設定する"),
    (re.compile(_START + _GIT + r"config\b" + _ARGS + r"\s(?i:core\.hookspath)\s+[^\s;&|]"),
     "git hook の置き場を差し替えて hook を飛ばす", "hook が止めた原因を直す。hook の置き場を変えるのは保守者が判断する"),
    (re.compile(_START + r"rm\s+(?=(?:" + _ARGS + r"\s)?(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?:\s|$))(?=(?:"
                + _ARGS + r"\s)?(?:-[a-zA-Z]*f[a-zA-Z]*|--force)(?:\s|$))"),
     "再帰削除は取り消せない", "`mv <対象> <scratchpad>/` で退避する（H-2 の標準。削除でなく退避）"),
    (re.compile(_START + r"find\b" + _ARGS + r"\s-delete(?:\s|$)"),
     "find -delete は対象を見ないまま消える", "`find … -print` で対象を出し、`mv <対象> <scratchpad>/` で退避する"),
    (re.compile(r"(?<!\|)\|(?!\|)\s*(?:sudo\s+(?:-\S+\s+)*)?(?:env\s+(?:\S+=\S*\s+)*)?(?:\S*/)?" + _SH + r"(?=\s|$|\))"),
     "シェルへ流し込んで実行する（中身が照合を通らない）", "流す中身を 1 行ずつ普通のコマンドとして実行する。スクリプトならファイルに保存し、中身を読んでから保守者に実行を依頼する"),
    (re.compile(r"\b(?:curl|wget)\b[^\n;&]*?(?<!\|)\|(?!\|)\s*(?:sudo\s+(?:-\S+\s+)*)?(?:env\s+(?:\S+=\S*\s+)*)?"
                r"(?:python[0-9.]*|perl|ruby|node)\b"),
     "取得したスクリプトを中身を見ずに実行する", "`curl -fsSL <URL> -o <scratchpad>/x.sh` で保存し、中身を読んでから保守者に実行を依頼する"),
    (re.compile(r"(?:^|[\s;&|(])(?:\S*/)?" + _SH + r"(?:\s+-\S+)*\s*<<<"),
     "シェルへ流し込んで実行する（`sh <<< …`）", "流す中身を普通のコマンドとして実行する"),
    (re.compile(r"(?:^|[\s;&|(])(?:\S*/)?" + _SH + r"(?:\s+-[a-zA-Z]+)*\s+-[a-zA-Z]*s[a-zA-Z]*(?=\s|$)"),
     "標準入力をシェルとして実行する（`sh -s`）", "流す中身を普通のコマンドとして実行する"),
    (re.compile(r"(?:(?:^|[\s;&|(])(?:\S*/)?(?:" + _SH + r"|source)|(?:^|[\s;&|(])\.)\s+(?:-\S+\s+)*<\("),
     "プロセス置換の出力をシェルとして実行する（`source <(…)`・`bash <(…)`）", "中身をファイルに保存して読んでから、保守者に実行を依頼する"),
)
# 引用の中身を消すと見えなくなる形（`sh -c "$(curl …)"`・`bash <(curl …)`）は元の文字列に当てる
_RAW_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\b(?:(?:ba|z|da|k)?sh\s+(?:-\S+\s+)*-\S*c|eval)\s+[\"']?\$\(\s*(?:curl|wget)\b"),
     "取得したスクリプトを中身を見ずに実行する", "`curl -fsSL <URL> -o <scratchpad>/x.sh` で保存し、中身を読んでから保守者に実行を依頼する"),
)
# 秘密ファイルが引数に現れても中身を読まないコマンド（それ以外はすべて deny。読み出しコマンドの一覧は漏れるので持たない）。
# ただし出力がパイプで次へ流れる断片では例外にしない（`echo .env | xargs cat`）
_NON_READERS = frozenset({"ls", "stat", "test", "[", "[[", "rm", "touch", "chmod", "file", "du", "mkdir", "echo", "printf"})
_DEST_CMDS = frozenset({"cp", "mv", "ln", "install"})   # 書き先は最後の引数か -t <DIR>（`cp .env.example .env` は通す）
_TARGET_OPTS = ("-t", "--target-directory")
# 値がメッセージ・検索語のオプション（その値はパスとして見ない）はコマンド別に限る。他のコマンドの -e・-S・-T・-t は値を取らない
_GIT_MSG = {"commit": ("-m", "--message"), "tag": ("-m", "--message"), "merge": ("-m", "--message"),
            "stash": ("-m", "--message"), "log": ("--grep", "-S", "-G", "--format", "--pretty"),
            "shortlog": ("--grep", "-S", "-G", "--format")}
_GREP = frozenset({"grep", "egrep", "fgrep", "rg", "ag"})
_GREP_NUM = frozenset({"-A", "-B", "-C", "-m", "--max-count", "--context", "--after-context", "--before-context"})
_RG_ARG = frozenset({"-t", "--type", "--type-not"})     # rg だけは -t が値を取る（ag -t・grep -T は値を取らない）
# 表示せずに消費する形（限定する）
_GIT_TIDY = frozenset({"add", "rm", "check-ignore", "ls-files", "status"})   # diff / show / log -p は表示するので入れない
_DIRENV_OK = frozenset({"allow", "deny", "reload", "status"})
_COMPOSE_OK = frozenset({"up", "down", "ps", "build", "pull", "restart", "stop", "start", "logs"})
_COMPOSE_ARG = frozenset({"-f", "--file", "-p", "--project-name", "--profile", "--project-directory", "--env-file",
                          "--ansi", "--progress", "--parallel"})
_DOCKER_GLOBAL_ARG = frozenset({"-c", "--context", "-H", "--host", "--config", "-l", "--log-level"})
_DOTENV_ARG = frozenset({"-e", "-f", "--file", "-v", "-c", "-r", "--rc-file", "--environments", "--env-file", "--path"})
_DOTENV_PRINT = frozenset({"-p", "--print", "get", "config", "decrypt", "keypair", "ls"})
_UV_ARG = frozenset({"--env-file", "--with", "--with-requirements", "--python", "-p", "--project", "--directory",
                     "--package", "--extra", "--group", "--index", "--index-url", "--from"})
# 表示系（例外と同じ行にあれば deny。`git add .env && git diff --cached`）
_DISPLAY = frozenset({"cat", "printenv", "env", "set", "export", "declare", "less", "more", "head", "tail", "bat", "tac",
                      "nl", "od", "xxd", "hexdump", "strings", "base64", "compgen"})
_SHOWY = frozenset({"sh", "bash", "zsh", "dash", "ksh", "printenv", "env", "cat", "echo", "printf", "less", "more",
                    "head", "tail", "set", "export", "declare", "npm", "pnpm", "yarn", "npx", "bunx"})
_INTERP = frozenset({"python", "python3", "node", "perl", "ruby", "php", "awk", "sh", "bash", "zsh", "tsx", "ts-node",
                     "bun", "deno"})
_EVAL_LETTERS = set("ceErpm")            # -c / -e / -E / -r / -p（--print）/ -m（python -m）。どのインタプリタでも不可
_NPM_OK = frozenset({"test", "start", "build", "ci", "install", "lint"})
_REDIRECT_OUT = frozenset({">", ">>", ">|", "&>", "&>>", ">&", "<>"})
_REDIRECT_IN = frozenset({"<", "<<<"})
# 秘密情報を差し替えられる git の環境変数（hooksPath・alias を環境から入れられる）
_GIT_ENV = re.compile(r"^(?:GIT_CONFIG\w*|GIT_DIR|GIT_WORK_TREE)=")
_GIT_GLOBAL_ARG = frozenset({"-C", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"})


def strip_noise(cmd: str) -> str:
    return _QUOTED.sub("''", _HEREDOC.sub("", cmd))


def _base(t: str) -> str:
    return t.rsplit("/", 1)[-1]


def _values(t: str, prev: str) -> list[str]:
    """引数から判定する値: そのもの・`k=v` の v・`-v a:b` の a/b・`--mount k=v,k=v` の各 v。"""
    vals = [t]
    if prev == "--mount" or t.startswith("--mount="):
        vals += [kv.split("=", 1)[-1] for kv in t.removeprefix("--mount=").split(",")]
    elif prev in ("-v", "--volume") or t.startswith("--volume="):
        vals += t.removeprefix("--volume=").split(":")
    elif "=" in t:
        vals.append(t.split("=", 1)[1])                  # dd if=.env・--file=.env
    return vals


def _is_secret_arg(t: str, prev: str, cwd: str | None) -> bool:
    return any(v and (is_secret_path(v, cwd) or glob_may_match_secret(v, shell=True)) for v in _values(t, prev))


def _first_word(toks: list[str], i: int, with_arg: frozenset[str]) -> int:
    """i から先のオプション（値を取るものは値ごと）を飛ばした最初の語の位置。"""
    while i < len(toks) and toks[i].startswith("-") and toks[i] != "--":
        i += 2 if toks[i] in with_arg else 1
    return i


def _env_file_idx(toks: list[str], opts: tuple[str, ...], upto: int) -> set[int]:
    return {k for k in range(1, min(upto, len(toks)))
            if toks[k - 1] in opts or toks[k].startswith(tuple(o + "=" for o in opts if o.startswith("--")))}


def _script_ok(w: list[str]) -> bool:
    """インタプリタ + スクリプトファイル（`python app.py`・`node server.js`）。スクリプトより前に -c/-e/-r/-E/-p/-m・
    --eval・--print・eval があれば不可（中身をその場で書ける）。sh/bash/zsh/awk はスクリプトでも不可。"""
    if _base(w[0]) in ("sh", "bash", "zsh", "awk"):
        return False
    for x in w[1:]:
        if x == "eval" or x.startswith(("--eval", "--print")) or (
                x.startswith("-") and not x.startswith("--") and _EVAL_LETTERS.intersection(x[1:])):
            return False
        if not x.startswith("-"):
            return True                                   # 最初の位置引数がスクリプト（その後ろはスクリプトの引数）
    return False


def _exec_ok(w: list[str], module_ok: bool = False) -> bool:
    """消費系の例外（uv run / dotenv / dotenvx / env-cmd）の後ろで許す実行コマンドか。`--` は読み飛ばす。
    module_ok: `uv run <module>`（pytest 等）を許す。"""
    if w and w[0] == "--":
        w = w[1:]
    if not w:
        return False
    c, a = _base(w[0]), (w[1] if len(w) > 1 else "")
    if c in _INTERP:
        return _script_ok(w)
    if c in ("npm", "pnpm", "yarn"):                    # npm exec・npx・任意のスクリプト名は不可
        return a in _NPM_OK or (a == "run" and len(w) > 2 and not w[2].startswith("-"))
    if c == "npx":
        if a in ("playwright", "vitest", "jest"):
            return True
        return a in ("tsx", "ts-node") and _script_ok(w[1:])
    if c == "pytest":
        return True
    if c == "uv":
        return a == "run" and len(w) > 2 and w[2].endswith(".py")
    return module_ok and c not in _SHOWY


def _consumed(toks: list[str]) -> set[int]:
    """表示せずに消費する形なら、その秘密ファイル引数の位置。形を限定する（B-19 2 周目）。"""
    off = 1 if _base(toks[0]) == "npx" and len(toks) > 1 else 0
    t = toks[off:]
    cmd, n = _base(t[0]), len(t)
    out: set[int] = set()
    if cmd == "direnv":
        if n > 1 and t[1] in _DIRENV_OK:                  # direnv exec は例外にしない
            out = set(range(2, n))
    elif cmd == "git":
        i = 1
        while i < n and t[i].startswith("-"):
            i += 2 if t[i] in _GIT_GLOBAL_ARG or t[i] == "-c" else 1
        if i < n and t[i] in _GIT_TIDY:
            out = set(range(i + 1, n))
    elif cmd in ("docker", "podman", "docker-compose", "podman-compose"):
        i = 1 if cmd.endswith("compose") else _first_word(t, 1, _DOCKER_GLOBAL_ARG)
        if cmd.endswith("compose") or (i < n and t[i] == "compose"):
            j = _first_word(t, i if cmd.endswith("compose") else i + 1, _COMPOSE_ARG)
            if j < n and t[j] in _COMPOSE_OK:              # config・exec・run は表示できるので不可
                out = _env_file_idx(t, ("--env-file",), j)
    elif cmd in ("dotenv", "dotenv-cli", "dotenvx", "env-cmd"):
        dd = t.index("--") if "--" in t else n
        if not _DOTENV_PRINT.intersection(t[1:dd]):
            if cmd == "dotenvx":
                ok = _first_word(t, 1, _DOTENV_ARG) < dd and t[_first_word(t, 1, _DOTENV_ARG)] == "run" and dd < n
                start = dd + 1
            else:
                start = dd + 1 if dd < n else _first_word(t, 1, _DOTENV_ARG)
                ok = True
            if ok and _exec_ok(t[start:]):
                out = _env_file_idx(t, ("-e", "-f", "--file", "--env-file", "--path"), start)
    elif cmd == "uv":
        if n > 1 and t[1] == "run":
            j = _first_word(t, 2, _UV_ARG)
            if _exec_ok(t[j:], module_ok=True):            # uv run … -- python -c も -- を読み飛ばして判定する
                out = _env_file_idx(t, ("--env-file",), j)
    elif cmd == "kubectl":
        words = {k for k in range(1, n) if t[k] in ("secret", "secrets")}   # リソース名の語（ファイルではない）
        shows = any(x.startswith(("--dry-run", "--output")) or x == "-o" or (x.startswith("-o") and len(x) > 2)
                    for x in t[1:])
        out = words | (set() if shows else _env_file_idx(t, ("--from-env-file",), n))
    return {k + off for k in out}


def _is_display(toks: list[str]) -> bool:
    c = _base(toks[0])
    if c in _DISPLAY:
        return True
    if c in ("docker", "podman", "kubectl", "docker-compose", "podman-compose"):   # コンテナの中で表示できる
        i = 1 if c.endswith("compose") else _first_word(toks, 1, _DOCKER_GLOBAL_ARG)
        sub = toks[i] if i < len(toks) else ""
        if sub in ("compose", "container") and not c.endswith("compose"):
            j = _first_word(toks, i + 1, _COMPOSE_ARG)
            sub = toks[j] if j < len(toks) else ""
        return sub in ("exec", "run") if (c.endswith("compose") or toks[i:i + 1] == ["compose"]) else sub == "exec"
    if c == "git":
        i = 1
        while i < len(toks) and toks[i].startswith("-"):
            i += 2 if toks[i] in _GIT_GLOBAL_ARG or toks[i] == "-c" else 1
        sub = toks[i] if i < len(toks) else ""
        return sub in ("diff", "show") or (sub == "log" and any(x in ("-p", "--patch", "-u") for x in toks[i:]))
    return False


def _msg_opts(toks: list[str]) -> tuple[str, ...]:
    """値がメッセージ・検索語になるオプション（コマンド別）。"""
    cmd = _base(toks[0])
    if cmd == "git":
        i = 1
        while i < len(toks) and toks[i].startswith("-"):
            i += 2 if toks[i] in _GIT_GLOBAL_ARG or toks[i] == "-c" else 1
        return _GIT_MSG.get(toks[i], ()) if i < len(toks) else ()
    if cmd == "gh":
        return ("--title", "--body", "-t", "-b")
    return ("-e", "--regexp") if cmd in _GREP else ()


def secret_arg(toks: list[str], cwd: str | None, pipe_out: bool = False) -> tuple[str | None, bool]:
    """秘密ファイルが引数に現れる断片なら (その引数, _)。2 つ目は「表示せずに消費する」例外を使ったか。
    例外: _NON_READERS（パイプで流す断片を除く）・cp/mv/ln/install の書き先・> の書き先・メッセージ／検索語の値・
    表示せずに消費する形（パイプ・出力リダイレクトのある断片を除く）。`< .env` は常に判定する。"""
    if not toks:
        return None, False
    cmd, n = _base(toks[0]), len(toks)
    redirected = any(t in _REDIRECT_OUT for t in toks)
    consumed = set() if (pipe_out or redirected) else _consumed(toks)
    items: list[tuple[int, str, str, bool]] = []      # (位置, 引数, 直前のトークン, 入力リダイレクトで読むもの)
    i = 1
    while i < n:
        t = toks[i]
        if t in _REDIRECT_OUT or t == "<<":
            i += 2                          # 書き先・ヒアドキュメントの区切り語
            continue
        if t in _REDIRECT_IN:
            if i + 1 < n:
                items.append((i + 1, toks[i + 1], t, True))
            i += 2
            continue
        if t.isdigit() and i + 1 < n and toks[i + 1] in _REDIRECT_OUT | _REDIRECT_IN:
            i += 1                          # 2>/dev/null の 2
            continue
        items.append((i, t, toks[i - 1], False))
        i += 1
    skip: set[int] = set()
    msg = _msg_opts(toks)
    for k, t, prev, red in items:           # メッセージ・検索語の値（コマンド別。-m"…" のように付いた形も）
        if not red and msg and (prev in msg or t.startswith(tuple(o + "=" for o in msg if o.startswith("--")))
                                or any(len(o) == 2 and t.startswith(o) and len(t) > 2 for o in msg)):
            skip.add(k)
    if cmd in _GREP and not any(t in ("-e", "--regexp", "-f", "--file") or t.startswith(("--regexp=", "--file="))
                                for t in toks[1:]):
        for k, t, prev, red in items:       # 最初の位置引数は検索語（2 番目以降はパスとして見る）
            if red or k in skip:
                continue
            if prev in _GREP_NUM or (cmd == "rg" and prev in _RG_ARG):
                skip.add(k)
                continue
            if not t.startswith("-"):
                skip.add(k)
                break
    if cmd in _DEST_CMDS:
        tdir = {k for k, t, prev, red in items if prev in _TARGET_OPTS or t.startswith("--target-directory=")}
        if tdir:
            skip |= tdir                    # -t <DIR> が書き先。他の引数はすべて読む元
        else:
            pos = [k for k, t, prev, red in items if not red and not t.startswith("-")]
            skip |= set(pos[-1:])
    non_reader = cmd in _NON_READERS and not pipe_out
    used = False
    for k, t, prev, red in items:
        if k in skip:
            continue
        if not red and k in consumed:
            used = True
            continue
        if (red or not non_reader) and _is_secret_arg(t, prev, cwd):
            return t, used
    return None, used


def docker_run_env(toks: list[str], cwd: str | None) -> bool:
    """`docker run|create|exec … --env-file <秘密>`（image の後ろで何でも表示できる）。"""
    if _base(toks[0]) not in ("docker", "podman"):
        return False
    i = _first_word(toks, 1, _DOCKER_GLOBAL_ARG)
    if i >= len(toks) or toks[i] not in ("run", "create", "exec", "container"):
        return False
    return any(_is_secret_arg(toks[k], toks[k - 1], cwd) for k in _env_file_idx(toks, ("--env-file",), len(toks)))


def git_override(toks: list[str]) -> str | None:
    """git のグローバル -c で alias・hooksPath を差し替える断片なら理由を返す。"""
    if not toks or _base(toks[0]) != "git":
        return None
    i, n = 1, len(toks)
    while i < n:
        t, kv = toks[i], None
        if t == "-c" and i + 1 < n:
            kv, i = toks[i + 1], i + 2
        elif t == "--config-env" and i + 1 < n:
            kv, i = toks[i + 1], i + 2
        elif t.startswith("--config-env="):
            kv, i = t.split("=", 1)[1], i + 1
        elif t in _GIT_GLOBAL_ARG:
            i += 2
            continue
        elif t.startswith("-"):
            i += 1
            continue
        else:
            break
        key = kv.split("=", 1)[0].lower()
        if key.startswith("alias."):
            return "`-c alias.…` で別名を定義する（既存の規則を別名で迂回できる）"
        if key == "core.hookspath":
            return "git hook の置き場を差し替えて hook を飛ばす"
    return None


def _stop(why: str, alt: str) -> str:
    return f"取り返しのつかない操作を止めた: {why}。代わりに: {alt}。どうしても必要なら保守者に依頼して実行してもらう（H-2）"


def check(cmd: str, cwd: str | None = None) -> str | None:
    """止めるなら理由文を返す。"""
    a = analyze_command(cmd)
    for s in a.strings:
        for rules, text in ((_RULES, strip_noise(s)), (_RAW_RULES, s)):
            for pat, why, alt in rules:
                if pat.search(text):
                    return _stop(why, alt)
    for kv in a.assigns + [t for toks in a.segments if toks[0] == "export" for t in toks[1:]]:
        if _GIT_ENV.match(kv):
            return _stop(f"環境変数 {kv.split('=', 1)[0]} で git の設定・置き場を差し替える（hooksPath や alias を環境から入れられる）",
                         "前置きを外して実行する")
    used_any = False
    for toks, pipe in zip(a.segments, a.pipe_out):
        why = git_override(toks)
        if why:
            return _stop(why, "hook が止めた原因を直す")
        if docker_run_env(toks, cwd):
            return ("秘密ファイルを `docker run --env-file` に渡すと、image の後ろのコマンドで値を表示できるので止めた。"
                    "代わりに: `docker compose --env-file <file> up` を使うか、保守者が打つ")
        hit, used = secret_arg(toks, cwd, pipe)
        if hit:
            return SECRET_READ_REASON.format(path=hit)
        used_any |= used
    if used_any and any(_is_display(t) for t in a.segments):
        return ("秘密ファイルを「表示せずに消費する」コマンドと、表示するコマンド（git diff / show / log -p・cat・printenv 等）が"
                "同じ行にあるので止めた。代わりに: 別々に実行する。値が要るなら保守者に聞く")
    if a.too_deep:
        return _stop("入れ子（bash -c・$( ) 等）が 3 段以上あり判定しきれない", "入れ子を減らして 1 段ずつ実行する")
    return None


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": f"[block-destructive] {reason}",
    }}, ensure_ascii=False))
    log_decision("block-destructive", "deny", reason.removeprefix("取り返しのつかない操作を止めた: "),
                 _CTX.get("tool", ""), _CTX.get("summary", ""), _CTX.get("cwd"))
    return 0


def _main() -> int:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            raise ValueError("JSON の最上位がオブジェクトでない")
        ti = data.get("tool_input") or {}
        if not isinstance(ti, dict):
            raise ValueError("tool_input がオブジェクトでない")
    except ValueError as e:     # JSONDecodeError・UnicodeDecodeError も含む
        return deny(f"hook の入力が読めない（{type(e).__name__}）ので止めた（fail-closed）。"
                    "続けて起きるなら Claude Code と hook の版の組み合わせを保守者に確認してもらう")
    if data.get("tool_name") != "Bash":
        return 0
    _CTX.update(tool="Bash", summary=input_summary(ti), cwd=data.get("cwd") if isinstance(data.get("cwd"), str) else None)
    cmd = ti.get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return 0
    if analyze_command is None:
        return deny("判定不能で止めた: `03_ClaudeCode/hooks/secret_patterns.py` が無い。hook と同じ場所に置く"
                    "（保守者に install.sh / export-project.sh での入れ直しを依頼する）")
    cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else None
    reason = check(cmd, cwd)
    return deny(reason) if reason else 0


def main() -> int:
    try:
        return _main()
    except Exception as e:   # RecursionError（深い入れ子の JSON）・判定の不具合。Traceback を出さず止める
        return deny(f"hook 内部エラー: {type(e).__name__}（判定不能なので止めた。続けて起きるなら保守者に hook の不具合として報告する）")


if __name__ == "__main__":
    sys.exit(main())
