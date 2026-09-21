#!/usr/bin/env python3
"""進捗つきステータスライン。

タスク進行中（.claude/progress.json あり）: 進捗（タスク名・ステップ・経過/見積・残り）を
従来表示（~/.claude/statusline.sh）の前に連結して出す。従来表示は常に消さない。
待機中: 従来表示のみ。
常時: セッションの累計消費を差分読みで出す（⚠ Σ268.4M 出力1,341/t 660t）。消費を尋ねるターン自体が文脈全量を読み直すため、表示で済ませる。
"""
import json
import os
import pathlib
import subprocess
import sys
import time

_FILE = pathlib.Path(__file__).resolve().parent.parent / "progress.json"
_FALLBACK = pathlib.Path.home() / ".claude" / "statusline.sh"
_TOKEN_CACHE = pathlib.Path.home() / ".claude" / ".statusline-tokens.json"
_USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
_OUT_WARN = 1000  # 1 応答あたり出力がこれを超えたら ⚠（H-0 の目安）


def _fmt(sec: float) -> str:
    sec = max(0, int(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def _progress_part() -> str:
    """進行中タスクの進捗文字列。無ければ空文字。"""
    if not _FILE.exists():
        return ""
    try:
        d = json.loads(_FILE.read_text(encoding="utf-8"))
        elapsed = time.time() - d["started"]
        est = d["estimate_sec"]
        remain = est - elapsed
        tail = (f"残り {_fmt(remain)}" if remain >= 0
                else f"残り 0:00（超過 +{_fmt(-remain)}）")
        return f"⏱ {d['task']} [{d['step']}] {_fmt(elapsed)}/{_fmt(est)} {tail}"
    except (json.JSONDecodeError, KeyError, OSError):
        return ""  # 壊れた進捗ファイルは無視して従来表示のみ


def _fallback_part(stdin_raw: str) -> str:
    """従来のステータスライン出力。常に表示し続ける。"""
    if _FALLBACK.exists():
        try:
            out = subprocess.run(
                ["bash", str(_FALLBACK)], input=stdin_raw, capture_output=True,
                text=True, timeout=5,
            )
            return out.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass
    return os.path.basename(os.getcwd())


def _human(n: int) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k"


def _token_part(stdin_raw: str) -> str:
    """セッションの累計消費（Σ）・1 応答あたり出力・応答数。前回の読み終わり位置から差分だけ読む。"""
    try:
        path = pathlib.Path(json.loads(stdin_raw or "{}").get("transcript_path") or "")
        if not path.is_file():
            return ""
        c = json.loads(_TOKEN_CACHE.read_text(encoding="utf-8")) if _TOKEN_CACHE.exists() else {}
        if c.get("path") != str(path) or c.get("offset", 0) > path.stat().st_size:
            c = {"path": str(path), "offset": 0, "total": 0, "out": 0, "n": 0, "last": ""}
        with path.open("rb") as f:
            f.seek(c["offset"])
            for raw in f:
                if not raw.endswith(b"\n"):
                    break  # 書きかけの行は次回
                c["offset"] += len(raw)
                try:
                    e = json.loads(raw)
                except ValueError:
                    continue
                m = e.get("message") if e.get("type") == "assistant" else None
                if not isinstance(m, dict) or not m.get("usage") or m.get("id") == c["last"]:
                    continue
                c["last"] = m.get("id") or ""
                u = m["usage"]
                c["total"] += sum(int(u.get(k) or 0) for k in _USAGE_KEYS)
                c["out"] += int(u.get("output_tokens") or 0)
                c["n"] += 1
        _TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_CACHE.write_text(json.dumps(c), encoding="utf-8")
        if not c["n"]:
            return ""
        per = c["out"] // c["n"]
        warn = "⚠ " if per > _OUT_WARN else ""
        return f"{warn}Σ{_human(c['total'])} 出力{per:,}/t {c['n']}t"
    except (OSError, ValueError, TypeError, AttributeError):
        return ""  # 表示の失敗で従来表示を消さない


def main() -> int:
    stdin_raw = sys.stdin.read()
    parts = [p for p in (_progress_part(), _token_part(stdin_raw)) if p]
    base = _fallback_part(stdin_raw)
    print(" ｜ ".join(parts + [base]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
