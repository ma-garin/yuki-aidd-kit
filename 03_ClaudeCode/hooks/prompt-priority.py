#!/usr/bin/env python3
"""保守者の発言が「作業より優先」であることを、発言の直後に注入する UserPromptSubmit フック。

「今すぐ」「報告」「説明」「なぜ」「止め」等を含む発言には、次のツール呼び出しより先に日本語で応答する旨を
additionalContext で添える（instruction-guard.py が同じことを物理的に強制する。こちらは何をすべきかを先に伝える）。
語を含まない通常の発言には何も足さない（毎回のコストを増やさない）。
"""
import datetime
import json
import pathlib
import subprocess
import os
import re
import sys
import zoneinfo

LOCAL_TZ = os.environ.get("AIDD_TZ", "Asia/Tokyo")   # 保守者の時計。実行環境が UTC でもここに合わせる

URGENT_RE = re.compile(r"(今すぐ|直ちに|報告|説明|なぜ|理由|止め|やめ|中断|答え|回答|怒)")


def calibration() -> str:
    """直近の予実から見積の癖を1文で返す。履歴が 3 件未満なら空。

    見積を分で体感で置くと当たらない（実測 0.16 倍＝6 倍の過大見積だった）。
    補正係数を見積を書く時点で見せる。計測は tool-timer.py が持つ。
    """
    timer = pathlib.Path(__file__).resolve().parent / "tool-timer.py"
    if not timer.is_file():
        return ""
    try:
        out = subprocess.run([sys.executable, str(timer), "factor"], capture_output=True,
                             text=True, timeout=5).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return ""
    if len(out) != 2:
        return ""
    try:
        f, n = float(out[0]), int(out[1])
    except ValueError:
        return ""
    if 0.67 <= f <= 1.5:
        return f" 直近 {n} 件の予実はほぼ一致。同じ出し方でよい"
    kind = "過大" if f < 1 else "過小"
    return (f" **直近 {n} 件の実測は見積の {f:.2f} 倍（{kind}見積の癖）。"
            f"素の見積に {f:.2f} を掛けてから出す**")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = data.get("prompt") or ""
    if not isinstance(prompt, str) or not prompt.strip():
        return 0
    # 見積もりの提示は例外なし（A-2）。2 分を超えるかの判断を AI に任せると急ぐ場面ほど飛ばすため、毎回注入する。
    # 現在時刻を同梱する: これが無いと AI は date を実行する前に完了予定時刻を書く。
    # さらにリモート実行環境（Claude Code on the web・CI）は UTC で動くため、素の now() だと保守者の時計と 9 時間ずれる。
    # 保守者の時計に合わせる（2026-09-22 の指摘: 完了予定が UTC で出ていた）。zoneinfo が無い環境では時刻を省く
    try:
        now = datetime.datetime.now(zoneinfo.ZoneInfo(LOCAL_TZ)).strftime("%H:%M")
    except Exception:
        now = ""
    head = f"現在 {now}（{LOCAL_TZ}）。" if now else ""
    cal = calibration()   # 過去の予実から出した補正。体感で置いた分を実測で殴り返す
    tail = f"完了予定は {now} に N 分を足して計算し、推測で書かない" if now else "先に時刻を取得してから書き、推測で書かない"
    ctx = (f"[estimate] {head}ツールを使う作業をするなら、応答の 1 行目を "
           f"`見積: N分（HH:MM 完了予定）` にする。{tail}（A-2。例外なし）{cal}")
    if URGENT_RE.search(prompt):
        ctx = ("[prompt-priority] この発言は進行中の作業より優先する。次のツール呼び出しより先に、この発言に日本語で応答する"
               "（報告・説明・理由を求められたら、切り分けの途中でも止めて答える。instruction-guard.py が強制する。A-13）\n" + ctx)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
