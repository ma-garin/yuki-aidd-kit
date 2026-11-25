"""中間報告を本文に出さずに作業を続けることを止める（tool-timer.py pre から呼ぶ。全ツールの PreToolUse）。

経緯:
  2026-11-24 作成。instruction-guard.py から呼ぶ形だったが、instruction-guard.py が settings.json に未配線で
  一度も動かなかった。さらに見積を metering の状態ファイルから読んでいたため、AIDD_METERING_STATE で
  別の場所に置くと見えなかった。2026-11-25 に 66 分中 28 分おきの報告しか出ず、利用者に止められた。
  → 2026-11-25 作り直し: 配線済みの tool-timer.py pre から呼ぶ／見積は会話の記録だけから読む。

判定（会話の記録 transcript だけを見る。状態ファイルに頼らない）:
  - 進行中の見積 = 本文に書いた最後の「見積もり：N分」「【見積もり：N分」「【見積：N分」。
    その後に終了行（「実測:」を含む【…】）を書いていれば見積は終わっている。
  - 間隔 = 見積 N 分 × 60 ÷ 5 秒（下限 30 秒）。進行中の見積が無いときは既定 300 秒。
  - 基準時刻 = 本文で最後に報告した時刻（【進捗:…】・見積の行・終了行）と、利用者の最後の発言の時刻の遅い方。
  - いま − 基準時刻 が間隔を超えたら deny。
  - metering.py だけを実行する Bash は通す（報告に貼る行を取るため）。
  - 間隔より長く走りうる Bash（timeout 未指定は 120 秒扱い）は先に止める（実行中は報告できない）。
本文はツール呼び出しの直前に書かれるため、超過と判定したときだけ短く待って読み直す。
判定できない（記録が読めない等）ときは通す。
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

TAIL_KB = 4096
DEFAULT_INTERVAL = 300.0
MIN_INTERVAL = 30.0
EST_RE = re.compile(r"(?:【\s*)?見積(?:もり)?[：:]\s*(\d+(?:\.\d+)?)\s*分")
END_MARK = "実測:"
PROGRESS_MARK = "【進捗:"
METERING_ONLY = re.compile(r"(?:AIDD_METERING_STATE=\S+ +)?python3 +\S*metering\.py +(begin|mid|end|factor|now)\b[^;&|`$()<>\n]*")


def tail_lines(path: Path) -> list[str]:
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > TAIL_KB * 1024:
            f.seek(size - TAIL_KB * 1024)
            f.readline()
        data = f.read()
    return data.decode("utf-8", errors="replace").splitlines()


def _ts(e: dict) -> float | None:
    try:
        return datetime.fromisoformat(str(e.get("timestamp")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _is_prompt(e: dict) -> bool:
    """利用者の発言（ツールの結果・hook の注入・要約ではない）。"""
    if e.get("type") != "user" or e.get("isMeta") or e.get("isCompactSummary"):
        return False
    c = (e.get("message") or {}).get("content")
    if isinstance(c, str):
        return bool(c.strip()) and not c.lstrip().startswith("<")
    if isinstance(c, list):
        kinds = {b.get("type") for b in c if isinstance(b, dict)}
        return "text" in kinds and "tool_result" not in kinds
    return False


JST = timezone(timedelta(hours=9))
CLOCK_TOL_MIN = 1
PAREN_TIME = re.compile(r"[（(](\d{1,2}):(\d{2})[）)]")
START_TIME = re.compile(r"開始:(\d{1,2}):(\d{2})")
END_TIME = re.compile(r"終了:(\d{1,2}):(\d{2})")


def clock_error(line: str, ts: float) -> str | None:
    """報告の行に書いた「いまの時刻」が、記録された時刻と CLOCK_TOL_MIN 分を超えてずれていれば理由を返す。
    見るのは: 進捗行の（HH:MM）・開始行の 開始:・終了行の（HH:MM）と 終了:。見積の行の（HH:MM）は予定なので見ない。"""
    if "【" not in line:
        return None
    found = []
    if PROGRESS_MARK in line or END_MARK in line:
        found += PAREN_TIME.findall(line)
    if END_MARK in line:
        found += END_TIME.findall(line)
    if re.search(r"【\s*見積[：:]", line) and END_MARK not in line:
        found += START_TIME.findall(line)
    now = datetime.fromtimestamp(ts, JST)
    for h, m in found:
        diff = abs((now.hour * 60 + now.minute) - (int(h) * 60 + int(m)))
        diff = min(diff, 1440 - diff)
        if diff > CLOCK_TOL_MIN:
            return f"報告の時刻 {int(h):02d}:{m} が実際の {now:%H:%M} と {diff} 分ずれている"
    return None


def scan(lines: list[str]) -> dict:
    """{est: 進行中の見積分 or None, last: 基準時刻 or None, clock: 最後の報告の時刻の誤り or None}"""
    est: float | None = None
    last: float | None = None
    clock: str | None = None
    for line in lines:
        if '"assistant"' not in line and '"user"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict) or e.get("isSidechain"):
            continue
        ts = _ts(e)
        if ts is None:
            continue
        if _is_prompt(e):
            last = max(last or 0.0, ts)
            continue
        if e.get("type") != "assistant":
            continue
        texts = [b.get("text", "") for b in (e.get("message") or {}).get("content") or []
                 if isinstance(b, dict) and b.get("type") == "text"]
        for t in texts:
            reported = False
            for ln in t.splitlines():
                if PROGRESS_MARK in ln or (END_MARK in ln and "【" in ln) or re.search(r"【\s*見積[：:]", ln):
                    clock = clock_error(ln, ts)
                if END_MARK in ln and "【" in ln:
                    est, reported = None, True
                    continue
                m = EST_RE.search(ln)
                if m:
                    est, reported = float(m.group(1)), True
                if PROGRESS_MARK in ln:
                    reported = True
            if reported:
                last = max(last or 0.0, ts)
    return {"est": est, "last": last, "clock": clock}


def interval_of(est: float | None) -> float:
    return DEFAULT_INTERVAL if est is None else max(est * 60 / 5, MIN_INTERVAL)


def check(data: dict, lines: list[str], now: float | None = None) -> str | None:
    """deny の理由を返す。通すときは None。"""
    cmd = str((data.get("tool_input") or {}).get("command", "")).strip()
    if data.get("tool_name") == "Bash" and METERING_ONLY.fullmatch(cmd):
        return None
    s = scan(lines)
    if s["clock"]:
        return (f"[progress-report] {s['clock']}。時刻を自分で書かない。`python3 ~/.agents/skills/work-metering/scripts/metering.py mid <k>`"
                "（または now）を実行し、その出力どおりの行で本文に訂正を書いてから次のツールを使う")
    interval = interval_of(s["est"])
    if data.get("tool_name") == "Bash":
        try:
            limit = float((data.get("tool_input") or {}).get("timeout") or 120000) / 1000
        except (TypeError, ValueError):
            limit = 120.0
        if limit > interval:
            return (f"[progress-report] このコマンドは最大 {limit:.0f} 秒走り、中間報告の間隔 {interval:.0f} 秒を超える。"
                    f"timeout を {interval * 1000:.0f} 以下にして分割するか、本文で再見積（見積もり：N分）して間隔を広げる")
    if s["last"] is None:
        return None
    gap = (now or time.time()) - s["last"]
    if gap <= interval:
        return None
    basis = f"見積 {s['est']:g} 分 × 60 ÷ 5" if s["est"] is not None else "見積なしの既定"
    return (f"[progress-report] 本文で最後に報告してから {gap:.0f} 秒（間隔 {interval:.0f} 秒 = {basis}）。"
            "`python3 ~/.agents/skills/work-metering/scripts/metering.py mid <k>` を実行し、"
            "その出力の【進捗:…】行を本文にそのまま書いてから次のツールを使う（ツール出力に出しただけでは報告ではない）")


def gate(data: dict) -> str | None:
    """hook から呼ぶ入口。超過のときだけ本文の書き込み遅れを待って読み直す。"""
    tp = data.get("transcript_path")
    if not tp or not Path(tp).is_file():
        return None
    why = None
    # 本文は記録にまとめて後から書き込まれ、ツールの判定より 1〜2 秒遅れることがある（2026-11-25 実測:
    # 本文の 4 秒後の Edit が 1.2 秒の読み直しで本文を読めず誤って拒否）。拒否しそうなときだけ最大 7.5 秒読み直す。
    for wait in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
        time.sleep(wait)
        try:
            why = check(data, tail_lines(Path(tp)))
        except OSError:
            return None
        if why is None:
            return None
    return why
