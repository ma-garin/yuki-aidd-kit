#!/usr/bin/env python3
"""Codex CLI + tmux の4行ステータス。Python 3.11+、tmux 3.3+。"""
from __future__ import annotations

import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import re
import select
import shlex
import shutil
import signal
import subprocess as sp
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
BACKEND = os.environ.get("CODEX_STATUS_BACKEND", "/opt/homebrew/bin/codex")
# Standard API料金。出典・長文境界・Fast倍率は README.md に記載。
# input / cached input / cache write / output、USD / 1M tokens。
PRICES = {"gpt-6.1-sol": (2.0, .10, 2.50, 10.0)}
JPY = 160
ACCESS = {
    "manual": ("手動承認", ["-a", "on-request", "-s", "workspace-write", "-c", 'approvals_reviewer="user"']),
    "auto": ("代理承認", ["--approve-for-me"]),
    "full": ("Full Access", ["--dangerously-bypass-approvals-and-sandbox"]),
}


def clean(value):
    """端末制御文字を表示文字列に持ち込まない。"""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", str(value))


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def money(value):
    return f"${value:,.2f}（¥{round(value * JPY):,}）"


def rate_line(label, window):
    if not isinstance(window, dict):
        return f"{label:<7} (n/a)"
    pct = number(window.get("used_percent", window.get("usedPercent")))
    if pct is None or pct > 100:
        return f"{label:<7} (n/a)"
    pct = int(pct)
    filled = pct // 10
    reset = window.get("resets_at", window.get("resetsAt"))
    stamp = "-"
    if number(reset) is not None:
        try:
            stamp = dt.datetime.fromtimestamp(reset, ZoneInfo("Asia/Tokyo")).strftime("%m/%d %H:%M")
        except (ValueError, OverflowError, OSError):
            pass
    return f"{label:<7} {'●' * filled}{'○' * (10 - filled)} {pct}% ↻{stamp}"


def windows(limits):
    """primary=5h と決めつけず、実際の時間幅で対応づける。"""
    found = {}
    if isinstance(limits, dict):
        for key in ("primary", "secondary"):
            w = limits.get(key)
            if isinstance(w, dict):
                minutes = w.get("window_minutes", w.get("windowDurationMins"))
                if minutes in (300, 10080):
                    found[minutes] = w
    return found.get(300), found.get(10080)


def access_label(settings):
    sandbox = settings.get("sandbox_policy", settings.get("sandbox_mode"))
    if isinstance(sandbox, dict):
        sandbox = sandbox.get("type")
    policy = settings.get("approval_policy")
    reviewer = settings.get("approvals_reviewer")
    if sandbox == "danger-full-access" and policy == "never":
        return "Full Access"
    if reviewer in ("guardian", "auto_review"):
        return "代理承認"
    if policy == "never":
        return "承認なし"
    if policy in ("on-request", "on-failure", "untrusted"):
        return "手動承認"
    return "承認モード未取得"


