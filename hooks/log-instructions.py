#!/usr/bin/env python3
"""どの指示ファイル（CLAUDE.md / rules / skills）がいつ・なぜ読み込まれたかを記録する InstructionsLoaded フック。

目的: 常時読み込み層の「推定」を「実測」に置き換える材料（internal/spec/11 U-2 / U-3）。
Claude には何も返さない（コンテキストを増やさない）。集計は scripts/token-audit.sh。

出力先: $CLAUDE_PROJECT_DIR/.claude/instructions-loaded.log（.claude/ が無ければ ~/.claude/）。
1 行 = ISO 時刻 TAB hook 入力の JSON（スキーマの変更に耐えるため加工しない）。*.log は .gitignore 済み。
"""
import json
import os
import sys
import time
from pathlib import Path


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        return 0
    proj = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    target_dir = proj / ".claude" if (proj / ".claude").is_dir() else Path.home() / ".claude"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        with (target_dir / "instructions-loaded.log").open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%dT%H:%M:%S%z") + "\t" + json.dumps(data, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
