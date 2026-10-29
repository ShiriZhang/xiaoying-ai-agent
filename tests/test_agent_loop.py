import json
import unittest
from unittest.mock import Mock

from agent_support import Script, call, finish, make_agent, search_result
from enterprise_knowledge_qa.models import ModelReply, ToolCall


class LoopTests(unittest.TestCase):
    def test_model_changes_next_action_based_on_actual_search_observation(self):
        for candidates in ([], [{"passage_id": "D03-P01"}]):
            requests = []
            def policy(messages, tools):
                requests.append(messages)
                observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
                if not observations:
                    return call("search", {"query": "材料"}, ident="model-search")
                if observations[-1].get("candidates"):
                    return call("read", {"passage_ids": ["D03-P01"]}, ident="model-read")
                return finish(with_ref=bool(observations[-1].get("passages")))
            search = Mock(side_effect=lambda q, limit, snap: search_result(snap, candidates=candidates))
            result = make_agent(policy, search=search).run("报销材料")
            self.assertEqual(result["status"], "answered" if candidates else "incomplete")
            self.assertEqual(result["counts"]["tool_calls"], 2 if candidates else 1)
            self.assertEqual(search.call_args.args[:2], ("材料", 6))
            tool_message = [m for m in requests[1] if m["role"] == "tool"][0]
            self.assertEqual(tool_message["tool_call_id"], "model-search")

    def test_multiple_calls_all_rejected_and_original_ids_receive_feedback(self):
        one = call("search", {"query": "test"}, ident="one").calls[0]
        two = call("read", {"passage_ids": ["D03-P01"]}, ident="two").calls[0]
        script = Script(ModelReply((one, two)), finish())
        search = Mock()
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["counts"]["tool_calls"], 0)
        self.assertEqual(result["counts"]["format_corrections"], 1)
        search.assert_not_called()
        self.assertEqual({m["tool_call_id"] for m in script.requests[1] if m["role"] == "tool"}, {"one", "two"})

    def test_unknown_action_does_not_execute_and_model_can_repair(self):
        script = Script(call("delete_all"), finish())
        result = make_agent(script).run("q")
        self.assertEqual(result["stop_reason"], "finished")
        self.assertEqual(result["counts"]["tool_calls"], 0)
        self.assertEqual(result["counts"]["format_corrections"], 1)

    def test_original_text_and_task_readset_are_not_shared_between_runs(self):
        script = Script(call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True), finish(with_ref=True), finish())
        agent = make_agent(script)
        first = agent.run("q")
        self.assertEqual(first["status"], "answered")
        self.assertIn("发票", first["citations"][0]["text"])
        second = agent.run("q again")
        self.assertEqual(second["counts"]["format_corrections"], 1)
        self.assertEqual(second["read_set"], [])