class Usage:
    def __init__(self):
        self.model = "取得待ち"
        self.effort = "?"
        self.cwd = os.getcwd()
        self.tier = None
        self.access_settings = {}
        self.limits = {}
        self.previous = {}
        self.cost = 0.0
        self.last_cost = None
        self.unknown = False
        self.cache = "cache (n/a)"
        self.active = False
        self.session_id = None
        self.agents_line = ""

    def feed(self, record):
        p = record.get("payload") or {}
        if not isinstance(p, dict):
            return
        kind = record.get("type")
        if kind == "session_meta":
            if self.session_id is None:
                self.session_id = p.get("id")
            self.cwd = p.get("cwd") or self.cwd
        elif kind == "turn_context":
            self.model = p.get("model") or self.model
            self.effort = p.get("effort") or self.effort
            self.tier = p.get("service_tier")
            self.access_settings.update({key: p[key] for key in ("approval_policy", "approvals_reviewer", "sandbox_policy") if key in p})
        elif kind == "event_msg":
            event = p.get("type")
            if event == "task_started":
                self.active = True
            elif event in ("task_complete", "task_completed", "turn_aborted"):
                self.active = False
            elif event == "token_count":
                limits = p.get("rate_limits")
                if isinstance(limits, dict) and limits.get("limit_id", "codex") == "codex":
                    self.limits = limits
                info = p.get("info") or {}
                total = info.get("total_token_usage")
                last = info.get("last_token_usage") or {}
                if not isinstance(total, dict) or total == self.previous:
                    return
                keys = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens")
                delta = {k: total.get(k, 0) - self.previous.get(k, 0) for k in keys}
                self.previous = total.copy()
                if any(number(v) is None for v in delta.values()):
                    self.unknown = True
                    self.last_cost = None
                    return
                inp, cached, write, output = (delta[k] for k in keys)
                self.cache = f"cache read {int(last.get('cached_input_tokens', 0)):,}t"
                price = PRICES.get(self.model)
                # 推測の単価を適用しない。不明な処理ティアも未換算にする。
                if price is None or self.tier not in (None, "default", "standard", "priority", "fast"):
                    self.unknown = True
                    self.last_cost = None
                    return
                if cached + write > inp:
                    self.unknown = True
                    self.last_cost = None
                    return
                rates = list(price)
                if last.get("input_tokens", inp) > 272_000:
                    rates = [r * m for r, m in zip(rates, (2, 2, 2, 1.5))]
                multiplier = 2 if self.tier in ("priority", "fast") else 1
                self.last_cost = sum(n * r for n, r in zip((inp - cached - write, cached, write, output), rates)) / 1e6 * multiplier
                self.cost += self.last_cost

    def lines(self):
        cost = f"API換算概算 {money(self.cost)}"
        if self.unknown:
            cost += "＋未換算あり"
        if self.last_cost is not None:
            cost += f" 直近+{money(self.last_cost)}"
        head = [f"{self.model} {self.effort}", Path(self.cwd).name, access_label(self.access_settings), self.cache, cost]
        # Claudeのprogress.jsonとは混ぜず、Codex専用の進捗を読む。
        if self.active:
            try:
                p = json.loads((CODEX_HOME / "progress.json").read_text())
                elapsed = max(0, int(time.time() - p["started"]))
                estimate = max(0, int(p["estimate_sec"]))
                fmt = lambda n: f"{n // 60}:{n % 60:02d}"
                head.append(f"⏱ {p['task']} [{p['step']}] {fmt(elapsed)}/{fmt(estimate)} 残り {fmt(max(0, estimate - elapsed))}")
            except (OSError, ValueError, KeyError, TypeError):
                pass
        five, week = windows(self.limits)
        return [clean(" ｜ ".join(head)), rate_line("current", five), rate_line("weekly", week), clean(self.agents_line)]


def initial_usage(args):
    usage = Usage()
    try:
        config = tomllib.loads((CODEX_HOME / "config.toml").read_text())
    except (OSError, ValueError):
        config = {}
    overrides = {}
    for index, arg in enumerate(args[:-1]):
        value = args[index + 1]
        if arg in ("-p", "--profile"):
            config.update(config.get("profiles", {}).get(value, {}))
        elif arg in ("-m", "--model"):
            overrides["model"] = value
        elif arg in ("-C", "--cd"):
            usage.cwd = str(Path(value).expanduser().resolve())
        elif arg in ("-c", "--config"):
            try:
                overrides.update(tomllib.loads(value))
            except ValueError:
                pass
    for index, arg in enumerate(args):
        if arg == "--dangerously-bypass-approvals-and-sandbox":
            overrides.update(approval_policy="never", sandbox_mode="danger-full-access")
        elif arg == "--approve-for-me":
            overrides.update(approval_policy="on-request", sandbox_mode="workspace-write", approvals_reviewer="guardian")
        elif arg in ("-a", "--ask-for-approval", "-s", "--sandbox") and index + 1 < len(args):
            overrides["approval_policy" if arg in ("-a", "--ask-for-approval") else "sandbox_mode"] = args[index + 1]
        elif arg.startswith(("--ask-for-approval=", "--sandbox=")):
            key, value = arg.split("=", 1)
            overrides["approval_policy" if key == "--ask-for-approval" else "sandbox_mode"] = value
    config.update(overrides)
    usage.access_settings = {key: config[key] for key in ("approval_policy", "approvals_reviewer", "sandbox_mode") if key in config}
    usage.model = config.get("model", usage.model)
    usage.effort = config.get("model_reasoning_effort", usage.effort)
    usage.tier = config.get("service_tier")
    return usage


