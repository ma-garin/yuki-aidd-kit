#!/usr/bin/env python3
"""check-layers.py — 共通層（02_共通/）が Claude Code 専用層・Codex 専用層に依存していないかを検査する（キット自身用・読むだけ）。

層の向き（INDEX.md「配置」）: 03_ClaudeCode/・04_Codex/ は 02_共通/ を使ってよいが、逆は不可。
02_共通/ は Claude Code と Codex の両方へ配られ（rules は .claude/rules/、ツールは <対象>/scripts/）、
片方にしか無い物を前提に書くと、もう片方（git も bash も無い Windows の Codex を含む）で黙って壊れる。

規則（02_共通/ 配下のテキストファイルを行単位で見る）:
  L1 キット内の専用層パス   `03_ClaudeCode/`・`04_Codex/` を名指しする（配布先には存在しないパス）            NG
  L2 Claude Code 専用の実体 `.claude/hooks/`・`~/.claude/hooks/`・`hooks/<名前>.py|sh`（Codex に hook は無い）       NG
  L3 Codex 専用の実体       `.codex/`・`agents/openai.yaml`                                                     NG
  L4 片側だけの指示書名     `CLAUDE.md` を書いているのに同じファイルに `AGENTS.md` が無い（Codex が読む先が無い）  WARN
  `skills/<名前>/` は両方にある（Codex 版は 04_Codex/build_codex_skills.py が生成）ので対象外。

キット自身を検査する道具（KIT_SELF。配布しない・キットの checkout でだけ動く）は L1〜L3 の対象外。
基準線（BASELINE）: 導入時点で既にあった参照は下の表に「規則・相対パス・一致した語」で載せ、NG に数えない（直すのは別作業）。
表に無い新しい参照だけを NG にする。表にあって今は無いものは「基準線から外せる」と出す（件数は減る方向だけ）。
標準ライブラリのみ・Python 3.9 互換・ネット不使用。

使い方: python3 02_共通/ツール/check-layers.py [--root DIR] [--json] [--no-baseline]
終了コード: 0=新しい違反なし / 1=新しい違反あり / 2=02_共通/ が無い
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULES = (
    ("L1", re.compile(r"(?:03_ClaudeCode|04_Codex)(?:/[^\s`'\")|,]*)?")),
    ("L2", re.compile(r"(?:~/)?\.claude/hooks/[^\s`'\")|,]*|(?<![\w./-])hooks/[\w.-]+\.(?:py|sh)\b")),
    ("L3", re.compile(r"(?<![\w-])\.codex/[^\s`'\")|,]*|agents/openai\.yaml")),
)
TEXT_EXT = {".md", ".py", ".sh", ".txt", ".json", ".yml", ".yaml", ".toml", ".css", ".js", ".html", ".csv", ""}
SKIP_PARTS = {"__pycache__", ".git", "node_modules"}

# キットの checkout でだけ動き、配布しない（export-project.sh・install.sh の同梱一覧に無い）道具。専用層を読むのが仕事
KIT_SELF = {
    "02_共通/ツール/check-layers.py",
    "02_共通/ツール/check-version.py",
    "02_共通/ツール/skill-lint.py",
    "02_共通/ツール/llms-txt.py",
}

# 導入時点（8.6.0＋未リリース分）の既存参照。直さずに基準線として固定する（増やさない）。
BASELINE = {
    # cite-check.py: キット内パスの接頭辞の一覧（引用の判定用。専用層を前提にした処理ではない）
    ("L1", "02_共通/ツール/cite-check.py", "03_ClaudeCode/"),
    ("L1", "02_共通/ツール/cite-check.py", "04_Codex/"),
    # req-lint.py: 曖昧語辞書の探索先（キットの checkout で動くときだけの候補。配布先は隣の references/ を先に見る）
    ("L1", "02_共通/ツール/req-lint.py", "03_ClaudeCode/skills/sdd-ecc-workflow/references/"),
    ("L1", "02_共通/ツール/req-lint.py", "03_ClaudeCode"),
    # skill-scan.py: secret_patterns.py の探索先（無ければ U05 で判定不能に落とす）
    ("L1", "02_共通/ツール/skill-scan.py", "03_ClaudeCode/hooks/secret_patterns.py"),
    ("L1", "02_共通/ツール/skill-scan.py", "03_ClaudeCode"),
    # absolute-rules.md A-2: 実測の取り方として tool-timer.py を名指し（Codex 側は「未計測」と書く運用）
    ("L2", "02_共通/rules/absolute-rules.md", "hooks/tool-timer.py"),
}


def scan(root: Path) -> tuple[list[tuple[str, str, int, str]], list[tuple[str, str]]]:
    hits: list[tuple[str, str, int, str]] = []
    warns: list[tuple[str, str]] = []
    base = root / "02_共通"
    for f in sorted(base.rglob("*")):
        if not f.is_file() or f.suffix not in TEXT_EXT or set(f.relative_to(root).parts) & SKIP_PARTS:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = f.relative_to(root).as_posix()
        if rel in KIT_SELF:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            for rule, rx in RULES:
                for m in rx.finditer(line):
                    hits.append((rule, rel, i, m.group(0)))
        if "CLAUDE.md" in text and "AGENTS.md" not in text:
            warns.append(("L4", rel))
    return hits, warns


def main() -> int:
    ap = argparse.ArgumentParser(description="02_共通/ から専用層への逆向きの参照を検査する")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-baseline", action="store_true", help="基準線を使わず全件を NG に数える")
    a = ap.parse_args()
    root = Path(a.root)
    if not (root / "02_共通").is_dir():
        print(f"判定不能: {root}/02_共通 が無い", file=sys.stderr)
        return 2
    hits, warns = scan(root)
    baseline = set() if a.no_baseline else BASELINE
    new = [h for h in hits if (h[0], h[1], h[3]) not in baseline]
    known = [h for h in hits if (h[0], h[1], h[3]) in baseline]
    present = {(h[0], h[1], h[3]) for h in hits}
    stale = sorted(b for b in baseline if b not in present)
    if a.json:
        print(json.dumps({
            "ok": not new,
            "ng": [{"rule": r, "file": f, "line": l, "match": m} for r, f, l, m in new],
            "baseline": [{"rule": r, "file": f, "line": l, "match": m} for r, f, l, m in known],
            "baseline_removable": [{"rule": r, "file": f, "match": m} for r, f, m in stale],
            "warn": [{"rule": r, "file": f} for r, f in warns],
        }, ensure_ascii=False, indent=2))
        return 1 if new else 0
    for r, f, l, m in new:
        print(f"NG  {r} {f}:{l} {m}")
    for r, f in warns:
        print(f"WARN {r} {f}: CLAUDE.md だけを書いている（AGENTS.md も併記する）")
    for r, f, m in stale:
        print(f"INFO 基準線から外せる: {r} {f} {m}")
    print(f"{'NG' if new else 'OK'}: 新しい違反 {len(new)} 件・基準線 {len(known)} 件・WARN {len(warns)} 件"
          "（02_共通/ → 03_ClaudeCode/・04_Codex/ の逆向き参照）")
    return 1 if new else 0


if __name__ == "__main__":
    sys.exit(main())
