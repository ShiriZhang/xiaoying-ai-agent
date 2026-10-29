import json
import unittest

from agent_support import Script, call, finish, make_agent
from enterprise_knowledge_qa.models import ModelReply, ToolCall


class FormatTests(unittest.TestCase):
    def test_invalid_arguments_one_repair_preserves_original_call_id(self):
        script = Script(call("read", {"passage_ids": []}, ident="original-invalid-id"),
                        call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        result = make_agent(script).run("q")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 1)
        self.assertEqual(result["counts"]["recoveries"], 0)
        self.assertEqual(script.requests[1][-1]["tool_call_id"], "original-invalid-id")
        self.assertIn("1 to 3", script.requests[1][-1]["content"])

    def test_repair_still_invalid_stops_without_second_repair(self):
        script = Script(call("read", {"passage_ids": []}), call("read", {"passage_ids": []}), finish())
        result = make_agent(script).run("q")
        self.assertEqual(result["stop_reason"], "format_repair_failed")
        self.assertEqual(result["counts"]["tool_calls"], 0)
        self.assertEqual(len(script.requests), 2)

    def test_illegal_finish_structure_can_be_repaired(self):
        result = make_agent(Script(finish(status="invalid-status"), finish())).run("q")
        self.assertEqual(result["stop_reason"], "finished")
        self.assertEqual(result["counts"]["format_corrections"], 1)

    def test_unread_unknown_cross_snapshot_and_bad_markers_rejected(self):
        for ref in (
            {"marker": "[C1]", "passage_id": "D03-P01", "corpus_fingerprint": "other"},
            {"marker": "[C1]", "passage_id": "unknown", "corpus_fingerprint": "other"},
            {"marker": "bad", "passage_id": "D03-P01", "corpus_fingerprint": "other"},
        ):
            with self.subTest(ref=ref):
                result = make_agent(Script(finish(with_ref=True, citation_refs=[ref]), finish())).run("q")
                self.assertEqual(result["counts"]["format_corrections"], 1)
        read = call("read", {"passage_ids": ["D03-P01"]})
        result = make_agent(Script(read, finish(with_ref=True, citation_refs=[{
            "marker": "[C1]", "passage_id": "D03-P01", "corpus_fingerprint": "other",
        }]), finish(with_ref=True))).run("q")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 1)

    def test_bad_json_duplicate_keys_no_action_and_multiple_actions(self):
        bad = [ModelReply(()), ModelReply((ToolCall("a", "read", "{"),)),
               ModelReply((ToolCall("a", ["bad-name"], "{}"),)),
               ModelReply((ToolCall("a", "read", '{"reason":"x","reason":"y"}'),))]
        for response in bad:
            with self.subTest(response=response):
                result = make_agent(Script(response, finish())).run("q")
                self.assertEqual(result["counts"]["format_corrections"], 1)
                self.assertEqual(result["counts"]["tool_calls"], 0)

    def test_invalid_memory_proposal_does_not_use_business_repair(self):
        result = make_agent(Script(finish(anchor_snapshot="invalid-memory"))).run("q")
        self.assertEqual(result["counts"]["format_corrections"], 0)
        self.assertFalse(result["memory_valid"])
        self.assertIsNotNone(result["memory_warning"])
