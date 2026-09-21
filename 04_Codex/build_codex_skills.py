#!/usr/bin/env python3
"""03_ClaudeCode の skills/ と commands/ から Codex 用スキル（04_Codex/skills/）を生成する。

Codex の仕様（出典: https://learn.chatgpt.com/codex/build-skills）:
  - `<名前>/SKILL.md`（frontmatter の name・description が必須）、任意で `agents/openai.yaml`
  - スキルはスラッシュメニューに並び、`$名前` で明示的に呼び出せる
カスタムプロンプトの置き場所は公式ドキュメントで確認できないため、commands/ もスキルに変換する。

使い方: python3 04_Codex/build_codex_skills.py          # 生成
        python3 04_Codex/build_codex_skills.py --check  # 生成物が最新か検査（差分があれば exit 1）
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SRC_SKILLS = KIT / "03_ClaudeCode" / "skills"
SRC_COMMANDS = KIT / "03_ClaudeCode" / "commands"
OUT = KIT / "04_Codex" / "skills"
FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
HEADER = "<!-- 生成物: 04_Codex/build_codex_skills.py が 03_ClaudeCode/ から生成する。直接編集しない -->\n"


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    return fm, text[m.end():]


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def short(desc: str, limit: int = 60) -> str:
    first = re.split(r"[。.]", desc, maxsplit=1)[0].strip()
    return first if len(first) <= limit else first[: limit - 1] + "…"


def write_skill(dst: Path, name: str, desc: str, body: str, display: str) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {yaml_str(desc)}\n---\n{HEADER}{body.lstrip()}", encoding="utf-8")
    (dst / "agents").mkdir(exist_ok=True)
    (dst / "agents" / "openai.yaml").write_text(
        f"display_name: {yaml_str(display)}\nshort_description: {yaml_str(short(desc))}\n"
        "allow_implicit_invocation: true\n", encoding="utf-8")


def build(out: Path) -> int:
    if out.exists():
        shutil.rmtree(out)
    n = 0
    for src in sorted(p for p in SRC_SKILLS.iterdir() if (p / "SKILL.md").is_file()):
        fm, body = frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
        name = fm.get("name", src.name)
        dst = out / src.name
        write_skill(dst, name, fm.get("description", ""), body, name)
        for sub in sorted(src.iterdir()):  # references/・scripts/ などはそのまま写す
            if sub.name == "SKILL.md" or sub.name.startswith(".") or sub.name == "__pycache__":
                continue
            if sub.is_dir():
                shutil.copytree(sub, dst / sub.name, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
            else:
                shutil.copy2(sub, dst / sub.name)
        n += 1
    for cmd in sorted(SRC_COMMANDS.glob("*.md")):
        text = cmd.read_text(encoding="utf-8")
        fm, body = frontmatter(text)
        title = next((l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#")), cmd.stem)
        desc = fm.get("description") or title
        body = ("コマンド `/" + cmd.stem + "` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。\n\n" + body)
        write_skill(out / f"cmd-{cmd.stem}", f"cmd-{cmd.stem}", desc if desc.startswith("/") else f"/{cmd.stem} 相当: {desc}", body, f"/{cmd.stem}")
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.check:
        print(f"生成: {build(OUT)} 件 → {OUT.relative_to(KIT)}")
        return 0
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t) / "skills"
        build(tmp)
        a_files = {p.relative_to(tmp): p.read_bytes() for p in tmp.rglob("*") if p.is_file()}
        b_files = {p.relative_to(OUT): p.read_bytes() for p in OUT.rglob("*") if p.is_file() and p.name != ".DS_Store"} if OUT.exists() else {}
    diff = sorted(str(k) for k in a_files.keys() ^ b_files.keys()) + sorted(str(k) for k in a_files.keys() & b_files.keys() if a_files[k] != b_files[k])
    if diff:
        print(f"NG: 04_Codex/skills が古い（{len(diff)} 件）。python3 04_Codex/build_codex_skills.py で再生成: " + ", ".join(diff[:5]))
        return 1
    print(f"OK: 04_Codex/skills は最新（{len(a_files)} ファイル）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
