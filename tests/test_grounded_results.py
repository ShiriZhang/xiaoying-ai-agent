import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_support import ROOT, FakeClock, Script, call, finish, make_agent, snapshot
from enterprise_knowledge_qa.actions import ActionError, validate_finish
from enterprise_knowledge_qa.models import ModelError


class CitationTests(unittest.TestCase):
    def args(self):
        return json.loads(finish(with_ref=True).calls[0].arguments)

    def test_canonical_source_is_copied_verbatim(self):
        snap = snapshot()
        result = validate_finish(self.args(), snap, {"D03-P01"})
        citation = result["citations"][0]
        doc = snap.documents_by_id["D03"]
        self.assertEqual(citation["text"], snap.passages_by_id["D03-P01"].text)
        self.assertEqual(citation["version_date"], doc.version_date)
        self.assertEqual(citation["effective_date"], doc.effective_date)
        self.assertNotEqual(citation["text"], result["answer"])

    def test_provenance_and_marker_failures_are_independent(self):
        base = self.args()
        variants = []
        for field, value in (("passage_id", "unknown"), ("corpus_fingerprint", "old-snapshot"),
                             ("marker", "[C0]"), ("text", "模型概括")):
            args = copy.deepcopy(base)
            args["citation_refs"][0][field] = value
            variants.append(args)
        for marker in ("[C2]", "[C01]", "[Cfoo]", "[C-1]", "[C1", "[C 1]"):
            args = copy.deepcopy(base)
            args["answer"] += marker
            variants.append(args)
        args = copy.deepcopy(base)
        args["citation_refs"] *= 2
        variants.append(args)
        for args in variants:
            with self.subTest(args=args), self.assertRaises(ActionError):
                validate_finish(args, snapshot(), {"D03-P01"})
        with self.assertRaises(ActionError):
            validate_finish(base, snapshot(), set())

    def test_invalid_citation_uses_only_format_repair(self):
        script = Script(call("read", {"passage_ids": ["D03-P01"]}),
                        finish(with_ref=True, answer="材料[C0]"), finish(with_ref=True))
        result = make_agent(script).run("报销材料？")
        self.assertEqual(result["status"], "answered")
        self.assertEqual(result["counts"]["format_corrections"], 1)
        self.assertEqual(result["counts"]["recoveries"], 0)


def mixed_result(kind):
    """Controlled model outputs exercise the contract, not model semantics."""
    snap = snapshot()
    refs = [{"marker": "[C1]", "passage_id": "D03-P01", "corpus_fingerprint": snap.fingerprint}]
    answer = "材料：发票与出差审批单[C1]。\n"
    ids = ["D03-P01"]
    clarification = None
    if kind == "needs_clarification":
        ids += ["D01-P01", "D02-P01"]
        refs += [{"marker": f"[C{i}]", "passage_id": p, "corpus_fingerprint": snap.fingerprint}
                 for i, p in ((2, "D01-P01"), (3, "D02-P01"))]
        answer += "期限：D01为30天[C2]，D02为15天[C3]，缺少消解依据。"
        gap = "尚无确认现行期限或替代关系的依据。"
        clarification = "能提供现行制度或替代说明吗？"
        question = "报销材料和期限是什么？"
    elif kind == "insufficient_evidence":
        answer += "住房补贴：现有资料未覆盖，无法确认。"
        gap = "住房补贴资料缺失。"
        question = "报销材料和住房补贴政策是什么？"
    else:
        answer += "天气：超出公司资料问答范围。"
        gap = "天气不属于服务范围。"
        question = "报销材料是什么，今天天气怎样？"
    # A real local search observation reaches the controlled model before finish;
    # no assertion here claims the scripted policy made a semantic decision.
    from enterprise_knowledge_qa.embeddings import MockEncoder
    from enterprise_knowledge_qa.retrieval import HybridIndex
    search = HybridIndex.build(snap, MockEncoder())
    script = Script(call("search", {"query": question}), call("read", {"passage_ids": ids}),
                    call("search", {"query": gap, "limit": 12}),
                    finish(status=kind, answer=answer, citation_refs=refs, gaps=[gap],
                           part_statuses=["answered", kind], clarification=clarification))
    return make_agent(script, search=search).run(question)


