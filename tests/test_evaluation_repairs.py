import json
import unittest

from agent_support import call, finish, make_agent, snapshot


class LiveFailureRegressionTests(unittest.TestCase):
    def test_bare_citation_marker_receives_actionable_repair_feedback(self):
        requests = []
        def policy(messages, tools):
            requests.append(messages)
            if len(requests) == 1:
                return call("read", {"passage_ids": ["D03-P01"]})
            if len(requests) == 2:
                return finish(with_ref=True, citation_refs=[{"marker": "C1", "passage_id": "D03-P01",
                    "corpus_fingerprint": snapshot().fingerprint}])
            feedback = json.loads(messages[-1]["content"])
            self.assertIn("[C1]", feedback["error"]["message"])
            self.assertIn("square brackets", feedback["error"]["message"])
            return finish(with_ref=True)
        result = make_agent(policy).run("材料？")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 1)
        self.assertEqual(result["counts"]["recoveries"], 0)

    def test_two_question_clarification_repairs_to_one_without_losing_business(self):
        count = 0
        def policy(messages, tools):
            nonlocal count
            count += 1
            if count == 1:
                return finish(status="needs_clarification", answer="需要确认现行依据。", gaps=["现行依据缺失"],
                              clarification="能提供制度吗？有替代说明吗？")
            message = json.loads(messages[-1]["content"])["error"]["message"]
            self.assertIn("remove extra questions", message)
            return finish(status="needs_clarification", answer="需要确认现行依据。", gaps=["现行依据缺失"],
                          clarification="能提供现行制度或替代说明吗？")
        result = make_agent(policy).run("期限？")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["counts"]["format_corrections"], 1)
        self.assertEqual(result["clarification"].count("？"), 1)

    def test_follow_up_search_exposes_unread_candidates_without_granting_read_rights(self):
        count = 0
        def policy(messages, tools):
            nonlocal count
            count += 1
            if count == 1:
                return call("read", {"passage_ids": ["D03-P01"]})
            if count == 2:
                return call("search", {"query": "补充依据"})
            observed = json.loads(next(m["content"] for m in reversed(messages) if m["role"] == "tool"))
            self.assertEqual(observed["task_evidence"]["read_passage_ids"], ["D03-P01"])
            self.assertEqual(observed["task_evidence"]["unread_candidate_ids"], ["D04-P01"])
            self.assertIn("读取新相关候选", observed["instruction"])
            self.assertEqual(messages[-1]["role"], "system")
            return finish(with_ref=True)
        result = make_agent(policy, search=lambda query, limit, snap: {
            "tool": "search", "status": "success", "corpus_fingerprint": snap.fingerprint,
            "candidates": [{"passage_id": "D03-P01"}, {"passage_id": "D04-P01"}]}).run("q")
        self.assertEqual(result["read_set"], ["D03-P01"])
        self.assertEqual(result["citations"][0]["passage_id"], "D03-P01")


if __name__ == "__main__":
    unittest.main()