class Rollout:
    """JSONLを差分読み。書き込み途中の行は次の更新まで保留する。"""
    def __init__(self, path):
        self.path = Path(path)
        self.offset = 0

    def update(self, usage):
        with self.path.open("rb") as stream:
            if self.path.stat().st_size < self.offset:
                raise OSError("rollout was truncated")
            stream.seek(self.offset)
            while raw := stream.readline():
                if not raw.endswith(b"\n"):
                    break
                self.offset = stream.tell()
                # 会話本文・ツール出力をJSONとして読み込まない。
                if b'"event_msg"' not in raw[:180] and b'"turn_context"' not in raw[:180] and b'"session_meta"' not in raw[:180]:
                    continue
                try:
                    usage.feed(json.loads(raw))
                except (ValueError, TypeError, AttributeError):
                    continue


def timestamp(value):
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError):
        return None


class AgentLog:
    """子ログの先頭メタデータとライフサイクルだけを差分読みする。"""
    def __init__(self, path, meta):
        self.path = path
        self.id = meta.get("id")
        self.parent = meta.get("parent_thread_id")
        spawn = ((meta.get("source") or {}).get("subagent") or {}).get("thread_spawn") or {}
        self.parent = self.parent or spawn.get("parent_thread_id")
        self.name = meta.get("agent_path") or spawn.get("agent_path") or meta.get("agent_nickname") or self.id
        self.started = timestamp(meta.get("timestamp"))
        self.ended = None
        self.state = "未取得"
        self.offset = 0

    def update(self):
        with self.path.open("rb") as stream:
            if self.path.stat().st_size < self.offset:
                self.state = "未取得"
                self.offset = 0
            stream.seek(self.offset)
            while raw := stream.readline():
                if not raw.endswith(b"\n"):
                    break
                self.offset = stream.tell()
                if b'"event_msg"' not in raw[:180]:
                    continue
                try:
                    record = json.loads(raw)
                    payload = record.get("payload") or {}
                    event = payload.get("type")
                    stamp = timestamp(record.get("timestamp"))
                    if event == "task_started":
                        self.state, self.started, self.ended = "実行中", stamp, None
                    elif event in ("task_complete", "task_completed", "turn_aborted"):
                        self.state = "中断" if event == "turn_aborted" else "完了"
                        self.ended = stamp
                except (ValueError, TypeError, AttributeError):
                    continue

    def label(self, now):
        name = str(self.name).removeprefix("/root/")
        elapsed = "時間未取得"
        if self.started is not None:
            seconds = max(0, int((self.ended if self.ended is not None else now) - self.started))
            elapsed = f"{seconds // 60}:{seconds % 60:02d}"
        if self.started is not None:
            elapsed = f"{seconds // 60}分{seconds % 60}秒"
        return clean(f"{name} {elapsed}")


class Subagents:
    """セッションツリー内だけを表示。ファイル探索は10秒間隔、本文は再読しない。"""
    def __init__(self, root=None):
        self.root = root if root is not None else CODEX_HOME / "sessions"
        self.seen = set()
        self.logs = {}
        self.next_scan = 0
        self.scan_failed = False

    def update(self, usage):
        if not usage.session_id:
            return
        if time.monotonic() >= self.next_scan:
            self.next_scan = time.monotonic() + 10
            self.scan_failed = not self.root.is_dir()
            for path in self.root.glob("**/rollout-*.jsonl"):
                if path in self.seen:
                    continue
                try:
                    with path.open("rb") as stream:
                        raw = stream.readline()
                    if not raw.endswith(b"\n"):
                        continue
                    record = json.loads(raw)
                    meta = record.get("payload") or {}
                    if record.get("type") != "session_meta":
                        continue
                    if isinstance(meta.get("source"), dict) and meta.get("id"):
                        self.logs[meta["id"]] = AgentLog(path, meta)
                    self.seen.add(path)
                except (OSError, ValueError, TypeError, AttributeError):
                    self.scan_failed = True
        descendants = {usage.session_id}
        while True:
            added = {key for key, log in self.logs.items() if log.parent in descendants}
            if added <= descendants:
                break
            descendants |= added
        logs = [log for key, log in self.logs.items() if key in descendants and key != usage.session_id]
        now = time.time()
        for log in logs:
            try:
                log.update()
            except OSError:
                log.state = "読取失敗"
        active = sorted((log for log in logs if log.state == "実行中"), key=lambda log: str(log.name))
        issues = [log for log in logs if log.state in ("未取得", "読取失敗")]
        if active:
            usage.agents_line = f"並列作業 {len(active)}件 ｜ " + " ｜ ".join(log.label(now) for log in active)
        elif issues or self.scan_failed:
            usage.agents_line = "並列作業 ｜ 状態を取得できません"
        else:
            usage.agents_line = ""


