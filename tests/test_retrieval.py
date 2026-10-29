import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from agent_support import ROOT, snapshot
from enterprise_knowledge_qa.embeddings import MockEncoder
from enterprise_knowledge_qa.knowledge import parse_documents
from enterprise_knowledge_qa.retrieval import HybridIndex, RetrievalStore, tokenize
from enterprise_knowledge_qa.snapshots import CorpusSnapshot


class ConstantEncoder:
    mode = "mock"
    metadata = {"mode": "mock", "model_id": "controlled-constant", "revision": "1"}

    def __init__(self):
        self.calls = []
        self.fail = False

    def encode(self, texts, *, query=False):
        self.calls.append((tuple(texts), query))
        if self.fail:
            raise RuntimeError("controlled encoder failure")
        return tuple((1.0, 0.0) for _ in texts)


class RetrievalTests(unittest.TestCase):
    def test_routes_rrf_dedup_and_requested_counts(self):
        index = HybridIndex.build(snapshot(), MockEncoder())
        small, large = index.search("差旅报销材料"), index.search("差旅报销材料", 12)
        self.assertEqual(len(small["candidates"]), 6)
        self.assertEqual(len(large["candidates"]), 12)
        self.assertEqual(len({p["passage_id"] for p in large["candidates"]}), 12)
        self.assertLessEqual(len(large["branch_rankings"]["bm25"]), 12)
        self.assertEqual(len(large["branch_rankings"]["semantic"]), 12)
        first = small["candidates"][0]
        self.assertAlmostEqual(first["rrf_score"], sum(1 / (60 + r["rank"]) for r in first["branches"].values()))
        self.assertNotIn("confidence", json.dumps(small))
        self.assertNotIn("text", first)  # candidate summary does not grant read permission

    def test_single_D01_is_positive_bm25_and_never_padded(self):
        raw = json.loads((ROOT / "data/knowledge.json").read_text(encoding="utf-8"))
        raw["documents"] = raw["documents"][:1]
        index = HybridIndex.build(CorpusSnapshot(parse_documents(raw)), ConstantEncoder())
        result = index.search("报销期限", 12)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertGreater(result["branch_rankings"]["bm25"][0]["score"], 0)
        self.assertEqual(result["candidates"][0]["doc_id"], "D01")

    def test_stable_ties_and_successful_empty_candidate_set(self):
        index = HybridIndex.build(snapshot(), ConstantEncoder())
        ids = [p["passage_id"] for p in index.search("zzzz", 12)["candidates"]]
        self.assertEqual(ids, sorted(index.passage_ids))
        empty = HybridIndex.build(CorpusSnapshot(()), ConstantEncoder()).search("query")
        self.assertEqual(empty["status"], "success")
        self.assertEqual(empty["candidates"], [])
        self.assertIsNone(empty["error"])

    def test_encoding_failure_malformed_vectors_and_bad_arguments_never_single_route(self):
        encoder = ConstantEncoder()
        index = HybridIndex.build(snapshot(), encoder)
        encoder.fail = True
        failed = index.search("报销")
        self.assertEqual(failed["status"], "error")
        self.assertEqual(failed["candidates"], [])
        for query, limit in (("", 6), ("q", 7), (None, 6), ("q", True)):
            self.assertEqual(index.search(query, limit)["error"]["kind"], "validation_error")
        encoder.fail = False
        encoder.encode = lambda texts, query=False: ((float("nan"), 1),)
        self.assertEqual(index.search("q")["status"], "error")

    def test_cross_snapshot_result_rejected_and_index_state_is_immutable(self):
        index = HybridIndex.build(snapshot(), MockEncoder())
        other = CorpusSnapshot(())
        self.assertEqual(index("q", 6, other)["error"]["code"], "snapshot_mismatch")
        with self.assertRaises(TypeError):
            index.term_counts[0]["forged"] = 5
        metadata = index.encoder_metadata
        metadata["mode"] = "live"
        self.assertEqual(index.encoder_metadata["mode"], "mock")

    def test_tokenization_normalization_leaves_canonical_original_untouched(self):
        self.assertEqual(tokenize("ＭＰ４差旅"), ("mp4", "差", "旅", "差旅"))
        snap = snapshot()
        before = snap.passages_by_id["D03-P01"].text
        index = HybridIndex.build(snap, MockEncoder())
        index.search("报销")
        self.assertEqual(snap.passages_by_id["D03-P01"].text, before)


class ReloadTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "variant.json"
        self.raw = json.loads((ROOT / "data/knowledge.json").read_text(encoding="utf-8"))
        self.original = (ROOT / "data/knowledge.json").read_bytes()
        self.write()

    def tearDown(self):
        self.assertEqual((ROOT / "data/knowledge.json").read_bytes(), self.original)

    def write(self):
        self.path.write_text(json.dumps(self.raw, ensure_ascii=False), encoding="utf-8")

    def test_text_reload_rebuilds_both_routes_and_old_task_keeps_old_index(self):
        encoder = MockEncoder()
        store = RetrievalStore(self.path, encoder)
        old = store.acquire()
        self.raw["documents"][9]["passages"][0]["text"] = self.raw["documents"][9]["passages"][0]["text"].replace("1080p", "1440p")
        self.write()
        self.assertIs(store.acquire(), old)
        new = store.reload()
        self.assertNotEqual(old.snapshot.fingerprint, new.snapshot.fingerprint)
        self.assertNotEqual(old.vectors, new.vectors)
        self.assertNotIn("1440p", old.term_counts[9])
        self.assertIn("1440p", new.term_counts[9])
        self.assertIn("1080p", old.snapshot.passages_by_id["D10-P01"].text)
        self.assertIn("1440p", new.snapshot.passages_by_id["D10-P01"].text)

    def test_failed_encoding_reload_or_invalid_corpus_never_publishes_partial_index(self):
        encoder = ConstantEncoder()
        store = RetrievalStore(self.path, encoder)
        old = store.acquire()
        encoder.fail = True
        with self.assertRaises(RuntimeError):
            store.reload()
        self.assertIs(store.acquire(), old)
        self.path.write_text("bad-json", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.reload()
        self.assertIs(store.acquire(), old)

    def test_adding_D02_rebuilds_without_hiding_older_D01(self):
        two = copy.deepcopy(self.raw["documents"][:2])
        self.raw["documents"] = two[:1]
        self.write()
        encoder = ConstantEncoder()
        store = RetrievalStore(self.path, encoder)
        old = store.acquire()
        self.raw["documents"] = two
        self.write()
        new = store.reload()
        self.assertEqual([len(call[0]) for call in encoder.calls], [1, 2])
        self.assertEqual(len(old.search("报销期限")["candidates"]), 1)
        self.assertEqual({p["doc_id"] for p in new.search("报销期限")["candidates"]}, {"D01", "D02"})
