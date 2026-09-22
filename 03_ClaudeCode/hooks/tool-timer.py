#!/usr/bin/env python3
"""ツール実行時間を積算する PreToolUse / PostToolUse フック。

見積の「実績」を体感でなく実測で出すための計測器（2026-09-22 の指摘: 実績値に定義が無く、
入力待ちと思考時間が混ざった差し引きを実績と称していた）。

**測るもの**: ツールが走っていた時間の合計だけ。保守者の入力待ち・モデルの思考時間は含まない。
見積（`rules/absolute-rules.md` A-2）はこの定義の時間に対して出す。

使い方:
  python3 .claude/hooks/tool-timer.py pre     # PreToolUse に配線（stdin に hook の JSON）
  python3 .claude/hooks/tool-timer.py post    # PostToolUse に配線
  python3 .claude/hooks/tool-timer.py report          # 実績を1行（経過時間だけ。報告に貼る）
  python3 .claude/hooks/tool-timer.py report --full   # ツール実行時間・回数・通算も出す
  python3 .claude/hooks/tool-timer.py elapsed # このターンの経過分（見積との突合用。数値のみ）
  python3 .claude/hooks/tool-timer.py reset          # ターンの計測を 0 に戻す（UserPromptSubmit に配線済み）
  python3 .claude/hooks/tool-timer.py reset-session  # 通算も 0 に戻す（新しい作業を始めるとき）

記録先は `.claude/tool-time.json`。hook は失敗しても作業を止めない（常に exit 0）。
"""
import json
import pathlib
import sys
import time

_FILE = pathlib.Path(__file__).resolve().parent.parent / "tool-time.json"
# total_* はターン単位（UserPromptSubmit の reset で 0 に戻る）。session_* は通算で、
# reset では消えない（複数ターンにまたがる作業の実績を出すため。2026-09-22 の残課題）
_EMPTY = {"total_sec": 0.0, "count": 0, "inflight": {}, "since": None, "window_start": None,
          "session_sec": 0.0, "session_count": 0}


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


def span_of(total: float) -> str:
    m, s = divmod(int(round(total)), 60)
    return f"{m}分{s}秒" if m else f"{s}秒"


def fmt(data: dict, full: bool = False) -> str:
    """実績の1行。既定は経過時間だけ（見積と同じ単位。報告に貼る用）。

    full=True でツール実行時間と回数・通算も出す（内訳を見たいときだけ）。
    報告が長いと読まれないので既定は最短にする（2026-09-22 の指摘）。
    """
    since = data.get("since")
    elapsed = span_of(max(0.0, time.time() - since)) if isinstance(since, (int, float)) else "-"
    if not full:
        return f"実績: {elapsed}"
    out = f"実績: {elapsed}（ツール {span_of(float(data['total_sec']))} / {int(data['count'])}回）"
    sc = int(data["session_count"])
    if sc > int(data["count"]):
        out += f" 通算 {span_of(float(data['session_sec']))} / {sc}回"
    return out


def elapsed_min(data: dict) -> float | None:
    """このターンの経過分。見積（分）と突き合わせる用。"""
    since = data.get("since")
    if not isinstance(since, (int, float)) or int(data["count"]) == 0:
        return None
    return max(0.0, time.time() - since) / 60.0


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
            data["session_count"] = int(data["session_count"]) + 1
        if not data["inflight"]:
            start = data.get("window_start")
            if isinstance(start, (int, float)):
                span = max(0.0, time.time() - start)
                data["total_sec"] = float(data["total_sec"]) + span
                data["session_sec"] = float(data["session_sec"]) + span
            data["window_start"] = None
        save(data)
    elif cmd == "report":
        print(fmt(load(), full="--full" in sys.argv))
    elif cmd == "elapsed":
        m = elapsed_min(load())
        print("" if m is None else f"{m:.2f}")
    elif cmd == "reset":
        # ターンの計測だけ 0 に戻す。通算（session_*）は引き継ぐ
        old = load()
        save(dict(_EMPTY, inflight={}, since=time.time(),
                  session_sec=float(old["session_sec"]), session_count=int(old["session_count"])))
    elif cmd == "reset-session":
        save(dict(_EMPTY, inflight={}, since=time.time()))
    else:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
