#!/usr/bin/env python3
"""token_audit.py — トークン節約の仕組みが効いているかを機械で点検する（手動実行）。

キット本体でも配布先プロジェクトでも動く。会話には結論だけ（3 層要約）、全件は token-audit-report.md。
NG>0 で exit 1、WARN のみは exit 0。

  1. 床（常時読み込み）  rules/*.md（paths 無し）＋ CLAUDE.md（@AGENTS.md 展開）の文字数と推定トークン。
                          換算は spec/11 D-1（日本語 1.0 tok/char・ASCII 0.27 tok/char）。**推定**であり実測は /context
  2. 実測ログ            .claude/instructions-loaded.log（log-instructions.py）があればファイル別の読み込み回数
  3. 仕組みの配線        settings.json に filter-output / pre-read-guard / context-guard / pre-compact が配線されているか、
                          effortLevel / autoCompactWindow / BASH_MAX_OUTPUT_LENGTH があるか（無ければ NG）
  4. MCP                 .mcp.json / settings の mcpServers の数。MCP_WARN_COUNT（既定 3）超で WARN（CLI で代替できないか）
  5. スキルの肥大        SKILL.md が SKILL_WARN_LINES（既定 150）超で WARN（check-docs.sh の 200 行 NG より手前で気づく）
  6. 手元でしか測れないもの  /context /usage /doctor のコマンドを印字するだけ

使い方: python3 scripts/token_audit.py [--root DIR] [-o REPORT]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

HOOKS_REQUIRED = ("filter-output.py", "pre-read-guard.py", "context-guard.py", "pre-compact.py")
SETTINGS_REQUIRED = ("effortLevel", "autoCompactWindow")
ENV_REQUIRED = ("BASH_MAX_OUTPUT_LENGTH",)
FLOOR_WARN_TOKENS = 8000        # spec/11 D-1: M16 後の床 ≒ 5,400。超えたら WARN
MCP_WARN_COUNT = 3
SKILL_WARN_LINES = 150
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.M)


class Result:
    def __init__(self) -> None:
        self.ng: list[tuple[str, str, str]] = []
        self.warn: list[tuple[str, str, str]] = []
        self.info: list[str] = []

    def add(self, is_ng: bool, kind: str, target: str, detail: str) -> None:
        (self.ng if is_ng else self.warn).append((kind, target, detail))


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def est_tokens(text: str) -> int:
    ja = sum(1 for c in text if ord(c) > 0x2E7F)
    other = len(text) - ja
    return int(ja * 1.0 + other * 0.27)


def has_paths_frontmatter(p: Path) -> bool:
    lines = read(p).splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for l in lines[1:20]:
        if l.strip() == "---":
            return False
        if l.strip().startswith("paths:"):
            return True
    return False


def expand_imports(p: Path) -> str:
    """CLAUDE.md の @path import を展開する（起動時に展開されるので床に含める）。"""
    text = read(p)
    for m in IMPORT_RE.finditer(text):
        target = (p.parent / m.group(1)).resolve()
        if not target.is_file() and target.with_name(target.name + ".template").is_file():
            target = target.with_name(target.name + ".template")     # キット本体では AGENTS.md.template
        if target.is_file():
            text = text.replace(m.group(0), read(target), 1)
    return text


def floor_files(root: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for d in ("rules", ".claude/rules"):
        for f in sorted((root / d).glob("*.md")):
            if not has_paths_frontmatter(f):
                out.append((f"{d}/{f.name}（常時）", f))
    for name in ("CLAUDE.md", "CLAUDE.md.template"):
        f = root / name
        if f.is_file():
            out.append((name, f))
            break
    return out


def check_floor(root: Path, r: Result) -> int:
    total = 0
    rows = []
    for label, f in floor_files(root):
        text = expand_imports(f) if f.name.startswith("CLAUDE.md") else read(f)
        t = est_tokens(text)
        total += t
        rows.append(f"{label}: {len(text)} 文字 ≒ {t} tok")
    r.info.append("床（推定）: " + " / ".join(rows) + f" → 合計 ≒ {total} tok")
    if total > FLOOR_WARN_TOKENS:
        r.add(False, "床", "常時読み込み", f"推定 {total} tok > {FLOOR_WARN_TOKENS}。rules を paths 付きにするか references へ逃がす")
    return total


def check_loaded_log(root: Path, r: Result) -> None:
    for d in (root / ".claude", Path.home() / ".claude"):
        log = d / "instructions-loaded.log"
        if log.is_file():
            c: Counter[str] = Counter()
            for line in read(log).splitlines():
                try:
                    data = json.loads(line.split("\t", 1)[1])
                except (IndexError, ValueError):
                    continue
                path = next((v for k, v in data.items() if "path" in k.lower() and isinstance(v, str)), "?")
                c[path] += 1
            top = ", ".join(f"{Path(k).name}×{n}" for k, n in c.most_common(6))
            r.info.append(f"実測ログ {log}: {sum(c.values())} 件（{top}）")
            return
    r.info.append("実測ログ無し（log-instructions.py が InstructionsLoaded で書く。セッションを回すと溜まる）")


def load_settings(root: Path) -> tuple[dict, Path | None]:
    # キット本体（claude-code/hooks/settings.json がある形）では配布形の settings を見る。キット自身の .claude/settings.json は
    # 開発セッション用の一部配線（instruction-guard 等）だけなので、床・配線の判定対象にしない
    for c in (root / "claude-code/hooks/settings.json", root / ".claude/settings.json", Path.home() / ".claude/settings.json"):
        if c.is_file():
            try:
                return json.loads(read(c)), c
            except ValueError:
                return {}, c
    return {}, None


def check_wiring(root: Path, r: Result) -> None:
    s, path = load_settings(root)
    if path is None:
        r.add(True, "配線", "settings.json", "見つからない（.claude/settings.json / claude-code/hooks/settings.json / ~/.claude/settings.json）")
        return
    blob = json.dumps(s, ensure_ascii=False)
    for h in HOOKS_REQUIRED:
        if h not in blob:
            r.add(True, "配線", path.name, f"{h} が hooks に配線されていない")
    for k in SETTINGS_REQUIRED:
        if k not in s:
            r.add(True, "配線", path.name, f"{k} が無い")
    for k in ENV_REQUIRED:
        if k not in (s.get("env") or {}):
            r.add(True, "配線", path.name, f"env.{k} が無い")
    r.info.append(f"settings: {path}（effortLevel={s.get('effortLevel')} autoCompactWindow={s.get('autoCompactWindow')} "
                  f"BASH_MAX_OUTPUT_LENGTH={(s.get('env') or {}).get('BASH_MAX_OUTPUT_LENGTH')}）")


def check_mcp(root: Path, r: Result) -> None:
    n = 0
    names: list[str] = []
    for c in (root / ".mcp.json", root / ".claude/settings.json", Path.home() / ".claude/settings.json", Path.home() / ".claude.json"):
        if c.is_file():
            try:
                d = json.loads(read(c))
            except ValueError:
                continue
            srv = d.get("mcpServers") or {}
            names += list(srv.keys())
    n = len(set(names))
    r.info.append(f"MCP サーバ: {n} 個" + (f"（{', '.join(sorted(set(names)))}）" if names else ""))
    if n > MCP_WARN_COUNT:
        r.add(False, "MCP", "mcpServers", f"{n} 個 > {MCP_WARN_COUNT}。CLI（gh / aws 等）で代替できるものは無効化する（1 MCP ≒ 数千 tok）")


def check_skills(root: Path, r: Result) -> None:
    for d in ("skills", ".claude/skills"):
        for f in sorted((root / d).glob("*/SKILL.md")):
            n = len(read(f).splitlines())
            if n > SKILL_WARN_LINES:
                r.add(False, "スキル肥大", f"{d}/{f.parent.name}/SKILL.md", f"{n} 行 > {SKILL_WARN_LINES}（発火時のコスト。references へ逃がす）")


def write_report(path: Path, root: Path, r: Result) -> None:
    lines = ["# トークン監査レポート", "", f"- 対象: `{root}`", f"- NG: {len(r.ng)} 件 ／ 警告: {len(r.warn)} 件",
             "- 規約: `rules/model-routing.md` ／ 根拠: `docs/rules-rationale/model-routing.md` ／ 一次情報: `spec/11` §2", "",
             "## 計測", ""] + [f"- {i}" for i in r.info]
    lines += ["", "## NG 一覧", ""]
    lines += (["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.ng]) if r.ng else ["なし。"]
    lines += ["", "## 警告", ""]
    lines += (["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.warn]) if r.warn else ["なし。"]
    lines += ["", "## 手元でしか測れないもの（Claude Code で実行）", "",
              "- `/context` — 実際にロードされた指示ファイルと内訳（上の「床」は推定。ここで実測に置き換える）",
              "- `/usage` — スキル・サブエージェント・MCP 別の消費、キャッシュミス・長コンテキストのフラグ",
              "- `/doctor` — CLAUDE.md の削減案"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="トークン節約の仕組みの点検")
    ap.add_argument("--root", default=".")
    ap.add_argument("-o", "--report", default="token-audit-report.md")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    r = Result()
    total = check_floor(root, r)
    check_loaded_log(root, r)
    check_wiring(root, r)
    check_mcp(root, r)
    check_skills(root, r)
    report = Path(a.report)
    if not report.is_absolute():
        report = root / report
    write_report(report, root, r)

    print(f"=== トークン監査: {root} ===")
    print(f"床（常時読み込み・推定）≒ {total} tok（実測は /context）")
    if r.ng:
        kinds: dict[str, int] = {}
        for k, _, _ in r.ng:
            kinds[k] = kinds.get(k, 0) + 1
        print(f"❌ NG={len(r.ng)}")
        for k, n in kinds.items():
            print(f"  - {k}: {n} 件")
        print("  例（先頭5件）:")
        for k, t, d in r.ng[:5]:
            print(f"    {k}: {t} — {d}")
    else:
        print("✅ NG=0（絞る hook 4 本と設定 3 キーが配線済み）")
    if r.warn:
        print(f"⚠ 警告 {len(r.warn)} 件（" + ", ".join(sorted({k for k, _, _ in r.warn})) + "。詳細はレポート）")
    print("次: Claude Code で /context と /usage を実行し、推定を実測に置き換える")
    print(f"詳細: {report}")
    return 1 if r.ng else 0


if __name__ == "__main__":
    sys.exit(main())
