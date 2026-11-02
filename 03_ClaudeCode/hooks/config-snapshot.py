#!/usr/bin/env python3
"""AI の構成（モデル・指示ファイル・ツール設定）の変化を記録する hook（SessionStart / UserPromptSubmit）。

根拠: コードを 1 行も変えていなくても、モデルの版・ツール設定・指示ファイルが変われば AI の振る舞いは変わる。
構成の変更も「変更」として記録し、変わったら確認セットを通し直す（quality-decision）。

使い方:
  config-snapshot.py snapshot     … hook として。stdin の JSON（model・cwd）を読み、前回と差があれば追記して通知
  config-snapshot.py report [N]   … 直近 N 件（既定 10）の変更履歴を Markdown の表で出す（検収の「構成の記録」）
保存先: <cwd>/.claude/ai-config-log.jsonl（環境変数 AIDD_CONFIG_LOG で差し替え）。
記録するのはハッシュ先頭 12 桁・モデル名・環境変数のキー名だけ（値は記録しない）。
失敗しても作業を止めない（fail-open。例外時は無出力で exit 0）。
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secret_patterns import log_decision
except ImportError:          # 記録は付け足し。部品が無くても動作は変えない
    def log_decision(*_a, **_k) -> None:
        pass

_PROJECT_FILES = ("CLAUDE.md", "AGENTS.md", ".claude/settings.json", ".claude/settings.local.json", "KIT_VERSION")
_HOME_FILES = ("~/.claude/CLAUDE.md", "~/.claude/settings.json")


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def log_path(cwd: str) -> Path:
    env = os.environ.get("AIDD_CONFIG_LOG")
    return Path(env).expanduser() if env else Path(cwd) / ".claude" / "ai-config-log.jsonl"


def collect(cwd: str, data: dict) -> dict:
    """比較対象の構成。存在しないファイルは載せない（消えたら差として出る）。"""
    base = Path(cwd)
    items: dict[str, str] = {}
    for rel in _PROJECT_FILES:
        h = _sha(base / rel)
        if h:
            items[rel] = h
    rules = base / ".claude" / "rules"
    if rules.is_dir():
        for p in sorted(rules.glob("*.md")):
            h = _sha(p)
            if h:
                items[f".claude/rules/{p.name}"] = h
    for rel in _HOME_FILES:
        h = _sha(Path(rel).expanduser())
        if h:
            items[rel] = h
    model = data.get("model")
    if isinstance(model, dict):
        model = model.get("id") or model.get("display_name")
    if model:
        items["model"] = str(model)
    keys = sorted(k for k, v in os.environ.items()
                  if v and (k == "ANTHROPIC_MODEL" or k.startswith("CLAUDE_CODE_")))
    if keys:
        items["env_keys"] = ",".join(keys)
    if os.environ.get("ANTHROPIC_MODEL"):     # モデル名は値も比較する（版の差し替えを拾う）
        items["env:ANTHROPIC_MODEL"] = os.environ["ANTHROPIC_MODEL"]
    return items


def last_record(path: Path) -> dict | None:
    try:
        lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


def diff(old: dict, new: dict) -> list[str]:
    return sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))


def snapshot() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
        if not isinstance(data, dict):
            data = {}
    except ValueError:
        data = {}
    cwd = data.get("cwd") or os.getcwd()
    event = data.get("hook_event_name") or "SessionStart"
    items = collect(cwd, data)
    path = log_path(cwd)
    prev = last_record(path)
    changed = diff(prev.get("items", {}), items) if prev else []
    if prev and not changed:
        return 0
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, "changed": changed, "items": items}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if not prev:                              # 初回は記録だけ
        return 0
    names = "、".join(changed[:6]) + (f" ほか {len(changed) - 6} 件" if len(changed) > 6 else "")
    ctx = (f"AI の構成が変わった: {names}。\n"
           "確認セットを通し直してから次の改修に使う（quality-decision）。\n"
           f"履歴: {path}（`config-snapshot.py report` で表示）")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": ctx}},
                     ensure_ascii=False))
    log_decision("config-snapshot", "warn", f"構成変更: {names}", event, "", cwd)
    return 0


def report(n: int) -> int:
    path = log_path(os.getcwd())
    recs = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        print(f"構成の記録が無い: {path}")
        return 0
    print(f"## 構成の記録（直近 {min(n, len(recs))} 件 / 全 {len(recs)} 件）\n")
    print("| 日時 | 契機 | 変わった項目 | モデル |")
    print("|---|---|---|---|")
    for r in recs[-n:]:
        ch = "、".join(r.get("changed") or []) or "（初回記録）"
        model = r.get("items", {}).get("model") or r.get("items", {}).get("env:ANTHROPIC_MODEL") or "-"
        print(f"| {r.get('time', '-')} | {r.get('event', '-')} | {ch} | {model} |")
    return 0


def main() -> int:
    args = sys.argv[1:]
    mode = args[0] if args else "snapshot"
    try:
        if mode == "report":
            return report(int(args[1]) if len(args) > 1 and args[1].isdigit() else 10)
        return snapshot()
    except Exception:        # fail-open: 構成の記録が壊れても作業は止めない
        return 0


if __name__ == "__main__":
    sys.exit(main())
