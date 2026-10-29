from collections import Counter
import copy
from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from enterprise_knowledge_qa.knowledge import CorpusError, load_documents, parse_documents


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/knowledge.json"


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(CORPUS.read_text(encoding="utf-8"))
        (ROOT / ".cache").mkdir(exist_ok=True)

    def test_base_coverage_and_confirmed_business_rules(self):
        docs = load_documents(CORPUS)
        self.assertEqual(len(docs), 12)
        self.assertEqual(Counter(d.topic for d in docs), {"差旅报销": 4, "人事": 4, "视频产品": 4})
        expected = {
            "D01": ["30 天"], "D02": ["15 天"], "D03": ["发票", "出差审批单"],
            "D04": ["直属负责人", "财务"], "D05": ["2 个工作日"],
            "D06": ["1 个工作日", "替代 D05", "2026-10-01"],
            "D07": ["补卡日期", "原因"], "D08": ["人事服务台"],
            "D09": ["MP4", "MOV"], "D10": ["1080p"],
            "D11": ["自动生成字幕"], "D12": ["本地", "手动删除"],
        }
        self.assertEqual({d.doc_id for d in docs}, set(expected))
        for doc in docs:
            body = "\n".join(p.text for p in doc.passages)
            for term in expected[doc.doc_id]:
                self.assertIn(term, body)
        self.assertNotIn("替代", docs[0].passages[0].text)
        self.assertNotIn("替代", docs[1].passages[0].text)

    def test_missing_empty_and_unknown_fields_are_rejected(self):
        variants = []
        for key in self.raw["documents"][0]:
            raw = copy.deepcopy(self.raw)
            del raw["documents"][0][key]
            variants.append(raw)
        for key in ("title", "scope", "passages"):
            raw = copy.deepcopy(self.raw)
            raw["documents"][0][key] = [] if key == "passages" else ""
            variants.append(raw)
        raw = copy.deepcopy(self.raw)
        raw["documents"][0]["priority"] = 1
        variants.append(raw)
        variants.extend([{}, {**self.raw, "documents": []}, {**self.raw, "synthetic": False}])
        for index, raw in enumerate(variants):
            with self.subTest(variant=index), self.assertRaises(CorpusError):
                parse_documents(raw)

    def test_duplicate_ids_bad_references_and_empty_original_rejected(self):
        variants = []
        raw = copy.deepcopy(self.raw)
        raw["documents"].append(copy.deepcopy(raw["documents"][0]))
        variants.append(raw)
        raw = copy.deepcopy(self.raw)
        raw["documents"][0]["passages"] *= 2
        variants.append(raw)
        for key, value in (("doc_id", "D02"), ("passage_id", "D02-P01"), ("text", " ")):
            raw = copy.deepcopy(self.raw)
            raw["documents"][0]["passages"][0][key] = value
            variants.append(raw)
        for raw in variants:
            with self.subTest(raw=variants.index(raw)), self.assertRaises(CorpusError):
                parse_documents(raw)

    def test_invalid_dates_and_metadata_body_mismatch_rejected(self):
        for key, value in (
            ("version_date", "2026-02-30"), ("effective_date", "20261001"),
            ("effective_date", "2026-02-01"), ("version_date", "2026-01-02"),
            ("title", "changed"), ("scope", "other employees"), ("topic", "changed"),
        ):
            raw = copy.deepcopy(self.raw)
            raw["documents"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(CorpusError):
                parse_documents(raw)
        raw = copy.deepcopy(self.raw)
        raw["documents"][0]["passages"][0]["text"] = raw["documents"][0]["passages"][0]["text"].replace("生效日期：2026-01-01", "生效日期：2026-05-01")
        with self.assertRaises(CorpusError):
            parse_documents(raw)

    def test_bad_json_duplicate_keys_missing_file_and_invalid_encoding(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            path = Path(directory) / "corpus.json"
            for content in (b"not json", b'{"schema_version":1,"schema_version":2}', b"\xff"):
                path.write_bytes(content)
                with self.assertRaises(CorpusError):
                    load_documents(path)
            with self.assertRaises(CorpusError):
                load_documents(Path(directory) / "absent.json")

    def test_small_corpus_allowed_and_validated_values_are_immutable(self):
        self.raw["documents"] = self.raw["documents"][:1]
        docs = parse_documents(self.raw)
        self.assertEqual(len(docs), 1)
        with self.assertRaises(FrozenInstanceError):
            docs[0].title = "changed"
        before = docs[0].passages[0].text
        self.raw["documents"][0]["passages"][0]["text"] = "mutated input"
        self.assertEqual(docs[0].passages[0].text, before)
