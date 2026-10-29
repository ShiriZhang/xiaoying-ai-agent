import json
from pathlib import Path
import tempfile
import unittest

from agent_support import ROOT, Script, call, finish, make_agent, snapshot
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.embeddings import MockEncoder
from enterprise_knowledge_qa.memory import AnchorError, validate_anchor
from enterprise_knowledge_qa.retrieval import HybridIndex
from enterprise_knowledge_qa.sessions import SessionStore


def current_ids(messages):
    content = next(m["content"] for m in messages if m["role"] == "system" and m["content"].startswith("本轮消息标识："))
    return json.loads(content.split("：", 1)[1])


def anchor(value, source, *, focus=None, pending=None):
    return {"subject": {"value": value, "source_message_ids": [source]},
            "focus": focus, "pending_clarification": pending}


def product_policy(*, passage="D09-P01", text="MP4、MOV[C1]", expect_subject=None):
    def policy(messages, tools):
        observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
        if not observations:
            if expect_subject:
                memory = next(m["content"] for m in messages if m["role"] == "system" and m["content"].startswith("对话锚点"))
                assert json.loads(memory.split("：", 1)[1])["subject"]["value"] == expect_subject
            return call("search", {"query": "星帆剪辑 导出 分辨率"})
        if observations[-1]["tool"] == "search":
            return call("read", {"passage_ids": [passage]})
        ids = current_ids(messages)
        return finish(status="answered", part_statuses=["answered"], answer=text,
                      citation_refs=[{"marker": "[C1]", "passage_id": passage,
                                      "corpus_fingerprint": snapshot().fingerprint}],
                      anchor_snapshot=anchor("星帆剪辑", ids["user_message_id"]))
    return policy


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "sessions.sqlite3"
        self.store = SessionStore(self.path)
        self.session = self.store.create_session()
        self.index = HybridIndex.build(snapshot(), MockEncoder())

    def service(self, policy, *, store=None, **settings):
        return ConversationService(store or self.store, lambda: make_agent(policy, search=self.index, **settings))

    def test_restart_cross_window_anchor_understanding_still_reads_new_evidence(self):
        first = self.service(product_policy()).run(self.session, "星帆剪辑支持什么导出格式？")
        restarted = SessionStore(self.path)
        second = self.service(product_policy(passage="D10-P01", text="最高1080p[C1]", expect_subject="星帆剪辑"),
                              store=restarted, history_token_budget=1).run(self.session, "那最高支持多大分辨率？")
        self.assertEqual(second["status"], "answered")
        self.assertEqual(second["history_selection"]["selected_message_ids"], [])
        self.assertEqual(second["memory_update"]["before"], first["anchor_snapshot"])
        self.assertEqual(second["read_set"], ["D10-P01"])
        self.assertNotIn("D09-P01", second["read_set"])
        self.assertEqual(second["counts"]["model_calls"], 3)
        self.assertEqual(second["counts"]["tool_calls"], 2)
        self.assertTrue(second["memory_persisted"])
        self.assertEqual(restarted.get_session(self.session)["anchor_snapshot"], second["anchor_snapshot"])

    def test_topic_change_correction_and_pending_clear_replace_whole_snapshot(self):
        def pending_policy(messages, tools):
            source = current_ids(messages)["user_message_id"]
            return finish(status="needs_clarification", answer="需要确认讨论对象。", gaps=["对象不明"],
                          clarification="请问是哪项制度？", anchor_snapshot=anchor("报销", source,
                          focus={"value": "材料", "source_message_ids": [source]},
                          pending={"value": "确认对象", "source_message_ids": [source]}))
        self.service(pending_policy).run(self.session, "报销怎么做？")
        for question, subject in (("不问报销，改问星帆剪辑", "星帆剪辑"), ("刚才说错了，问人事请假", "请假")):
            def correction(messages, tools):
                return finish(anchor_snapshot=anchor(subject, current_ids(messages)["user_message_id"]))
            result = self.service(correction).run(self.session, question)
            self.assertEqual(result["anchor_snapshot"]["subject"]["value"], subject)
            self.assertIsNone(result["anchor_snapshot"]["focus"])
            self.assertIsNone(result["anchor_snapshot"]["pending_clarification"])
            self.assertTrue(result["memory_valid"])
        self.assertEqual(self.store.get_session(self.session)["anchor_snapshot"], result["anchor_snapshot"])

    def test_current_assistant_and_same_session_older_sources_are_allowed(self):
        first = self.service(product_policy()).run(self.session, "导出格式？")
        def policy(messages, tools):
            ids = current_ids(messages)
            proposal = anchor("星帆剪辑", first["message_ids"]["user_message_id"],
                              focus={"value": "分辨率", "source_message_ids": [ids["assistant_message_id"]]})
            return finish(anchor_snapshot=proposal)
        result = self.service(policy, history_token_budget=1).run(self.session, "继续")
        self.assertTrue(result["memory_valid"])
        state = self.store.get_session(self.session)
        self.assertIn(result["message_ids"]["assistant_message_id"], {m["id"] for m in state["messages"]})

    def test_invalid_anchor_structure_and_sources_have_safe_feedback(self):
        good = anchor("对象", "message")
        invalid = [None, "invalid", {}, {**good, "extra": None}, {**good, "focus": "bad"},
                   anchor("", "message"), anchor("对象", "D03-P01"), anchor("对象", "other-session"),
                   anchor("对象", "missing"), anchor("对象", 123)]
        for proposal in invalid:
            with self.subTest(proposal=proposal), self.assertRaises(AnchorError):
                validate_anchor(proposal, {"message"})

    def test_cross_session_source_degrades_memory_without_discarding_business(self):
        other = self.store.create_session()
        other_result = self.service(product_policy()).run(other, "导出？")
        def bad_policy(messages, tools):
            observations = [m for m in messages if m["role"] == "tool"]
            if not observations:
                return call("read", {"passage_ids": ["D03-P01"]})
            return finish(with_ref=True, anchor_snapshot=anchor("对象", other_result["message_ids"]["user_message_id"]))
        self.service(product_policy()).run(self.session, "导出？")
        result = self.service(bad_policy).run(self.session, "改问材料")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 0)
        self.assertFalse(result["memory_valid"])
        self.assertEqual(result["memory_warning"], "anchor_sources_must_belong_to_this_session")
        self.assertFalse(self.store.get_session(self.session)["memory_valid"])
        follow_up = self.service(Script(finish()), history_token_budget=1).run(self.session, "继续")
        self.assertIsNone(follow_up["memory_update"]["before"])


if __name__ == "__main__":
    unittest.main()