def live_agents(session_id, cache_path=None):
    """起動済み旧ラッパーにも、tmuxの1回の描画呼び出しだけで4行目を供給する。"""
    name = re.sub(r"[^A-Za-z0-9_-]", "_", session_id)
    cache = Path(cache_path) if cache_path else CODEX_HOME / f"statusline-agents-{name}.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.with_suffix(cache.suffix + ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        monitor = Subagents()
        try:
            saved = json.loads(cache.read_text())
            if not isinstance(saved, dict):
                raise ValueError("invalid cache")
            if saved.get("version") == 1 and saved.get("session_id") == session_id and saved.get("root") == str(monitor.root):
                if not isinstance(saved["seen"], list) or not isinstance(saved["logs"], list) or number(saved["next_scan"]) is None:
                    raise ValueError("invalid cache metadata")
                if any(not isinstance(path, str) or not Path(path).is_relative_to(monitor.root) for path in saved["seen"]):
                    raise ValueError("invalid cache paths")
                monitor.seen = {Path(path) for path in saved["seen"]}
                monitor.scan_failed = saved.get("scan_failed", False)
                monitor.next_scan = time.monotonic() + max(0, min(10, saved["next_scan"] - time.time()))
                for entry in saved["logs"]:
                    if not isinstance(entry, dict) or any(not isinstance(entry.get(key), str) for key in ("id", "parent", "name", "path")):
                        raise ValueError("invalid cached agent")
                    if not Path(entry["path"]).is_relative_to(monitor.root) or type(entry.get("offset")) is not int or entry["offset"] < 0:
                        raise ValueError("invalid cached offset")
                    if entry.get("state") not in ("実行中", "完了", "中断", "未取得", "読取失敗") or any(entry.get(key) is not None and number(entry[key]) is None for key in ("started", "ended")):
                        raise ValueError("invalid cached state")
                    log = AgentLog.__new__(AgentLog)
                    for key in ("id", "parent", "name", "started", "ended", "state", "offset"):
                        setattr(log, key, entry[key])
                    log.path = Path(entry["path"])
                    monitor.logs[log.id] = log
        except (OSError, ValueError, TypeError, KeyError):
            monitor = Subagents()
        usage = Usage()
        usage.session_id = session_id
        monitor.update(usage)
        payload = {"version": 1, "session_id": session_id, "root": str(monitor.root),
                   "next_scan": time.time() + max(0, monitor.next_scan - time.monotonic()),
                   "scan_failed": monitor.scan_failed, "seen": [str(path) for path in monitor.seen],
                   "logs": [dict(vars(log), path=str(log.path)) for log in monitor.logs.values()]}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=cache.parent, prefix=cache.name + ".", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False)
            temporary.replace(cache)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        return clean(usage.agents_line).replace("#", "##")


def rollout_for(pid):
    """起動したCLIプロセス群が開くファイルだけを対象にする。"""
    rows = sp.run(["ps", "-axo", "pid=,ppid="], capture_output=True, text=True, timeout=3)
    descendants = {pid}
    pairs = [tuple(map(int, line.split())) for line in rows.stdout.splitlines() if len(line.split()) == 2]
    while True:
        more = {child for child, parent in pairs if parent in descendants}
        if more <= descendants:
            break
        descendants |= more
    # 他プロジェクト・同時起動セッションから拾わない。
    result = sp.run(["lsof", "-n", "-P", "-a", "-p", ",".join(map(str, descendants)), "-Fn"], capture_output=True, text=True, timeout=3)
    paths = {Path(line[1:]) for line in result.stdout.splitlines() if line.startswith("n") and "/rollout-" in line and line.endswith(".jsonl")}
    candidates = []
    for path in paths:
        try:
            with path.open() as stream:
                meta = json.loads(stream.readline()).get("payload", {})
            if meta.get("thread_source", "user") == "user" and not isinstance(meta.get("source"), dict):
                candidates.append(path)
        except (OSError, ValueError):
            pass
    return candidates[0] if len(candidates) == 1 else None


