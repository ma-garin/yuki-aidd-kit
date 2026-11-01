import os, shutil, subprocess, sys, tempfile, json
SRC = os.path.join(os.path.dirname(__file__), "..", "est.py")

def run(d, *a):
    r = subprocess.run([sys.executable, os.path.join(d, "est.py"), *a], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr

def setup():
    d = tempfile.mkdtemp(); shutil.copy(SRC, d); return d

def test_basic_flow_and_log():
    d = setup()
    assert run(d, "t0")[0] == 0
    rc, out = run(d, "plan", "UI改修", "5", "--lines", "250")
    assert rc == 0 and "106s" in out
    assert run(d, "plan", "UI改修", "3")[0] != 0          # 見積は1回のみ
    assert run(d, "end")[0] == 0
    rows = open(os.path.join(d, "log.csv")).read().splitlines()
    assert len(rows) == 2 and rows[1].split(",")[2] == "UI改修"

def test_input_validation():
    d = setup(); run(d, "t0")
    assert run(d, "plan", "謎", "2")[0] != 0
    assert run(d, "plan", "UI改修", "0")[0] != 0

def test_t0_refuses_unfinished_and_abort_logs_unfinished():
    d = setup(); run(d, "t0"); run(d, "plan", "調査", "2")
    assert run(d, "t0")[0] != 0
    assert run(d, "abort")[0] == 0
    assert open(os.path.join(d, "log.csv")).read().splitlines()[1].endswith(",1")

def test_forgotten_pause_is_excluded():
    d = setup(); run(d, "t0"); run(d, "plan", "調査", "2")
    s = json.load(open(os.path.join(d, "state.json"))); s["last"] -= 700; s["t0"] -= 700; s["open"] -= 700
    json.dump(s, open(os.path.join(d, "state.json"), "w"))
    rc, out = run(d, "tick")
    assert rc == 0 and "除外" in out
