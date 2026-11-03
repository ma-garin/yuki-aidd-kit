#!/usr/bin/env python3
"""doctor.py — キットの checkout が「この PC で今動くか」を、軽いコマンドを実際に走らせて診る（読むだけ・副作用なし）。

verify.sh は導入先の配置を見る。こちらは導入の前・Codex（Windows・git/bash 無し）に渡す前に、キット側の部品が
この環境の Python で読み込めるか・必要な道具が揃っているかを確かめる。**実行した時点のスナップショット**であり、
常駐・定期実行・監視はしない（結果は次の変更で古くなる）。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。ファイルを書かない（構文検査はメモリ上で compile し、
子プロセスには PYTHONDONTWRITEBYTECODE=1 を渡して __pycache__ も作らない）。

診断（各項目 OK / WARN / NG / SKIP）:
  D1 python        子プロセスで `<この Python> --version` を実行し、3.9 以上か（NG）
  D2 VERSION       ルートの VERSION が X.Y.Z で読めるか（NG）
  D3 hook の配線    03_ClaudeCode/hooks/settings.json の command が指す hook ファイルが実在するか（NG）
  D4 hook の構文    hooks/*.py を compile（NG）・hooks/*.sh を `bash -n`（bash が無ければ SKIP）
  D5 道具          REQUIRED_TOOLS が 02_共通/ツール/ に揃い、*.py が compile できるか（NG）・*.sh を `bash -n`
  D6 部品の自己検査  `secret_patterns.py --self-test` を実行して exit 0 か（NG）
  D7 Codex 生成物   `04_Codex/build_codex_skills.py --check`（一時ディレクトリで生成して比較するだけ）が exit 0 か（NG）
  D8 外部コマンド   git・bash の有無（WARN。Codex の Windows 環境には無いのが前提なので止めない）
  D9 規則ハッシュ   rules-manifest.json（02_共通/rules/*.md・CLAUDE.md・CLAUDE.md.template の sha256）とキット内の
                   ファイルを比較（NG）。--home 指定時は <HOME>/.claude/rules/aidd-kit/*.md とも比較（導入先が無ければ SKIP）
  D10 hook 配線     --settings（複数可。既定は <HOME>/.claude/settings.json と plugins 配下の yuki-aidd-kit の hooks.json）を
                   **読むだけ**で、(a) 登録 (b) 実体 (c) .sh 実行権限／.py compile (d) constitution-gate pre が PreToolUse 先頭
                   を検査（NG）。キットの hook が 1 本も無い settings は「未導入」の WARN、読む対象が無ければ SKIP
  D11 A-2 発火      一時プロジェクトで constitution-gate.py に (i) 見積なしの Write → deny と停止 file、
                   (ii) `見積：5分` の後の Write → 出力空、を与えて確かめる（NG）。一時ディレクトリは消す
  D12 必須環境変数   REQUIRED_ENV の値と一致するか・GH_TOKEN か `gh auth status` 成功か（NG）。**値は出さない**

使い方: python3 00_導入/03_点検/doctor.py [--root DIR] [--json] [--home [DIR]] [--settings PATH ...]
       python3 00_導入/03_点検/doctor.py --write-manifest   （保守者用: rules-manifest.json を書き直す）
終了コード: 0=NG なし / 1=NG あり
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import re
import shutil
import hashlib
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
MIN_PY = (3, 9)
REQUIRED_TOOLS = (
    "md-section.py", "section_hash.py", "baseline.py", "skill-scan.py", "req-lint.py", "cite-check.py",
    "check_approval.py", "quality_harness.py", "test_metrics.py", "test-weaken-check.py", "pw-spec-lint.py",
    "e2e_history.py", "check-handoff.py", "pack-context.py", "check-version.py", "check-layers.py",
    "skill-lint.py", "llms-txt.py", "trace-check.sh", "security-scan.sh",
)
TIMEOUT = 60
HOOK_CMD_RE = re.compile(r"hooks/([\w.-]+\.(?:py|sh))")
# D12 必須環境変数（一覧はここ 1 か所）。値が None なら「有ること」だけを見る。出力に値は出さない
REQUIRED_ENV = {
    "TZ": "Asia/Tokyo",
    "CLAUDE_CODE_GOAL_CHECKIN_MINUTES": "0",  # 03_ClaudeCode/hooks/settings.json の env と同じ値
}
GH_ENV = "GH_TOKEN"  # これが有るか `gh auth status` が成功すれば OK
MANIFEST = Path("00_導入/03_点検/rules-manifest.json")


class Report:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, check: str, status: str, target: str, detail: str = "") -> None:
        self.items.append({"check": check, "status": status, "target": target, "detail": detail})

    def count(self, status: str) -> int:
        return sum(1 for i in self.items if i["status"] == status)


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, f"{type(e).__name__}: {e}"
    out = (p.stdout + p.stderr).strip().splitlines()
    return p.returncode, (out[-1] if out else "")


def compile_check(f: Path) -> tuple[str, str]:
    """メモリ上で compile する（.pyc を書かない）。(状態, 詳細)。SyntaxWarning は将来の版でエラーになるので WARN。"""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")
        except (SyntaxError, UnicodeDecodeError, ValueError) as e:
            return "NG", f"{type(e).__name__}: {e}"
    sw = [w for w in caught if issubclass(w.category, SyntaxWarning)]
    if sw:
        return "WARN", f"SyntaxWarning {len(sw)} 件（{sw[0].lineno} 行: {sw[0].message}）"
    return "OK", ""


def check_sh(r: Report, check: str, f: Path, bash: str | None, root: Path) -> None:
    if not bash:
        r.add(check, "SKIP", rel(f, root), "bash が無い（Windows の Codex 環境では .sh は使わない）")
        return
    rc, last = run([bash, "-n", str(f)], root)
    r.add(check, "OK" if rc == 0 else "NG", rel(f, root), "" if rc == 0 else last)


def rel(f: Path, root: Path) -> str:
    try:
        return f.relative_to(root).as_posix()
    except ValueError:
        return f.as_posix()


def diagnose(root: Path, home: Path | None = None, settings_paths: list[Path] | None = None) -> Report:
    r = Report()
    bash = shutil.which("bash")
    # D1
    rc, last = run([sys.executable, "--version"], root)
    m = re.search(r"(\d+)\.(\d+)", last)
    ok = rc == 0 and m is not None and (int(m.group(1)), int(m.group(2))) >= MIN_PY
    r.add("D1 python", "OK" if ok else "NG", sys.executable, last or f"exit {rc}")
    # D2
    try:
        v = (root / "VERSION").read_text(encoding="utf-8").strip()
        r.add("D2 VERSION", "OK" if re.fullmatch(r"\d+\.\d+\.\d+", v) else "NG", "VERSION", v)
    except OSError as e:
        r.add("D2 VERSION", "NG", "VERSION", str(e))
    # D3・D4
    hooks = root / "03_ClaudeCode" / "hooks"
    settings = hooks / "settings.json"
    try:
        wired = sorted(set(HOOK_CMD_RE.findall(settings.read_text(encoding="utf-8"))))
        json.loads(settings.read_text(encoding="utf-8"))
        missing = [h for h in wired if not (hooks / h).is_file()]
        r.add("D3 hook の配線", "NG" if missing else "OK", rel(settings, root),
              ("無い: " + ", ".join(missing)) if missing else f"{len(wired)} 本の hook が実在")
    except (OSError, ValueError) as e:
        r.add("D3 hook の配線", "NG", rel(settings, root), f"{type(e).__name__}: {e}")
    if hooks.is_dir():
        for f in sorted(hooks.glob("*.py")):
            st, why = compile_check(f)
            r.add("D4 hook の構文", st, rel(f, root), why)
        for f in sorted(hooks.glob("*.sh")):
            check_sh(r, "D4 hook の構文", f, bash, root)
    # D5
    tools = root / "02_共通" / "ツール"
    for name in REQUIRED_TOOLS:
        f = tools / name
        if not f.is_file():
            r.add("D5 道具", "NG", rel(f, root), "無い")
        elif f.suffix == ".py":
            st, why = compile_check(f)
            r.add("D5 道具", st, rel(f, root), why)
        else:
            check_sh(r, "D5 道具", f, bash, root)
    # D6
    sp = hooks / "secret_patterns.py"
    if sp.is_file():
        rc, last = run([sys.executable, str(sp), "--self-test"], root)
        r.add("D6 部品の自己検査", "OK" if rc == 0 else "NG", rel(sp, root), last)
    else:
        r.add("D6 部品の自己検査", "NG", rel(sp, root), "無い")
    # D7
    builder = root / "04_Codex" / "build_codex_skills.py"
    if builder.is_file():
        rc, last = run([sys.executable, str(builder), "--check"], root)
        r.add("D7 Codex 生成物", "OK" if rc == 0 else "NG", rel(builder, root), last)
    else:
        r.add("D7 Codex 生成物", "NG", rel(builder, root), "無い")
    # D8
    for cmd in ("git", "bash"):
        path = shutil.which(cmd)
        if path:
            rc, last = run([path, "--version"], root)
            r.add("D8 外部コマンド", "OK" if rc == 0 else "WARN", cmd, last.splitlines()[0] if last else f"exit {rc}")
        else:
            r.add("D8 外部コマンド", "WARN", cmd, "無い（Codex 環境では想定どおり。.sh の道具と git hook は使えない）")
    # D9〜D12
    base = home or Path.home()
    check_rules_hash(r, root, home)
    check_wiring(r, root, settings_paths if settings_paths is not None else default_settings(base), base)
    check_a2(r, root)
    check_env(r, root)
    return r


def manifest_targets(root: Path) -> list[Path]:
    return sorted((root / "02_共通" / "rules").glob("*.md")) + [root / "CLAUDE.md", root / "03_ClaudeCode" / "CLAUDE.md.template"]


def sha256(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def write_manifest(root: Path) -> Path:
    data = {rel(f, root): sha256(f) for f in manifest_targets(root) if f.is_file()}
    out = root / MANIFEST
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def check_rules_hash(r: Report, root: Path, home: Path | None) -> None:
    mf = root / MANIFEST
    try:
        data = json.loads(mf.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        r.add("D9 規則ハッシュ", "NG", rel(mf, root), f"台帳が読めない（{type(e).__name__}）。保守者が --write-manifest")
        return
    bad = [k for k, h in data.items() if not (root / k).is_file() or sha256(root / k) != h]
    extra = [rel(f, root) for f in manifest_targets(root) if f.is_file() and rel(f, root) not in data]
    r.add("D9 規則ハッシュ", "NG" if bad or extra else "OK", rel(mf, root),
          ("不一致: " + ", ".join(bad + extra)) if bad or extra else f"{len(data)} 件一致")
    if home is None:
        return
    dst = home / ".claude" / "rules" / "aidd-kit"
    if not dst.is_dir():
        r.add("D9 規則ハッシュ", "SKIP", dst.as_posix(), "導入先が無い")
        return
    rules = {k: h for k, h in data.items() if k.startswith("02_共通/rules/")}
    bad = [Path(k).name for k, h in rules.items() if not (dst / Path(k).name).is_file() or sha256(dst / Path(k).name) != h]
    r.add("D9 規則ハッシュ", "NG" if bad else "OK", dst.as_posix(),
          ("台帳と違う: " + ", ".join(bad)) if bad else f"{len(rules)} 件一致")


def default_settings(home: Path) -> list[Path]:
    out = []
    s = home / ".claude" / "settings.json"
    if s.is_file():
        out.append(s)
    plugins = home / ".claude" / "plugins"
    if plugins.is_dir():
        out += sorted(p for p in plugins.rglob("hooks.json")
                      if "yuki-aidd-kit" in p.as_posix() and p.parent.name == ".claude-plugin")
    return out


def resolve_hook(cmd: str, name: str, settings: Path, home: Path) -> Path:
    if "CLAUDE_PLUGIN_ROOT" in cmd:
        return settings.parent.parent / "03_ClaudeCode" / "hooks" / name
    if "CLAUDE_PROJECT_DIR" in cmd:
        return settings.parent.parent / "03_ClaudeCode" / "hooks" / name
    if "~/.claude/hooks/" in cmd or "$HOME/.claude/hooks/" in cmd:
        return home / ".claude" / "hooks" / name
    if ".claude/hooks/" in cmd:
        return settings.parent.parent / ".claude" / "hooks" / name
    return settings.parent / name


def check_wiring(r: Report, root: Path, paths: list[Path], home: Path) -> None:
    try:
        kit_hooks = set(HOOK_CMD_RE.findall((root / ".claude-plugin" / "hooks.json").read_text(encoding="utf-8")))
    except OSError as e:
        r.add("D10 hook 配線", "NG", ".claude-plugin/hooks.json", f"真実源が読めない: {e}")
        return
    if not paths:
        r.add("D10 hook 配線", "SKIP", (home / ".claude").as_posix(), "settings も plugin の hooks.json も無い（未導入）")
        return
    for sp in paths:
        tgt = sp.as_posix()
        try:
            hooks = json.loads(sp.read_text(encoding="utf-8")).get("hooks") or {}
        except (OSError, ValueError, AttributeError) as e:
            r.add("D10 hook 配線", "NG", tgt, f"読めない（{type(e).__name__}）")
            continue
        cmds = [(ev, h.get("command", "")) for ev, gs in hooks.items() for g in gs for h in g.get("hooks", [])]
        names = {m for _, c in cmds for m in HOOK_CMD_RE.findall(c)}
        if not names & kit_hooks:
            r.add("D10 hook 配線", "WARN", tgt, "キットの hook が未導入（00_導入/01_インストール/新規マシン導入手順.md）")
            continue
        missing = sorted(kit_hooks - names)
        r.add("D10 hook 配線", "NG" if missing else "OK", tgt,
              ("(a) 未登録: " + ", ".join(missing)) if missing else f"(a) {len(kit_hooks)} 本登録")
        probs = []
        for _, c in cmds:
            for n in HOOK_CMD_RE.findall(c):
                f = resolve_hook(c, n, sp, home)
                if not f.is_file():
                    probs.append(f"(b) 実体なし {n}")
                elif n.endswith(".sh") and not os.access(f, os.X_OK):
                    probs.append(f"(c) 実行権限なし {n}")
                elif n.endswith(".py") and compile_check(f)[0] == "NG":
                    probs.append(f"(c) compile 不可 {n}")
        r.add("D10 hook 配線", "NG" if probs else "OK", tgt,
              "; ".join(sorted(set(probs))) if probs else "(b)(c) 実体・権限・構文")
        pre = hooks.get("PreToolUse") or []
        first = (pre[0].get("hooks") or [{}])[0].get("command", "") if pre else ""
        ok = "constitution-gate.py" in first and " pre" in first and "matcher" not in pre[0]
        r.add("D10 hook 配線", "OK" if ok else "NG", tgt,
              "(d) constitution-gate pre が PreToolUse の先頭" if ok else "(d) PreToolUse の先頭が constitution-gate pre でない")


def check_a2(r: Report, root: Path) -> None:
    gate = root / "03_ClaudeCode" / "hooks" / "constitution-gate.py"
    if not gate.is_file():
        r.add("D11 A-2 発火", "NG", rel(gate, root), "無い")
        return
    now = 1790000000

    def line(kind: str, uid: str, text: str) -> str:
        content = text if kind == "user" else [{"type": "text", "text": text}]
        return json.dumps({"type": kind, "uuid": uid, "message": {"role": kind, "content": content}}, ensure_ascii=False)

    with tempfile.TemporaryDirectory(prefix="doctor-d11-") as tmp:
        results = []
        for case, msgs in (("i", [("user", "u1", "a.py を実装して")]),
                           ("ii", [("user", "u1", "a.py を実装して"), ("assistant", "a1", "見積：5分\n着手します")])):
            p = Path(tmp) / case
            (p / ".claude").mkdir(parents=True)
            (p / "06_保守者向け").mkdir()
            lessons = p / "06_保守者向け" / "学んだこと.md"
            lessons.write_text("# 学んだこと\n", encoding="utf-8")
            os.utime(lessons, (now - 86400, now - 86400))
            t = p / "transcript.jsonl"
            t.write_text("".join(line(*m) + "\n" for m in msgs), encoding="utf-8")
            payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Write",
                                  "tool_input": {"file_path": "/x/a.py", "content": "x"},
                                  "transcript_path": str(t), "cwd": str(p)}, ensure_ascii=False)
            env = {k: v for k, v in os.environ.items()
                   if k not in ("CLAUDE_PROJECT_DIR", "AIDD_STOP_FILE", "AIDD_REPORT_INTERVAL_SEC")}
            env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", AIDD_NOW_EPOCH=str(now),
                       AIDD_HOOK_LOG=str(Path(tmp) / "hook-decisions.log"),
                       AIDD_TOOL_TIME=str(Path(tmp) / "tool-time.json"), AIDD_TRANSCRIPT_FLUSH_SEC="0")
            try:
                cp = subprocess.run([sys.executable, str(gate), "pre"], input=payload, cwd=str(p), env=env,
                                    capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT)
                out = (cp.stdout + cp.stderr).strip()
            except (OSError, subprocess.TimeoutExpired) as e:
                out = f"ERROR {type(e).__name__}"
            stopped = (p / ".claude" / "constitution-stop").exists()
            results.append((case, out, stopped))
    (_, o1, s1), (_, o2, s2) = results
    ok1 = '"permissionDecision": "deny"' in o1 and s1
    ok2 = o2 == "" and not s2
    r.add("D11 A-2 発火", "OK" if ok1 else "NG", rel(gate, root),
          "(i) 見積なしの Write → deny・停止 file" if ok1 else f"(i) 期待外: deny={'deny' in o1} 停止file={s1}")
    r.add("D11 A-2 発火", "OK" if ok2 else "NG", rel(gate, root),
          "(ii) 見積行の後の Write → 通過" if ok2 else f"(ii) 期待外: 出力={o2[:80]!r} 停止file={s2}")


def check_env(r: Report, root: Path) -> None:
    for k, want in REQUIRED_ENV.items():
        v = os.environ.get(k)
        if v is None:
            r.add("D12 必須環境変数", "NG", k, "無")
        elif want is not None and v != want:
            r.add("D12 必須環境変数", "NG", k, "有・期待値と不一致")
        else:
            r.add("D12 必須環境変数", "OK", k, "有・期待値一致" if want is not None else "有")
    if os.environ.get(GH_ENV):
        r.add("D12 必須環境変数", "OK", GH_ENV, "有")
        return
    gh = shutil.which("gh")
    rc = run([gh, "auth", "status"], root)[0] if gh else 127
    r.add("D12 必須環境変数", "OK" if rc == 0 else "NG", f"{GH_ENV} / gh auth status",
          "gh auth status 成功" if rc == 0 else ("無・gh auth status 失敗" if gh else "無・gh が無い"))


def main() -> int:
    ap = argparse.ArgumentParser(description="キットの部品がこの環境で動くかを診る（読むだけのスナップショット）")
    ap.add_argument("--root", default=str(KIT))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--home", nargs="?", const=str(Path.home()), default=None,
                    help="D9 で <HOME>/.claude/rules/aidd-kit とも比べる。D10 の既定 settings もここから探す")
    ap.add_argument("--settings", action="append", default=None, help="D10 で読む settings / hooks.json（複数可）")
    ap.add_argument("--write-manifest", action="store_true", help="保守者用: rules-manifest.json を書き直して終わる")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if a.write_manifest:
        print(f"書いた: {write_manifest(root)}")
        return 0
    r = diagnose(root, Path(a.home).expanduser() if a.home else None,
                 [Path(x).expanduser() for x in a.settings] if a.settings else None)
    taken = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    summary = {s: r.count(s) for s in ("OK", "WARN", "NG", "SKIP")}
    if a.json:
        print(json.dumps({
            "snapshot": True,
            "note": "実行した時点のスナップショット。常駐・定期実行はしない。ファイルは書かない",
            "taken_at": taken, "root": str(root), "platform": platform.platform(),
            "python": sys.version.split()[0], "summary": summary, "items": r.items,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"doctor: {root}（{taken} 時点のスナップショット。読むだけ・常駐しない）")
        for i in r.items:
            if i["status"] != "OK":
                print(f"{i['status']:<4} {i['check']}  {i['target']}  {i['detail']}")
        print("| 状態 | 項目 | 対象 | 詳細 |")
        print("|---|---|---|---|")
        for i in r.items:
            if i["check"].split()[0] in ("D9", "D10", "D11", "D12"):
                print(f"| {i['status']} | {i['check']} | {i['target']} | {i['detail']} |")
        print(f"{'NG' if summary['NG'] else 'OK'}: OK={summary['OK']} WARN={summary['WARN']} "
              f"NG={summary['NG']} SKIP={summary['SKIP']}（全件は --json）")
        print("全緑" if not summary["NG"] else f"赤（NG={summary['NG']}）")
    return 1 if summary["NG"] else 0


if __name__ == "__main__":
    sys.exit(main())
