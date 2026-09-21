#!/usr/bin/env python3
"""check_docs.py — キット文書の整合をリポジトリ実体と突合する（キット自身用）。

verify.sh は「配置」だけを自動導出していたが、INDEX の参照コスト・README のケース数・
manual の数値は手書きのままで、10 箇所以上が実体からズレていた（06_保守者向け/内部仕様/09-findings.md F-01〜F-03, F-09）。
本スクリプトは次を機械判定する。NG>0 で exit 1（CI でそのまま落とせる）。

  1. 参照コスト   INDEX.md 等の「N行」表記 ↔ 実測 wc -l
  2. 掲載漏れ     skills / commands / rules / hooks が INDEX.md に載っているか
  3. ケース数     「test-X.sh … Nケース」「PASS=N」 ↔ 実際にテストを実行した PASS+FAIL
  4. 参照切れ     `skills/...` 等のキット内相対パス参照が実在するか（ECC 外部・配布先の生成パスは除外）
  5. frontmatter  SKILL.md の name ↔ ディレクトリ名
  6. 常時読込     rules/*.md で paths: frontmatter の無いものの合計行数 ≦ RULES_ALWAYS_MAX
  7. 行数目安     SKILL.md ≦ SKILL_MAX / commands ≦ COMMAND_MAX（05_プロジェクト管理/要求仕様.md 使用性）
  9. 常時読込     03_ClaudeCode/CLAUDE.md.template ＋ 04_Codex/AGENTS.md.template の合計 ≦ CLAUDE_TOTAL_MAX（公式の 200 行目安。@import は展開される）
 10. 件数        README / INDEX / userguide / manual に書かれた「スキル N」「コマンド N」「hooks N」を実数と突合（WARN。直値を書かない）
  8. spec 同期    06_保守者向け/内部仕様/01-inventory.md の行数 ↔ 実測、実ファイルが目録に載っているか

6・7 とも NG（M16 / M17 で昇格済み）。SIZE_STRICT / RULES_STRICT を False に戻すと WARN に降格できる（--strict で NG に戻る）。
出力は context-compression の3層（結論 → 種別ごと → 全件は check-docs-report.md）。

使い方: python3 06_保守者向け/回帰テスト/check_docs.py [--root DIR] [-o REPORT] [--strict] [--skip-tests] [--fix-inventory]
  --fix-inventory: 06_保守者向け/内部仕様/01-inventory.md の行数を実測で書き換えてから検査する（網羅性の不足は手で足す）
  環境変数 CHECK_DOCS_TEST_TOTALS="test-hooks.sh=19,test-trace-check.sh=15" でテスト実行を代替できる（回帰テスト用）。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

# ---- しきい値（RULES_STRICT は M16、SIZE_STRICT は M17 で NG に昇格済み） -------------
RULES_ALWAYS_MAX = 100
CLAUDE_TOTAL_MAX = 200   # 検査9: 03_ClaudeCode/CLAUDE.md.template ＋ 04_Codex/AGENTS.md.template（@import は起動時に展開される）。公式「200 行未満」
SKILL_MAX = 200
COMMAND_MAX = 40
RULES_STRICT = True     # 検査6: S7（M16）で NG に昇格
SIZE_STRICT = True      # 検査7: S13（M17）で NG に昇格済み

# ---- 参照切れ検査の除外 ----------------------------------------------------------------
# ECC（外部キット）のスキル名。実在はこのリポジトリから検証不能（05_プロジェクト管理/要求仕様.md 制約・AUDIT A-08）
ECC_SKILLS = {
    "accessibility", "backend-patterns", "browser-qa", "deep-research", "django-patterns",
    "e2e-testing", "eval-harness", "frontend-patterns", "python-patterns", "python-testing",
    "react-patterns", "security-review", "tdd-workflow", "verification-loop", "vite-patterns",
}
# 配布先プロジェクト側に生成されるパス（init-*.sh / e2e-cycle の既定パス）。キット内には無くて正しい
TARGET_SIDE_PREFIXES = (
    "docs/lifecycle", "docs/test", "docs/quality", "docs/system_test_cases.csv", "docs/odc_analysis.md",
    "docs/plan.md", "docs/index.html", "docs/manifest.json", "docs/lessons.md", "docs/文言変更表.md",
    "quality/", "scripts/pre-commit",  # scripts/pre-commit は実在するが「<project>/scripts/pre-commit」の言及も多い
)
# 参照切れ検査の対象から外すディレクトリ（06_保守者向け/内部仕様/ は計画中の未作成ファイルを正当に参照する）
GENERATED_REPORTS = ("check-docs-report.md", "trace-check-report.md", "check-design-report.md",
                     "check-approval-report.md", "token-audit-report.md", "test-metrics-report.md")
# git 管理外の手元の生成物（.gitignore 対象・ツールの作業ファイル）。目録の網羅性検査に含めない
LOCAL_JUNK_PREFIXES = (".playwright-mcp/", ".claude/settings.local.json")
LOCAL_JUNK_PARTS = (".DS_Store", "__pycache__")


def is_local_junk(rel: str) -> bool:
    return rel.startswith(LOCAL_JUNK_PREFIXES) or any(p in LOCAL_JUNK_PARTS for p in rel.split("/"))


REF_SCAN_EXCLUDE_PREFIXES = ("06_保守者向け/内部仕様/", ".git/", "CHANGELOG.md") + GENERATED_REPORTS  # CHANGELOG は過去の版の旧パスを記録として残す
# 履歴文書（当時の事実を記録しているので数値の突合対象にしない）
HISTORY_DOCS = {"05_プロジェクト管理/ロードマップ.md", "06_保守者向け/AUDIT-2026-07.md"}

ID_LINE_RE = re.compile(r"`([^`]+)`（(\d+)行）")           # 散文の「`x`（N行）」
TABLE_COST_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|.*\|\s*(\d+)行\s*\|\s*$")
BACKTICK_PATH_RE = re.compile(
    r"`((?:skills|templates|scripts|tools|ci|docs|rules|hooks|commands"
    r"|00_導入|01_利用者向け資料|02_共通|03_ClaudeCode|04_Codex|05_プロジェクト管理|06_保守者向け)"
    r"/[A-Za-z0-9_./\-\u3040-\u30ff\u4e00-\u9fff]+)`")
# 配布物の呼び名 → キット内の実体（導入先では .claude/ 配下・scripts/ 配下に置かれる）
ASSET_HOME = {"skills/": "03_ClaudeCode/", "commands/": "03_ClaudeCode/", "hooks/": "03_ClaudeCode/", "rules/": "02_共通/"}
TOOL_HOME = "02_共通/ツール/"   # 導入先の scripts/ に置かれる道具
CASE_RE = re.compile(r"(\d+)\s*ケース")
PASS_RE = re.compile(r"PASS=(\d+)")


class Result:
    def __init__(self) -> None:
        self.ng: list[tuple[str, str, str]] = []    # (種別, 対象, 内容)
        self.warn: list[tuple[str, str, str]] = []

    def add(self, strict_kind: bool, kind: str, target: str, detail: str) -> None:
        (self.ng if strict_kind else self.warn).append((kind, target, detail))


def wc_l(p: Path) -> int:
    with p.open("rb") as f:
        return sum(1 for _ in f)


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def resolve_cost_name(root: Path, name: str) -> Path | None:
    """INDEX の表・散文に出る名前を実ファイルへ解決する。"""
    cands = []
    if name.startswith("/"):
        cands.append(root / "03_ClaudeCode/commands" / f"{name[1:]}.md")
    cands += [
        root / name,
        root / "03_ClaudeCode/skills" / name / "SKILL.md",
        root / "02_共通/rules" / f"{name}.md",
        root / "03_ClaudeCode/hooks" / name,
    ]
    for c in cands:
        if c.is_file():
            return c
    return None


INVENTORY_PREFIXES = (
    "", "02_共通/rules/", "03_ClaudeCode/skills/", "03_ClaudeCode/commands/", "03_ClaudeCode/hooks/", "00_導入/", "02_共通/ツール/", "06_保守者向け/回帰テスト/", "03_ClaudeCode/", "04_Codex/",
    "02_共通/ひな形/", "02_共通/ひな形/lifecycle/", "02_共通/ひな形/test/", "02_共通/ひな形/github/",
    "02_共通/ひな形/components/", "02_共通/ひな形/ui/", "01_利用者向け資料/", "01_利用者向け資料/サンプル/図書貸出/", "05_プロジェクト管理/", "02_共通/ひな形/github/workflows/",
    "06_保守者向け/", "06_保守者向け/設計判断の根拠/",
)


def resolve_inventory_name(root: Path, name: str) -> Path | None:
    for pre in INVENTORY_PREFIXES:
        c = root / (pre + name)
        if c.is_file():
            return c
    return None


# ---- 各検査 -----------------------------------------------------------------------------

def check_costs(root: Path, r: Result) -> None:
    for rel in ("INDEX.md", "README.md"):
        p = root / rel
        if not p.is_file():
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            for name, n in [(m.group(1), int(m.group(2))) for m in TABLE_COST_RE.finditer(line)] + \
                           [(m.group(1), int(m.group(2))) for m in ID_LINE_RE.finditer(line)]:
                f = resolve_cost_name(root, name)
                if f is None:
                    r.add(True, "参照コスト", f"{rel}:{i}", f"`{name}` を実ファイルに解決できない")
                    continue
                actual = wc_l(f)
                if actual != n:
                    r.add(True, "参照コスト", f"{rel}:{i}", f"`{name}` 記載 {n}行 / 実測 {actual}行")


def check_index_coverage(root: Path, r: Result) -> None:
    idx = read(root / "INDEX.md") if (root / "INDEX.md").is_file() else ""
    def listed(name: str) -> bool:
        return f"`{name}`" in idx
    for d in sorted((root / "03_ClaudeCode/skills").glob("*/")):
        if (d / "SKILL.md").is_file() and not listed(d.name):
            r.add(True, "掲載漏れ", f"skills/{d.name}", "INDEX.md に無い")
    for f in sorted((root / "03_ClaudeCode/commands").glob("*.md")):
        if not listed(f"/{f.stem}"):
            r.add(True, "掲載漏れ", f"commands/{f.name}", "INDEX.md に無い")
    for f in sorted((root / "02_共通/rules").glob("*.md")):
        if not listed(f.stem):
            r.add(True, "掲載漏れ", f"rules/{f.name}", "INDEX.md に無い")
    for f in sorted(list((root / "03_ClaudeCode/hooks").glob("*.sh")) + list((root / "03_ClaudeCode/hooks").glob("*.py"))):
        if not listed(f.name):
            r.add(True, "掲載漏れ", f"hooks/{f.name}", "INDEX.md に無い")


def test_totals(root: Path, skip: bool) -> dict[str, int]:
    env = os.environ.get("CHECK_DOCS_TEST_TOTALS")
    if env:
        out = {}
        for kv in env.split(","):
            k, v = kv.split("=")
            out[k.strip()] = int(v)
        return out
    if skip:
        return {}
    totals = {}
    for f in sorted((root / "06_保守者向け/回帰テスト").glob("test-*.sh")):
        if f.name == "test-check-docs.sh":   # 自分自身の回帰テストは再帰になるので除外
            continue
        proc = subprocess.run(["bash", str(f)], cwd=root, capture_output=True, text=True, errors="replace",
                              env={**os.environ, "GATES_REQUESTED": "1"})
        m = re.search(r"PASS=(\d+)\s*/\s*FAIL=(\d+)", proc.stdout)
        if m:
            totals[f.name] = int(m.group(1)) + int(m.group(2))
    return totals


def check_case_counts(root: Path, r: Result, totals: dict[str, int]) -> None:
    if not totals:
        r.add(False, "ケース数", "-", "テスト未実行のため突合をスキップ（--skip-tests）")
        return
    for rel in ("README.md", "INDEX.md", "01_利用者向け資料/操作マニュアル.html"):
        p = root / rel
        if not p.is_file():
            continue
        lines = read(p).splitlines()
        for i, line in enumerate(lines):
            for name, total in totals.items():
                if name not in line:
                    continue
                window = lines[i:i + 5]
                for j, w in enumerate(window):
                    nums = [int(x) for x in CASE_RE.findall(w)] + [int(x) for x in PASS_RE.findall(w)]
                    # 同じ窓に別スクリプト名があれば、その行以降は別スクリプトの数値
                    if j > 0 and any(o in w for o in totals if o != name):
                        break
                    for n in nums:
                        if n != total:
                            r.add(True, "ケース数", f"{rel}:{i + j + 1}", f"{name} 記載 {n} / 実測 {total}")


def check_references(root: Path, r: Result) -> None:
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root).as_posix()
        if rel.startswith(REF_SCAN_EXCLUDE_PREFIXES):
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            for ref in BACKTICK_PATH_RE.findall(line):
                if ref.startswith("skills/") and ref.split("/")[1] in ECC_SKILLS:
                    continue
                if ref.startswith(TARGET_SIDE_PREFIXES):
                    continue
                if ref.startswith("scripts/") and (root / TOOL_HOME / ref[len("scripts/"):]).is_file():
                    continue  # 導入先の scripts/ に置かれる道具（キット内の実体は 02_共通/ツール/）
                home = next((h for pre, h in ASSET_HOME.items() if ref.startswith(pre)), None)
                if home and (root / home / ref).exists():
                    continue  # 配布物の名前（キット内の実体は 02_共通/ ・ 03_ClaudeCode/。導入先では .claude/ 配下）
                if not (root / ref).exists():
                    r.add(True, "参照切れ", f"{rel}:{i}", f"`{ref}` が存在しない")


def check_frontmatter(root: Path, r: Result) -> None:
    for d in sorted((root / "03_ClaudeCode/skills").glob("*/")):
        f = d / "SKILL.md"
        if not f.is_file():
            r.add(True, "frontmatter", f"skills/{d.name}", "SKILL.md が無い")
            continue
        head = read(f).splitlines()[:6]
        names = [l.split(":", 1)[1].strip() for l in head if l.startswith("name:")]
        if not names or names[0] != d.name:
            r.add(True, "frontmatter", f"skills/{d.name}/SKILL.md", f"name={names[0] if names else '(なし)'} ≠ ディレクトリ名")
        if not any(l.startswith("description:") for l in head):
            r.add(True, "frontmatter", f"skills/{d.name}/SKILL.md", "description が無い")


def has_paths_frontmatter(p: Path) -> bool:
    lines = read(p).splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for l in lines[1:20]:
        if l.strip() == "---":
            return False
        if l.startswith("paths:"):
            return True
    return False


def check_always_loaded(root: Path, r: Result, strict: bool) -> None:
    always = [(f, wc_l(f)) for f in sorted((root / "02_共通/rules").glob("*.md")) if not has_paths_frontmatter(f)]
    total = sum(n for _, n in always)
    if total > RULES_ALWAYS_MAX:
        detail = f"合計 {total}行 > {RULES_ALWAYS_MAX}（" + ", ".join(f"{f.name}={n}" for f, n in always) + "）"
        r.add(strict, "常時読込", "rules/（paths 無し）", detail)


COUNT_PATTERNS = (
    ("skills", re.compile(r"(?:スキル|skills?/?)[^0-9\n]{0,4}(\d+)\s*(?:本|個|件|の)")),
    ("commands", re.compile(r"(?:コマンド|commands?/?)[^0-9\n]{0,4}(\d+)\s*(?:本|個|件|の)")),
    ("hooks", re.compile(r"(?:hooks?|見張り役)[^0-9\n]{0,4}(\d+)\s*(?:本|個|件)")),
)
COUNT_DOCS = ("README.md", "INDEX.md", "01_利用者向け資料/利用ガイド.html", "01_利用者向け資料/操作マニュアル.html")


def check_counts(root: Path, r: Result) -> None:
    """検査10: 資産の件数を直値で書いた箇所が実数とズレていないか（WARN）。"""
    actual = {
        "skills": len(list((root / "03_ClaudeCode/skills").glob("*/SKILL.md"))),
        "commands": len(list((root / "03_ClaudeCode/commands").glob("*.md"))),
        "hooks": len(list((root / "03_ClaudeCode/hooks").glob("*.sh"))) + len(list((root / "03_ClaudeCode/hooks").glob("*.py"))),
    }
    for rel in COUNT_DOCS:
        p = root / rel
        if not p.is_file():
            continue
        for i, line in enumerate(read(p).splitlines(), 1):
            for key, pat in COUNT_PATTERNS:
                for m in pat.finditer(line):
                    n = int(m.group(1))
                    if n != actual[key] and abs(n - actual[key]) <= 6:
                        r.add(False, "件数", f"{rel}:{i}", f"{key} を {n} と記載 / 実数 {actual[key]}（直値を書かず実体から出す）")


ABS_PATH_RE = re.compile(r"(?<![\w<])(/Users/|/home/|/root/)")
ABS_PATH_DOCS = ("README.md", "01_利用者向け資料/利用ガイド.html", "01_利用者向け資料/操作マニュアル.html")


def check_absolute_paths(root: Path, r: Result) -> None:
    """検査11: 利用者向け文書・雛形に絶対パス（/Users/ /home/ /root/）が無いか（WARN）。

    利用者は CLI の知識が無い前提。文書のコマンドは貼れば動く形にし、環境依存のパスは <対象ディレクトリ> のような
    プレースホルダにする（06_保守者向け/maintainer-tendencies.md #22）。
    """
    files = [root / rel for rel in ABS_PATH_DOCS] + sorted((root / "02_共通/ひな形").rglob("*.md"))
    for p in files:
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        for i, line in enumerate(read(p).splitlines(), 1):
            m = ABS_PATH_RE.search(line)
            if m:
                r.add(False, "絶対パス", f"{rel}:{i}", f"`{m.group(1)}...` を含む。<対象ディレクトリ> 等のプレースホルダにする（貼れば動く形）")


def check_claude_total(root: Path, r: Result) -> None:
    files = [root / "03_ClaudeCode/CLAUDE.md.template", root / "04_Codex/AGENTS.md.template"]
    files = [f for f in files if f.is_file()]
    if not files:
        return
    total = sum(wc_l(f) for f in files)
    if total > CLAUDE_TOTAL_MAX:
        r.add(True, "常時読込", "03_ClaudeCode/CLAUDE.md.template + 04_Codex/AGENTS.md.template",
              f"合計 {total}行 > {CLAUDE_TOTAL_MAX}（" + ", ".join(f"{f.name}={wc_l(f)}" for f in files) + "）。skills へ移す")


def check_size_targets(root: Path, r: Result, strict: bool) -> None:
    for f in sorted((root / "03_ClaudeCode/skills").glob("*/SKILL.md")):
        n = wc_l(f)
        if n > SKILL_MAX:
            r.add(strict, "行数目安", f"skills/{f.parent.name}/SKILL.md", f"{n}行 > {SKILL_MAX}")
    for f in sorted((root / "03_ClaudeCode/commands").glob("*.md")):
        n = wc_l(f)
        if n > COMMAND_MAX:
            r.add(strict, "行数目安", f"commands/{f.name}", f"{n}行 > {COMMAND_MAX}")


INVENTORY_ROW_RE = re.compile(r"^(\|\s*`([^`]+)`\s*\|\s*)(\d+)(\s*\|.*)$")


def fix_spec_inventory(root: Path) -> int:
    """06_保守者向け/内部仕様/01-inventory.md の行数セルを実測で書き換える。書き換えた行数を返す。"""
    p = root / "06_保守者向け" / "内部仕様" / "01-inventory.md"
    if not p.is_file():
        return 0
    out, changed = [], 0
    for line in read(p).splitlines():
        m = INVENTORY_ROW_RE.match(line)
        if m:
            f = resolve_inventory_name(root, m.group(2))
            if f is not None and wc_l(f) != int(m.group(3)):
                line = f"{m.group(1)}{wc_l(f)}{m.group(4)}"
                changed += 1
        out.append(line)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def check_spec_inventory(root: Path, r: Result) -> None:
    p = root / "06_保守者向け" / "内部仕様" / "01-inventory.md"
    if not p.is_file():
        return
    row = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|")
    for i, line in enumerate(read(p).splitlines(), 1):
        m = row.match(line)
        if not m:
            continue
        name, n = m.group(1), int(m.group(2))
        f = resolve_inventory_name(root, name)
        if f is None:
            r.add(True, "spec同期", f"06_保守者向け/内部仕様/01-inventory.md:{i}", f"`{name}` が実在しない")
            continue
        actual = wc_l(f)
        if actual != n:
            r.add(True, "spec同期", f"06_保守者向け/内部仕様/01-inventory.md:{i}", f"`{name}` 記載 {n}行 / 実測 {actual}行")
    # 網羅性: リポジトリの実ファイル（06_保守者向け/内部仕様/ と生成物を除く）が目録に載っているか
    text = read(p)
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = unicodedata.normalize("NFC", f.relative_to(root).as_posix())  # macOS の複製は日本語名が NFD になる
        if rel.startswith((".git/", "06_保守者向け/内部仕様/")) or rel in GENERATED_REPORTS:
            continue
        if is_local_junk(rel):
            continue
        names = {rel} | {rel[len(pre):] for pre in INVENTORY_PREFIXES if pre and rel.startswith(pre)}
        if not any(f"`{n}`" in text for n in names):
            r.add(True, "spec同期", "06_保守者向け/内部仕様/01-inventory.md", f"`{rel}` が目録に無い")


# ---- 出力 ---------------------------------------------------------------------------------

def write_report(path: Path, root: Path, r: Result) -> None:
    lines = ["# 文書整合検査レポート", "", f"- 対象: `{root}`", f"- NG: {len(r.ng)} 件 ／ 警告: {len(r.warn)} 件",
             "- 規約: `05_プロジェクト管理/要求仕様.md`（FR-05 検索構造・使用性）／ `06_保守者向け/内部仕様/09-findings.md`", "", "## NG 一覧", ""]
    if r.ng:
        lines += ["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.ng]
    else:
        lines.append("なし。")
    lines += ["", "## 警告", ""]
    if r.warn:
        lines += ["| 種別 | 対象 | 内容 |", "|---|---|---|"] + [f"| {k} | {t} | {d} |" for k, t, d in r.warn]
    else:
        lines.append("なし。")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="キット文書の整合検査")
    ap.add_argument("--root", default=".")
    ap.add_argument("-o", "--report", default="check-docs-report.md")
    ap.add_argument("--strict", action="store_true", help="検査 6・7 を WARN でなく NG にする")
    ap.add_argument("--skip-tests", action="store_true", help="検査 3 のテスト実行を省く")
    ap.add_argument("--fix-inventory", action="store_true", help="06_保守者向け/内部仕様/01-inventory.md の行数を実測で書き換えてから検査する")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    r = Result()
    if a.fix_inventory:
        print(f"06_保守者向け/内部仕様/01-inventory.md: {fix_spec_inventory(root)} 行の行数を実測に更新")

    check_costs(root, r)
    check_index_coverage(root, r)
    check_case_counts(root, r, test_totals(root, a.skip_tests))
    check_references(root, r)
    check_frontmatter(root, r)
    check_always_loaded(root, r, a.strict or RULES_STRICT)
    check_claude_total(root, r)
    check_counts(root, r)
    check_absolute_paths(root, r)
    check_size_targets(root, r, a.strict or SIZE_STRICT)
    check_spec_inventory(root, r)

    report = Path(a.report)
    if not report.is_absolute():
        report = root / report
    write_report(report, root, r)

    print(f"=== 文書整合検査: {root.name} ===")
    if r.ng:
        print(f"❌ NG={len(r.ng)}")
        for kind, n in Counter(k for k, _, _ in r.ng).most_common():
            print(f"  - {kind}: {n} 件")
        print("  例（先頭5件）:")
        for k, t, d in r.ng[:5]:
            print(f"    {k}: {t} — {d}")
    else:
        print("✅ NG=0")
    for k, t, d in r.warn:
        print(f"⚠ {k}: {t} — {d}")
    print(f"詳細: {report}")
    return 1 if r.ng else 0


if __name__ == "__main__":
    sys.exit(main())
