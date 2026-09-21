#!/usr/bin/env python3
"""token_report.py — セッション JSONL（~/.claude/projects/<proj>/<id>.jsonl）から消費構造を実測する。依存なし。

token_audit.py が「仕組みが配線されているか」を見るのに対し、こちらは「実際に何に使ったか」を数える。
同じ message.id の usage は 1 回だけ数える（ストリーミングで複数行に分かれるため）。

  input / cache_write / cache_read / output の合計と構成比、応答数、1 応答あたりの出力
  費用比: 単価の倍率（input=1, cache_write=1.25, cache_read=0.1, output=5）で重み付けした構成比。
          倍率は 5 分キャッシュの公表比。1 時間キャッシュは cache_write=2.0（--write-mult で変更）

使い方: python3 00_導入/token_report.py [JSONL ...]   （省略時はカレントのプロジェクトの最新セッション）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
LABELS = ("input", "cache_write", "cache_read", "output")


def latest_session() -> Path | None:
    proj = Path.home() / ".claude" / "projects" / str(Path.cwd()).replace("/", "-").replace(".", "-")
    files = sorted(proj.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def collect(path: Path) -> tuple[dict[str, int], int]:
    totals = dict.fromkeys(KEYS, 0)
    seen: set[str] = set()
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            msg = e.get("message") if isinstance(e, dict) else None
            if e.get("type") != "assistant" or not isinstance(msg, dict) or not msg.get("usage"):
                continue
            mid = msg.get("id") or e.get("uuid")
            if mid in seen:
                continue
            seen.add(mid)
            for k in KEYS:
                totals[k] += int(msg["usage"].get(k) or 0)
    return totals, len(seen)


def report(path: Path, write_mult: float) -> str:
    t, n = collect(path)
    total = sum(t.values()) or 1
    mults = dict(zip(KEYS, (1.0, write_mult, 0.1, 5.0)))
    cost = {k: t[k] * mults[k] for k in KEYS}
    ctotal = sum(cost.values()) or 1
    rows = [f"# {path.name}  応答 {n} 件・出力 {t['output_tokens'] // max(n, 1):,} tok/応答",
            "| 区分 | トークン | 構成比 | 費用比 |", "|---|---:|---:|---:|"]
    rows += [f"| {lab} | {t[k]:,} | {t[k] / total:.2%} | {cost[k] / ctotal:.2%} |" for k, lab in zip(KEYS, LABELS)]
    rows.append(f"| 計 | {total:,} | | |")
    return "\n".join(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jsonl", nargs="*", type=Path)
    ap.add_argument("--write-mult", type=float, default=1.25)
    args = ap.parse_args()
    paths = args.jsonl or [p for p in [latest_session()] if p]
    if not paths:
        print("セッション JSONL が見つからない。パスを引数で渡す", file=sys.stderr)
        return 1
    for p in paths:
        print(report(p, args.write_mult))
    return 0


if __name__ == "__main__":
    sys.exit(main())
