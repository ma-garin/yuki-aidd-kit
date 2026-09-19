#!/usr/bin/env python3
"""会話の寿命を見張る UserPromptSubmit フック（警告して通す。止めない）。

`rules/model-routing.md` の「1 時間以上離れて再開するときは要約から始める」「無関係なタスクへ移るときは /clear」を
人の記憶に頼らず機械が思い出させる。判断は人が行うので additionalContext を注入するだけ。

  - アイドル判定: hook 入力の transcript_path の mtime と現在時刻の差（状態ファイル不要）。
    CONTEXT_GUARD_IDLE_MIN（既定 55 分。サブスクのキャッシュ寿命 1 時間の手前）を超えたら
    「キャッシュが切れ、この 1 通は全履歴を再処理する」旨を注入
  - 肥大判定: transcript のサイズが CONTEXT_GUARD_MAX_MB（既定 4 MB ≒ 数十万トークン）を超えたら
    「区切りで /compact か /clear」を注入
"""
import json
import os
import sys
import time
from pathlib import Path

IDLE_MIN = int(os.environ.get("CONTEXT_GUARD_IDLE_MIN", "55"))
MAX_MB = float(os.environ.get("CONTEXT_GUARD_MAX_MB", "4"))


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tp = data.get("transcript_path", "")
    if not tp or not Path(tp).is_file():
        return 0
    try:
        st = Path(tp).stat()
    except OSError:
        return 0
    idle_min = (time.time() - st.st_mtime) / 60
    size_mb = st.st_size / (1024 * 1024)

    notes = []
    if idle_min > IDLE_MIN:
        notes.append(
            f"[context-guard] 前回の応答から {int(idle_min)} 分空いています。プロンプトキャッシュ（寿命 1 時間）が切れ、"
            "この 1 通は会話全体を再処理します。無関係な作業なら `/clear` してから送り直す、続きなら"
            "「ここまでの決定事項と変更ファイル」を 5 行で要約してから進める（rules/model-routing.md）。"
        )
    if size_mb > MAX_MB:
        notes.append(
            f"[context-guard] 会話ログが {size_mb:.1f} MB あります。毎メッセージが履歴全体を引きます。"
            "作業の区切りで `/compact`（残すもの: 決定事項・変更ファイル・未解決）か、別タスクなら `/clear`。"
        )
    if not notes:
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes),
    }}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
