import json
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from agent_support import ROOT, Script, finish, make_agent
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.sessions import SessionNotFound, SessionStore, StorageError


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "sessions.sqlite3"
        self.store = SessionStore(self.path)
        self.session = self.store.create_session()

    def run_question(self, policy=None, question="q"):
        return ConversationService(self.store, lambda: make_agent(policy or Script(finish()))).run(self.session, question)

    def test_restart_preserves_full_messages_results_and_isolates_sessions(self):
        first = self.run_question(question="完整问题\n不截断")
        restarted = SessionStore(self.path)
        state = restarted.get_session(self.session)
        self.assertEqual([m["role"] for m in state["messages"]], ["user", "assistant"])
        self.assertEqual(state["messages"][0]["content"], "完整问题\n不截断")
        saved = json.loads(state["runs"][0]["result_json"])
        self.assertEqual(saved["trace"], first["trace"])
        other = restarted.create_session()
        self.assertEqual(restarted.get_session(other)["messages"], [])
        second = ConversationService(restarted, lambda: make_agent(Script(finish()))).run(self.session, "续问")
        self.assertEqual(second["history_selection"]["selected_message_ids"], [m["id"] for m in state["messages"]])
        self.assertEqual(len(restarted.get_session(self.session)["messages"]), 4)

    def test_no_write_transaction_held_during_model_wait(self):
        def policy(messages, tools):
            # A second actual SQLite writer can commit while the model is running.
            connection = sqlite3.connect(self.path, timeout=0.01)
            try:
                connection.execute("INSERT INTO sessions(id) VALUES ('concurrent-session')")
                connection.commit()
            finally:
                connection.close()
            return finish()
        self.assertTrue(self.run_question(policy)["persistence"]["saved"])
        self.assertEqual(self.store.get_session("concurrent-session")["messages"], [])

    def test_real_sqlite_failure_rolls_back_assistant_and_result(self):
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_assistant BEFORE INSERT ON messages WHEN NEW.role='assistant' "
                       "BEGIN SELECT RAISE(ABORT, 'private storage details'); END")
            db.commit()
        result = self.run_question()
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["persistence"], {"saved": False, "user_message_saved": True, "result_saved": False})
        self.assertEqual(result["memory_warning"], "storage_failed")
        self.assertNotIn("private storage details", json.dumps(result))
        state = self.store.get_session(self.session)
        self.assertEqual([m["role"] for m in state["messages"]], ["user"])
        self.assertEqual(state["runs"][0]["state"], "running")
        self.assertIsNone(state["runs"][0]["result_json"])
        self.assertFalse(state["memory_valid"])

    def test_failed_begin_never_calls_model_or_claims_user_saved(self):
        self.run_question()
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TRIGGER fail_user BEFORE INSERT ON messages WHEN NEW.role='user' "
                       "BEGIN SELECT RAISE(ABORT, 'private details'); END")
            db.commit()
        script = Script(finish())
        result = self.run_question(script)
        self.assertFalse(script.requests)
        self.assertEqual(result["persistence"]["user_message_saved"], False)
        state = self.store.get_session(self.session)
        self.assertEqual(len(state["messages"]), 2)
        self.assertFalse(state["memory_valid"])

    def test_unknown_session_and_initialization_failure_are_explicit(self):
        with self.assertRaises(SessionNotFound):
            self.store.get_session("unknown")
        with self.assertRaises(SessionNotFound):
            ConversationService(self.store, lambda: make_agent(Script(finish()))).run("unknown", "q")
        with self.assertRaises(StorageError):
            SessionStore(self.path / "not-a-directory.sqlite3")

    def test_unfinished_request_stays_invalid_after_restart(self):
        self.run_question()
        self.assertTrue(self.store.get_session(self.session)["memory_valid"])
        ids = self.store.begin_run(self.session, "已换题但进程中断")
        restarted = SessionStore(self.path)
        self.assertFalse(restarted.get_session(self.session)["memory_valid"])
        script = Script(finish())
        result = ConversationService(restarted, lambda: make_agent(script)).run(self.session, "继续")
        self.assertIsNone(result["memory_update"]["before"])
        abandoned = [r for r in restarted.get_session(self.session)["runs"] if r["id"] == ids["request_id"]][0]
        self.assertEqual(abandoned["state"], "abandoned")
        self.assertIn(ids["user_message_id"], result["history_selection"]["omitted_message_ids"])

    def test_same_session_serializes_across_store_instances(self):
        entered, release, second_model = Event(), Event(), Event()
        def first_policy(messages, tools):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("test worker was not released")
            return finish()
        def second_policy(messages, tools):
            second_model.set()
            return finish()
        first = ConversationService(self.store, lambda: make_agent(first_policy))
        second = ConversationService(SessionStore(self.path), lambda: make_agent(second_policy))
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first.run, self.session, "first")
            self.assertTrue(entered.wait(2))
            two = pool.submit(second.run, self.session, "second")
            try:
                self.assertFalse(second_model.wait(0.05))
            finally:
                release.set()
            first_result, second_result = one.result(timeout=3), two.result(timeout=3)
        self.assertTrue(first_result["persistence"]["saved"])
        self.assertEqual(len(second_result["history_selection"]["selected_message_ids"]), 2)
        self.assertEqual([m["role"] for m in self.store.get_session(self.session)["messages"]],
                         ["user", "assistant", "user", "assistant"])

    def test_preinvalidation_storage_failures_quarantine_across_instances(self):
        for failure in ("read", "invalidation_write"):
            with self.subTest(failure=failure):
                self.run_question()
                self.assertTrue(self.store.get_session(self.session)["memory_valid"])
                script = Script(finish())
                if failure == "read":
                    with patch.object(self.store, "get_session", side_effect=StorageError("storage_failed")):
                        result = self.run_question(script, question="改问产品")
                else:
                    with closing(sqlite3.connect(self.path)) as db:
                        db.execute("CREATE TRIGGER fail_invalidation BEFORE UPDATE ON sessions "
                                   "WHEN NEW.anchor_valid=0 BEGIN SELECT RAISE(ABORT, 'write failed'); END")
                        db.commit()
                    try:
                        result = self.run_question(script, question="改问产品")
                    finally:
                        with closing(sqlite3.connect(self.path)) as db:
                            db.execute("DROP TRIGGER fail_invalidation")
                            db.commit()
                self.assertFalse(result["persistence"]["saved"])
                self.assertFalse(script.requests)
                reopened = SessionStore(self.path)
                self.assertFalse(reopened.get_session(self.session)["memory_valid"])
                with closing(sqlite3.connect(self.path)) as db:
                    self.assertEqual(db.execute("SELECT anchor_valid FROM sessions WHERE id=?", (self.session,)).fetchone()[0], 1)
                follow = ConversationService(reopened, lambda: make_agent(Script(finish()))).run(self.session, "继续")
                self.assertIsNone(follow["memory_update"]["before"])
                self.assertTrue(follow["memory_valid"])


if __name__ == "__main__":
    unittest.main()
