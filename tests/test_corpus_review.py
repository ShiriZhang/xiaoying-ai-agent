"""Keep accepted review evidence tied to the exact, fully displayed corpus."""

from datetime import date
import json
from pathlib import Path
import unittest

from enterprise_knowledge_qa.reading import ReadTool
from enterprise_knowledge_qa.snapshots import load_snapshot


ROOT = Path(__file__).resolve().parents[1]


class CorpusReviewTests(unittest.TestCase):
    def test_confirmation_and_full_review_match_current_corpus(self):
        snapshot = load_snapshot(ROOT / "data/knowledge.json")
        review = (ROOT / "data/REVIEW.md").read_text(encoding="utf-8")
        record = json.loads((ROOT / "examples/batch-2/review.json").read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "accepted")
        self.assertEqual(record["corpus_fingerprint"], snapshot.fingerprint)
        self.assertEqual(record["user_confirmation"], "已阅读完整审阅稿，确认接受")
        self.assertIn(snapshot.fingerprint, review)
        self.assertIn(record["user_confirmation"], review)
        for document in snapshot.documents:
            for passage in document.passages:
                self.assertIn(passage.text, review)
                self.assertIn(passage.passage_id, review)

    def test_reviewed_effective_boundary_and_replacement_evidence_remain_visible(self):
        snapshot = load_snapshot(ROOT / "data/knowledge.json")
        tool = ReadTool(snapshot)
        result = tool.read(["D05-P01", "D06-P01"])
        self.assertEqual(result["status"], "success")
        old, new = result["passages"]
        # Fixture boundary checks only; do not pretend this is a model decision.
        self.assertLess(date(2026, 9, 30), date.fromisoformat(new["effective_date"]))
        self.assertEqual(date(2026, 10, 1), date.fromisoformat(new["effective_date"]))
        self.assertLess(date.fromisoformat(new["version_date"]), date.fromisoformat(new["effective_date"]))
        self.assertIn("2 个工作日", old["text"])
        self.assertIn("1 个工作日", new["text"])
        self.assertIn("自 2026-10-01 起", new["text"])
        self.assertIn("替代 D05", new["text"])
        self.assertIn("在 2026-10-01 之前", new["text"])

    def test_variant_expectations_are_documented_as_expectations(self):
        review = (ROOT / "data/REVIEW.md").read_text(encoding="utf-8")
        for term in ("不是运行结果", "仅 D01", "D01 与 D02", "2026-09-30", "2026-10-01", "待澄清"):
            self.assertIn(term, review)
