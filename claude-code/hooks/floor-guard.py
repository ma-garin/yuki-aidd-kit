#!/usr/bin/env python3
"""基準を下げる差分を `git commit` の前に止める PreToolUse フック（A-12 基準を緩めない）。CLI としても使える。

出所: `rules/absolute-rules.md` A-12「しきい値・語彙・テスト・除外リストを『通すため』に変えない」は散文で、
機械が見ていなかった。agent-skills（constraint-driven-development の floor-guard）の型を借り、差分だけを見て
「基準を下げる手」を検出する。**厳しくする変更は黙って通し、緩める変更だけ鳴らす。**

検出（作業ツリー＋index の HEAD との差分、＋未追跡ファイル）:
  skip        テストファイルに skip / only / xfail が追加された
  assert      テストファイルから assert / expect が正味で減った
  test-del    テストファイルが削除された
  suppress    lint / 型 / セキュリティ検査の抑止コメント（noqa, type: ignore, eslint-disable, ts-ignore, nosec …）が追加された
  stub        TODO / FIXME / NotImplementedError / 空 except / 空 catch がコードに追加された
  threshold   しきい値ファイル（TESTING_STRATEGY.md §7, feature_contracts.yml, pyproject, coverage, jest/vitest/playwright 設定,
              check_*.py, quality_harness.py）で基準の数値が緩む向きに変わった
  exclude     同じファイルで除外リスト（EXCLUDE / allowlist / IGNORE）に項目が追加された

使い方:
  hook（PreToolUse Bash）: stdin の JSON を読み、コマンドが git commit なら検査して NG で deny。
  CLI: python3 floor-guard.py --check [--root DIR] [--base REF]  → exit 0 合格 / 1 違反 / 2 判定不能（git 無し）
例外: commit メッセージに `Floor-Guard-Allow: <理由 10 文字以上>` を書くと通す（git 履歴に残る。環境変数のバイパスは無い）。
除外: `.floor-guard-ignore`（root 直下。1 行 1 glob）。文書（.md .html .txt）と本ファイル・回帰テストは既定で対象外。
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

TEST_PATH_RE = re.compile(r"(^|/)(tests?|__tests__|spec|e2e)/|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.[jt]sx?$|\.spec\.[jt]sx?$|_test\.go$|Test\.java$")
CODE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".sh", ".mjs", ".cjs", ".vue", ".rs", ".kt", ".swift", ".php")
DOC_EXT = (".md", ".html", ".txt", ".csv", ".svg")
DEFAULT_IGNORE = ("claude-code/hooks/floor-guard.py", ".claude/hooks/floor-guard.py", "scripts/test-*.sh", "**/floor-guard.py")

SKIP_RE = re.compile(r"@pytest\.mark\.(skip|xfail)|pytest\.skip\(|@unittest\.skip|self\.skipTest\(|\b(it|test|describe)\.(skip|only)\b|\.only\(|\bxit\(|\bxdescribe\(|\bxtest\(")
ASSERT_RE = re.compile(r"^\s*assert\b|\bexpect\(|\bassert[A-Z]\w*\(|\bassert_\w+\(|\.toBe\w*\(|\.toEqual\(|\.toHave\w*\(")
SUPPRESS_RE = re.compile(r"#\s*noqa|#\s*type:\s*ignore|eslint-disable|@ts-ignore|@ts-nocheck|@ts-expect-error|istanbul ignore|pylint:\s*disable|#\s*nosec|nosemgrep|rubocop:disable|--no-verify|gitleaks:allow|coverage:\s*ignore|pragma:\s*no cover")
STUB_RE = re.compile(r"\bTODO\b|\bFIXME\b|NotImplementedError|[Nn]ot implemented|^\s*except\b[^:\n]*:\s*pass\s*$|catch\s*(\([^)]*\))?\s*\{\s*\}|^\s*pass\s*#\s*stub")
THRESHOLD_FILE_RE = re.compile(r"(TESTING_STRATEGY|CONSTRAINTS|DEFINITION_OF_DONE)\.md$|feature_contracts\.ya?ml$|pyproject\.toml$|setup\.cfg$|\.coveragerc$|(jest|vitest|playwright)\.config\.[cm]?[jt]s$|ruff\.toml$|mypy\.ini$|tox\.ini$|\.eslintrc|(^|/)check_[a-z_]+\.py$|quality_harness\.py$")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])")
LOWER_IS_LOOSER = re.compile(r">=|>\s*\d|fail_under|threshold|しきい値|\bmin\b|min_|MIN|coverage|branches|lines|functions|statements", re.I)
HIGHER_IS_LOOSER = re.compile(r"<=|<\s*\d|\bmax\b|max_|MAX|limit|上限|timeout|retries|tolerance", re.I)
EXCLUDE_CTX_RE = re.compile(r"EXCLUDE|exclude|allowlist|ALLOWLIST|IGNORE|ignore_|SKIP_|skip_list|whitelist", re.I)
BARE_ITEM_RE = re.compile(r"""^\s*["'][^"']+["'],?\s*(#.*)?$|^\s*-\s+["']?[\w./*-]+["']?\s*(#.*)?$""")
ALLOW_RE = re.compile(r"Floor-Guard-Allow:\s*(\S.{9,})")
COMMIT_RE = re.compile(r"(?:^|&&|\|\||;|\n)\s*git\s+(?:-C\s+\S+\s+)?commit\b")


def git(root: str, *args: str) -> str | None:
    try:
        return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def load_ignore(root: str) -> list[str]:
    pats = list(DEFAULT_IGNORE)
    p = os.path.join(root, ".floor-guard-ignore")
    if os.path.isfile(p):
        with open(p, encoding="utf-8", errors="replace") as f:
            pats += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    return pats


def ignored(path: str, pats: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(os.path.basename(path), p) for p in pats)


def parse_diff(text: str) -> dict[str, dict]:
    """path -> {added: [(lineno, text)], removed: [text], deleted: bool, ctx: [text]}"""
    files: dict[str, dict] = {}
    cur = None
    new_ln = 0
    for line in text.splitlines():
        if line.startswith("+++ "):
            name = line[4:]
            if name.startswith("b/"):
                name = name[2:]
            if name == "/dev/null":
                if cur is not None:
                    cur["deleted"] = True
                continue
            cur = files.setdefault(name, {"added": [], "removed": [], "deleted": False, "ctx": []})
            continue
        if line.startswith("--- "):
            name = line[4:]
            if name.startswith("a/"):
                name = name[2:]
            if name != "/dev/null":
                cur = files.setdefault(name, {"added": [], "removed": [], "deleted": False, "ctx": []})
            continue
        if cur is None:
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            new_ln = int(m.group(1)) if m else 0
            continue
        if line.startswith("+"):
            cur["added"].append((new_ln, line[1:]))
            cur["ctx"].append(line[1:])
            new_ln += 1
        elif line.startswith("-"):
            cur["removed"].append(line[1:])
            cur["ctx"].append(line[1:])
        elif line.startswith("\\"):
            continue
        else:
            cur["ctx"].append(line[1:] if line.startswith(" ") else line)
            new_ln += 1
    return files


def collect(root: str, base: str | None) -> dict[str, dict] | None:
    has_head = git(root, "rev-parse", "--verify", "HEAD") is not None
    if base:
        diff = git(root, "diff", "--no-color", "--unified=3", base)
    elif has_head:
        diff = git(root, "diff", "--no-color", "--unified=3", "HEAD")
    else:
        diff = git(root, "diff", "--no-color", "--unified=3", "--cached")
    if diff is None:
        return None
    files = parse_diff(diff)
    others = git(root, "ls-files", "--others", "--exclude-standard") or ""
    for rel in others.splitlines():
        p = os.path.join(root, rel)
        try:
            if not os.path.isfile(p) or os.path.getsize(p) > 1_000_000:
                continue
            with open(p, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        files[rel] = {"added": list(enumerate(lines, 1)), "removed": [], "deleted": False, "ctx": lines}
    return files


def threshold_findings(path: str, d: dict) -> list[str]:
    out = []
    removed_by_skel: dict[str, list[str]] = {}
    for r in d["removed"]:
        removed_by_skel.setdefault(NUM_RE.sub("#", r).strip(), []).append(r)
    for ln, a in d["added"]:
        skel = NUM_RE.sub("#", a).strip()
        olds = removed_by_skel.get(skel)
        if not olds or "#" not in skel:
            continue
        old = olds[0]
        on = [float(x) for x in NUM_RE.findall(old)]
        nn = [float(x) for x in NUM_RE.findall(a)]
        if len(on) != len(nn) or on == nn:
            continue
        lower = any(n < o for o, n in zip(on, nn))
        higher = any(n > o for o, n in zip(on, nn))
        lo, hi = LOWER_IS_LOOSER.search(a), HIGHER_IS_LOOSER.search(a)
        if lo and not hi:      # 「以上」型: 下げたら緩む。上げるのは黙って通す
            if lower:
                out.append(f"threshold {path}:{ln} 基準が下がった: {a.strip()[:100]}")
        elif hi and not lo:    # 「以下」型: 上げたら緩む
            if higher:
                out.append(f"threshold {path}:{ln} 上限が緩んだ: {a.strip()[:100]}")
        else:
            out.append(f"threshold {path}:{ln} しきい値の数値が変わった（向き不明。理由を Floor-Guard-Allow に）: {a.strip()[:100]}")
    return out


def check(root: str, base: str | None = None) -> list[str] | None:
    files = collect(root, base)
    if files is None:
        return None
    pats = load_ignore(root)
    findings: list[str] = []
    for path, d in sorted(files.items()):
        if ignored(path, pats):
            continue
        is_test = bool(TEST_PATH_RE.search(path))
        is_doc = path.lower().endswith(DOC_EXT)
        is_code = path.lower().endswith(CODE_EXT)
        if is_test and d["deleted"]:
            findings.append(f"test-del {path} テストファイルの削除")
            continue
        if is_test:
            for ln, a in d["added"]:
                if SKIP_RE.search(a):
                    findings.append(f"skip {path}:{ln} {a.strip()[:100]}")
            lost = sum(1 for r in d["removed"] if ASSERT_RE.search(r)) - sum(1 for _, a in d["added"] if ASSERT_RE.search(a))
            if lost > 0:
                findings.append(f"assert {path} assert / expect が正味 {lost} 件減った")
        if not is_doc:
            for ln, a in d["added"]:
                if SUPPRESS_RE.search(a):
                    findings.append(f"suppress {path}:{ln} {a.strip()[:100]}")
        if is_code and not is_test:
            for ln, a in d["added"]:
                if STUB_RE.search(a):
                    findings.append(f"stub {path}:{ln} {a.strip()[:100]}")
        if THRESHOLD_FILE_RE.search(path):
            findings += threshold_findings(path, d)
            ctx = d["ctx"]
            for i, line in enumerate(ctx):
                if any(line == a for _, a in d["added"]) and BARE_ITEM_RE.match(line):
                    window = ctx[max(0, i - 8):i]
                    if any(EXCLUDE_CTX_RE.search(w) for w in window):
                        findings.append(f"exclude {path} 除外リストに追加: {line.strip()[:80]}")
    return findings


def hook_main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not COMMIT_RE.search(cmd):
        return 0
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    findings = check(root)
    if findings is None:
        return 0  # git の外。判定不能はここでは通す（CLI は exit 2）
    if not findings:
        return 0
    m = ALLOW_RE.search(cmd)
    if m:
        print(json.dumps({"systemMessage": f"[floor-guard] 基準を下げる差分 {len(findings)} 件を Floor-Guard-Allow で通した: {m.group(1).strip()[:80]}"}, ensure_ascii=False))
        return 0
    shown = "／".join(findings[:6]) + (f" ほか {len(findings) - 6} 件" if len(findings) > 6 else "")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "floor-guard（A-12 基準を緩めない）: 基準を下げる差分がある。テスト・しきい値・除外リスト・抑止コメントを「通すため」に"
            "変えない。直すか、正当な変更なら commit メッセージに `Floor-Guard-Allow: <理由>` を書く。 " + shown
        ),
    }}, ensure_ascii=False))
    return 0