def fetch_limits(stop, usage):
    """公式App Serverの読み取りAPI。LLM呼び出しは行わない。"""
    child = None
    try:
        child = sp.Popen([BACKEND, "app-server", "--stdio"], stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.DEVNULL, bufsize=0)
        def send(message):
            child.stdin.write((json.dumps(message) + "\n").encode())
            child.stdin.flush()
        send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "codex_statusline", "version": "1.0"}}})
        buffer = b""
        ready = False
        next_poll = time.monotonic() + 15
        deadline = time.monotonic() + 15
        while not stop.is_set() and child.poll() is None:
            readable, _, _ = select.select([child.stdout], [], [], .5)
            if readable:
                chunk = os.read(child.stdout.fileno(), 65536)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    msg = json.loads(line)
                    if msg.get("id") == 1:
                        if "error" in msg:
                            return
                        send({"method": "initialized", "params": {}})
                        ready = True
                        next_poll = 0
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
        pass  # 通信失敗時はログ由来の値または n/a を維持。
    finally:
        if child is not None:
            child.terminate() if child.poll() is None else None
            try:
                child.wait(timeout=3)
            except sp.TimeoutExpired:
                child.kill()
                child.wait()


def save_lines(path, usage):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(usage.lines(), ensure_ascii=False))
    tmp.replace(path)


def run_child(state_dir):
    root = Path(state_dir)
    spec = json.loads((root / "args.json").read_text())
    usage = initial_usage(spec["args"])
    stop = threading.Event()
    reader = None
    subagents = Subagents()
    child = sp.Popen([BACKEND, "--no-daemon", "-c", "tui.status_line=[]", *spec["args"]])
    # Ctrl-CはCodex自身に処理させ、監視役は継続する。
    signal.signal(signal.SIGINT, lambda *_: None)
    def exit_runner(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, exit_runner)
    signal.signal(signal.SIGHUP, exit_runner)
    rpc = threading.Thread(target=fetch_limits, args=(stop, usage), daemon=True)
    rpc.start()
    try:
        while child.poll() is None:
            try:
                path = rollout_for(child.pid)
                if path and (reader is None or reader.path != path):
                    usage = initial_usage(spec["args"])
                    # スレッドの取得先を保つためRPCを新たに開始しない。
                    stop.set()
                    rpc.join(timeout=5)
                    stop = threading.Event()
                    reader = Rollout(path)
                    rpc = threading.Thread(target=fetch_limits, args=(stop, usage), daemon=True)
                    rpc.start()
                if reader:
                    reader.update(usage)
                    subagents.update(usage)
                save_lines(root / "lines.json", usage)
            except (OSError, ValueError, sp.TimeoutExpired):
                pass
            stop.wait(2)
    finally:
        stop.set()
        rpc.join(timeout=5)
        if child.poll() is None:
            child.terminate()
        try:
            code = child.wait(timeout=5)
        except sp.TimeoutExpired:
            child.kill()
            code = child.wait()
        (root / "exit.json").write_text(json.dumps(code if code >= 0 else 128 - code))


def passthrough(args):
    if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get("CODEX_STATUS_DISABLE") == "1":
        return True
    if any(arg == "--remote" or arg.startswith("--remote=") for arg in args):
        return True
    # オプションの値やプロンプト文字列をサブコマンドと誤認しない。
    takes_value = {"-c", "--config", "-m", "--model", "-p", "--profile", "-C", "--cd", "-s", "--sandbox", "-a", "--ask-for-approval", "-i", "--image", "--enable", "--disable", "--add-dir", "--remote", "--remote-auth-token-env"}
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg in ("-h", "--help", "-V", "--version"):
            return True
        elif arg in takes_value:
            skip = True
        elif arg == "--":
            break
        elif not arg.startswith("-"):
            return arg in {"agents", "exec", "e", "review", "login", "logout", "mcp", "plugin", "app-server", "remote-control", "app", "completion", "update", "doctor", "sandbox", "debug", "apply", "a", "queue", "archive", "delete", "migrate-rollouts", "unarchive", "cloud", "exec-server", "features", "help"}
    return False


