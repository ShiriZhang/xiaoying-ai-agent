import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_support import ROOT, Script, call, finish, make_agent
from enterprise_knowledge_qa.models import MockModel, ModelReply
from enterprise_knowledge_qa.tracing import save_trace, usage_record, usage_summary


class TraceTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)

    def test_actual_trace_saved_contains_actions_observations_counts_and_input(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            result = make_agent(Script(call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))).run(
                "报销材料", session_id="controlled-session", trace_directory=directory)
            saved = json.loads((Path(directory) / (result["request_id"] + ".json")).read_text(encoding="utf-8"))
            self.assertEqual(saved["mode"], "mock")
            self.assertEqual(saved["session_id"], "controlled-session")
            self.assertEqual(saved["input"]["question"], "报销材料")
            for kind in ("model_request", "model_response", "action", "tool_observation", "stop"):
                self.assertIn(kind, [e["kind"] for e in saved["trace"]])
            self.assertEqual(saved["counts"]["model_calls"], 2)
            self.assertEqual(saved["usage"]["requests_with_unknown_usage"], 2)
            self.assertIsNone(saved["usage"]["total_estimated_cny"])
            self.assertIn("corpus_fingerprint", saved)
            self.assertIn("as_of_date", saved)
            self.assertEqual(list(Path(directory).glob("*.partial")), [])

    def test_secret_and_internal_reasoning_are_removed_from_return_and_file(self):
        agent = make_agent(Script(finish(anchor_snapshot={"reasoning_content": "private-test-reasoning"})))
        agent.model.secrets = ("synthetic-sensitive-key",)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            result = agent.run("synthetic-sensitive-key", trace_directory=directory)
            text = (Path(directory) / (result["request_id"] + ".json")).read_text(encoding="utf-8")
            self.assertNotIn("synthetic-sensitive-key", text + json.dumps(result))
            self.assertNotIn("private-test-reasoning", text + json.dumps(result))

    def test_usage_known_unknown_partial_and_cache_fields(self):
        known = usage_record({"prompt_tokens": 100, "completion_tokens": 50,
                              "prompt_cache_hit_tokens": 20, "prompt_cache_miss_tokens": 80}, "live")
        self.assertAlmostEqual(known["estimated_cny_upper_rate"], 0.0006)
        unknown = usage_record(None, "live")
        summary = usage_summary([known, unknown])
        self.assertIsNone(summary["total_estimated_cny"])
        self.assertEqual(summary["requests_with_unknown_usage"], 1)
        self.assertAlmostEqual(summary["known_requests_estimated_cny"], 0.0006)
        self.assertIsNone(usage_record({"prompt_tokens": -1}, "live")["prompt_tokens"])

    def test_storage_failure_is_explicit_and_never_claims_saved(self):
        with patch("enterprise_knowledge_qa.agent.save_trace", side_effect=OSError("private-path")):
            result = make_agent(Script(finish())).run("q", trace_directory="unused")
        self.assertIn({"code": "trace_save_failed"}, result["execution_issues"])
        self.assertNotIn("private-path", json.dumps(result))

    def test_expired_save_does_not_publish_and_duplicate_id_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            with self.assertRaises(TimeoutError):
                save_trace(directory, {"request_id": "safe-id"}, can_commit=lambda: False)
            self.assertEqual(list(Path(directory).iterdir()), [])
            save_trace(directory, {"request_id": "safe-id", "data": 1})
            with self.assertRaises(FileExistsError):
                save_trace(directory, {"request_id": "safe-id", "data": 2})
            self.assertEqual(json.loads((Path(directory) / "safe-id.json").read_text())["data"], 1)
