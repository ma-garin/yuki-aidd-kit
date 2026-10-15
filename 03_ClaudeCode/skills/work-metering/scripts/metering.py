#!/usr/bin/env python3
"""作業の計測行（開始・中間・終了）を印字し、予実を記録して見積の校正係数を出す。hook に依存しない（Codex・手動用）。

使い方:
  metering.py now                              # HH:MM（Asia/Tokyo）
  metering.py factor                           # 校正係数と件数（例 "0.50 14"）。3 件未満は "1.00 0"
  metering.py begin "<作業名>" <見積分> [n]     # 開始行を印字し、開始時刻を保存
  metering.py mid <k>                          # 中間行を印字（k = 終わったタスク数）
  metering.py end [成功|失敗]                  # 終了行と `見積: N分 / 実測: M分` を印字し、履歴に [見積, 実測] を積む
  metering.py note "<原因 1 行>"               # 乖離の原因を実測記録に追記（H-6）
予実の履歴は Claude Code の tool-timer.py と同じファイル（~/.claude/tool-time.json の "history"）を共有する。
無ければ ~/.agents/metering.json。環境変数 AIDD_TOOL_TIME で差し替え可。失敗しても作業を止めない（exit 0）。
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import sys
import time

LOCAL_TZ = os.environ.get("AIDD_TZ", "Asia/Tokyo")
HISTORY_MAX = 30
_HOME = pathlib.Path.home()
_CANDIDATES = [_HOME / ".claude" / "tool-time.json", _HOME / ".agents" / "metering.json"]


def hist_file() -> pathlib.Path:
    env = os.environ.get("AIDD_TOOL_TIME")
    if env:
        return pathlib.Path(env)
    for p in _CANDIDATES:
        if p.is_file():
            return p
    return _CANDIDATES[0] if _CANDIDATES[0].parent.is_dir() else _CANDIDATES[1]


def state_file() -> pathlib.Path:
    return pathlib.Path(os.environ.get("AIDD_METERING_STATE") or hist_file().with_name("metering-state.json"))


def load_json(p: pathlib.Path) -> dict:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save_json(p: pathlib.Path, d: dict) -> None:
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def now_dt() -> datetime.datetime:
    try:
        import zoneinfo
        return datetime.datetime.now(zoneinfo.ZoneInfo(LOCAL_TZ))
    except Exception:
        return datetime.datetime.now()


def hhmm(ts: float | None = None) -> str:
    d = now_dt() if ts is None else datetime.datetime.fromtimestamp(ts, now_dt().tzinfo)
    return d.strftime("%H:%M")


def factor() -> tuple[float, int]:
    h = [x for x in load_json(hist_file()).get("history", []) if isinstance(x, list) and len(x) == 2 and x[0] > 0]
    if len(h) < 3:
        return 1.0, 0
    rs = sorted(a / e for e, a in h)
    mid = rs[len(rs) // 2] if len(rs) % 2 else (rs[len(rs) // 2 - 1] + rs[len(rs) // 2]) / 2
    return mid, len(h)


def record(est: float, act: float) -> None:
    p = hist_file()
    d = load_json(p)
    h = [x for x in d.get("history", []) if isinstance(x, list) and len(x) == 2]
    h.append([est, act])
    d["history"] = h[-HISTORY_MAX:]
    save_json(p, d)


def deviation_log() -> pathlib.Path:
    env = os.environ.get("AIDD_METERING_LOG")
    if env:
        return pathlib.Path(env)
    # kit が手元にあればその実測記録へ。無ければ ~/.agents/metering-deviations.md
    for base in (_HOME / "dev" / "active", _HOME / "dev", _HOME):
        p = base / "yuki-aidd-kit" / "06_保守者向け" / "02_設計判断の根拠" / "speed-harness.md"
        if p.is_file():
            return p
    return _HOME / ".agents" / "metering-deviations.md"


def cmd_begin(args: list[str]) -> int:
    if len(args) < 2:
        print("使い方: metering.py begin \"<作業名>\" <見積分> [タスク数]")
        return 0
    name, est = args[0], float(args[1])
    n = int(args[2]) if len(args) > 2 else 1
    start = time.time()
    save_json(state_file(), {"name": name, "est": est, "n": n, "start": start, "last_mid": start})
    print(f"【見積：{est:g}分 | 開始:{hhmm(start)} | 終了:{hhmm(start + est * 60)} | タスク数：{n}】")
    return 0


def cmd_mid(args: list[str]) -> int:
    s = load_json(state_file())
    if not s:
        print("開始行がありません。先に `metering.py begin \"<作業名>\" <見積分> [n]` を実行する")
        return 0
    k = int(args[0]) if args else 0
    n, est, start = int(s["n"]), float(s["est"]), float(s["start"])
    elapsed = (time.time() - start) / 60
    expected = est * (k / n) if n else est
    if elapsed > est or (expected > 0 and elapsed > expected * 1.2):
        mark, finish = "遅れ", time.time() + max(est - elapsed, 0) * 60 + (elapsed - expected) * 60
    elif expected > 0 and elapsed < expected * 0.8:
        mark, finish = "前倒し", start + est * 60
    else:
        mark, finish = "順調", start + est * 60
    s["last_mid"] = time.time()
    save_json(state_file(), s)
    print(f"【進捗:{mark} | 経過時間：{elapsed:.0f}分 | 終了:{hhmm(finish)} | タスク数:{k}/{n}】")
    return 0


def cmd_end(args: list[str]) -> int:
    s = load_json(state_file())
    if not s:
        print("開始行がありません。実測は「未計測」と書く")
        return 0
    result = args[0] if args else "成功"
    est, start, end = float(s["est"]), float(s["start"]), time.time()
    act = (end - start) / 60
    record(est, act)
    save_json(state_file(), {})
    print(f"【見積:{est:g}分 | 実測:{act:.0f}分 | 開始:{hhmm(start)} | 終了:{hhmm(end)} | 作業時間記録:{result}】")
    print(f"見積: {est:g}分 / 実測: {act:.0f}分")
    ratio = act / est if est > 0 else 1.0
    if ratio > 1.5 or (ratio < 1 / 3 and act >= 2):
        kind = "超過" if ratio > 1.5 else "過大見積"
        print(f"[H-6] 予実が離れている（{kind}: 実測は見積の {ratio:.2f} 倍）。原因を 1 行書き "
              f"`metering.py note \"<原因>\"` で記録してから報告する")
    return 0


def cmd_note(args: list[str]) -> int:
    if not args:
        print("使い方: metering.py note \"<原因 1 行>\"")
        return 0
    p = deviation_log()
    line = f"\n- {now_dt().strftime('%Y-%m-%d')} {' '.join(args)}\n"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
        print(f"記録: {p}")
    except OSError as e:
        print(f"記録できなかった（{e}）。報告本文に原因 1 行を残す")
    return 0


def main() -> int:
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else ""), sys.argv[2:]
    if cmd == "now":
        print(hhmm())
    elif cmd == "factor":
        f, n = factor()
        print(f"{f:.2f} {n}")
    elif cmd == "begin":
        return cmd_begin(args)
    elif cmd == "mid":
        return cmd_mid(args)
    elif cmd == "end":
        return cmd_end(args)
    elif cmd == "note":
        return cmd_note(args)
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