def cli_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="基準を下げる差分の検査（A-12）")
    ap.add_argument("--check", action="store_true", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--base", default=None, help="この REF との差分を見る（省略時は HEAD と作業ツリー）")
    a = ap.parse_args(argv)
    findings = check(os.path.abspath(a.root), a.base)
    LAST.update(findings=findings or [])
    if findings is None:
        print("floor-guard: 判定不能（git リポジトリでない、または git が無い）")
        return 2
    if not findings:
        print("floor-guard: NG=0（基準を下げる差分なし）")
        return 0
    print(f"floor-guard: NG={len(findings)}")
    for f in findings:
        print(f"  - {f}")
    return 1




# ---- --json: エージェント向け出力契約（WeKnora CLI の AGENTS.md の型） ------------------------
# {"ok": bool, "exit": 0|1|2, "data": {...}, "meta": {...}, "error": {"type", "message", "hint", "retry_argv"}}
# 「エラー文は AI の判断入力になる」。hint は次の一手、retry_argv は直した後に再実行するコマンド。
LAST: dict = {}
JSON_ERROR_TYPES = {1: 'floor.lowered', 2: 'floor.undetermined'}
JSON_HINTS = {1: '基準を下げる差分を直す。正当な変更なら commit メッセージに Floor-Guard-Allow: <理由> を書く', 2: 'git リポジトリの中で実行する'}
JSON_RETRY_ARGV = ['python3', '.claude/hooks/floor-guard.py', '--check']


def _jsonable(x):
    import dataclasses
    from pathlib import Path as _P
    if dataclasses.is_dataclass(x) and not isinstance(x, type):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(x).items()}
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [_jsonable(v) for v in x]
    if isinstance(x, _P):
        return str(x)
    if isinstance(x, float) and x != x:
        return None
    return x


def _run_json(fn) -> int:
    import contextlib
    import io
    import json as _json
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = int(fn() or 0)
        except SystemExit as e:  # argparse のエラー等
            code = int(e.code or 0) if isinstance(e.code, int) else 2
    text = buf.getvalue().rstrip().splitlines()
    env = {"ok": code == 0, "exit": code, "data": _jsonable(dict(LAST)), "meta": {"stdout": text}}
    if code != 0:
        env["error"] = {
            "type": JSON_ERROR_TYPES.get(code, "unknown"),
            "message": next((ln for ln in reversed(text) if ln.strip()), f"exit {code}"),
            "hint": JSON_HINTS.get(code, ""),
            "retry_argv": JSON_RETRY_ARGV,
        }
    print(_json.dumps(env, ensure_ascii=False))
    return code


if __name__ == "__main__":
    if "--check" in sys.argv:
        if "--json" in sys.argv:
            sys.argv.remove("--json")
            sys.exit(_run_json(lambda: cli_main(sys.argv[1:])))
        sys.exit(cli_main(sys.argv[1:]))
    sys.exit(hook_main())
