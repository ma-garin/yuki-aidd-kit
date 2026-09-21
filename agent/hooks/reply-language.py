#!/usr/bin/env python3
"""ターンの最後の応答が保守者の言語（日本語）になっていなければ止める Stop フック。

instruction-guard.py（PreToolUse）はツールを呼ぶ前を見張る。こちらは**ツールを呼ばずに終わる応答**を見張る。
最後の人の発言に日本語があり、最後のアシスタント応答に日本語が無い（または応答が無い）場合、
decision=block で続行させ、日本語で出し直させる。stop_hook_active のときは何もしない（無限ループ防止）。
判定ロジックは instruction-guard.py と共有する。
"""
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # hooks ディレクトリに __pycache__ を作らない


def load_guard():
    p = Path(__file__).resolve().parent / "instruction-guard.py"
    spec = importlib.util.spec_from_file_location("instruction_guard", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def last_instruction(g, lines: list[str]) -> str | None:
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and not e.get("isSidechain"):
            inst = g.instruction_of(e)
            if inst is not None:
                return inst
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("stop_hook_active"):
        return 0
    # 最後の assistant エントリはこのフックの後に transcript へ書かれる。transcript で判定すると
    # 1 つ前の途中報告を「最後の応答」と誤認し、日本語で答えていても差し戻す（2026-09-21 に発生）。
    # 判定は入力の last_assistant_message だけで行い、無ければ判定できないので通す。
    msg = data.get("last_assistant_message")
    if not isinstance(msg, str) or not msg.strip():
        return 0
    g = load_guard()
    if g.has_ja(msg):
        return 0
    tp = data.get("transcript_path", "")
    if not tp or not Path(tp).is_file():
        return 0
    try:
        inst = last_instruction(g, g.tail_lines(Path(tp)))
    except OSError:
        return 0
    if inst is None or not g.has_ja(inst):
        return 0
    head = " ".join(inst.split())[:80]
    reason = f"[reply-language] 最後の応答に日本語が無い。指示「{head}」は日本語。日本語で出し直す（A-13）"
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
