#!/usr/bin/env python3
"""完了の合言葉が出るまで同じ依頼を回し直す、opt-in の完了ループ（Stop フック。G2）。

`/ralph` が `.claude/ralph.json` を作ったときだけ動く。無ければ何もしない（no-op）。

  - 状態ファイル: `.claude/ralph.json` = {"prompt": 依頼文, "iteration": 回数（0 始まり）, "max": 上限（既定 5）,
    "done_phrase": 完了の合言葉（既定 RALPH_DONE）, "session_id": 任意}
    置き場は AIDD_RALPH_STATE（テスト用）> `$CLAUDE_PROJECT_DIR/.claude/` > 入力の cwd の `.claude/`
  - 判定: 最後の応答（入力の last_assistant_message、無ければ transcript の最後の assistant の本文）に done_phrase が
    **無く**、iteration < max なら decision=block で止めずに、reason で依頼文を渡し直す。iteration を 1 増やして書き戻す
  - 終わり方: 応答に done_phrase がある・iteration が max に達した → 止めてよい。状態ファイルを消し、systemMessage で知らせる
  - 壊れた状態（JSON でない・prompt が空・数値でない）→ 何も消さずに止めてよい。systemMessage で警告だけ出す
    （人が中身を見て直すか `/cancel-ralph` で消す）
  - 別セッション: 状態に session_id があり入力の session_id と違えば何もしない。無ければ最初の Stop で今のセッションに結び付ける
  - stop_hook_active（Stop フックの block で続いている）でも回す。無限ループは max で止める（max は 1〜20 に丸める）
  - 失敗しても作業を止めない（fail-open。例外は無言で exit 0）

限界: 合言葉を書けば検証の有無にかかわらず止まる（完了の判定は done-gate スキルと reply-language.py の照合に任せる）。
Codex には Stop フックが無いので使えない（`/ralph` は Claude Code 専用）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

STATE_NAME = "ralph.json"
DEFAULT_MAX = 5
MAX_CAP = 20
DEFAULT_DONE = "RALPH_DONE"

try:
    from secret_patterns import log_decision
except ImportError:          # 記録は付け足し（B12）
    def log_decision(*_a, **_k) -> None:
        return None


def state_path(data: dict) -> Path | None:
    explicit = os.environ.get("AIDD_RALPH_STATE")
    if explicit:
        return Path(explicit)
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), data.get("cwd")):
        if isinstance(base, str) and base:
            return Path(base) / ".claude" / STATE_NAME
    return None


def last_message(data: dict) -> str:
    msg = data.get("last_assistant_message")
    if isinstance(msg, str):
        return msg
    tp = data.get("transcript_path")
    if not isinstance(tp, str) or not tp:
        return ""
    try:
        with open(tp, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 256 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get("message") if isinstance(d, dict) else None
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        content = m.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            if texts:
                return "\n".join(t for t in texts if isinstance(t, str))
    return ""


def emit(obj: dict) -> int:
    print(json.dumps(obj, ensure_ascii=False))
    return 0


def main() -> int:
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return 0
        path = state_path(data)
        if path is None or not path.is_file():
            return 0                                        # opt-in。状態が無ければ何もしない
        try:
            st = json.loads(path.read_text(encoding="utf-8"))
            prompt = st["prompt"]
            it = st.get("iteration", 0)
            mx = st.get("max", DEFAULT_MAX)
            done = st.get("done_phrase") or DEFAULT_DONE
            if (not isinstance(prompt, str) or not prompt.strip() or not isinstance(done, str)
                    or isinstance(it, bool) or isinstance(mx, bool) or not isinstance(it, int) or not isinstance(mx, int)):
                raise ValueError
        except (OSError, ValueError, KeyError, TypeError):
            return emit({"systemMessage": f"[ralph-stop] {path.name} が壊れているのでループしない（消してはいない）。"
                                          "中身を直すか /cancel-ralph で消す"})
        sid = data.get("session_id")
        owner = st.get("session_id")
        if isinstance(owner, str) and owner and isinstance(sid, str) and sid and owner != sid:
            return 0                                        # 別のセッションのループ
        mx = max(1, min(mx, MAX_CAP))
        if done in last_message(data):
            path.unlink(missing_ok=True)
            return emit({"systemMessage": f"[ralph-stop] 完了の合言葉（{done}）を確認。{it + 1} 回目で終了し {path.name} を消した"})
        if it >= mx:
            path.unlink(missing_ok=True)
            return emit({"systemMessage": f"[ralph-stop] 上限 {mx} 回に達したので止める（合言葉 {done} は出ていない）。"
                                          f"{path.name} を消した。続けるなら状況を確かめてから /ralph をやり直す"})
        st["iteration"] = it + 1
        st["max"] = mx
        st["done_phrase"] = done
        if isinstance(sid, str) and sid and not owner:
            st["session_id"] = sid
        path.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
        reason = (f"[ralph-stop] 完了ループ {it + 1}/{mx} 回目。まだ完了の合言葉が出ていないので同じ依頼を続ける。"
                  f"本当に終わった（検証まで済んだ）ときだけ応答に `{done}` と書く。止めたいときは /cancel-ralph。\n\n"
                  f"依頼:\n{prompt}")
        log_decision("ralph-stop", "block", f"完了ループ {it + 1}/{mx}", "Stop", "", data.get("cwd") if isinstance(data.get("cwd"), str) else None)
        return emit({"decision": "block", "reason": reason})
    except Exception:   # ループは付け足し。壊れた入力でも止める側に倒す（無言で exit 0）
        return 0


if __name__ == "__main__":
    sys.exit(main())
