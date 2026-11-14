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
  D9 外部スキル     00_導入/01_インストール/external-skills.json と ~/.agents/skills・~/.claude/skills・
                   ~/.codex/skills の現物を突き合わせる。マニフェストが無い・読めない＝NG／置き場が 3 つとも無い＝SKIP／
                   差分（未登録・欠落・sha256 不一致・retired の残存・リンク切れ）はすべて WARN（導入前の PC を NG にしない）。
                   kit が配る名前（03_ClaudeCode/skills・04_Codex/skills・04_Codex/native-skills）は外部に数えない
                   （ただしマニフェストにある名前は外部として検査する）。集計行に「検査 n 件／マニフェスト m 件」を必ず出す

使い方: python3 00_導入/03_点検/doctor.py [--root DIR] [--home DIR] [--json]
終了コード: 0=NG なし / 1=NG あり
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
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


def diagnose(root: Path, home: "str | Path | None" = None) -> Report:
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
    check_external_skills(r, root, Path(home) if home else Path.home())
    return r


SKILL_LOCS = (("agents", (".agents", "skills")), ("claude", (".claude", "skills")), ("codex", (".codex", "skills")))
D9 = "D9 外部スキル"


def tree_sha256(d: Path) -> str:
    """04_Codex/build_codex_skills.py の skills-manifest と同じ算出法（相対パス＋NUL＋中身＋NUL を昇順に連結）。"""
    h = hashlib.sha256()
    files = sorted(f for f in d.rglob("*") if f.is_file() and f.name != ".DS_Store" and "__pycache__" not in f.parts)
    for f in sorted(files, key=lambda f: f.relative_to(d).as_posix()):
        h.update(f.relative_to(d).as_posix().encode("utf-8") + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def kit_skill_names(root: Path) -> set:
    names: set = set()
    for parts in (("03_ClaudeCode", "skills"), ("04_Codex", "skills"), ("04_Codex", "native-skills")):
        d = root.joinpath(*parts)
        if d.is_dir():
            names |= {c.name for c in d.iterdir() if c.is_dir()}
    return names


def check_external_skills(r: Report, root: Path, home: Path) -> None:
    mpath = root / "00_導入" / "01_インストール" / "external-skills.json"
    target = rel(mpath, root)
    try:
        doc = json.loads(mpath.read_text(encoding="utf-8"))
        manifest = doc["skills"]
        if not isinstance(manifest, dict):
            raise ValueError("skills がオブジェクトでない")
    except (OSError, ValueError, KeyError, TypeError) as e:
        r.add(D9, "NG", target, f"マニフェストが読めない（{type(e).__name__}: {e}）")
        return
    ignored = set(doc.get("ignored") or [])
    retired = set(doc.get("retired") or [])
    locs = [(k, home.joinpath(*p)) for k, p in SKILL_LOCS if home.joinpath(*p).is_dir()]
    if not locs:
        r.add(D9, "SKIP", target, f"置き場が無い（{home} 配下の .agents/.claude/.codex の skills）／マニフェスト {len(manifest)} 件")
        return
    kit = kit_skill_names(root) - set(manifest)
    present: dict = {}   # 名前 → [(置き場, パス)]
    for k, base in locs:
        for c in base.iterdir():
            if c.name.startswith(".") and c.name not in ignored or c.name in ignored or c.name in kit:
                continue
            if c.is_dir() or c.is_symlink():
                present.setdefault(c.name, []).append((k, c))
    diffs = []
    for name in sorted(set(present) | set(manifest)):
        where = present.get(name, [])
        for k, c in where:
            if c.is_symlink() and not c.exists():
                diffs.append((f"{k}/{name}", "リンク切れ"))
        live = [(k, c) for k, c in where if c.exists()]
        if name in retired and live:
            diffs.append((name, "退役済み（retired）の名前が環境に戻っている"))
            continue
        entry = manifest.get(name)
        if entry is None:
            if live:
                diffs.append((name, "環境にあるがマニフェストに無い外部スキル"))
            continue
        have = {k for k, _ in live}
        missing = [k for k in entry.get("locations", []) if k not in have]
        if missing:
            diffs.append((name, "マニフェストの置き場に無い: " + ", ".join(missing)))
        if live and entry.get("sha256"):
            order = {"agents": 0, "claude": 1, "codex": 2}
            first = sorted(live, key=lambda x: order.get(x[0], 9))[0][1]
            if tree_sha256(first) != entry["sha256"]:
                diffs.append((name, "sha256 が一致しない（中身が変わった）"))
    for t, why in diffs:
        r.add(D9, "WARN", t, why)
    r.add(D9, "WARN" if diffs else "OK", target,
          f"検査 {len(set(present) | set(manifest))} 件／マニフェスト {len(manifest)} 件・差分 {len(diffs)} 件")


def main() -> int:
    ap = argparse.ArgumentParser(description="キットの部品がこの環境で動くかを診る（読むだけのスナップショット）")
    ap.add_argument("--root", default=str(KIT))
    ap.add_argument("--home", default=None, help="スキルの置き場を探すホーム（既定: このユーザーのホーム）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    r = diagnose(root, a.home)
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
            if i["status"] != "OK" or i["check"] == D9:  # D9 は検査件数を必ず見せる
                print(f"{i['status']:<4} {i['check']}  {i['target']}  {i['detail']}")
        print(f"{'NG' if summary['NG'] else 'OK'}: OK={summary['OK']} WARN={summary['WARN']} "
              f"NG={summary['NG']} SKIP={summary['SKIP']}（全件は --json）")
    return 1 if summary["NG"] else 0


if __name__ == "__main__":
    sys.exit(main())
