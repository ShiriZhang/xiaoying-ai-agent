from dataclasses import replace
import json
import unittest

from agent_support import ROOT, Script, call, finish, snapshot
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.embeddings import MockEncoder
from enterprise_knowledge_qa.models import MockModel
from enterprise_knowledge_qa.retrieval import HybridIndex, create_agent


class RetrievalAgentTests(unittest.TestCase):
    def test_same_executor_uses_actual_query_rewrite_search_read_and_finish(self):
        index = HybridIndex.build(snapshot(), MockEncoder())
        script = Script(call("search", {"query": "材料", "limit": 6}),
                        call("search", {"query": "发票 出差审批单", "limit": 12}),
                        call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        settings = load_settings(ROOT / ".env.example", environ={})
        result = create_agent(settings, MockModel(script), index).run("出差花的钱要报销，得交啥凭证")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["tool_calls"], 3)
        queries = [event["arguments"]["query"] for event in result["trace"] if event["kind"] == "action" and event["action"] == "search"]
        self.assertEqual(queries, ["材料", "发票 出差审批单"])
        observations = [event["observation"] for event in result["trace"] if event["kind"] == "tool_observation"]
        self.assertEqual([len(o["candidates"]) for o in observations[:2]], [6, 12])
        self.assertEqual(result["embedding"]["mode"], "mock")
        self.assertIn("发票", result["citations"][0]["text"])

    def test_model_adapts_to_actual_hybrid_observation_without_scripted_executor(self):
        index = HybridIndex.build(snapshot(), MockEncoder())
        def policy(messages, tools):
            observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
            if not observations:
                return call("search", {"query": "报销材料"})
            if observations[-1]["tool"] == "search":
                found = any(p["passage_id"] == "D03-P01" for p in observations[-1]["candidates"])
                return call("read", {"passage_ids": ["D03-P01"]}) if found else finish()
            return finish(with_ref=True)
        result = create_agent(load_settings(ROOT / ".env.example", environ={}), MockModel(policy), index).run("报销材料")
        self.assertEqual(result["status"], "answered")

    def test_encoding_failure_is_tool_observation_and_model_can_stop_without_mock_fallback(self):
        encoder = MockEncoder()
        index = HybridIndex.build(snapshot(), encoder)
        def fail(*args, **kwargs):
            raise RuntimeError("controlled underlying encoder failure")
        encoder.encode = fail
        script = Script(call("search", {"query": "发票"}), finish())
        result = create_agent(load_settings(ROOT / ".env.example", environ={}), MockModel(script), index).run("q")
        observation = [event["observation"] for event in result["trace"] if event["kind"] == "tool_observation"][0]
        self.assertEqual(observation["error"]["code"], "retrieval_failed")
        self.assertEqual(observation["candidates"], [])
        self.assertIn("retrieval_failed", script.requests[1][-1]["content"])
        self.assertEqual(result["status"], "incomplete")

    def test_mode_mismatch_cannot_silently_mix_live_and_mock(self):
        settings = replace(load_settings(ROOT / ".env.example", environ={}), mode="live")
        with self.assertRaises(ValueError):
            create_agent(settings, MockModel(Script(finish())), HybridIndex.build(snapshot(), MockEncoder()))
