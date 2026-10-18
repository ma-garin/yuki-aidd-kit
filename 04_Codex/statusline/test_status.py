"""料金の二重計上、使用枠の誤表示、差分読みの回帰を検査する。"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import codex_status
from codex_status import Rollout, Usage, access_args, passthrough, rate_line, windows


def event(total, last=None):
    return {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": total, "last_token_usage": last or total}}}


class StatusTest(unittest.TestCase):
    def test_rollout_detection_preserves_launch_access_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "args.json").write_text(json.dumps({"args": ["--status-test"]}))
            def seeded_usage(args):
                u = Usage()
                u.access_settings = {"approval_policy": "never", "sandbox_mode": "danger-full-access"}
                return u
            with patch.object(codex_status, "initial_usage", side_effect=seeded_usage), \
                 patch.object(codex_status.sp, "Popen") as process, \
                 patch.object(codex_status.threading, "Thread"), \
                 patch.object(codex_status.signal, "signal"), \
                 patch.object(codex_status, "rollout_for", return_value=root / "rollout.jsonl"), \
                 patch.object(codex_status, "Rollout"), \
                 patch.object(codex_status, "save_lines") as save, \
                 patch.object(codex_status.threading.Event, "wait"):
                process.return_value.poll.side_effect = [None, 0, 0]
                process.return_value.wait.return_value = 0
                codex_status.run_child(temp)
                self.assertEqual(save.call_args.args[1].lines()[0].split(" ｜ ")[2], "Full Access")

    def test_access_mode_is_third_and_updates_from_context(self):
        u = Usage()
        u.access_settings = {"approval_policy": "on-request"}
        self.assertEqual(u.lines()[0].split(" ｜ ")[2], "手動承認")
        u.feed({"type": "turn_context", "payload": {"approval_policy": "never", "sandbox_policy": {"type": "danger-full-access"}}})
        self.assertEqual(u.lines()[0].split(" ｜ ")[2], "Full Access")
        u.feed({"type": "turn_context", "payload": {"approval_policy": "on-request", "approvals_reviewer": "guardian", "sandbox_policy": {"type": "workspace-write"}}})
        self.assertEqual(u.lines()[0].split(" ｜ ")[2], "代理承認")
        u.feed({"type": "turn_context", "payload": {"approvals_reviewer": "auto_review"}})
        self.assertEqual(u.lines()[0].split(" ｜ ")[2], "代理承認")

    def test_duplicate_usage_is_not_billed_twice(self):
        u = Usage()
        u.model = "gpt-6.1-sol"
        record = event({"input_tokens": 1000, "cached_input_tokens": 600, "output_tokens": 100, "total_tokens": 1100})
        u.feed(record)
        self.assertAlmostEqual(u.cost, .00186)
        u.feed(record)
        self.assertAlmostEqual(u.cost, .00186)

    def test_reasoning_tokens_are_part_of_output(self):
        u = Usage()
        u.model = "gpt-6.1-sol"
        u.feed(event({"input_tokens": 0, "output_tokens": 100, "reasoning_output_tokens": 80}))
        self.assertAlmostEqual(u.cost, .001)

    def test_unknown_model_does_not_get_a_fake_price(self):
        u = Usage()
        u.model = "unknown-model"
        u.feed(event({"input_tokens": 1000, "output_tokens": 100}))
        self.assertTrue(u.unknown)
        self.assertIsNone(u.last_cost)

    def test_long_context_and_fast_multipliers(self):
        u = Usage()
        u.model, u.tier = "gpt-6.1-sol", "priority"
        u.feed(event({"input_tokens": 300_000, "output_tokens": 1000}))
        self.assertAlmostEqual(u.cost, 2.43)

    def test_actual_window_length_controls_the_label(self):
        short = {"usedPercent": 25, "windowDurationMins": 15}
        weekly = {"usedPercent": 44, "windowDurationMins": 10080}
        self.assertEqual(windows({"primary": short, "secondary": weekly}), (None, weekly))
        self.assertEqual(rate_line("current", short).split()[1], "●●○○○○○○○○")
        self.assertEqual(rate_line("current", {"usedPercent": float("nan")}), "current (n/a)")

    def test_partial_jsonl_waits_until_newline(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "rollout-test.jsonl"
            raw = json.dumps(event({"input_tokens": 1000, "output_tokens": 100}), separators=(",", ":"))
            path.write_text(raw)
            u = Usage()
            u.model = "gpt-6.1-sol"
            reader = Rollout(path)
            reader.update(u)
            self.assertEqual(u.cost, 0)
            with path.open("a") as stream:
                stream.write("\n")
            reader.update(u)
            self.assertAlmostEqual(u.cost, .003)
            reader.update(u)
            self.assertAlmostEqual(u.cost, .003)

    def test_subcommands_passthrough_but_option_values_do_not(self):
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True):
            self.assertTrue(passthrough(["exec", "hello"]))
            self.assertTrue(passthrough(["--version"]))
            self.assertFalse(passthrough(["resume", "--last"]))
            self.assertFalse(passthrough(["-m", "review", "hello"]))

    def test_access_modes_and_conflict(self):
        self.assertIn('approvals_reviewer="user"', access_args([], "manual"))
        self.assertEqual(access_args([], "auto"), ["--approve-for-me"])
        self.assertEqual(access_args([], "full"), ["--dangerously-bypass-approvals-and-sandbox"])
        with self.assertRaises(ValueError):
            access_args(["--sandbox", "read-only"], "full")
        self.assertEqual(access_args(["--sandbox", "read-only"]), ["--sandbox", "read-only"])

    def test_default_access_is_full_and_displayed_before_first_turn(self):
        with patch("builtins.input", side_effect=AssertionError("起動時の選択は禁止")):
            args = access_args([])
            self.assertEqual(args, ["--dangerously-bypass-approvals-and-sandbox"])
            self.assertEqual(access_args(["resume", "--last"]), [*args, "resume", "--last"])
            with tempfile.TemporaryDirectory() as temp, patch.object(codex_status, "CODEX_HOME", Path(temp)):
                usage = codex_status.initial_usage(args)
                self.assertEqual(usage.access_settings["approval_policy"], "never")
                self.assertEqual(usage.access_settings["sandbox_mode"], "danger-full-access")
                self.assertEqual(usage.lines()[0].split(" ｜ ")[2], "Full Access")


class SubagentTest(unittest.TestCase):
    def write_log(self, root, agent, parent, events=(), extra_meta=None):
        path = root / f"rollout-{agent}.jsonl"
        meta = {"id": agent, "parent_thread_id": parent, "agent_path": f"/root/{agent}",
                "source": {"subagent": {"thread_spawn": {"parent_thread_id": parent}}},
                "timestamp": "2026-10-18T12:00:00Z"}
        rows = [{"type": "session_meta", "payload": meta}]
        if extra_meta:
            rows.append({"type": "session_meta", "payload": extra_meta})
        rows.extend({"type": "event_msg", "timestamp": stamp, "payload": {"type": event}} for event, stamp in events)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return path

    def test_fourth_line_has_scoped_children_nested_status_and_elapsed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_log(root, "review", "parent", [("task_started", "2026-10-18T12:00:00Z")])
            self.write_log(root, "verify", "review", [("task_started", "2026-10-18T12:00:00Z"), ("task_complete", "2026-10-18T12:01:00Z")])
            self.write_log(root, "unrelated", "other", [("task_started", "2026-10-18T12:00:00Z")])
            u = Usage(); u.session_id = "parent"
            before = u.lines()[:3]
            monitor = codex_status.Subagents(root)
            with patch.object(codex_status.time, "time", return_value=codex_status.timestamp("2026-10-18T12:02:00Z")):
                monitor.update(u)
            self.assertEqual(u.lines()[:3], before)
            self.assertEqual(len(u.lines()), 4)
            self.assertIn("review 2分0秒", u.lines()[3])
            self.assertNotIn("verify", u.lines()[3])
            self.assertIn("並列作業 1件", u.lines()[3])
            self.assertNotIn("unrelated", u.lines()[3])

    def test_waiting_empty_and_missing_are_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            u = Usage(); monitor = codex_status.Subagents(Path(temp))
            monitor.update(u)
            self.assertEqual("", u.lines()[3])
            u.session_id = "parent"; monitor.update(u)
            self.assertEqual("", u.lines()[3])
            codex_status.Subagents(Path(temp) / "missing").update(u)
            self.assertIn("状態を取得できません", u.lines()[3])

    def test_abort_resume_partial_line_and_inherited_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.write_log(root, "review", "parent", [("task_started", "2026-10-18T12:00:00Z"), ("turn_aborted", "2026-10-18T12:00:30Z")], {"id": "parent"})
            u = Usage(); u.session_id = "parent"
            monitor = codex_status.Subagents(root); monitor.update(u)
            self.assertEqual("", u.lines()[3])
            raw = json.dumps({"type": "event_msg", "timestamp": "2026-10-18T12:01:00Z", "payload": {"type": "task_started"}})
            with path.open("a") as stream: stream.write(raw)
            monitor.update(u)
            self.assertEqual("", u.lines()[3])
            with path.open("a") as stream: stream.write("\n")
            with patch.object(codex_status.time, "time", return_value=codex_status.timestamp("2026-10-18T12:02:00Z")):
                monitor.update(u)
            self.assertIn("review 1分0秒", u.lines()[3])
            replay = Usage(); Rollout(path).update(replay)
            self.assertEqual(replay.session_id, "review")


    def test_live_renderer_restores_offsets_and_reads_only_appended_events(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); sessions = root / "sessions"; sessions.mkdir()
            path = self.write_log(sessions, "review", "parent", [("task_started", "2026-10-18T12:00:00Z")])
            cache = root / "agents.json"
            with patch.object(codex_status, "CODEX_HOME", root):
                first = codex_status.live_agents("parent", cache)
                self.assertIn("並列作業 1件 ｜ review", first)
                saved = json.loads(cache.read_text())
                self.assertEqual(saved["logs"][0]["offset"], path.stat().st_size)
                with path.open("a") as stream:
                    stream.write(json.dumps({"type": "event_msg", "timestamp": "2026-10-18T12:01:00Z", "payload": {"type": "task_complete"}}) + "\n")
                with patch.object(codex_status.AgentLog, "__init__", side_effect=AssertionError("header was re-read")):
                    second = codex_status.live_agents("parent", cache)
                self.assertEqual("", second)
                self.assertEqual(json.loads(cache.read_text())["logs"][0]["offset"], path.stat().st_size)
                cache.write_text("broken")
                self.assertEqual("", codex_status.live_agents("parent", cache))

    def test_control_characters_are_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.write_log(root, "review", "parent")
            value = path.read_text().replace("/root/review", "/root/review\\u001b[31m")
            path.write_text(value)
            u = Usage(); u.session_id = "parent"
            codex_status.Subagents(root).update(u)
            self.assertNotIn("\x1b", u.lines()[3])


if __name__ == "__main__":
    unittest.main()
