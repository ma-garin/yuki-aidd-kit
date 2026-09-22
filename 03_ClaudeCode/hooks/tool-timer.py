#!/usr/bin/env python3
"""ツール実行時間を積算する PreToolUse / PostToolUse フック。

見積の「実績」を体感でなく実測で出すための計測器（2026-09-22 の指摘: 実績値に定義が無く、
入力待ちと思考時間が混ざった差し引きを実績と称していた）。

**測るもの**: ツールが走っていた時間の合計だけ。保守者の入力待ち・モデルの思考時間は含まない。
見積（`rules/absolute-rules.md` A-2）はこの定義の時間に対して出す。

使い方:
  python3 .claude/hooks/tool-timer.py pre     # PreToolUse に配線（stdin に hook の JSON）
  python3 .claude/hooks/tool-timer.py post    # PostToolUse に配線
  python3 .claude/hooks/tool-timer.py report  # 実績を1行で出す（見積と並べて報告する）
  python3 .claude/hooks/tool-timer.py reset   # 次の作業の計測を始める（見積を出した直後に叩く）

記録先は `.claude/tool-time.json`。hook は失敗しても作業を止めない（常に exit 0）。
"""
import json
import pathlib
import sys
import time

_FILE = pathlib.Path(__file__).resolve().parent.parent / "tool-time.json"
_EMPTY = {"total_sec": 0.0, "count": 0, "inflight": {}, "since": None, "window_start": None}


def load() -> dict:
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_EMPTY, inflight={})
    if not isinstance(data, dict):
        return dict(_EMPTY, inflight={})
    for k, v in _EMPTY.items():
        data.setdefault(k, {} if isinstance(v, dict) else v)
    if not isinstance(data.get("inflight"), dict):
        data["inflight"] = {}
    return data


def save(data: dict) -> None:
    try:
        _FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def key_of(payload: dict) -> str:
    """並列実行を取り違えないための鍵。tool_use_id が無ければツール名で代用する。"""
    for k in ("tool_use_id", "toolUseId", "tool_use_ID"):
        v = payload.get(k)
        if isinstance(v, str) and v:
            return v
    name = payload.get("tool_name") or payload.get("toolName") or "?"
    return f"name:{name}"


def read_payload() -> dict:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def fmt(total: float, count: int) -> str:
    m, s = divmod(int(round(total)), 60)
    span = f"{m}分{s}秒" if m else f"{s}秒"
    return f"実績: ツール実行 {span} / {count} 回（入力待ち・思考時間を含まない）"


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    # 並列実行を二重に数えないため、積算するのは「1本以上が走っている区間」の実時間。
    # 各ツールの所要時間を足すと、H-4 の並列委譲で実際の 30 倍が出る
    if cmd == "pre":
        data = load()
        if data["since"] is None:
            data["since"] = time.time()
        if not data["inflight"]:
            data["window_start"] = time.time()
        data["inflight"][key_of(read_payload())] = time.time()
        save(data)
    elif cmd == "post":
        data = load()
        if data["inflight"].pop(key_of(read_payload()), None) is not None:
            data["count"] = int(data["count"]) + 1
        if not data["inflight"]:
            start = data.get("window_start")
            if isinstance(start, (int, float)):
                data["total_sec"] = float(data["total_sec"]) + max(0.0, time.time() - start)
            data["window_start"] = None
        save(data)
    elif cmd == "report":
        data = load()
        print(fmt(float(data["total_sec"]), int(data["count"])))
    elif cmd == "reset":
        save(dict(_EMPTY, inflight={}, since=time.time()))
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
