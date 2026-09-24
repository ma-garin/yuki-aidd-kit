#!/usr/bin/env python3
"""skill-scan.py — 外部のスキル・コマンド・hook 設定・MCP 設定・プラグインを、導入する前に実行せずに走査する（B-24 B03）。

他者のスキルや MCP サーバ・プラグインを取り込むとき、注入の文言・秘密の読み取り・外部送信・難読化・過大な
許可を確かめる手順が無かった。本スクリプトは中身を読むだけで判定し、何も実行しない（ネットも使わない）。

対象: 引数のファイル、またはディレクトリ配下のファイル（SKILL.md・references・commands/*.md・agents/*.md・
      hooks の settings.json・.mcp.json・plugin の manifest（.claude-plugin/plugin.json 等）・同梱スクリプト）。
      画像・フォントは読まない。シンボリックリンクはたどらない（UNKNOWN）。

判定（ファイルごと。全体はいちばん重いもの。重い順に DANGEROUS > UNKNOWN > CAUTION > SAFE）:
  DANGEROUS  K01 取得したものをシェルへ流す（curl/wget … をパイプで sh・bash・python へ、`bash <(curl …)` 等）
             K02 再帰の強制削除（rm に -r と -f。`Remove-Item -Recurse -Force`）
             K03 秘密ファイルの読み取り（~/.ssh・.aws/credentials・.env・id_rsa・.netrc 等を cat/open/読んで/送って）
             K04 許可確認の無効化（bypassPermissions・--dangerously-skip-permissions）
             K05 不可視文字・双方向制御文字・タグ文字（見えない命令）
             K06 base64 で隠した命令（復号して実行・復号すると命令文になる長い base64）
             K07 外部 URL への送信（curl -d/-F/-X POST・requests.post・fetch の POST 等。localhost は除く）
             K08 動的な eval（eval 関数・`eval "$(…)"`・new Function・復号やダウンロードを exec）
             K09 既知形式の秘密値（03_ClaudeCode/hooks/secret_patterns.py の値パターン）
             K10 すべての Bash を許す許可（permissions.allow の `Bash(*)`・`Bash`）
             K11 画面に出ない所（HTML コメント・display:none）で秘密や外部 URL への送信を指示する
  CAUTION    C01 ネットワーク（curl・wget・fetch・requests・リモート MCP）／C02 ファイルの書き込み・削除
             ／C03 環境変数の参照／C04 `npx -y <未知のパッケージ>`（@modelcontextprotocol/ @playwright/ @anthropic-ai/ 以外）
             ／C05 注入の文言・HTML コメント内の指示／C06 広い許可（Write(*)・Bash(rm…)・Bash(sudo…)・allowed-tools の Bash）
             ／C07 コマンドの実行（exec・shell=True・os.system・child_process）／C08 base64 の復号
  UNKNOWN    U01 読めない（UTF-8 でない・大きすぎる）／U02 JSON として読めない／U03 シンボリックリンク
             ／U04 パスが無い・検査できるファイルが無い／U05 秘密値の検査部品（secret_patterns.py）が見つからない
  SAFE       上のどれにも当たらない

照合の前処理:
  - Markdown は説明文の NG 例を数えない: コードブロック・コードスパン・「」『』の引用・行頭が 例:／NG 例:／OK 例:／>
    の行を空白にしてから照合する。不可視文字（K05）・命令文になる base64（K06）・秘密値（K09）は覆わずに見る。
  - 行ごとに secret_patterns の正規化（`$'\x72m'`・`${IFS}`・引用の連結 `r""m`・ラッパー剥がし・{a,b}）と、
    コマンド名の /bin/・/usr/bin/ の接頭辞を落とした形でも照合する。
  - JSON は構造で見る（scan_json）。permissions.deny の値は常に SAFE。settings*.json と .mcp.json は
    allow・defaultMode・command 系のキー・MCP の command＋args・値の不可視文字と秘密値だけを判定する。

扱い（呼び出し側。install.sh・install_guard.py）: DANGEROUS は導入しない（環境変数 AIDD_SKILL_SCAN_OK=1 で 1 回だけ通す）。
  UNKNOWN は CAUTION と同じ扱い（一覧を出して導入を続ける。SAFE には数えない）。
終了コード: 0 = DANGEROUS なし（CAUTION・UNKNOWN は警告だけ）、1 = DANGEROUS あり、2 = 使い方の誤り。
出力には該当行の中身を出さない（秘密値・不可視文字を画面に流さない）。file:line・規則・要旨だけ。

使い方: python3 02_共通/ツール/skill-scan.py [--json] [--brief] PATH [PATH ...]
  --brief  CAUTION・UNKNOWN はファイルごとに 1 行（規則 ID の一覧）にまとめる（DANGEROUS は全件出す）

標準ライブラリのみ・ネット不使用。
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import sys
from pathlib import Path

LEVELS = ("SAFE", "CAUTION", "UNKNOWN", "DANGEROUS")   # 後ろほど重い
RANK = {lv: i for i, lv in enumerate(LEVELS)}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".woff", ".woff2", ".ttf", ".otf", ".eot"}
MAX_BYTES = 2 * 1024 * 1024
KNOWN_NPX_SCOPES = ("@modelcontextprotocol/", "@playwright/", "@anthropic-ai/")

# ---------------------------------------------------------------- secret_patterns（B02 の規則を共用）
_SP = None
_HERE = Path(__file__).resolve().parent
for _d in (_HERE.parent.parent / "03_ClaudeCode" / "hooks", _HERE, Path.home() / ".claude" / "hooks", Path.cwd() / ".claude" / "hooks"):
    if not (_d / "secret_patterns.py").is_file():
        continue
    sys.path.insert(0, str(_d))
    try:
        import secret_patterns as _SP  # noqa: E402
    except Exception:   # 壊れた部品を読んでも走査全体は止めない（U05 で判定不能にする）
        _SP = None
    finally:
        sys.path.pop(0)
    if _SP is not None:
        break

# ---------------------------------------------------------------- 規則
EXT_URL = r"https?://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?:[:/\s\"'`]|$))[^\s\"'`<>)]+"
SECRET_PATH = (r"(?:~|\$HOME|\$\{HOME\})?/?(?:[\w.-]+/)*"
               r"(?:\.ssh/[\w.-]*|\.aws/(?:credentials|config)|\.netrc|\.npmrc|\.pypirc|\.git-credentials"
               r"|\.config/gh/hosts\.yml|\.docker/config\.json|\.kube/config|\.gnupg/[\w.-]*"
               r"|id_(?:rsa|ed25519|ecdsa|dsa)(?!\.pub)|[\w.-]*\.env(?!\.(?:example|sample|template|dist))(?:\.[\w-]+)?"
               r"|[\w.-]+\.(?:pem|p12|pfx)|credentials\.json)(?![\w-])")
SHELLS = r"(?:(?:ba|z|da|k|fi)?sh|python[0-9.]*|node|perl|ruby|iex|Invoke-Expression)"

DANGEROUS_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("K01", "取得したものをそのままシェル・インタプリタへ流す", re.compile(
        r"\b(?:curl|wget|iwr|irm|Invoke-WebRequest|Invoke-RestMethod)\s+[^|\s][^|\n]*\|\s*(?:sudo\s+(?:-\S+\s+)*)?"
        r"(?:env\s+(?:\S+=\S*\s+)*)?" + SHELLS + r"\b"
        r"|\b(?:ba|z|da|k)?sh\s+(?:-s\s+)?<\(\s*(?:curl|wget)\b"
        r"|\b(?:ba|z|da|k)?sh\s+-c\s+[\"']?\$\(\s*(?:curl|wget)\b"
        r"|\b(?:source|\.)\s+<\(\s*(?:curl|wget)\b"
        r"|\b(?:iex|Invoke-Expression)\b[^\n]*\b(?:iwr|irm|Invoke-WebRequest|Invoke-RestMethod|DownloadString)\b",
        re.IGNORECASE)),
    ("K03", "秘密ファイルを読む・表示する・送る", re.compile(
        r"(?:^|[\s;&|(`$\"'])(?:cat|less|more|head|tail|bat|nl|strings|xxd|od|base64|scp|rsync|gpg|openssl)\s+"
        r"(?:-{1,2}[\w=-]+\s+)*[\"']?" + SECRET_PATH +
        r"|(?:\bopen|read_text|read_bytes|readFile(?:Sync)?|Get-Content|fs\.read\w*|expanduser)\s*\(?\s*[^)\n]{0,60}?" + SECRET_PATH +
        r"|\b(?:read|print|display|show|send|upload|exfiltrate|dump|output|copy|paste)\s+(?:the\s+)?(?:contents?\s+of\s+|file\s+)?[`\"']?"
        + SECRET_PATH +
        r"|" + SECRET_PATH + r"[`\"'」）)]*\s*(?:の(?:中身|内容|値)\s*)?を\s*"
        r"(?:読ん|読み|読め|読む|読ま|表示して|表示する|表示せよ|出力|送|貼|コピー|アップロード|添付|含め)(?!\S{0,4}(?:ない|ず|禁止))",
        re.IGNORECASE)),
    ("K04", "許可確認を無効にする（bypassPermissions 等）", re.compile(
        r"bypassPermissions|--dangerously-skip-permissions|dangerouslySkipPermissions", re.IGNORECASE)),
    ("K06", "base64 で隠した命令を復号して実行する", re.compile(
        r"\bbase64\s+(?:-d|--decode|-D)\b[^\n]*\|\s*(?:sudo\s+)?" + SHELLS + r"\b"
        r"|\b(?:eval|exec|Function|system|popen|spawn|execSync)\b[^\n]{0,40}\b(?:atob|b64decode|fromBase64)\b"
        r"|\b(?:eval|exec|Function)\s*\([^\n]{0,40}Buffer\.from\([^)]*base64", re.IGNORECASE)),
    ("K07", "外部 URL へ送信する", re.compile(
        r"\bcurl\b(?=[^\n]*(?:\s-X\s*POST|\s--request\s+POST|\s-d[\s'\"@]|\s--data(?:-raw|-binary|-urlencode)?[\s=]"
        r"|\s-F\s|\s--form[\s=]|\s-T\s|\s--upload-file[\s=]))(?=[^\n]*(?:" + EXT_URL + r"|\$\{?\w+))"
        r"|\bwget\b(?=[^\n]*--post-(?:data|file))(?=[^\n]*(?:" + EXT_URL + r"|\$\{?\w+))"
        r"|\b(?:requests|httpx)\.(?:post|put|patch)\(\s*f?[\"']" + EXT_URL +
        r"|\baxios\.(?:post|put|patch)\(\s*[\"'`]" + EXT_URL +
        r"|\bfetch\(\s*[\"'`]" + EXT_URL + r"[^\n]*method\s*:\s*[\"'`](?:POST|PUT|PATCH)"
        r"|\bInvoke-(?:WebRequest|RestMethod)\b[^\n]*-Method\s+(?:Post|Put|Patch)"
        r"|\bnavigator\.sendBeacon\(", re.IGNORECASE)),
    ("K08", "動的な eval（文字列・取得物・復号物をコードとして実行）", re.compile(
        r"(?<![\w.$])eval\s*\("
        r"|(?:^|[\s;&|(`{])eval\s+[\"']?[$`]"
        r"|\bnew\s+Function\s*\("
        r"|(?<![\w.])exec\s*\(\s*(?:compile\s*\(|base64|__import__|requests|urllib|codecs|bytes\.fromhex|zlib|marshal)")),
]
CAUTION_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    ("C01", "ネットワークを使う", re.compile(
        r"(?:^|[\s;&|(`\"'])(?:curl|wget|nc|ncat|telnet|ftp)\s+-{0,2}\w"
        r"|\b(?:requests|httpx|aiohttp)\.\w+\(|\burllib\.request\b|\burlopen\(|\bfetch\s*\(|\baxios[.(]"
        r"|\bXMLHttpRequest\b|\bWebSocket\(|\bInvoke-(?:WebRequest|RestMethod)\b|\bsocket\.socket\(|\bhttp\.client\b")),
    ("C02", "ファイルを書き込む・削除する", re.compile(
        r"(?:>>?|\btee\s+(?:-a\s+)?)\s*[\"']?(?:~|\$HOME|\$\{HOME\})/"
        r"|\bchmod\s+(?:[+-]?[0-7]{3,4}|[ugoa]*[+=-][rwxst]+)\s"
        r"|(?:^|[\s;&|(`])rm\s+(?:-\S+\s+)*-\w*[rR]"
        r"|\b(?:shutil\.rmtree|rimraf|os\.remove|os\.unlink|unlinkSync|rmSync)\b"
        r"|\.write_(?:text|bytes)\(|\b(?:write|append)File(?:Sync)?\(|\bopen\([^)\n]*,\s*[\"'][wax]b?\+?[\"']"
        r"|\bdd\s+if=")),
    ("C03", "環境変数を参照する", re.compile(
        r"\bos\.environ\b|\bos\.getenv\(|\bgetenv\(|\bprocess\.env\b|\$env:\w+|\bENV\["
        r"|\$\{?[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIALS?|AUTH)[A-Z0-9_]*\}?")),
    ("C05", "注入の文言（これまでの指示を無視させる）", re.compile(
        r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|system)\s+"
        r"(?:instructions?|prompts?|rules)"
        r"|(?:これまで|以前|前|上記|先)の(?:指示|命令|ルール|規則)を(?:すべて|全て)?(?:無視|忘れ)", re.IGNORECASE)),
    ("C07", "コマンドを実行する", re.compile(
        r"(?<![\w.])exec\s*\(|\bsubprocess\.\w+\([^\n]*shell\s*=\s*True|\bos\.system\(|\bos\.popen\(|\bchild_process\b"
        r"|\bexecSync\(|\bspawnSync\(")),
    ("C08", "base64 を復号する", re.compile(r"\bbase64\s+(?:-d|--decode|-D)\b|\batob\(|\bb64decode\(|\bfromBase64\(")),
]
NPX_RE = re.compile(r"\bnpx\s+(?:-y|--yes)\s+(?:-\S+\s+)*([^\s\"',\]]+)")
RM_RE = re.compile(r"(?:^|[\s;&|(`\"'])(?:sudo\s+(?:-\S+\s+)*)?rm\s+((?:-{1,2}[\w-]+\s*)+)")
PS_REMOVE_RE = re.compile(r"\bRemove-Item\b(?=[^\n]*-Recurse)(?=[^\n]*-Force)", re.IGNORECASE)
INVISIBLE_RE = re.compile("[​-‏⁠-⁤﻿‪-‮⁦-⁩\U000e0000-\U000e007f]")
B64_BLOB_RE = re.compile(r"(?<![A-Za-z0-9+/=])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/=])")
B64_SUSPICIOUS = re.compile(r"curl|wget|bash|/bin/sh|\bsh\b|eval|exec|rm -|https?:|ignore|instruction|subprocess|"
                            r"import os|powershell|chmod|base64|token|password|secret|\.ssh|指示|無視|実行", re.IGNORECASE)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
COMMENT_IMPERATIVE_RE = re.compile(r"実行|無視|必ず|ignore|execute|\brun\b|curl|wget|送信", re.IGNORECASE)
ALLOWED_TOOLS_RE = re.compile(r"^allowed-tools\s*:\s*(.*)$", re.MULTILINE)
# 説明文の NG 例を数えないための覆い（Markdown だけ。スクリプトの ` はコマンド置換なので覆わない）
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
CODE_SPAN_RE = re.compile(r"(`+)(?!`).+?(?<!`)\1(?!`)")
QUOTE_JA_RE = re.compile(r"「[^」\n]*」|『[^』\n]*』")
EXAMPLE_LINE_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:>|(?:NG|OK)\s*例\s*[:：]|例\s*[:：])")
BIN_PREFIX_RE = re.compile(r"(?<![\w.~$/-])/(?:usr/(?:local/)?)?s?bin/(?=[\w.-])")
# 画面に出ない所（HTML コメント・display:none・hidden）の送信の指示（K11）
HIDDEN_ELEM_RE = re.compile(r"<(\w+)\b[^>]*(?:display\s*:\s*none|\bhidden\b)[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
HIDDEN_SECRET_SEND_RE = re.compile(r"(?:秘密|鍵|id_rsa|\.env|token).*(?:送信|送れ|POST|アップロード|upload|exfil)",
                                   re.IGNORECASE | re.DOTALL)
EXT_URL_RE = re.compile(EXT_URL, re.IGNORECASE)
SEND_WORD_RE = re.compile(r"送信|送れ|送って|送る|POST|アップロード|upload|send|exfil", re.IGNORECASE)
# JSON: 構造だけで見るファイル（settings*.json・.mcp.json）とコマンドとして判定するキー
STRUCTURAL_JSON_RE = re.compile(r"^(?:settings(?:\.[\w-]+)*\.json|(?:.*\.)?mcp\.json|\.mcp\.json)$", re.IGNORECASE)
COMMAND_KEYS = {"command", "apiKeyHelper", "awsAuthRefresh", "awsCredentialExport", "otelHeadersHelper"}


class Finding:
    __slots__ = ("level", "rule", "line", "detail")

    def __init__(self, level: str, rule: str, line: int, detail: str) -> None:
        self.level, self.rule, self.line, self.detail = level, rule, line, detail

    def as_dict(self) -> dict:
        return {"level": self.level, "rule": self.rule, "line": self.line, "detail": self.detail}


class FileResult:
    def __init__(self, path: str) -> None:
        self.path = path
        self.findings: list[Finding] = []

    def add(self, level: str, rule: str, line: int, detail: str) -> None:
        if not any(f.rule == rule and f.line == line for f in self.findings):
            self.findings.append(Finding(level, rule, line, detail))

    @property
    def verdict(self) -> str:
        return max((f.level for f in self.findings), key=RANK.__getitem__, default="SAFE")


def _rm_is_rf(flags: str) -> bool:
    toks = flags.split()
    rec = any(t in ("--recursive",) or (t.startswith("-") and not t.startswith("--") and ("r" in t or "R" in t)) for t in toks)
    force = any(t == "--force" or (t.startswith("-") and not t.startswith("--") and "f" in t) for t in toks)
    return rec and force


def _b64_hidden(line: str) -> bool:
    for m in B64_BLOB_RE.finditer(line):
        blob = m.group(0)
        try:
            raw = base64.b64decode(blob + "=" * (-len(blob) % 4), validate=True)
            text = raw.decode("utf-8")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
        printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\t")
        if text and printable / len(text) >= 0.9 and B64_SUSPICIOUS.search(text):
            return True
    return False


def _variants(line: str) -> list[str]:
    """照合に使う書き換え。secret_patterns の正規化（`$'\\x72m'`・`${IFS}`・引用の連結 `r""m`・ラッパー剥がし・
    {a,b} の展開）と、コマンド名の /bin/・/usr/bin/ の接頭辞を落とした形・引用符を外した形。"""
    vs = [line]
    if _SP is not None and re.search(r"['\"\\$`{]|/s?bin/", line):
        try:
            vs += [_SP.normalize(line)] + list(_SP.unwrap_command(line)) + list(_SP._expand_braces(line))
        except Exception:   # 正規化の失敗で走査を止めない（元の行では照合する）
            pass
    extra = []
    for v in vs:
        extra.append(BIN_PREFIX_RE.sub("", v))
        extra.append(BIN_PREFIX_RE.sub("", re.sub(r"[\"'\\]", "", v)))
    return list(dict.fromkeys(vs + extra))


def check_line(res: FileResult, no: int, line: str, prefix: str = "") -> None:
    """1 行（またはコマンド 1 つ）に DANGEROUS・CAUTION の規則を当てる。"""
    hit_rm = False
    for v in _variants(line):
        for m in RM_RE.finditer(v):
            if _rm_is_rf(m.group(1)):
                res.add("DANGEROUS", "K02", no, prefix + "再帰の強制削除（rm に -r と -f）")
                hit_rm = True
        if PS_REMOVE_RE.search(v):
            res.add("DANGEROUS", "K02", no, prefix + "再帰の強制削除（Remove-Item -Recurse -Force）")
            hit_rm = True
        for rid, desc, rx in DANGEROUS_RULES:
            if rx.search(v):
                res.add("DANGEROUS", rid, no, prefix + desc)
    for rid, desc, rx in CAUTION_RULES:
        if rid == "C02" and hit_rm and not rx.search(RM_RE.sub(" ", line)):
            continue   # rm -rf は K02 で出したので、同じ行の C02 は重ねない
        if rx.search(line):
            res.add("CAUTION", rid, no, prefix + desc)
    for m in NPX_RE.finditer(line):
        pkg = m.group(1)
        if not pkg.startswith(KNOWN_NPX_SCOPES):
            res.add("CAUTION", "C04", no, prefix + f"npx -y で未知のパッケージを取得して実行（{pkg[:60]}。版と出所を確かめる）")


def check_raw(res: FileResult, text: str) -> None:
    """隠せないもの（不可視文字・命令文になる base64・秘密値）は生の本文で見る（コードスパンの中でも数える）。"""
    for no, line in enumerate(text.splitlines(), 1):
        chk = line[1:] if no == 1 and line.startswith("\ufeff") else line   # 先頭の BOM だけは許す
        if INVISIBLE_RE.search(chk):
            res.add("DANGEROUS", "K05", no, "不可視文字・双方向制御文字・タグ文字を含む（見えない命令）")
        if _b64_hidden(line):
            res.add("DANGEROUS", "K06", no, "復号すると命令文になる base64 を含む")
    if _SP is not None:
        for name, no in _SP.find_secret_values(text):
            res.add("DANGEROUS", "K09", no, f"既知形式の秘密値（{name}）を含む")
    else:
        res.add("UNKNOWN", "U05", 0, "秘密値の検査部品 secret_patterns.py が見つからない（秘密値は未検査）")


def _blank(m: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def mask_code(text: str) -> str:
    """コードブロック（``` / ~~~）の中身とコードスパンを空白にする（行の数と位置は保つ）。"""
    out, fence = [], ""
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = ""
            out.append(" " * len(line))
            continue
        if m:
            fence = m.group(1)
            out.append(" " * len(line))
            continue
        out.append(CODE_SPAN_RE.sub(_blank, line))
    return "\n".join(out)


def mask_explanations(text: str) -> str:
    """説明文の NG 例を数えない: コードブロック・コードスパン・「」『』の引用・行頭が 例:／NG 例:／OK 例:／> の行を空白にする。"""
    lines = []
    for line in mask_code(text).split("\n"):
        lines.append(" " * len(line) if EXAMPLE_LINE_RE.match(line) else QUOTE_JA_RE.sub(_blank, line))
    return "\n".join(lines)


def scan_text(res: FileResult, text: str, markdown: bool) -> None:
    check_raw(res, text)
    body = mask_explanations(text) if markdown else text
    for no, line in enumerate(body.splitlines(), 1):
        if line.strip():
            check_line(res, no, line)


def scan_hidden(res: FileResult, text: str) -> None:
    """画面に出ない所（HTML コメント・display:none・hidden）の指示。秘密や外部 URL への送信の指示は DANGEROUS。"""
    body = mask_code(text)   # コードとして見せている例は除く（「」の引用では隠せない）
    for rx in (HTML_COMMENT_RE, HIDDEN_ELEM_RE):
        for m in rx.finditer(body):
            chunk = m.group(0)
            no = body.count("\n", 0, m.start()) + 1
            if HIDDEN_SECRET_SEND_RE.search(chunk) or (EXT_URL_RE.search(chunk) and SEND_WORD_RE.search(chunk)):
                res.add("DANGEROUS", "K11", no, "画面に出ない所（HTML コメント・display:none）で秘密や外部 URL への送信を指示している")
            elif COMMENT_IMPERATIVE_RE.search(chunk):
                res.add("CAUTION", "C05", no, "画面に出ない所（HTML コメント・display:none）に指示がある")


def scan_markdown(res: FileResult, text: str) -> None:
    head = text[:4000]
    if head.startswith("---"):
        fm = head.split("---", 2)[1] if head.count("---") >= 2 else ""
        for m in ALLOWED_TOOLS_RE.finditer(fm):
            items = [t.strip() for t in re.split(r"[,\s]+(?![^()]*\))", m.group(1).strip("[] ")) if t.strip()]
            if any(t in ("Bash", "Bash(*)", "Bash(:*)", "*") for t in items):
                no = text.count("\n", 0, text.index(m.group(0))) + 1
                res.add("CAUTION", "C06", no, "allowed-tools がすべての Bash を許す（範囲を絞る）")


def _line_of(text: str, value: str) -> int:
    needle = json.dumps(value, ensure_ascii=False)[1:-1][:80]
    pos = text.find(needle) if needle else -1
    return text.count("\n", 0, pos) + 1 if pos >= 0 else 0


def _mcp_servers(data) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    if not isinstance(data, dict):
        return out
    for key in ("mcpServers", "servers"):
        if isinstance(data.get(key), dict):
            out += [(n, s) for n, s in data[key].items() if isinstance(s, dict)]
    for proj in (data.get("projects") or {}).values() if isinstance(data.get("projects"), dict) else []:
        if isinstance(proj, dict) and isinstance(proj.get("mcpServers"), dict):
            out += [(n, s) for n, s in proj["mcpServers"].items() if isinstance(s, dict)]
    return out


def scan_json(res: FileResult, text: str, name: str) -> None:
    """JSON は文字列照合ではなく構造で見る。permissions.deny の値は常に SAFE（止める対象を書いているだけ）。
    判定するもの: permissions.allow・defaultMode・command 系のキー（hooks・statusLine・apiKeyHelper 等）の中身・
    MCP の command＋args・package.json の scripts・値の不可視文字と秘密値。
    settings*.json と .mcp.json はこれだけを見る。その他の JSON（plugin の manifest 等）は値の文字列にも行の規則を当てる。"""
    try:
        data = json.loads(text)
    except ValueError as e:
        res.add("UNKNOWN", "U02", getattr(e, "lineno", 0), "JSON として読めない（形式不明。中身を人が確かめる）")
        scan_text(res, text, markdown=False)   # 構造で見られないので生の行で見る（判定不能を SAFE にしない）
        return
    for no, line in enumerate(text.splitlines(), 1):   # 生の不可視文字（キーの中も）
        if INVISIBLE_RE.search(line[1:] if no == 1 and line.startswith("\ufeff") else line):
            res.add("DANGEROUS", "K05", no, "不可視文字・双方向制御文字・タグ文字を含む（見えない命令）")
    structural_only = bool(STRUCTURAL_JSON_RE.match(name))

    def walk(obj, path: tuple) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if path[-1:] == ("permissions",) and k == "deny":
                    continue   # deny に書いた危険な形は止める対象の一覧（常に SAFE）
                walk(v, path + (k,))
        elif isinstance(obj, list):
            for v in obj:
                walk(v, path + ("[]",))
        elif isinstance(obj, str):
            ln = _line_of(text, obj)
            if INVISIBLE_RE.search(obj):
                res.add("DANGEROUS", "K05", ln, "不可視文字・双方向制御文字を含む値（\\u エスケープ）")
            if _SP is not None:
                for sname, _no in _SP.find_secret_values(obj):
                    res.add("DANGEROUS", "K09", ln, f"既知形式の秘密値（{sname}）を含む")
            key = path[-1] if path else ""
            is_cmd = key in COMMAND_KEYS or (name == "package.json" and len(path) >= 2 and path[-2] == "scripts")
            if is_cmd or not structural_only:
                for sub in obj.splitlines() or [obj]:
                    check_line(res, ln, sub, f"{'.'.join(p for p in path if p != '[]')}: " if is_cmd else "")

    walk(data, ())
    if _SP is None:
        res.add("UNKNOWN", "U05", 0, "秘密値の検査部品 secret_patterns.py が見つからない（秘密値は未検査）")
    if not isinstance(data, dict):
        return
    perms = data.get("permissions")
    if isinstance(perms, dict):
        mode = INVISIBLE_RE.sub("", str(perms.get("defaultMode", "")))
        if mode == "bypassPermissions":
            res.add("DANGEROUS", "K04", _line_of(text, "defaultMode"), "permissions.defaultMode が bypassPermissions（許可確認を飛ばす）")
        allow = perms.get("allow")
        for item in allow if isinstance(allow, list) else []:
            if not isinstance(item, str):
                continue
            t = INVISIBLE_RE.sub("", item).replace(" ", "")
            ln = _line_of(text, item)
            if t in ("Bash", "Bash(*)", "Bash(:*)"):
                res.add("DANGEROUS", "K10", ln, f"permissions.allow の {item} はすべての Bash を許す")
            elif t in ("Write", "Write(*)", "Edit", "Edit(*)", "WebFetch", "WebFetch(*)") or t.startswith(("Bash(rm", "Bash(sudo")):
                res.add("CAUTION", "C06", ln, f"permissions.allow の {item} は広い")
        if "allow" in perms and not isinstance(perms.get("allow"), list):
            res.add("UNKNOWN", "U02", _line_of(text, "allow"), "permissions.allow が配列でない（形式不明）")
    if INVISIBLE_RE.sub("", str(data.get("defaultMode", ""))) == "bypassPermissions":
        res.add("DANGEROUS", "K04", _line_of(text, "defaultMode"), "defaultMode が bypassPermissions（許可確認を飛ばす）")
    for sname, srv in _mcp_servers(data):
        cmd = " ".join(str(x) for x in [srv.get("command", "")] + list(srv.get("args") or []) if x)
        ln = _line_of(text, str(srv.get("command") or sname))
        if cmd:
            check_line(res, ln, cmd, f"MCP サーバ {sname}: ")
        if srv.get("url") or str(srv.get("type", "")).lower() in ("http", "sse"):
            res.add("CAUTION", "C01", ln, f"MCP サーバ {sname} はリモート（{srv.get('type', 'url')}）。送る内容と出所を確かめる")
        if srv.get("env"):
            res.add("CAUTION", "C03", ln, f"MCP サーバ {sname} に環境変数を渡す（値は平文で書かない）")


def scan_file(p: Path, shown: str) -> FileResult:
    res = FileResult(shown)
    if p.is_symlink():
        res.add("UNKNOWN", "U03", 0, "シンボリックリンク（たどらない。実体を確かめる）")
        return res
    try:
        if p.stat().st_size > MAX_BYTES:
            res.add("UNKNOWN", "U01", 0, f"大きすぎる（{MAX_BYTES // 1024 // 1024}MB 超）。中身を人が確かめる")
            return res
        text = p.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        res.add("UNKNOWN", "U01", 0, "UTF-8 として読めない（バイナリ・形式不明）")
        return res
    except OSError as e:
        res.add("UNKNOWN", "U01", 0, f"読めない（{e.__class__.__name__}）")
        return res
    suffix = p.suffix.lower()
    if suffix == ".json":
        scan_json(res, text, p.name)
        return res
    markdown = suffix in (".md", ".markdown", ".mdc")
    scan_text(res, text, markdown)
    if markdown:
        scan_markdown(res, text)
    if markdown or suffix in (".html", ".htm"):
        scan_hidden(res, text)
    return res


def collect(arg: str) -> list[FileResult]:
    p = Path(arg)
    if p.is_symlink() or p.is_file():
        return [scan_file(p, arg)]
    if not p.is_dir():
        r = FileResult(arg)
        r.add("UNKNOWN", "U04", 0, "パスが無い")
        return [r]
    out: list[FileResult] = []
    for f in sorted(p.rglob("*")):
        rel_parts = f.relative_to(p).parts
        if set(rel_parts[:-1]) & SKIP_DIRS:
            continue
        if f.is_symlink():
            out.append(scan_file(f, f.as_posix()))
        elif f.is_file() and f.suffix.lower() not in SKIP_EXTS:
            out.append(scan_file(f, f.as_posix()))
    if not out:
        r = FileResult(arg)
        r.add("UNKNOWN", "U04", 0, "検査できるファイルが無い")
        out.append(r)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="スキル・MCP・プラグインの導入前の静的検査（実行しない・ネット不使用）")
    ap.add_argument("paths", nargs="+", help="走査するファイルまたはディレクトリ")
    ap.add_argument("--json", action="store_true", help="結果を JSON で標準出力に出す（このときは他の文言を出さない）")
    ap.add_argument("--brief", action="store_true", help="CAUTION・UNKNOWN はファイルごとに 1 行にまとめる")
    a = ap.parse_args(argv)
    results: list[FileResult] = []
    for arg in a.paths:
        results += collect(arg)
    counts = {lv: 0 for lv in LEVELS}
    for r in results:
        counts[r.verdict] += 1
    verdict = max((r.verdict for r in results), key=RANK.__getitem__, default="UNKNOWN")
    rc = 1 if verdict == "DANGEROUS" else 0
    if a.json:
        print(json.dumps({"verdict": verdict, "exit": rc, "counts": counts,
                          "files": [{"path": r.path, "verdict": r.verdict,
                                     "findings": [f.as_dict() for f in r.findings]} for r in results]},
                         ensure_ascii=False, indent=2))
        return rc
    print(f"=== skill-scan: {' '.join(a.paths)} ===")
    for lv in ("DANGEROUS", "UNKNOWN", "CAUTION"):
        for r in results:
            fs = [f for f in r.findings if f.level == lv]
            if not fs:
                continue
            if a.brief and lv != "DANGEROUS":
                rules = ",".join(dict.fromkeys(f.rule for f in fs))
                print(f"  {lv:<9} {r.path}  {rules}（{fs[0].detail} ほか）" if len(fs) > 1 else f"  {lv:<9} {r.path}:{fs[0].line}  {fs[0].rule} {fs[0].detail}")
                continue
            for f in fs:
                print(f"  {lv:<9} {r.path}:{f.line}  {f.rule} {f.detail}")
    print(f"判定: {verdict}（ファイル数 DANGEROUS {counts['DANGEROUS']} / UNKNOWN {counts['UNKNOWN']} / "
          f"CAUTION {counts['CAUTION']} / SAFE {counts['SAFE']}）")
    if verdict == "DANGEROUS":
        print("❌ DANGEROUS: 導入しない。中身を確かめて入れると決めたなら AIDD_SKILL_SCAN_OK=1 を付けて導入を 1 回だけ再実行する")
    elif verdict in ("UNKNOWN", "CAUTION"):
        print(f"⚠ {verdict}: 導入は止めない。上の一覧（ネットワーク・書き込み・環境変数・判定不能）を確かめる。SAFE には数えない")
    else:
        print("✅ SAFE: 既知の危険な形は見つからない（静的な検査の範囲内。実行時の振る舞いは保証しない）")
    return rc


if __name__ == "__main__":
    sys.exit(main())
