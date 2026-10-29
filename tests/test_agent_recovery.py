import unittest
from unittest.mock import Mock

from agent_support import Script, call, finish, make_agent, search_result


class RecoveryTests(unittest.TestCase):
    def test_model_selects_changed_query_after_real_error_and_recovery_succeeds(self):
        script = Script(call("search", {"query": "first"}), call("search", {"query": "changed"}), finish())
        count = 0
        def search(q, limit, snap):
            nonlocal count
            count += 1
            return search_result(snap, error=count == 1)
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["stop_reason"], "finished")
        self.assertEqual(result["counts"]["recoveries"], 1)
        self.assertEqual(result["counts"]["tool_calls"], 2)
        self.assertIn("injected_error", script.requests[1][-1]["content"])

    def test_failed_recovery_stops_without_third_try_or_model_wrapup(self):
        script = Script(call("search", {"query": "first"}), call("search", {"query": "changed"}), finish())
        search = Mock(side_effect=lambda q, limit, snap: search_result(snap, error=True))
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["stop_reason"], "recovery_exhausted")
        self.assertEqual(result["counts"]["model_calls"], 2)
        self.assertEqual(search.call_count, 2)
        self.assertEqual(len(script.responses), 1)

    def test_model_can_finish_incomplete_without_recovery(self):
        script = Script(call("search", {"query": "first"}), finish())
        result = make_agent(script, search=lambda q, limit, snap: search_result(snap, error=True)).run("q")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["counts"]["recoveries"], 0)
        self.assertEqual(result["counts"]["tool_calls"], 1)

    def test_later_failure_cannot_reset_recovery_budget_by_query_change(self):
        script = Script(*[call("search", {"query": str(n)}) for n in range(4)])
        observations = iter([True, False, True])
        search = Mock(side_effect=lambda q, limit, snap: search_result(snap, error=next(observations)))
        result = make_agent(script, search=search).run("q")
        self.assertEqual(result["stop_reason"], "recovery_exhausted")
        self.assertEqual(search.call_count, 3)
        self.assertEqual(result["counts"]["recoveries"], 1)

    def test_model_service_failure_does_not_consume_tool_recovery(self):
        from enterprise_knowledge_qa.models import ModelError
        result = make_agent(Script(ModelError("authentication_failed"), finish())).run("q")
        self.assertEqual(result["stop_reason"], "authentication_failed")
        self.assertEqual(result["counts"]["model_calls"], 1)
        self.assertEqual(result["counts"]["recoveries"], 0)
