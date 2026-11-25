"""中間報告の強制（progress_report_gate）。拒否する場合と通す場合の両方を確かめる。"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import progress_report_gate as g  # noqa: E402

T0 = 1_800_000_000.0


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def asst(t, text):
    return json.dumps({"type": "assistant", "timestamp": _iso(t),
                       "message": {"content": [{"type": "text", "text": text}]}}, ensure_ascii=False)


def user(t, text):
    return json.dumps({"type": "user", "timestamp": _iso(t), "message": {"content": text}}, ensure_ascii=False)


EDIT = {"tool_name": "Edit", "tool_input": {}}


def test_denies_after_interval_from_estimate():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）\n目的: …")]
    assert g.check(EDIT, lines, now=T0 + 5 + 119) is None          # 間隔 120 秒以内は通す
    assert "progress-report" in g.check(EDIT, lines, now=T0 + 5 + 121)


def test_progress_line_resets_the_clock():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）"),
             asst(T0 + 100, "【進捗:順調 | 経過時間：2分（11:37） | 終了:12:00 | タスク数:1/3】")]
    assert g.check(EDIT, lines, now=T0 + 215) is None
    assert g.check(EDIT, lines, now=T0 + 225) is not None


def test_plain_text_without_report_line_does_not_reset():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）"), asst(T0 + 100, "読みます。")]
    assert g.check(EDIT, lines, now=T0 + 130) is not None


def test_end_line_closes_estimate_and_falls_back_to_default():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）"),
             asst(T0 + 60, "【見積:10分 | 実測:1分 | 開始:11:00 | 終了:11:01 | 作業時間記録:成功】")]
    assert g.check(EDIT, lines, now=T0 + 60 + 299) is None         # 見積なしの既定 300 秒
    assert g.check(EDIT, lines, now=T0 + 60 + 301) is not None


def test_no_estimate_uses_default_from_user_prompt():
    lines = [user(T0, "調べて")]
    assert g.check(EDIT, lines, now=T0 + 299) is None
    assert g.check(EDIT, lines, now=T0 + 301) is not None


def test_new_user_prompt_resets_clock():
    lines = [asst(T0, "見積もり：10分（12:00）"), user(T0 + 500, "中間報告！")]
    assert g.check(EDIT, lines, now=T0 + 560) is None


def test_metering_only_bash_passes_even_when_overdue():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）")]
    for cmd in ("python3 ~/.agents/skills/work-metering/scripts/metering.py mid 2",
                "AIDD_METERING_STATE=/x/m.json python3 ~/.agents/skills/work-metering/scripts/metering.py mid 2"):
        assert g.check({"tool_name": "Bash", "tool_input": {"command": cmd}}, lines, now=T0 + 999) is None
    chained = {"tool_name": "Bash", "tool_input": {"command": "python3 metering.py mid 2; pytest"}}
    assert g.check(chained, lines, now=T0 + 999) is not None


def test_long_bash_is_denied_before_it_starts():
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：5分（12:00）")]   # 間隔 60 秒
    long_cmd = {"tool_name": "Bash", "tool_input": {"command": "pytest", "timeout": 580000}}
    assert "最大 580 秒" in g.check(long_cmd, lines, now=T0 + 10)
    short = {"tool_name": "Bash", "tool_input": {"command": "pytest", "timeout": 50000}}
    assert g.check(short, lines, now=T0 + 10) is None


def test_sidechain_and_tool_results_are_ignored():
    side = json.dumps({"type": "assistant", "isSidechain": True, "timestamp": _iso(T0 + 200),
                       "message": {"content": [{"type": "text", "text": "【進捗:順調】"}]}}, ensure_ascii=False)
    tr = json.dumps({"type": "user", "timestamp": _iso(T0 + 200),
                     "message": {"content": [{"type": "tool_result", "content": "【進捗:順調】"}]}})
    lines = [user(T0, "直して"), asst(T0 + 5, "見積もり：10分（12:00）"), side, tr]
    assert g.check(EDIT, lines, now=T0 + 210) is not None


def test_hook_entry_emits_deny_json(tmp_path):
    import subprocess
    import time
    tp = tmp_path / "t.jsonl"
    now = time.time()
    tp.write_text("\n".join([user(now - 900, "直して"), asst(now - 890, "見積もり：10分（12:00）")]) + "\n")
    payload = json.dumps({"tool_name": "Edit", "tool_input": {}, "transcript_path": str(tp)})
    hook = Path(__file__).resolve().parents[1] / "tool-timer.py"
    out = subprocess.run([sys.executable, str(hook), "pre"], input=payload, capture_output=True, text=True,
                         env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"}, timeout=20)
    d = json.loads(out.stdout)
    assert d["hookSpecificOutput"]["permissionDecision"] == "deny"
