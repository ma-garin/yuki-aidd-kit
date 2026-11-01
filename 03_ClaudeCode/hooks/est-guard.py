#!/usr/bin/env python3
"""見積の表示義務と、根拠のない時間見積を止めるフック（PreToolUse / Stop 共用）。

背景（2026-11-01 の指摘）: est.py で再見積を計算したのに応答に出さず作業を続けた。
選択肢の比較表に est.py を通さない「約1.5時間」を書いた。どちらもルール違反で、規律に頼らず機械的に止める。

1. 表示義務: est.py が plan/reest を出すと ~/.claude/est-pending.json に見積行を書く。
   - PreToolUse: その行を含む SendUserMessage が出るまで、他のツール呼び出しを止める（est.py 自身の呼び出しは通す）。
   - Stop: 最後のアシスタント応答に行が無ければ終了を止める。出ていれば pending を消す。
2. 根拠のない時間見積: SendUserMessage / AskUserQuestion / 最終応答に「約N分」「約N時間」「N時間」「N分」が
   見積の文脈（見積・所要・コスト・かかる・工数）で現れたら、est.py quote/plan/reest で出した値か照合する。
   照合できない値は止める。「約」はそもそも禁止（est.py の値は確定値として書く）。
"""
import json
import os
import re
import sys
import time

PENDING = os.environ.get("EST_PENDING", os.path.expanduser("~/.claude/est-pending.json"))
QUOTES = os.environ.get("EST_QUOTES", os.path.expanduser("~/.claude/est-quotes.json"))
CTX = re.compile(r"見積|所要|コスト|かかる|工数|完了予定")
ROUGH = re.compile(r"約\s*\d+(?:\.\d+)?\s*(?:分|時間)")
DUR = re.compile(r"(\d+(?:\.\d+)?)\s*(分|時間)(?![前後間])")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def allowed_minutes():
    vals = {q.get("min") for q in load(QUOTES, []) if time.time() - q.get("at", 0) < 6 * 3600}
    pend = load(PENDING, {}).get("line", "")
    vals |= {int(m) for m in re.findall(r"(\d+)分", pend)}
    return vals


def unbacked_estimates(text):
    """見積の文脈にある時間のうち、est.py の値で裏付けられないもの。"""
    bad = [m.group(0) for m in ROUGH.finditer(text)]
    ok = allowed_minutes()
    for line in text.splitlines():
        if not CTX.search(line) or "実測" in line:
            continue
        for num, unit in DUR.findall(line):
            mins = float(num) * (60 if unit == "時間" else 1)
            if mins != int(mins) or int(mins) not in ok:
                bad.append(f"{num}{unit}")
    return sorted(set(bad))


def outgoing_text(tool, inp):
    if tool == "SendUserMessage":
        return inp.get("message", "")
    if tool == "AskUserQuestion":
        return json.dumps(inp.get("questions", []), ensure_ascii=False)
    return ""


def last_assistant_text(transcript):
    text = ""
    try:
        with open(transcript, encoding="utf-8") as f:
            for raw in f:
                try:
                    e = json.loads(raw)
                except ValueError:
                    continue
                if e.get("type") != "assistant":
                    continue
                parts = (e.get("message") or {}).get("content") or []
                t = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text")
                if t:
                    text = t
    except OSError:
        pass
    return text


def clear_pending(line):
    """表示済みの見積は、以後の報告で再掲できるよう許可リストに移す。"""
    qs = [q for q in load(QUOTES, []) if time.time() - q.get("at", 0) < 6 * 3600]
    qs += [{"min": int(m), "at": int(time.time())} for m in re.findall(r"(\d+)分", line)]
    try:
        with open(QUOTES, "w", encoding="utf-8") as f:
            json.dump(qs, f)
        os.remove(PENDING)
    except OSError:
        pass


def block(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        return
    pend = load(PENDING, {}).get("line")
    if ev.get("hook_event_name") == "Stop":
        if ev.get("stop_hook_active"):
            return
        text = last_assistant_text(ev.get("transcript_path", ""))
        if pend:
            if pend not in text:
                block(f"est-guard: 見積行「{pend}」を応答の1行目にそのまま出してください。")
            clear_pending(pend)
        bad = unbacked_estimates(text)
        if bad:
            block(f"est-guard: est.py で計算していない時間見積があります: {'、'.join(bad)}。est.py quote/plan/reest の値に置き換え、「約」を外してください。")
        return
    tool, inp = ev.get("tool_name", ""), ev.get("tool_input") or {}
    out = outgoing_text(tool, inp)
    if out:
        bad = unbacked_estimates(out)
        if bad:
            block(f"est-guard: est.py で計算していない時間見積があります: {'、'.join(bad)}。est.py quote で試算し、その値（「約」なし）を書いてください。")
        if pend and pend in out:
            clear_pending(pend)
        return
    if pend and not (tool == "Bash" and "est.py" in inp.get("command", "")):
        block(f"est-guard: 見積行「{pend}」をまだ応答に出していません。先に SendUserMessage でこの行をそのまま出してください。")


if __name__ == "__main__":
    main()
