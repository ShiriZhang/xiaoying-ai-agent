import unittest
from unittest.mock import Mock

from agent_support import Script, call, finish, make_agent, search_result


class BudgetTests(unittest.TestCase):
    def test_sixth_tool_stops_without_extra_model_or_seventh_tool(self):
        script = Script(*[call("search", {"query": str(n)}) for n in range(6)], finish())
        search = Mock(side_effect=lambda q, n, snap: search_result(snap))
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["stop_reason"], "tool_limit")
        self.assertEqual(result["counts"]["model_calls"], 6)
        self.assertEqual(search.call_count, 6)
        self.assertEqual(len(script.responses), 1)

    def test_failed_tool_counts_and_invalid_parameters_do_not(self):
        script = Script(call("read", {"passage_ids": []}), call("read", {"passage_ids": ["unknown"]}), finish())
        result = make_agent(script).run("q")
        self.assertEqual(result["counts"], {"model_calls": 3, "tool_calls": 1, "recoveries": 0, "format_corrections": 1})

    def test_seventh_finish_succeeds_after_five_tools_and_one_format_error(self):
        script = Script(call("unknown"), *[call("search", {"query": str(n)}) for n in range(4)],
                        call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True), finish())
        search = Mock(side_effect=lambda q, limit, snap: search_result(snap))
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["model_calls"], 7)
        self.assertEqual(result["counts"]["tool_calls"], 5)
        self.assertEqual(len(script.requests), 7)
        self.assertEqual(len(script.responses), 1)
        self.assertEqual(result["limits"]["model_calls"], 8)

    def test_seventh_nonfinish_executes_sixth_tool_then_no_eighth_or_ninth(self):
        script = Script(call("unknown"), *[call("search", {"query": str(n)}) for n in range(6)], finish(), finish())
        search = Mock(side_effect=lambda q, limit, snap: search_result(snap))
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["stop_reason"], "tool_limit")
        self.assertEqual(result["counts"]["model_calls"], 7)
        self.assertEqual(search.call_count, 6)
        self.assertEqual(len(script.responses), 2)
