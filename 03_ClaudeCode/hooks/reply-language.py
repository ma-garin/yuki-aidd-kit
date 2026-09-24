#!/usr/bin/env python3
"""ターンの最後の応答が保守者の言語（日本語）になっていなければ止める Stop フック。

instruction-guard.py（PreToolUse）はツールを呼ぶ前を見張る。こちらは**ツールを呼ばずに終わる応答**を見張る。
最後の人の発言に日本語があり、最後のアシスタント応答に日本語が無い（または応答が無い）場合、
decision=block で続行させ、日本語で出し直させる。stop_hook_active のときは何もしない（無限ループ防止）。
判定ロジックは instruction-guard.py と共有する。

合わせて**相槌だけで終わる応答**も止める（H-0「相槌・前置き・締めの申し出を書かない」）。
「承知しました」「了解」「指示待ちです」だけの応答はトークンを消費して情報を渡さない。
内容を答えるか動作するかのどちらかに出し直させる（2026-09-22 の指摘）。
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path


sys.dont_write_bytecode = True  # hooks ディレクトリに __pycache__ を作らない


# 相槌・謝辞・待機表明だけの応答。これらを除いて何も残らなければ情報がゼロ
FILLER_RE = re.compile(
    r"(承知(いた)?し(まし)?た|了解(です|しました|いたしました)?|かしこまりました|"
    r"(わ|分)かりました|失礼(いた)?しました|申し訳(ありません|ございません)(でした)?|すみません|"
    r"指示(を)?(お)?待ち(です|しています|します|いたします)?|お待ちしています|"
    r"無操作|対応します|進めます|はい|ええ|"
    r"以後(は)?(気をつけます|注意します|守ります|書きません|しません))"
)
# 記号・空白・括弧注記。相槌を除いた残りがこれだけなら情報がゼロと判定する
NOISE_RE = re.compile(r"[\s。、．，・…!?！？「」『』（）()\[\]\-—ー:：;；]+")


# 報告の長さの上限（見出し・表・コードブロックを除いた本文の行数）。
# 「つまり何か」を先に 1 文で言わず、経緯から書き始めると読み手の時間を奪う
# （2026-09-22: 1 セッションで「つまりどういうことか」「長い」を 4 回言わせた。傾向 #32）
BODY_MAX_LINES = 12
_BLOCK_RE = re.compile(r"```.*?```", re.S)
_SKIP_LINE_RE = re.compile(r"^\s*(#{1,6}\s|\||[-*]\s|\d+\.\s|>\s|$)")


def body_lines(msg: str) -> list[str]:
    """見出し・表・箇条書き・コードブロックを除いた散文の行。"""
    t = _BLOCK_RE.sub("", msg)
    return [l for l in t.splitlines() if not _SKIP_LINE_RE.match(l)]


def too_long(msg: str) -> int | None:
    n = len(body_lines(msg))
    return n if n > BODY_MAX_LINES else None


def is_filler_only(msg: str) -> bool:
    """相槌と記号を取り除いて何も残らないか。"""
    return NOISE_RE.sub("", FILLER_RE.sub("", msg)) == ""


_TIMER = Path(__file__).resolve().parent / "tool-timer.py"
ACTUAL_RE = re.compile(r"実測[:：]")


# B39: 完了の主張は、同じターン（直近の人の発言以降）に実行したテストの結果と照合する。
# 「完了しました」「全て PASS」等の主張だけで実行していない／FAIL のままなのを機械で止める（2026-09 指摘）。
CLAIM_RE = re.compile(r"(完了しました|実装しました|修正しました|直しました|全て\s*PASS|全緑|テストは通|exit\s*0\s*です)")
NOT_EXECUTED_RE = re.compile(r"(未実行|未検証)")
TEST_CMD_RE = re.compile(
    r"(test-.*\.sh|pytest|npm\s+test|npx\s+(playwright|vitest|jest)|"
    r"check_docs|check_design|python3\s+-m\s+unittest)"
)
FAIL_EQ_RE = re.compile(r"FAIL=(\d+)")
FAIL_LITERAL_RE = re.compile(r"exit 1|❌|Error")
CLAIM_MARKER = "[reply-language] 完了主張の照合"
MAX_CLAIM_BLOCKS = 2  # 3 回目は additionalContext の警告にして通す（無限ループ防止）


def test_failed(result: str) -> bool:
    m = FAIL_EQ_RE.search(result)
    if m and int(m.group(1)) >= 1:
        return True
    return bool(FAIL_LITERAL_RE.search(result))


def last_instruction_index(g, lines: list[str]) -> int | None:
    for i in range(len(lines) - 1, -1, -1):
        try:
            e = json.loads(lines[i])
        except ValueError:
            continue
        if isinstance(e, dict) and not e.get("isSidechain") and g.instruction_of(e) is not None:
            return i
    return None


def test_runs_since(g, lines: list[str], start: int) -> list[tuple[str, str]]:
    """start 行目以降の、テスト系 Bash 実行 (command, tool_result本文) の一覧。"""
    pending: dict[str, str] = {}
    runs: list[tuple[str, str]] = []
    for line in lines[start:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        for tid, name, inp in g.tool_uses_of(e):
            if name != "Bash":
                continue
            cmd = str((inp or {}).get("command", ""))
            if TEST_CMD_RE.search(cmd):
                pending[tid] = cmd
        for tid, content in g.tool_result_of(e).items():
            if tid in pending:
                runs.append((pending[tid], content))
    return runs


def claim_block_count(lines: list[str], start: int) -> int:
    """同じターンで、この照合による差し戻しが transcript に何回残っているか（無限ループ防止用）。"""
    return sum(1 for l in lines[start:] if CLAIM_MARKER in l)


def check_claim(g, tp0: str) -> tuple[str, int, list[str]] | None:
    """完了の主張の根拠が無ければ (問題の説明, 直近の人の発言の行番号, transcript の行) を返す。
    transcript が無い・人の発言が見つからない（判定できない）場合は None（fail-open）。
    """
    if not tp0 or not Path(tp0).is_file():
        return None
    try:
        lines = g.tail_lines(Path(tp0))
    except OSError:
        return None
    idx = last_instruction_index(g, lines)
    if idx is None:
        return None
    runs = test_runs_since(g, lines, idx)
    if not runs:
        return ("同じターンでテスト系の実行が 0 回", idx, lines)
    cmd, result = runs[-1]
    if test_failed(result):
        short_cmd = " ".join(cmd.split())[:40]
        short_result = " ".join(result.split())[:60]
        return (f"直近の `{short_cmd}` の結果が失敗（{short_result}）", idx, lines)
    return None


def missing_actual(msg: str) -> str | None:
    """このターンでツールを使ったのに実測行が無ければ、貼るべき実測の1行を返す。

    見積（A-2）は実測と対で初めて意味を持つ。数えているのに書かないのを止める。
    計測器が無い・0 回（会話だけのターン）なら None。
    """
    if ACTUAL_RE.search(msg):
        return None
    # 回数の判定は内訳（--full）で行い、返すのは最短形にする
    if "/ 0回" in timer("report", "--full"):
        return None
    out = timer("report")
    return out or None


# 見積の分と、差異を説明した形跡。H-6「見積の 1.5 倍を超えたら原因 1 行」を両方向に広げる
# （このセッションで起きたのは逆向きの乖離＝見積 40 分に対し実測 6 分。過大見積も同じ害）
EST_RE = re.compile(r"見積[:：]\s*(\d+)\s*分")
GAP_RE = re.compile(r"(差異|超過|再見積|見込み違い|見積より)")
GAP_MIN_EST = 3   # 3 分未満の見積は誤差が支配するので見ない


def timer(*args: str) -> str:
    if not _TIMER.is_file():
        return ""
    try:
        return subprocess.run([sys.executable, str(_TIMER), *args], capture_output=True,
                              text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def estimate_min(g, lines: list[str]) -> int | None:
    """直近の人の発言より後のアシスタント応答から、見積の分を拾う。"""
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        a = g.assistant_text_of(e)
        if a:
            # 実測を書いた応答は完了報告。それより前の見積は使い切っているので拾わない
            # （委譲先の報告で続く応答が、前の報告の見積と比較されて偽の乖離になる。2026-09-24 01:35）
            if ACTUAL_RE.search(a):
                return None
            m = EST_RE.search(a)
            if m:
                return int(m.group(1))
            continue
        if g.instruction_of(e) is not None:
            return None
    return None


def gap_note(est: int, elapsed: float) -> str | None:
    """見積と経過が離れていて、説明が要る場合にその一文を返す。"""
    if est < GAP_MIN_EST:
        return None
    if elapsed > est * 1.5:
        return f"見積 {est} 分に対し経過 {elapsed:.0f} 分（1.5 倍超）"
    if elapsed * 3 < est:
        return f"見積 {est} 分に対し経過 {elapsed:.0f} 分（3 分の 1 未満＝過大見積）"
    return None


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
    missing = missing_actual(msg)
    if missing is not None:
        reason = (f"[reply-language] 応答の最後に実測が無い。`見積: N分 / {missing}` の形で1行だけ足す（A-2）")
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0
    n = too_long(msg)
    if n is not None:
        reason = (f"[reply-language] 散文が {n} 行ある（上限 {BODY_MAX_LINES}）。"
                  "**1 文で「つまり何か」を先に書き、詳細は表か箇条書きにする**。"
                  "経緯・分析・弁明は求められたときだけ（H-0・A-9）")
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0
    if is_filler_only(msg):
        reason = ("[reply-language] 相槌だけで終わっている。相槌・謝辞・待機表明は情報を渡さない（H-0）。"
                  "問いに答える・結果を渡す・動作する のどれかに出し直す")
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0
    g = load_guard()
    tp0 = data.get("transcript_path", "")
    if CLAIM_RE.search(msg) and not NOT_EXECUTED_RE.search(msg):
        found = check_claim(g, tp0)
        if found is not None:
            problem, idx, lines = found
            if claim_block_count(lines, idx) >= MAX_CLAIM_BLOCKS:
                ctx = f"{CLAIM_MARKER}: {problem}（{MAX_CLAIM_BLOCKS} 回を超えたので通知に留める。無限ループ防止）"
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "Stop", "additionalContext": ctx}}, ensure_ascii=False))
                return 0
            reason = (f"{CLAIM_MARKER}: {problem}。"
                      "実行してから主張するか、『提案（未実行）』と書き直す")
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
            return 0
    # 委譲待ちの途中報告（「進行中」を含む）は完了報告ではないので、予実を突き合わせず履歴にも積まない。
    # 突き合わせると経過が見積に届く前に「過大見積」と誤判定し、偽の予実で校正係数を壊す（2026-09-23 に 5 回）
    if not GAP_RE.search(msg) and "進行中" not in msg and tp0 and Path(tp0).is_file():
        try:
            est = estimate_min(g, g.tail_lines(Path(tp0)))
        except OSError:
            est = None
        raw = timer("elapsed")
        if est is not None and raw:
            try:
                elapsed = float(raw)
            except ValueError:
                elapsed = None
            note = None
            if elapsed is not None:
                # 予実を履歴に積む。次の見積の校正に使う（prompt-priority が係数を注入する）
                timer("record", str(est), f"{elapsed:.2f}")
                note = gap_note(est, elapsed)
            if note:
                reason = (f"[reply-language] 予実が離れている: {note}。原因を 1 行で書き、"
                          "`06_保守者向け/02_設計判断の根拠/speed-harness.md` の実測記録に追記してから報告する"
                          "（H-6。見積の作り方を直さないと次も外す）")
                print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
                return 0
    # 完了報告（実測あり・進行中でない）を通した時点でターンの計測を区切る。区切らないと、委譲先の報告で
    # 続く次の応答が保守者の発言からの累計経過と比較され、偽の乖離と偽の予実が積まれる（2026-09-24 01:35 に 4 件）
    if ACTUAL_RE.search(msg) and "進行中" not in msg:
        timer("reset")
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
