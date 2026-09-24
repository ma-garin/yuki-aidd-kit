#!/usr/bin/env python3
"""保守者の指示への未応答を AI の文脈に載せる PreToolUse フック（全ツール対象）。

2026-09-21: deny をやめ additionalContext に変えた。PreToolUse の時点では同じターンで書いた応答が
transcript に未反映のため、応答済みでも毎回 deny が画面にエラー表示され、保守者に不快と指摘された。
サブエージェント内（入力に agent_id がある）は対象外（親の発言を未応答と誤認して止めていた）。
以下の「deny」は通知（additionalContext）と読み替える。

出所: 2026-09-19、作業中に届いた保守者の指示（「日本語で報告しなさい」「中間報告を今すぐ」）を、
AI がツール結果の一部として読み飛ばし、次のコマンドを続けた。**指示 ＞ 計画 ＞ 自分の規範** の順を
散文で約束しても守られないので、機械が止める（`rules/absolute-rules.md` A-13）。

判定（transcript_path の末尾を後ろから走査する）:
  - 保守者の発言（ターン冒頭の user テキスト／途中で届いた queued_command／queue-operation enqueue）の後に、
    アシスタントのテキスト応答が 1 つも無い → **deny**（指示の先頭を理由に載せる。読み飛ばしを物理的に防ぐ）
  - 応答はあるが、発言が日本語なのに応答に日本語が無い → **deny**（日本語で応答し直す）
  - それ以外（応答済み／発言が見つからない／transcript が無い／サブエージェント）→ 許可（fail-open）

同じ指示での deny はセッションごとに 1 回だけ（2026-09-21）。PreToolUse の時点では同じターンで書いた
テキスト応答がまだ transcript に書き込まれておらず、応答後も毎回 deny して全ツールが止まった。
1 回目の deny で指示は理由として必ず読まれるので、2 回目以降は通す（状態は TMPDIR の session 別ファイル）。

バイパス用の環境変数は用意しない。止めたいときは settings.json から外す（差分に残る）。
走査幅は INSTRUCTION_GUARD_TAIL_KB（既定 512 KB）。
"""
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

TAIL_KB = int(os.environ.get("INSTRUCTION_GUARD_TAIL_KB", "512"))
JA_RE = re.compile(r"[぀-ヿ一-鿿]")
ESTIMATE_RE = re.compile(r"見積[:：]")
# 自分が選択肢・可否を問うたまま、答えを待たずに着手したことを検出する（保守者の傾向 #39）。
# 2026-09-22: A か B かを尋ねた直後に A を実装し、「いつ作業をして良いと許可をした」と指摘された。
# A-7 は設計文書の承認しか扱っておらず、「直せ」を実装の許可と解釈する余地が残っていた。
ASKED_RE = re.compile(
    r"(どちらにしますか|どれにしますか|どうしますか|いずれ(に|を)しますか|"
    r"(可否|判断|指示|選択)を(お願い|ください|下さい)|"
    r"入れますか|やりますか|進めてよい|よろしいですか|確認をお願い|"
    r"^\s*-\s*\*\*?A[:：]|^\s*\*\*A[:：])", re.M)
# 問いを取り下げた・許可が出た後に自分が書く言葉（これがあれば待ちは解けている）
RESOLVED_RE = re.compile(r"(着手します|実装します|進めます|採用します|了解。|指定|決定|の指示|許可)")
TAG_BLOCK_RE = re.compile(r"<([a-zA-Z][\w-]*)(?:\s[^>]*)?>.*?</\1>", re.S)

# 人ではなく機械（サブエージェント・ハーネス・このフック自身）が書いた本文の印。
# これを含む user エントリは保守者の指示として扱わない。フック自身のエラー文を
# 次の「未応答の指示」として読み直す自己参照ループを防ぐ。
MACHINE_MARKERS = (
    "[instruction-guard]",
    "[reply-language]",
    "[Subagent hand-back]",
    "<task-notification>",
    "<agent-message",
    "Stop hook feedback:",
    "hook success:",
    "[SYSTEM NOTIFICATION - NOT USER INPUT]",
)


def has_ja(s: str) -> bool:
    return bool(JA_RE.search(s or ""))


def is_machine_text(s: str) -> bool:
    return any(m in (s or "") for m in MACHINE_MARKERS)


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
        raw = text_of(content)
        if is_machine_text(raw):
            return None
        s = visible_text(raw)
        return s or None
    if t == "attachment":
        att = entry.get("attachment") or {}
        if att.get("type") == "queued_command":
            raw = text_of(att.get("prompt"))
            if is_machine_text(raw):
                return None
            s = visible_text(raw)
            return s or None
        return None
    if t == "queue-operation" and entry.get("operation") == "enqueue":
        raw = text_of(entry.get("content"))
        if is_machine_text(raw):
            return None
        s = visible_text(raw)
        return s or None
    return None


