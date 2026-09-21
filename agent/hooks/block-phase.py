#!/usr/bin/env python3
"""未承認の工程の下流成果物への書き込みを物理ブロックする PreToolUse フック。

AIDD では、要件の取り違えが基本設計に入り込むと、詳細設計・実装・テストまで全部その上に積まれ、
受け入れテストで判明したときの手戻りが最大になる。本フックは**誤りの伝播を工程1つ分で止める**。
仕様: templates/lifecycle/approvals/README.md ／ 判定: scripts/check_approval.py

発動条件（オプトイン）: プロジェクトルートに `.claude/phase-gate` がある時だけ効く。
軽量 SDD（個人 PWA・単一 HTML ツール）では工程ゲート自体が過剰なため、既定は無効。

判定:
  - `docs/lifecycle/approvals/**` への書き込みは**常に許可**（承認者が止められては意味がない）
  - `docs/lifecycle/0<n>-*.md` への書き込みで、直前の着手済み工程が未承認・失効・判定不能 → deny
  - 既に承認済みの工程の成果物を書き換えようとした場合も deny（黙って承認が失効するのを防ぐ）
  - それ以外は許可

**バイパス用の環境変数は用意しない。** 止めたいときは `.claude/phase-gate` を消す
（消したことが git 差分に残り、第三者が検知できる）。
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

LIFECYCLE_RE = re.compile(r"^docs/lifecycle/0([0-9])-[^/]+\.md$")
CHECKER_CANDIDATES = ("scripts/check_approval.py", ".claude/scripts/check_approval.py")


def deny(reason: str) -> int:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    return 0


def find_checker(root: Path) -> Path | None:
    for c in CHECKER_CANDIDATES:
        p = root / c
        if p.is_file():
            return p
    p = Path.home() / ".claude" / "scripts" / "check_approval.py"
    return p if p.is_file() else None


def run_gate(checker: Path, root: Path, *args: str) -> tuple[int, str]:
    p = subprocess.run([sys.executable, str(checker), "--root", str(root), *args],
                       capture_output=True, text=True, timeout=20)
    return p.returncode, (p.stdout + p.stderr).strip()


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    if not (root / ".claude" / "phase-gate").exists():
        return 0

    fp = data.get("tool_input", {}).get("file_path", "")
    if not fp:
        return 0
    try:
        rel = Path(fp).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0

    if rel.startswith("docs/lifecycle/approvals/"):
        return 0            # 承認記録そのものへの書き込みは常に許可する
    m = LIFECYCLE_RE.match(rel)
    if not m:
        return 0
    phase = int(m.group(1))

    checker = find_checker(root)
    if checker is None:
        return deny(
            "工程承認ゲートが有効（.claude/phase-gate あり）ですが、判定に使う "
            "scripts/check_approval.py が見つかりません。\n"
            "配置してください: <キット>/scripts/export-project.sh . を再実行する、または "
            "check_approval.py / phase-hash.py を scripts/ へコピーする。\n"
            "ゲートを使わないなら .claude/phase-gate を削除してください（削除は git 差分に残ります）。"
        )

    # 1. 承認済みの工程の成果物を書き換えようとしていないか（黙って失効させない）
    rc, _ = run_gate(checker, root, "--phase", str(phase), "--quiet")
    if rc == 0:
        return deny(
            f"第{phase}工程の成果物は承認済みです: {rel}\n"
            f"このまま書き換えると承認が失効します（判子を押した後に中身が差し替わるのと同じ）。\n"
            f"変更が必要なら、先に docs/lifecycle/approvals/phase-{phase}.md の判定を「未記入」に戻し、"
            f"変更後に /phase-review {phase} → 人間の再承認を取ってください。"
        )

    # 2. 直前の着手済み工程が承認されているか
    rc, out = run_gate(checker, root, "--gate", str(phase))
    if rc == 0:
        return 0
    return deny(
        f"前工程が未承認のため {rel} を書けません（工程承認ゲート）。\n{out}\n"
        "誤りの伝播を工程1つ分で止めるための制限です。"
    )


if __name__ == "__main__":
    sys.exit(main())
