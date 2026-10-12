#!/usr/bin/env python3
"""skill-lint.py — SKILL.md の frontmatter と、Codex 版（04_Codex/skills/*/agents/openai.yaml）との対応を検査する（キット自身用・読むだけ）。

skill-scan.py は「危険な中身」を見る走査器。こちらは「スキルとして正しく発火・非発火するか」の形を見る。
check_docs.py 検査5（name ↔ ディレクトリ名・description ≦1024字・「」発火語）と同じ上限を使い、
加えて Claude Code で自動発火を止めたスキル（`disable-model-invocation: true`）が Codex 側で暗黙に発火しないかを突き合わせる。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。YAML ライブラリは使わず、1 行の `key: value` だけを読む。

検査（スキルのディレクトリごと）:
  S1 frontmatter   `---` で始まる frontmatter が無い                                                   NG
  S2 name          name が無い・ディレクトリ名と違う                                                      NG
  S3 description   無い・空                                                                                NG
  S4 長さ          description が DESC_MAX（1024 字。check_docs.py と同じ）を超える                        NG
                   DESC_WARN（500 字）を超える（毎セッション一覧に載る分のトークン。要約を先頭に寄せる）     WARN
  S5 値            `disable-model-invocation`・`user-invocable` が true/false 以外                          NG
  S6 未知のキー    KNOWN_KEYS に無いキー（綴り違いで効かない設定に気づく）                                  WARN
  S7 Codex 対応    disable-model-invocation: true なのに openai.yaml の allow_implicit_invocation が false でない NG
                   逆に、自動発火を許すスキルが allow_implicit_invocation: false                            WARN
                   Codex 版のディレクトリ・openai.yaml が無い（build_codex_skills.py で再生成）              WARN
                   openai.yaml に allow_implicit_invocation が無いときは S7 の照合をしない（項目が無い形式）

使い方: python3 02_共通/ツール/skill-lint.py [--skills DIR] [--codex DIR] [--json]
  既定: --skills <キット>/03_ClaudeCode/skills  --codex <キット>/04_Codex/skills（無ければ Codex 照合を飛ばす）
終了コード: 0=NG なし / 1=NG あり / 2=スキルのディレクトリが無い
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[2]
DESC_MAX = 1024
DESC_WARN = 500
FM_RE = re.compile(r"\A﻿?---\r?\n(.*?)\r?\n---\r?\n", re.S)
BOOL_KEYS = ("disable-model-invocation", "user-invocable")
KNOWN_KEYS = {
    "name", "description", "allowed-tools", "disable-model-invocation", "user-invocable", "model",
    "argument-hint", "license", "metadata", "when_to_use", "context", "agent", "hooks", "paths", "effort",
    "version", "compatibility",
}


def parse_frontmatter(text: str) -> dict[str, str] | None:
    m = FM_RE.match(text)
    if not m:
        return None
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-", "#")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def yaml_bool(path: Path, key: str) -> bool | None:
    """1 行の `key: true|false` を読む。項目が無ければ None。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(rf"^\s*{re.escape(key)}\s*:\s*(\S+)", text, re.M)
    if not m:
        return None
    return m.group(1).strip("\"'").lower() == "true"


def lint(skills: Path, codex: Path | None) -> tuple[list[str], list[str], int]:
    ng: list[str] = []
    warn: list[str] = []
    dirs = sorted(d for d in skills.iterdir() if d.is_dir() and (d / "SKILL.md").is_file())
    for d in dirs:
        where = f"{d.name}/SKILL.md"
        fm = parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8", errors="replace"))
        if fm is None:
            ng.append(f"S1 {where}: frontmatter（--- で囲んだ先頭）が無い")
            continue
        name = fm.get("name", "")
        if not name:
            ng.append(f"S2 {where}: name が無い")
        elif name != d.name:
            ng.append(f"S2 {where}: name「{name}」がディレクトリ名「{d.name}」と違う")
        desc = fm.get("description", "")
        if not desc:
            ng.append(f"S3 {where}: description が無い・空")
        elif len(desc) > DESC_MAX:
            ng.append(f"S4 {where}: description が {len(desc)} 字 > {DESC_MAX}")
        elif len(desc) > DESC_WARN:
            warn.append(f"S4 {where}: description が {len(desc)} 字 > {DESC_WARN}（毎セッションの一覧に載る。要約を先頭に）")
        for k in BOOL_KEYS:
            if k in fm and fm[k].lower() not in ("true", "false"):
                ng.append(f"S5 {where}: {k} は true/false（実際: {fm[k]}）")
        for k in sorted(set(fm) - KNOWN_KEYS):
            warn.append(f"S6 {where}: 未知のキー `{k}`（綴り違いなら効いていない）")
        if codex is None:
            continue
        yml = codex / d.name / "agents" / "openai.yaml"
        if not yml.is_file():
            warn.append(f"S7 {d.name}: Codex 版 {yml.relative_to(codex.parent).as_posix()} が無い（build_codex_skills.py で再生成）")
            continue
        implicit = yaml_bool(yml, "allow_implicit_invocation")
        if implicit is None:
            continue
        disabled = fm.get("disable-model-invocation", "").lower() == "true"
        if disabled and implicit:
            ng.append(f"S7 {d.name}: disable-model-invocation: true なのに Codex の allow_implicit_invocation が true（Codex では自動発火する）")
        elif not disabled and not implicit:
            warn.append(f"S7 {d.name}: Claude Code では自動発火するのに Codex の allow_implicit_invocation が false")
    return ng, warn, len(dirs)


def main() -> int:
    ap = argparse.ArgumentParser(description="SKILL.md の frontmatter と Codex 版の対応を検査する")
    ap.add_argument("--skills", default=str(KIT / "03_ClaudeCode" / "skills"))
    ap.add_argument("--codex", default=str(KIT / "04_Codex" / "skills"), help="Codex 版スキルの置き場所（'' で照合しない）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    skills = Path(a.skills)
    if not skills.is_dir():
        print(f"判定不能: スキルのディレクトリが無い: {skills}", file=sys.stderr)
        return 2
    codex = Path(a.codex) if a.codex and Path(a.codex).is_dir() else None
    ng, warn, n = lint(skills, codex)
    if a.json:
        print(json.dumps({"skills": n, "codex_checked": codex is not None, "ng": ng, "warn": warn},
                         ensure_ascii=False, indent=2))
    else:
        for r in ng:
            print(f"NG  {r}")
        for r in warn:
            print(f"WARN {r}")
        print(f"{'NG' if ng else 'OK'}: スキル {n} 件・NG={len(ng)} WARN={len(warn)}"
              f"（Codex 照合: {'あり' if codex else 'なし'}）")
    return 1 if ng else 0


if __name__ == "__main__":
    sys.exit(main())