def assistant_text_of(entry: dict) -> str | None:
    if entry.get("type") != "assistant":
        return None
    s = text_of((entry.get("message") or {}).get("content")).strip()
    return s or None


def tool_uses_of(entry: dict) -> list[tuple[str, str, dict]]:
    """assistant エントリの tool_use ブロック一覧 (id, name, input) を返す（B39 で reply-language.py が使う）。"""
    if entry.get("type") != "assistant":
        return []
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [(b.get("id", ""), b.get("name", ""), b.get("input") or {})
            for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]


def tool_result_of(entry: dict) -> dict[str, tuple[str, bool]]:
    """user エントリの tool_result ブロック {tool_use_id: (本文, is_error)} を返す（B39 で reply-language.py が使う）。"""
    if entry.get("type") != "user":
        return {}
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return {}
    return {b.get("tool_use_id", ""): (text_of(b.get("content")), bool(b.get("is_error")))
            for b in content if isinstance(b, dict) and b.get("type") == "tool_result"}


def tail_lines(path: Path) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > TAIL_KB * 1024:
            f.seek(size - TAIL_KB * 1024)
            f.readline()  # 途中から始まる行を捨てる
        data = f.read()
    return data.decode("utf-8", errors="replace").splitlines()


def judge(lines: list[str]) -> tuple[str, str] | None:
    """(kind, detail) を返す。None は許可。kind は 'unanswered' | 'language' | 'estimate' | 'awaiting'。"""
    reply: str | None = None
    replies: list[str] = []  # 指示より後のアシスタント応答すべて（見積もり行の有無を見る）
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
        a = assistant_text_of(e)
        if a is not None:
            replies.append(a)
            if reply is None:
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
        if not any(ESTIMATE_RE.search(r) for r in replies):
            return ("estimate", inst)
        # 直近の自分の応答が問いで終わっており、保守者がそれに答えていないなら待つ
        if reply is not None and ASKED_RE.search(reply) and not RESOLVED_RE.search(reply):
            return ("awaiting", " ".join(reply.split())[-120:])
        return None
    return None


def notify(context: str) -> int:
    """ツールは止めず、指示を additionalContext で AI の文脈に載せる（画面にエラーを出さない）。"""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": context,
    }}, ensure_ascii=False))
    return 0


def already_denied(session_id: str, inst: str) -> bool:
    """同じ指示で既に deny していれば True。初回は記録して False。"""
    if not session_id:
        return False
    key = hashlib.sha256(inst.encode("utf-8")).hexdigest()
    # f-string 式の中に \\ を書くと Python 3.11 以下で SyntaxError になる（PEP 701 は 3.12 から）。
    # このフックは A-13 を強制する要なので、古い系でも必ず読み込めるよう式の外へ出す。
    safe_id = re.sub(r"[^\w-]", "_", session_id)
    state = Path(tempfile.gettempdir()) / f"instruction-guard-{safe_id}"
    try:
        if state.is_file() and state.read_text().strip() == key:
            return True
        state.write_text(key)
    except OSError:
        return False
    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("agent_id"):
        return 0  # サブエージェント内の呼び出し。親の発言を未応答と誤認する
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
    if already_denied(data.get("session_id", ""), f"{kind}:{inst}"):
        return 0
    head = " ".join(inst.split())[:80]
    if kind == "unanswered":
        return notify(f"[instruction-guard] 未応答の指示: 「{head}」。まだ答えていなければ日本語で答え、"
                      "作業するなら 1 行目を `見積: N分（HH:MM 完了予定）` にする（A-13・A-2）")
    if kind == "estimate":
        return notify(f"[instruction-guard] 指示「{head}」への応答に見積もりが無い。"
                      "作業を続ける前に `見積: N分（HH:MM 完了予定）` を出す（A-2。例外なし）")
    if kind == "awaiting":
        return notify("[instruction-guard] 自分で選択肢・可否を問うた直後に着手しようとしている。"
                      f"直近の応答の末尾: 「…{head}」。**答えを待つ**（保守者の傾向 #39。"
                      "2026-09-22 に A/B を尋ねた直後に A を実装し「いつ作業をして良いと許可をした」と"
                      "指摘された）。答えが来ているなら、その指示に沿っていることを 1 行で示してから進む")
    return notify(f"[instruction-guard] 指示「{head}」は日本語。日本語で応答し直す（A-13）")


if __name__ == "__main__":
    sys.exit(main())
