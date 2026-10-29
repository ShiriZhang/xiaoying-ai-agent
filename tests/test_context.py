from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_support import ROOT, FakeClock, Script, call, finish, make_agent
from enterprise_knowledge_qa.context import estimate_messages, history_message, select_history
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.models import ModelError
from enterprise_knowledge_qa.sessions import SessionStore


class ContextTests(unittest.TestCase):
    def state(self):
        messages, runs = [], []
        for index, text in enumerate(("old", "middle" * 100, "recent")):
            run = str(index)
            runs.append({"id": run, "state": "completed"})
            messages += [{"id": run + role, "run_id": run, "role": role, "content": text}
                         for role in ("user", "assistant")]
        return {"messages": messages, "runs": runs}

    def test_exact_pair_boundary_stops_without_skipping_to_older_short_pair(self):
        state = self.state()
        recent = state["messages"][-2:]
        budget = estimate_messages([history_message(m) for m in recent])
        messages, metadata = select_history(state, budget)
        self.assertEqual(messages, [history_message(m) for m in recent])
        self.assertEqual(metadata["selected_message_ids"], [m["id"] for m in recent])
        self.assertEqual(metadata["omitted_message_ids"], [m["id"] for m in state["messages"][:-2]])
        self.assertEqual(metadata["estimated_tokens"], budget)
        self.assertEqual(select_history(state, budget - 1)[0], [])

    def test_order_full_text_default_budget_and_incomplete_pair_omission(self):
        state = self.state()
        state["runs"].append({"id": "unfinished", "state": "running"})
        state["messages"].append({"id": "orphan", "run_id": "unfinished", "role": "user", "content": "interrupted"})
        messages, metadata = select_history(state, 8000)
        self.assertEqual([json.loads(m["content"])["content"] for m in messages],
                         [m["content"] for m in state["messages"][:-1]])
        self.assertEqual(metadata["omitted_message_ids"], ["orphan"])

    def test_current_question_and_tool_loop_are_not_truncated_or_duplicated(self):
        question = "新问题很长" * 3000
        script = Script(call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            store = SessionStore(Path(folder) / "sessions.sqlite3")
            session = store.create_session()
            ConversationService(store, lambda: make_agent(Script(finish()))).run(session, "上一轮")
            result = ConversationService(store, lambda: make_agent(script, history_token_budget=1)).run(session, question)
            self.assertEqual(store.get_session(session)["messages"][-2]["content"], question)
        self.assertEqual(result["history_selection"]["selected_message_ids"], [])
        self.assertEqual(len(result["history_selection"]["omitted_message_ids"]), 2)
        for messages in script.requests:
            self.assertEqual(sum(m.get("content") == question for m in messages), 1)
        self.assertTrue(any(m["role"] == "tool" for m in script.requests[1]))
        self.assertEqual(result["status"], "answered")

    def test_input_usage_calibration_is_explicit_and_unknown_stays_unknown(self):
        known = replace(finish(), usage={"prompt_tokens": 1234, "completion_tokens": 20})
        result = make_agent(Script(known)).run("q")
        response = next(e for e in result["trace"] if e["kind"] == "model_response")
        calibration = response["input_calibration"]
        self.assertEqual(calibration["actual_prompt_tokens"], 1234)
        self.assertEqual(calibration["actual_to_estimate_ratio"], 1234 / calibration["estimated_tokens"])
        unknown = make_agent(Script(finish())).run("q")
        response = next(e for e in unknown["trace"] if e["kind"] == "model_response")
        self.assertIsNone(response["input_calibration"]["actual_prompt_tokens"])
        self.assertIsNone(response["input_calibration"]["actual_to_estimate_ratio"])

    def test_model_capacity_error_returns_incomplete_without_retry_or_truncation(self):
        script = Script(ModelError("context_capacity"))
        result = make_agent(script).run("完整必要问题" * 3000)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["stop_reason"], "context_capacity")
        self.assertEqual(len(script.requests), 1)
        self.assertEqual(len(script.requests[0][-1]["content"]), 18000)

    def test_expensive_input_estimate_rechecks_deadline_before_model_attempt(self):
        for elapsed in (280, 301):
            with self.subTest(elapsed=elapsed):
                clock = FakeClock()
                agent = make_agent(Script(finish()), clock=clock)
                timeouts = []
                def generate(messages, tools, timeout):
                    timeouts.append(timeout)
                    return finish()
                agent.model.generate = generate
                def estimate(messages):
                    clock.advance(elapsed)
                    return 1
                with patch("enterprise_knowledge_qa.agent.estimate_messages", side_effect=estimate):
                    result = agent.run("很长的输入")
                if elapsed > 300:
                    self.assertEqual(timeouts, [])
                    self.assertEqual(result["counts"]["model_calls"], 0)
                    self.assertEqual(result["stop_reason"], "task_timeout")
                else:
                    self.assertEqual(timeouts, [20])
                    self.assertEqual(result["counts"]["model_calls"], 1)


if __name__ == "__main__":
    unittest.main()
