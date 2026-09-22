#!/usr/bin/env python3
"""指示優先の 3 hook（instruction-guard / prompt-priority / reply-language）を ~/.claude に導入する。

Claude Code **全体**（全プロジェクト・全セッション）に効かせるための最小導入。`install.sh` と違い、既存の
`~/.claude/settings.json` を上書きせず、hooks の配線だけを **merge** する（他のキー・他の hook はそのまま）。
何度実行しても重複しない（冪等）。既存ファイルを変更するときは `.bak` を残す。

使い方:  python3 00_導入/01_インストール/install_guard.py [--home <HOME>] [--hooks-dir <キットの hooks>]
終了コード: 0 導入済み（変更あり／変更なし）、1 失敗（settings.json が壊れている等）
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

GUARDS = (
    # (ファイル, イベント, matcher(None=全ツール), 追加の設定, 引数)
    # tool-timer は reply-language が実績を読むための計測器。3 hook と同時に入れないと実績が空になる
    ("tool-timer.py", "PreToolUse", None, {"timeout": 5}, "pre"),
    ("tool-timer.py", "PostToolUse", None, {"timeout": 5}, "post"),
    ("tool-timer.py", "UserPromptSubmit", None, {"timeout": 5}, "reset"),
    ("instruction-guard.py", "PreToolUse", None, {"timeout": 5, "statusMessage": "保守者の指示に応答済みか確認中"}, ""),
    ("prompt-priority.py", "UserPromptSubmit", None, {"timeout": 5}, ""),
    ("reply-language.py", "Stop", None, {"timeout": 5}, ""),
)


def already_wired(entries: list, name: str) -> bool:
    for e in entries:
        for h in (e or {}).get("hooks", []) or []:
            if name in str((h or {}).get("command", "")):
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("HOME", str(Path.home())))
    ap.add_argument("--hooks-dir", default=str(Path(__file__).resolve().parents[2] / "03_ClaudeCode" / "hooks"))
    a = ap.parse_args()
    home = Path(a.home)
    claude = home / ".claude"
    hooks_dst = claude / "hooks"
    hooks_src = Path(a.hooks_dir)
    hooks_dst.mkdir(parents=True, exist_ok=True)

    copied = []
    for name, *_ in GUARDS:
        if name in copied:
            continue   # 同じファイルを複数イベントに配線する（tool-timer）
        src = hooks_src / name
        if not src.is_file():
            print(f"❌ {src} が無い（キットの hooks を指定する）")
            return 1
        shutil.copy2(src, hooks_dst / name)
        (hooks_dst / name).chmod(0o755)
        copied.append(name)

    sp = claude / "settings.json"
    if sp.is_file():
        try:
            settings = json.loads(sp.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"❌ {sp} が JSON として読めない: {e}。手で直してから再実行")
            return 1
        if not isinstance(settings, dict):
            print(f"❌ {sp} の最上位がオブジェクトでない")
            return 1
        existed = True
    else:
        settings, existed = {}, False

    hooks = settings.setdefault("hooks", {})
    added = []
    for name, event, matcher, extra, arg in GUARDS:
        entries = hooks.setdefault(event, [])
        if already_wired(entries, f"{name} {arg}".strip()):
            continue
        cmd = f"python3 ~/.claude/hooks/{name}" + (f" {arg}" if arg else "")
        h = {"type": "command", "command": cmd, **extra}
        entry = {"hooks": [h]}
        if matcher:
            entry["matcher"] = matcher
        entries.insert(0, entry)  # 先頭＝他の hook より先に判定する
        added.append(name)

    if added:
        if existed:
            shutil.copy2(sp, sp.with_suffix(".json.bak"))
        sp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"=== 指示優先 hook の導入: {claude} ===")
    print(f"✅ hooks: {', '.join(copied)} → {hooks_dst}")
    if added:
        print(f"✅ settings.json に配線: {', '.join(added)}" + ("（既存を .bak に退避して merge）" if existed else "（新規作成）"))
    else:
        print("✅ settings.json: 配線済み（変更なし）")
    print("効き方: 保守者の発言への未応答・見積もり未提示をツール呼び出しの直前に通知する（止めない）。実行中のセッションにも file watcher で反映される（反映されなければ再起動）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
