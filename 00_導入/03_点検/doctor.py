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

使い方: python3 00_導入/03_点検/doctor.py [--root DIR] [--json]
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
import subprocess
import sys
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


def diagnose(root: Path) -> Report:
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
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="キットの部品がこの環境で動くかを診る（読むだけのスナップショット）")
    ap.add_argument("--root", default=str(KIT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    r = diagnose(root)
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
        print(f"{'NG' if summary['NG'] else 'OK'}: OK={summary['OK']} WARN={summary['WARN']} "
              f"NG={summary['NG']} SKIP={summary['SKIP']}（全件は --json）")
    return 1 if summary["NG"] else 0


if __name__ == "__main__":
    sys.exit(main())