def access_args(args, choice=None):
    explicit = any(arg in ("-a", "--ask-for-approval", "-s", "--sandbox", "--approve-for-me", "--dangerously-bypass-approvals-and-sandbox") or arg.startswith(("--sandbox=", "--ask-for-approval=")) for arg in args)
    explicit |= any("approval_policy=" in arg or "approvals_reviewer=" in arg or "sandbox_mode=" in arg for arg in args)
    if explicit and choice:
        raise ValueError("--status-access と承認・サンドボックスの直接指定は併用できません")
    if explicit:
        return args
    if choice is None:
        choice = "full"
    print(f"起動モード: {ACCESS[choice][0]}", file=sys.stderr)
    return [*ACCESS[choice][1], *args]


def launch(args):
    choice = None
    args = list(args)
    for index, arg in enumerate(args):
        if arg == "--status-access" or arg.startswith("--status-access="):
            if arg == "--status-access":
                if index + 1 >= len(args):
                    sys.exit("--status-access manual|auto|full を指定してください")
                choice = args.pop(index + 1)
            else:
                choice = arg.split("=", 1)[1]
            args.pop(index)
            if choice not in ACCESS:
                sys.exit("--status-access manual|auto|full を指定してください")
            break
    if passthrough(args):
        if choice:
            sys.exit("--status-access は対話型CLIの起動で指定してください")
        os.execv(BACKEND, [BACKEND, *args])
    if not shutil.which("tmux"):
        sys.exit("4行表示にはtmuxが必要です。通常起動: CODEX_STATUS_DISABLE=1 codex")
    try:
        args = access_args(args, choice)
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        sys.exit(str(error) or "起動を取り消しました")
    env = os.environ.copy()
    env.pop("TMUX", None)
    socket = "codex-status-" + uuid.uuid4().hex[:12]
    def tmux(*cmd, **kwargs):
        return sp.run(["tmux", "-L", socket, "-f", "/dev/null", *cmd], env=env, check=True, **kwargs)
    with tempfile.TemporaryDirectory(prefix="codex-status-") as temp:
        root = Path(temp)
        (root / "args.json").write_text(json.dumps({"args": args}))
        save_lines(root / "lines.json", initial_usage(args))
        command = shlex.join([sys.executable, str(Path(__file__).resolve()), "--internal-run", temp])
        try:
            tmux("new-session", "-d", "-s", "codex", "-x", str(shutil.get_terminal_size().columns), "-y", str(shutil.get_terminal_size().lines), "-c", os.getcwd(), command)
            # Shift+Enterを通常のEnterと区別してCodexへ渡す。
            tmux("set-option", "-s", "extended-keys", "always")
            tmux("set-option", "-s", "extended-keys-format", "csi-u")
            tmux("set-option", "-t", "codex", "remain-on-exit", "on")
            tmux("set-option", "-t", "codex", "status", "4")
            tmux("set-option", "-t", "codex", "status-interval", "2")
            tmux("set-option", "-t", "codex", "status-style", "bg=default,fg=default")
            tmux("set-option", "-t", "codex", "mouse", "on")
            for index in range(4):
                render = shlex.join([sys.executable, str(Path(__file__).resolve()), "--internal-line", str(root / "lines.json"), str(index)])
                tmux("set-option", "-t", "codex", f"status-format[{index}]", "#(" + render + ")")
            # pane終了時にattachも終了させ、呼び出し元へ戻る。
            tmux("set-hook", "-t", "codex", "pane-died", "detach-client -s codex")
            tmux("attach-session", "-t", "codex")
            exit_file = root / "exit.json"
            return json.loads(exit_file.read_text()) if exit_file.exists() else 0
        finally:
            sp.run(["tmux", "-L", socket, "kill-server"], env=env, stdout=sp.DEVNULL, stderr=sp.DEVNULL)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--internal-run"]:
        run_child(args[1])
    elif args[:1] == ["--internal-agents"]:
        try:
            print(live_agents(args[1], args[2] if len(args) > 2 else None))
        except (OSError, ValueError, IndexError, TypeError):
            print("並列作業 ｜ 状態を取得できません")
    elif args[:1] == ["--internal-line"]:
        try:
            # tmuxのスタイル書式をユーザー文字列から注入させない。
            print(clean(json.loads(Path(args[1]).read_text())[int(args[2])]).replace("フルアクセス", "Full Access").replace("#", "##"))
        except (OSError, ValueError, IndexError):
            print("取得待ち")
    else:
        return launch(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
