#!/usr/bin/env python3
"""Claude Code の skills/・commands/ と Codex native-skills/ から配布用スキルを生成する。

Codex の仕様（出典: https://learn.chatgpt.com/codex/build-skills）:
  - `<名前>/SKILL.md`（frontmatter の name・description が必須）、任意で `agents/openai.yaml`
  - スキルはスラッシュメニューに並び、`$名前` で明示的に呼び出せる
カスタムプロンプトの置き場所は公式ドキュメントで確認できないため、commands/ もスキルに変換する。

`disable-model-invocation: true` のスキルは agents/openai.yaml の allow_implicit_invocation を false にする（明示呼び出しだけ）。

生成と同時に 04_Codex/skills-manifest.json を書く: スキルごとのファイル数と sha256。
sha256 はスキル配下の全ファイルを相対パス（/ 区切り）の昇順に並べ、各ファイルについて
「相対パス（UTF-8）＋NUL＋中身＋NUL」を連結したものの sha256（改名・追加・削除も版に入る）。
版管理の無い Codex 環境でも、受け取ったスキル一式が生成時と同じかを --check で確かめられる。

使い方: python3 04_Codex/build_codex_skills.py          # 生成（skills/ と skills-manifest.json）
        python3 04_Codex/build_codex_skills.py --check  # 生成物とマニフェストが最新か検査（差分があれば exit 1）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SRC_SKILLS = KIT / "03_ClaudeCode" / "skills"
SRC_COMMANDS = KIT / "03_ClaudeCode" / "commands"
NATIVE_SKILLS = KIT / "04_Codex" / "native-skills"
OUT = KIT / "04_Codex" / "skills"
MANIFEST = KIT / "04_Codex" / "skills-manifest.json"
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


def write_skill(dst: Path, name: str, desc: str, body: str, display: str, implicit: bool = True) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {yaml_str(desc)}\n---\n{HEADER}{body.lstrip()}", encoding="utf-8")
    (dst / "agents").mkdir(exist_ok=True)
    (dst / "agents" / "openai.yaml").write_text(
        f"interface:\n  display_name: {yaml_str(display)}\n  short_description: {yaml_str(short(desc))}\n"
        f"policy:\n  allow_implicit_invocation: {'true' if implicit else 'false'}\n", encoding="utf-8")


def build(out: Path) -> int:
    native = sorted(p for p in NATIVE_SKILLS.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()) if NATIVE_SKILLS.is_dir() else []
    sources = sorted(p for p in SRC_SKILLS.iterdir() if (p / "SKILL.md").is_file())
    commands = sorted(SRC_COMMANDS.glob("*.md"))
    generated_names = {p.name for p in sources} | {f"cmd-{p.stem}" for p in commands}
    collisions = sorted(p.name for p in native if p.name in generated_names)
    if collisions:
        raise ValueError("native-skills と生成スキルの名前が衝突: " + ", ".join(collisions))
    if out.exists():
        shutil.rmtree(out)
    n = 0
    for src in sources:
        fm, body = frontmatter((src / "SKILL.md").read_text(encoding="utf-8"))
        name = fm.get("name", src.name)
        dst = out / src.name
        implicit = fm.get("disable-model-invocation", "").lower() != "true"
        write_skill(dst, name, fm.get("description", ""), body, name, implicit)
        for sub in sorted(src.iterdir()):  # references/・scripts/ などはそのまま写す
            if sub.name == "SKILL.md" or sub.name.startswith(".") or sub.name == "__pycache__":
                continue
            if sub.is_dir():
                shutil.copytree(sub, dst / sub.name, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
            else:
                shutil.copy2(sub, dst / sub.name)
        n += 1
    for cmd in commands:
        text = cmd.read_text(encoding="utf-8")
        fm, body = frontmatter(text)
        title = next((l.lstrip("# ").strip() for l in body.splitlines() if l.startswith("#")), cmd.stem)
        desc = fm.get("description") or title
        body = ("コマンド `/" + cmd.stem + "` の Codex 版。引数は、呼び出し時にユーザーが続けて書いた文を `$ARGUMENTS` として読む。\n\n" + body)
        write_skill(out / f"cmd-{cmd.stem}", f"cmd-{cmd.stem}", desc if desc.startswith("/") else f"/{cmd.stem} 相当: {desc}", body, f"/{cmd.stem}")
        n += 1
    for src in native:
        shutil.copytree(src, out / src.name, ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
        n += 1
    return n


def skill_files(skills: Path) -> dict[str, dict[str, bytes]]:
    """スキル名 → {相対パス: 中身}。.DS_Store・__pycache__ は数えない。"""
    out: dict[str, dict[str, bytes]] = {}
    for d in sorted(p for p in skills.iterdir() if p.is_dir()):
        files = {}
        for f in sorted(d.rglob("*")):
            if f.is_file() and f.name != ".DS_Store" and "__pycache__" not in f.parts:
                files[f.relative_to(d).as_posix()] = f.read_bytes()
        out[d.name] = files
    return out


def manifest(skills: Path) -> dict:
    entries = {}
    for name, files in skill_files(skills).items():
        h = hashlib.sha256()
        for rel in sorted(files):
            h.update(rel.encode("utf-8") + b"\0" + files[rel] + b"\0")
        entries[name] = {"files": len(files), "sha256": h.hexdigest()}
    return {"generator": "04_Codex/build_codex_skills.py", "count": len(entries), "skills": entries}


def write_manifest(skills: Path, path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fp:
        json.dump(manifest(skills), fp, ensure_ascii=False, indent=2, sort_keys=True)
        fp.write("\n")


def check_manifest(skills: Path, path: Path) -> list[str]:
    """生成し直したスキル一式とマニフェストが食い違うスキル名を返す（読めなければその旨）。"""
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"skills-manifest.json を読めない（{type(e).__name__}）"]
    want = manifest(skills)["skills"]
    got = saved.get("skills", {}) if isinstance(saved, dict) else {}
    return sorted(k for k in want.keys() | got.keys() if want.get(k) != got.get(k))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if not a.check:
        n = build(OUT)
        write_manifest(OUT, MANIFEST)
        print(f"生成: {n} 件 → {OUT.relative_to(KIT)}（マニフェスト {MANIFEST.relative_to(KIT)}）")
        return 0
    mdiff = check_manifest(OUT, MANIFEST) if OUT.is_dir() else ["04_Codex/skills が無い"]
    if not SRC_SKILLS.is_dir():  # 生成元の無い配布先（Codex）: 手元の skills/ とマニフェストの照合だけ
        if mdiff:
            print(f"NG: 04_Codex/skills がマニフェストと食い違う（{len(mdiff)} 件）: " + ", ".join(mdiff[:5]))
            return 1
        print("OK: 04_Codex/skills はマニフェストと一致（生成元が無いので再生成との比較はしていない）")
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
    if mdiff:
        print(f"NG: 04_Codex/skills-manifest.json が生成物と食い違う（{len(mdiff)} 件）。"
              "python3 04_Codex/build_codex_skills.py で再生成: " + ", ".join(mdiff[:5]))
        return 1
    print(f"OK: 04_Codex/skills は最新（{len(a_files)} ファイル・マニフェスト一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
