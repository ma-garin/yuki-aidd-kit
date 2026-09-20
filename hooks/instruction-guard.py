#!/usr/bin/env python3
"""保守者の指示に応答するまでツールを呼ばせない PreToolUse フック（全ツール対象）。

出所: 2026-09-19、作業中に届いた保守者の指示（「日本語で報告しなさい」「中間報告を今すぐ」）を、
AI がツール結果の一部として読み飛ばし、次のコマンドを続けた。**指示 ＞ 計画 ＞ 自分の規範** の順を
散文で約束しても守られないので、機械が止める（`rules/absolute-rules.md` A-13）。

判定（transcript_path の末尾を後ろから走査する）:
  - 保守者の発言（ターン冒頭の user テキスト／途中で届いた queued_command／queue-operation enqueue）の後に、
    アシスタントのテキスト応答が 1 つも無い → **deny**（指示の先頭を理由に載せる。読み飛ばしを物理的に防ぐ）
  - 応答はあるが、発言が日本語なのに応答に日本語が無い → **deny**（日本語で応答し直す）
  - それ以外（応答済み／発言が見つからない／transcript が無い／サブエージェント）→ 許可（fail-open）

バイパス用の環境変数は用意しない。止めたいときは settings.json から外す（差分に残る）。
走査幅は INSTRUCTION_GUARD_TAIL_KB（既定 512 KB）。
"""
import json
import os
import re
import sys
from pathlib import Path

TAIL_KB = int(os.environ.get("INSTRUCTION_GUARD_TAIL_KB", "512"))
JA_RE = re.compile(r"[぀-ヿ一-鿿]")
TAG_BLOCK_RE = re.compile(r"<([a-zA-Z][\w-]*)>.*?</\1>", re.S)


def has_ja(s: str) -> bool:
    return bool(JA_RE.search(s or ""))


def visible_text(s: str) -> str:
    """<system-reminder> や <command-name> 等の機械由来ブロックを除いた、人が書いた部分。"""
    return TAG_BLOCK_RE.sub("", s or "").strip()


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def instruction_of(entry: dict) -> str | None:
    """人の発言ならそのテキスト（可視部分）を返す。ツール結果・メタ・機械由来なら None。"""
    t = entry.get("type")
    if t == "user":
        if entry.get("isMeta"):
            return None
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        s = visible_text(text_of(content))
        return s or None
    if t == "attachment":
        att = entry.get("attachment") or {}
        if att.get("type") == "queued_command":
            s = visible_text(text_of(att.get("prompt")))
            return s or None
        return None
    if t == "queue-operation" and entry.get("operation") == "enqueue":
        s = visible_text(text_of(entry.get("content")))
        return s or None
    return None


def assistant_text_of(entry: dict) -> str | None:
    if entry.get("type") != "assistant":
        return None
    s = text_of((entry.get("message") or {}).get("content")).strip()
    return s or None


def tail_lines(path: Path) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > TAIL_KB * 1024:
            f.seek(size - TAIL_KB * 1024)
            f.readline()  # 途中から始まる行を捨てる
        data = f.read()
    return data.decode("utf-8", errors="replace").splitlines()


def judge(lines: list[str]) -> tuple[str, str] | None:
    """(kind, detail) を返す。None は許可。kind は 'unanswered' | 'language'。"""
    reply: str | None = None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        if reply is None:
            a = assistant_text_of(e)
            if a is not None:
                reply = a
                continue
        inst = instruction_of(e)
        if inst is None:
            continue
        if e.get("isSidechain"):
            return None
        if reply is None:
            return ("unanswered", inst)
        if has_ja(inst) and not has_ja(reply):
            return ("language", inst)
        return None
    return None


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
    }}, ensure_ascii=False))
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tp = data.get("transcript_path", "")
    if not tp or not Path(tp).is_file():
        return 0
    try:
        verdict = judge(tail_lines(Path(tp)))
    except OSError:
        return 0
    if verdict is None:
        return 0
    kind, inst = verdict
    head = " ".join(inst.split())[:80]
    if kind == "unanswered":
        return deny(f"[instruction-guard] 保守者の指示に未応答: 「{head}」。ツールを呼ぶ前に、この指示に日本語で応答する"
                    "（報告・説明・理由を求められたら作業を中断してそれに答える。A-13）")
    return deny(f"[instruction-guard] 直前の応答に日本語が無い。指示「{head}」は日本語。日本語で応答し直してからツールを呼ぶ（A-13）")


if __name__ == "__main__":
    sys.exit(main())
