#!/usr/bin/env python3
"""Codex CLI の4行ステータス（Windows 版）。Windows Terminal の下部ペインに表示する。

集計（料金・残量・サブエージェント・表示行）は codex_status.py をそのまま使う（複製しない）。
Windows で動かない 4 点だけを置き換える:
  tmux status        → Windows Terminal の split-pane（wt.exe）に描画ループ
  ps / lsof          → ~/.codex/sessions の rollout をセッション開始時刻と cwd で特定
  select（パイプ）   → 読み取りスレッド＋キュー
  ~/.local/bin リンク → PowerShell プロファイルの codex 関数（install-win.ps1）
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess as sp
import sys
import tempfile
import threading
import time
import types

HERE = Path(__file__).resolve().parent


def _backend():
    found = os.environ.get("CODEX_STATUS_BACKEND")
    if found:
        return found
    npm = Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe"
    if npm.is_file():
        return str(npm)
    return shutil.which("codex.exe") or shutil.which("codex.cmd") or "codex"


os.environ["CODEX_STATUS_BACKEND"] = _backend()
# fcntl は旧ラッパー向けの live_agents でしか使わない。Windows では呼ばないので空のモジュールで import を通す
sys.modules.setdefault("fcntl", types.ModuleType("fcntl"))
sys.path.insert(0, str(HERE))
import codex_status as cs  # noqa: E402

BACKEND = cs.BACKEND
GREY, RESET = "\x1b[38;5;245m", "\x1b[0m"


def fetch_limits(stop, usage):
    """公式 App Server の読み取り API（原本と同じ手順）。select の代わりに読み取りスレッドを使う。"""
    child = None
    try:
        child = sp.Popen([BACKEND, "app-server", "--stdio"], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.DEVNULL,
                         bufsize=0, creationflags=getattr(sp, "CREATE_NO_WINDOW", 0))
        lines: queue.Queue = queue.Queue()

        def pump():
            for raw in iter(child.stdout.readline, b""):
                lines.put(raw)
            lines.put(None)
        threading.Thread(target=pump, daemon=True).start()

        def send(message):
            child.stdin.write((json.dumps(message) + "\n").encode())
            child.stdin.flush()
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codex_statusline", "version": "1.0"}}})
        ready, next_poll, deadline = False, time.monotonic() + 15, time.monotonic() + 15
        while not stop.is_set() and child.poll() is None:
            try:
                raw = lines.get(timeout=.5)
            except queue.Empty:
                raw = b""
            if raw is None:
                break
            if raw.strip():
                msg = json.loads(raw)
                if msg.get("id") == 1:
                    if "error" in msg:
                        return
                    send({"method": "initialized", "params": {}})
                    ready, next_poll = True, 0
                elif msg.get("id") == 2:
                    result = msg.get("result") or {}
                    limits = (result.get("rateLimitsByLimitId") or {}).get("codex") or result.get("rateLimits")
                    if isinstance(limits, dict) and limits.get("limitId", "codex") == "codex":
                        usage.limits = limits
            if not ready and time.monotonic() > deadline:
                break
            if ready and time.monotonic() >= next_poll:
                send({"id": 2, "method": "account/rateLimits/read"})
                next_poll = time.monotonic() + 60
    except (OSError, ValueError, TypeError):
        pass  # 通信失敗時はログ由来の値または n/a を維持
    finally:
        if child is not None:
            if child.poll() is None:
                child.terminate()
            try:
                child.wait(timeout=3)
            except sp.TimeoutExpired:
                child.kill()


def rollout_for(started, cwd, root=None):
    """lsof の代わり: 起動後に作られた、同じ cwd の利用者スレッドの rollout を選ぶ（サブエージェントは除く）。
    同じ cwd で同時に 2 つ起動した場合は新しい方を取る（原本は lsof で厳密に区別する。ここが唯一の差）。"""
    root = Path(root) if root else cs.CODEX_HOME / "sessions"
    want = os.path.normcase(os.path.abspath(cwd))
    best = None
    for path in root.glob("**/rollout-*.jsonl"):
        try:
            if path.stat().st_mtime < started - 2:
                continue
            with path.open("rb") as stream:
                meta = json.loads(stream.readline()).get("payload", {})
            if meta.get("thread_source", "user") != "user" or isinstance(meta.get("source"), dict):
                continue
            if os.path.normcase(os.path.abspath(meta.get("cwd") or "")) != want:
                continue
            created = cs.timestamp(meta.get("timestamp")) or 0
            if created >= started - 2 and (best is None or created > best[0]):
                best = (created, path)
        except (OSError, ValueError, AttributeError):
            continue
    return best[1] if best else None


def monitor(state, child, args, started, cwd):
    usage = cs.initial_usage(args)
    stop = threading.Event()
    reader, subagents = None, cs.Subagents()
    rpc = threading.Thread(target=fetch_limits, args=(stop, usage), daemon=True)
    rpc.start()
    next_find = 0
    while child.poll() is None:
        try:
            if time.monotonic() >= next_find:
                next_find = time.monotonic() + 3
                path = rollout_for(started, cwd)
                if path and (reader is None or reader.path != path):
                    limits = usage.limits
                    usage = cs.initial_usage(args)
                    usage.limits = limits
                    stop.set()
                    stop = threading.Event()
                    rpc = threading.Thread(target=fetch_limits, args=(stop, usage), daemon=True)
                    rpc.start()
                    reader = cs.Rollout(path)
            if reader:
                reader.update(usage)
                subagents.update(usage)
            cs.save_lines(state / "lines.json", usage)
        except (OSError, ValueError):
            pass
        time.sleep(2)
    stop.set()


def pane(state):
    """下部ペインの描画ループ。tmux の status-format と同じく灰色・左余白 2 桁で 4 行を出す。"""
    os.system("")  # Windows コンソールの VT 処理を有効にする
    sys.stdout.write("\x1b[?25l")
    last = None
    try:
        while not (state / "exit.json").exists():
            try:
                rows = json.loads((state / "lines.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                rows = ["取得待ち", "", "", ""]
            width = max(20, shutil.get_terminal_size().columns - 3)
            text = "\n".join(f"  {GREY}{cs.clean(r)[:width]}{RESET}\x1b[K" for r in rows[:4])
            if text != last:
                sys.stdout.write("\x1b[H" + text + "\x1b[J")
                sys.stdout.flush()
                last = text
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\x1b[?25h")


def launch(args):
    choice = None
    args = list(args)
    for index, arg in enumerate(args):
        if arg == "--status-access" or arg.startswith("--status-access="):
            choice = args.pop(index + 1) if arg == "--status-access" and index + 1 < len(args) else arg.partition("=")[2]
            args.pop(index)
            if choice not in cs.ACCESS:
                sys.exit("--status-access manual|auto|full を指定してください")
            break
    if cs.passthrough(args):
        if choice:
            sys.exit("--status-access は対話型CLIの起動で指定してください")
        return sp.call([BACKEND, *args])
    wt = shutil.which("wt.exe")
    if not os.environ.get("WT_SESSION") or not wt:
        print("4行表示には Windows Terminal が必要です。Codex 標準の表示で起動します。", file=sys.stderr)
        return sp.call([BACKEND, *args])
    try:
        args = cs.access_args(args, choice)
    except ValueError as error:
        sys.exit(str(error))
    state = Path(tempfile.mkdtemp(prefix="codex-status-"))
    rows = shutil.get_terminal_size().lines
    size = min(.5, max(.05, 5 / max(rows, 10)))
    sp.run([wt, "-w", "0", "split-pane", "-H", "--size", f"{size:.2f}", "-d", os.getcwd(),
            sys.executable, str(Path(__file__).resolve()), "--internal-pane", str(state)], check=False)
    time.sleep(.6)
    sp.run([wt, "-w", "0", "move-focus", "up"], check=False)
    started = time.time()
    signal.signal(signal.SIGINT, lambda *_: None)  # Ctrl-C は Codex 自身に処理させる
    child = sp.Popen([BACKEND, "--no-daemon", "-c", "tui.status_line=[]", *args])
    threading.Thread(target=monitor, args=(state, child, args, started, os.getcwd()), daemon=True).start()
    code = child.wait()
    (state / "exit.json").write_text(json.dumps(code))
    return code


def main():
    args = sys.argv[1:]
    if args[:1] == ["--internal-pane"]:
        pane(Path(args[1]))
        return 0
    return launch(args)


if __name__ == "__main__":
    sys.exit(main())
