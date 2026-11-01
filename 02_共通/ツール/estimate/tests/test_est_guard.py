"""est-guard フック（見積の表示義務・根拠のない時間見積の阻止）と est.py の連携テスト。"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HOOK = ROOT / "03_ClaudeCode" / "hooks" / "est-guard.py"
EST = ROOT / "02_共通" / "ツール" / "estimate" / "est.py"


def run_hook(ev, env):
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev, ensure_ascii=False), capture_output=True, text=True, env=env)
    return r.returncode, r.stderr


def env_for(tmp_path):
    import os
    return {**os.environ, "EST_PENDING": str(tmp_path / "pending.json"), "EST_QUOTES": str(tmp_path / "quotes.json")}


def pre(tool, inp):
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": inp}


def test_pending_blocks_other_tools_until_announced(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "pending.json").write_text(json.dumps({"line": "再見積: 16分（12:51 完了予定）", "at": 0}, ensure_ascii=False))
    assert run_hook(pre("Bash", {"command": "ls"}), env)[0] == 2
    assert run_hook(pre("Bash", {"command": "python3 est.py tick"}), env)[0] == 0
    assert run_hook(pre("SendUserMessage", {"message": "再見積: 16分（12:51 完了予定）\n続行します"}), env)[0] == 0
    assert not (tmp_path / "pending.json").exists()
    assert run_hook(pre("Bash", {"command": "ls"}), env)[0] == 0
    # 表示済みの値は以後の報告で再掲できる
    assert run_hook(pre("SendUserMessage", {"message": "再見積 16分のとおり進行"}), env)[0] == 0


def test_rough_and_unbacked_estimates_are_blocked(tmp_path):
    env = env_for(tmp_path)
    code, err = run_hook(pre("SendUserMessage", {"message": "| A | コスト: 約1.5時間 |"}), env)
    assert code == 2 and "約1.5時間" in err
    assert run_hook(pre("AskUserQuestion", {"questions": [{"question": "どれ?", "options": [{"label": "B", "description": "コスト: 4時間"}]}]}), env)[0] == 2
    (tmp_path / "quotes.json").write_text(json.dumps([{"min": 240, "at": 9e12}]))
    assert run_hook(pre("AskUserQuestion", {"questions": [{"question": "どれ?", "options": [{"label": "B", "description": "コスト: 4時間"}]}]}), env)[0] == 0
    # 見積の文脈でない時間や実測は対象外
    assert run_hook(pre("SendUserMessage", {"message": "毎朝 7:45 に配信。CI は 2分前に成功"}), env)[0] == 0
    assert run_hook(pre("SendUserMessage", {"message": "見積: 3分 / 実測: 5分"}), env)[0] == 0


def test_stop_requires_line_in_final_reply(tmp_path):
    env = env_for(tmp_path)
    (tmp_path / "pending.json").write_text(json.dumps({"line": "見積: 3分（12:47 完了予定）", "at": 0}, ensure_ascii=False))
    tr = tmp_path / "t.jsonl"
    tr.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "作業しました"}]}}, ensure_ascii=False) + "\n")
    ev = {"hook_event_name": "Stop", "transcript_path": str(tr), "stop_hook_active": False}
    assert run_hook(ev, env)[0] == 2
    tr.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "見積: 3分（12:47 完了予定）\n完了"}]}}, ensure_ascii=False) + "\n")
    assert run_hook(ev, env)[0] == 0 and not (tmp_path / "pending.json").exists()


def test_est_plan_writes_pending_and_quote_whitelists(tmp_path):
    env = env_for(tmp_path)
    work = tmp_path / "est"; work.mkdir()
    (work / "est.py").write_text(EST.read_text(encoding="utf-8"), encoding="utf-8")
    sh = lambda *a: subprocess.run([sys.executable, str(work / "est.py"), *a], capture_output=True, text=True, env=env)
    sh("t0")
    out = sh("plan", "UI改修", "5").stdout
    line = json.loads((tmp_path / "pending.json").read_text(encoding="utf-8"))["line"]
    assert line.startswith("見積: ") and "完了予定）" in line and line in out
    q = sh("quote", "UI改修", "100").stdout
    m = int(q.split("試算=")[1].split("分")[0])
    assert any(v["min"] == m for v in json.loads((tmp_path / "quotes.json").read_text()))
