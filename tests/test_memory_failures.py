import json
from pathlib import Path
import tempfile
import unittest

from agent_support import ROOT, FakeClock, Script, call, finish, make_agent
from test_memory import product_policy
from enterprise_knowledge_qa.agent import Agent
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.models import MockModel, ModelError
from enterprise_knowledge_qa.sessions import SessionStore
from enterprise_knowledge_qa.snapshots import load_snapshot


class MemoryFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.store = SessionStore(self.path / "sessions.sqlite3")

    def test_all_executor_interruptions_invalidate_old_anchors(self):
        for failure in ("model_failed", "format_repair_failed", "tool_limit", "model_timeout", "task_timeout"):
            with self.subTest(failure=failure):
                session = self.store.create_session()
                def seed(messages, tools):
                    from test_memory import anchor, current_ids
                    return finish(anchor_snapshot=anchor("报销", current_ids(messages)["user_message_id"]))
                ConversationService(self.store, lambda: make_agent(seed)).run(session, "报销")
                self.assertTrue(self.store.get_session(session)["memory_valid"])
                clock = FakeClock()
                if failure == "model_failed":
                    policy = Script(ModelError("model_failed"))
                elif failure == "format_repair_failed":
                    policy = Script(call("read", {"passage_ids": []}), call("read", {"passage_ids": []}))
                elif failure == "tool_limit":
                    policy = Script(*(call("read", {"passage_ids": ["D03-P01"]}) for _ in range(6)))
                else:
                    def policy(messages, tools):
                        clock.advance(61 if failure == "model_timeout" else 301)
                        return finish()
                result = ConversationService(self.store, lambda: make_agent(policy, clock=clock)).run(session, "改问产品")
                self.assertEqual(result["status"], "incomplete")
                self.assertEqual(result["stop_reason"], failure)
                self.assertFalse(result["memory_valid"])
                self.assertFalse(SessionStore(self.store.path).get_session(session)["memory_valid"])
                follow = ConversationService(self.store, lambda: make_agent(Script(finish()))).run(session, "继续")
                self.assertIsNone(follow["memory_update"]["before"])

    def test_old_answer_does_not_grant_current_citation_rights_after_reload(self):
        session = self.store.create_session()
        # First round records the old answer and fingerprint in persistent history.
        old_policy = product_policy(passage="D10-P01", text="最高1080p[C1]")
        ConversationService(self.store, lambda: make_agent(old_policy,
            search=lambda query, limit, snap: {"tool": "search", "status": "success",
                "corpus_fingerprint": snap.fingerprint, "candidates": []})).run(session, "最高分辨率？")
        variant = self.path / "knowledge.json"
        variant.write_text((ROOT / "data/knowledge.json").read_text(encoding="utf-8").replace("1080p", "4K"), encoding="utf-8")
        snap = load_snapshot(variant)
        def current_finish():
            return finish(status="answered", part_statuses=["answered"], answer="最高4K[C1]",
                          citation_refs=[{"marker": "[C1]", "passage_id": "D10-P01", "corpus_fingerprint": snap.fingerprint}])
        # History alone must not authorize an unread citation. Read repair then
        # valid finish proves old history did not populate the task read-set.
        script = Script(current_finish(), call("read", {"passage_ids": ["D10-P01"]}), current_finish())
        settings = load_settings(ROOT / ".env.example", environ={})
        result = ConversationService(self.store, lambda: Agent(settings, MockModel(script), snap)).run(session, "那现在呢？")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 1)
        self.assertEqual(result["read_set"], ["D10-P01"])
        self.assertIn("4K", result["citations"][0]["text"])
        self.assertNotIn("1080p", result["citations"][0]["text"])
        self.assertTrue(any("1080p" in m.get("content", "") for m in script.requests[0]))

    def test_expired_sqlite_publication_rolls_back_without_late_writes(self):
        session = self.store.create_session()
        ids = self.store.begin_run(session, "q")
        result = make_agent(Script(finish())).run("q")
        values = iter((1, 1, -1))  # Enter, SQLite busy-timeout bound, precommit check.
        with self.assertRaises(TimeoutError):
            self.store.finish_run(session, ids, result, remaining=lambda: next(values))
        state = self.store.get_session(session)
        self.assertEqual([m["role"] for m in state["messages"]], ["user"])
        self.assertEqual(state["runs"][0]["state"], "running")
        self.assertFalse(state["memory_valid"])


if __name__ == "__main__":
    unittest.main()
