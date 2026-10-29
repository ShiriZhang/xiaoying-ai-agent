from datetime import datetime, timezone
import threading
import time
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from agent_support import ROOT, FakeClock, Script, call, finish, make_agent, search_result, snapshot
from enterprise_knowledge_qa.reading import ReadTool


class DeadlineTests(unittest.TestCase):
    def test_single_model_timeout_passed_and_late_finish_rejected(self):
        clock = FakeClock()
        def slow(messages, tools):
            clock.advance(61)
            return finish()
        result = make_agent(slow, clock=clock).run("q")
        self.assertEqual(result["stop_reason"], "model_timeout")
        self.assertEqual(result["counts"]["model_calls"], 1)

    def test_total_deadline_shortens_next_request_and_no_late_tool_commit(self):
        clock = FakeClock()
        script = Script(call("search", {"query": "first"}), call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        def search(q, limit, snap):
            clock.advance(280)
            return search_result(snap)
        def read_fault(ids):
            clock.advance(21)
        reader = ReadTool(snapshot(), fault_hook=read_fault)
        result = make_agent(script, search=search, reader=reader, clock=clock).run("q")
        self.assertEqual(result["stop_reason"], "task_timeout")
        self.assertEqual(result["read_set"], [])
        self.assertEqual(reader.read_set, frozenset())
        requests = [e for e in result["trace"] if e["kind"] == "model_request"]
        self.assertEqual([e["timeout_seconds"] for e in requests], [60, 20])
        self.assertEqual(len(script.requests), 2)

    def test_wall_date_is_frozen_separately_from_monotonic_deadline(self):
        clock = FakeClock()
        def policy(messages, tools):
            clock.wall = datetime(2030, 1, 1, tzinfo=timezone.utc)
            clock.advance(1)
            return finish()
        result = make_agent(policy, clock=clock).run("q")
        self.assertEqual(result["as_of_date"], "2026-09-30")
        self.assertEqual(result["elapsed_seconds"], 1)

    def test_real_blocking_worker_cannot_commit_after_timeout_or_append_trace(self):
        released, started = threading.Event(), threading.Event()
        def hook(ids):
            started.set()
            released.wait(2)
        reader = ReadTool(snapshot(), fault_hook=hook)
        script = Script(call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        before = time.monotonic()
        result = make_agent(script, reader=reader, task_timeout_seconds=0.1).run("q")
        self.assertTrue(started.is_set())
        self.assertLess(time.monotonic() - before, 1)
        self.assertEqual(result["stop_reason"], "task_timeout")
        trace_count = len(result["trace"])
        released.set()
        time.sleep(0.02)
        self.assertEqual(result["read_set"], [])
        self.assertEqual(reader.read_set, frozenset())
        self.assertEqual(len(result["trace"]), trace_count)

    def test_storage_deadline_rejects_late_publication(self):
        from enterprise_knowledge_qa.tracing import save_trace
        clock = FakeClock()
        def slow_save(*args, **kwargs):
            clock.advance(301)
            return save_trace(*args, **kwargs)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            with patch("enterprise_knowledge_qa.agent.save_trace", side_effect=slow_save):
                result = make_agent(Script(finish()), clock=clock).run("q", trace_directory=directory)
            self.assertEqual(result["stop_reason"], "task_timeout")
            self.assertEqual(list(Path(directory).glob("*.json")), [])
