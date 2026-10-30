import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from agent_support import ROOT, call, finish, make_agent
from test_memory import anchor, current_ids, product_policy
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.memory import AnchorError, validate_anchor
from enterprise_knowledge_qa.sessions import SessionStore


class AnchorContentTests(unittest.TestCase):
    def test_topics_numbers_and_assertions_in_every_field(self):
        cases = json.loads((ROOT / "examples/batch-11/anchor-cases.json").read_text(encoding="utf-8"))
        for field in ("subject", "focus", "pending_clarification"):
            for key, accepted in (("allowed", True), ("rejected", False)):
                for value in cases[key]:
                    proposal = dict.fromkeys(("subject", "focus", "pending_clarification"))
                    proposal[field] = {"value": value, "source_message_ids": ["message"]}
                    with self.subTest(field=field, value=value):
                        if accepted:
                            self.assertEqual(validate_anchor(proposal, {"message"}), proposal)
                        else:
                            with self.assertRaisesRegex(AnchorError, "anchor_contains_company_conclusion"):
                                validate_anchor(proposal, {"message"})

    def test_original_real_failures_now_rejected_without_editing_evidence(self):
        cases = json.loads((ROOT / "examples/batch-11/anchor-cases.json").read_text(encoding="utf-8"))
        for case in cases["original_failures"]:
            result = json.loads((ROOT / case["file"]).read_text(encoding="utf-8"))["result"]
            proposal = result["anchor_snapshot"]
            ids = {s for item in proposal.values() if item for s in item["source_message_ids"]}
            with self.assertRaisesRegex(AnchorError, "anchor_contains_company_conclusion"):
                validate_anchor(proposal, ids)

    def test_content_failure_keeps_business_without_extra_model_or_repair(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            store = SessionStore(Path(folder) / "sessions.sqlite3")
            session = store.create_session()
            def policy(messages, tools):
                if not any(m["role"] == "tool" for m in messages):
                    return call("read", {"passage_ids": ["D03-P01"]})
                return finish(with_ref=True, anchor_snapshot=anchor("最高支持2160p", current_ids(messages)["user_message_id"]))
            result = ConversationService(store, lambda: make_agent(policy)).run(session, "材料？")
            self.assertEqual(result["status"], "answered")
            self.assertEqual(result["counts"], {"model_calls": 2, "tool_calls": 1, "recoveries": 0, "format_corrections": 0})
            self.assertEqual(result["memory_warning"], "anchor_contains_company_conclusion")
            self.assertFalse(result["memory_valid"])
            self.assertTrue(result["persistence"]["saved"])
            self.assertFalse(store.get_session(session)["memory_valid"])

    def test_legacy_pollution_is_not_injected_and_old_history_is_retained(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            path = Path(folder) / "sessions.sqlite3"
            store = SessionStore(path)
            session = store.create_session()
            first = ConversationService(store, lambda: make_agent(product_policy())).run(session, "星帆剪辑导出格式？")
            polluted = anchor("星帆剪辑", first["message_ids"]["user_message_id"],
                              focus={"value": "最高支持1080p", "source_message_ids": [first["message_ids"]["assistant_message_id"]]})
            with closing(sqlite3.connect(path)) as db:
                db.execute("UPDATE sessions SET anchor_json=?, anchor_valid=1 WHERE id=?", (json.dumps(polluted), session))
                db.commit()
            restarted = SessionStore(path)
            self.assertFalse(restarted.get_session(session)["memory_valid"])
            seen = []
            def policy(messages, tools):
                seen.extend(copy.deepcopy(messages))
                return finish(anchor_snapshot=anchor("星帆剪辑", current_ids(messages)["user_message_id"]))
            result = ConversationService(restarted, lambda: make_agent(policy)).run(session, "继续问导出")
            self.assertIsNone(result["memory_update"]["before"])
            self.assertEqual(result["memory_update"]["previous_warning"], "anchor_contains_company_conclusion")
            memory = next(m["content"] for m in seen if m["role"] == "system" and m["content"].startswith("对话锚点"))
            self.assertIsNone(json.loads(memory.split("：", 1)[1]))
            self.assertTrue(result["memory_valid"])
            self.assertEqual(len(restarted.get_session(session)["messages"]), 4)
            self.assertEqual(len(result["history_selection"]["selected_message_ids"]), 2)


if __name__ == "__main__":
    unittest.main()