class MixedResultTests(unittest.TestCase):
    def test_mixed_results_keep_supported_materials(self):
        for status in ("needs_clarification", "insufficient_evidence", "out_of_scope"):
            with self.subTest(status=status):
                result = mixed_result(status)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["part_statuses"], ["answered", status])
                self.assertIn("发票与出差审批单[C1]", result["answer"])
                self.assertEqual(result["citations"][0]["passage_id"], "D03-P01")
                self.assertEqual(len(result["citations"]), 3 if status == "needs_clarification" else 1)
                self.assertTrue(result["gaps"])
                self.assertEqual(result["execution_issues"], [])

    def test_every_mixed_priority_pair_is_enforced(self):
        priority = ["incomplete", "needs_clarification", "insufficient_evidence", "out_of_scope", "answered"]
        for i, high in enumerate(priority):
            for low in priority[i + 1:]:
                args = json.loads(finish(with_ref=True, status=high,
                                        part_statuses=[low, high], gaps=["待确认依据"],
                                        clarification="能提供依据吗？").calls[0].arguments)
                with self.subTest(high=high, low=low):
                    self.assertEqual(validate_finish(args, snapshot(), {"D03-P01"})["status"], high)
                    args["status"] = low
                    with self.assertRaises(ActionError):
                        validate_finish(args, snapshot(), {"D03-P01"})

    def test_invalid_parts_questions_and_missing_evidence_rejected(self):
        variants = [dict(part_statuses=[]), dict(part_statuses=[{}]), dict(status={"invalid": True}),
                    dict(clarification=["一问", "二问"]), dict(clarification="材料？期限？"),
                    dict(part_statuses=["answered"], status="answered"),
                    dict(status="needs_clarification", gaps=[], clarification=None),
                    dict(status="insufficient_evidence", gaps=[]),
                    dict(status="out_of_scope", clarification="你想问什么？")]
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(ActionError):
                args = json.loads(finish(**changes).calls[0].arguments)
                validate_finish(args, snapshot(), set())

    def test_interruption_keeps_evidence_without_fabricating_conclusion(self):
        script = Script(call("read", {"passage_ids": ["D03-P01"]}), ModelError("model_failed"))
        result = make_agent(script).run("材料和期限？")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["part_statuses"], ["incomplete"])
        self.assertEqual(result["citations"], [])
        self.assertEqual(result["gaps"], [])
        self.assertEqual(result["evidence"][0]["text"], snapshot().passages_by_id["D03-P01"].text)
        self.assertEqual(result["evidence"][0]["corpus_fingerprint"], snapshot().fingerprint)
        self.assertTrue(result["execution_issues"])
        self.assertEqual(result["counts"]["model_calls"], 2)

    def test_trace_save_timeout_preserves_already_valid_business_content(self):
        clock = FakeClock()
        def slow_save(*args, **kwargs):
            clock.advance(301)
            raise TimeoutError
        script = Script(call("read", {"passage_ids": ["D03-P01"]}), finish(with_ref=True))
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            with patch("enterprise_knowledge_qa.agent.save_trace", side_effect=slow_save):
                result = make_agent(script, clock=clock).run("材料？", trace_directory=directory)
            self.assertEqual(list(Path(directory).glob("*.json")), [])
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["part_statuses"], ["answered", "incomplete"])
        self.assertEqual(result["citations"][0]["text"], snapshot().passages_by_id["D03-P01"].text)
        self.assertIn("[C1]", result["answer"])
        self.assertEqual(result["stop_reason"], "task_timeout")


if __name__ == "__main__":
    unittest.main()
