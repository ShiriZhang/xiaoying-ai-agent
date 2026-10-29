from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from enterprise_knowledge_qa.knowledge import CorpusError
from enterprise_knowledge_qa.snapshots import CorpusStore, load_snapshot


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/knowledge.json"


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "variant.json"
        self.raw = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.base_hash = hashlib.sha256(CORPUS.read_bytes()).hexdigest()
        self.write()

    def tearDown(self):
        self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest(), self.base_hash)

    def write(self):
        self.path.write_text(json.dumps(self.raw, ensure_ascii=False), encoding="utf-8")

    def test_task_keeps_old_snapshot_until_explicit_reload(self):
        store = CorpusStore(self.path)
        task_snapshot = store.acquire()
        self.assertIs(store.acquire(), task_snapshot)
        original = task_snapshot.passages_by_id["D10-P01"].text
        self.raw["documents"][9]["passages"][0]["text"] = original.replace("1080p", "1440p")
        self.write()
        self.assertIs(store.acquire(), task_snapshot)
        updated = store.reload()
        self.assertIs(store.acquire(), updated)
        self.assertNotEqual(updated.fingerprint, task_snapshot.fingerprint)
        self.assertEqual(task_snapshot.passages_by_id["D10-P01"].text, original)
        self.assertIn("1440p", updated.passages_by_id["D10-P01"].text)

    def test_fingerprint_ignores_json_formatting_but_includes_metadata(self):
        first = load_snapshot(self.path)
        self.path.write_text(json.dumps(self.raw, indent=4, sort_keys=True), encoding="utf-8")
        self.assertEqual(load_snapshot(self.path).fingerprint, first.fingerprint)
        doc = self.raw["documents"][0]
        doc["title"] = "另一标题"
        doc["passages"][0]["text"] = doc["passages"][0]["text"].replace("差旅报销期限规定", "另一标题")
        self.write()
        self.assertNotEqual(load_snapshot(self.path).fingerprint, first.fingerprint)

    def test_failed_reload_does_not_publish_invalid_or_partial_snapshot(self):
        store = CorpusStore(self.path)
        original = store.acquire()
        self.path.write_text("invalid JSON", encoding="utf-8")
        with self.assertRaises(CorpusError):
            store.reload()
        self.assertIs(store.acquire(), original)

    def test_single_D01_then_conflict_variant_does_not_filter_older_source(self):
        first_two = self.raw["documents"][:2]
        self.raw["documents"] = first_two[:1]
        self.write()
        store = CorpusStore(self.path)
        single = store.acquire()
        self.assertEqual(set(single.documents_by_id), {"D01"})
        self.raw["documents"] = first_two
        self.write()
        conflict = store.reload()
        self.assertEqual(set(conflict.documents_by_id), {"D01", "D02"})
        self.assertNotEqual(single.fingerprint, conflict.fingerprint)
        self.assertEqual(set(single.documents_by_id), {"D01"})

    def test_snapshot_and_indexes_cannot_be_mutated(self):
        snapshot = load_snapshot(self.path)
        with self.assertRaises(TypeError):
            snapshot.passages_by_id["D01-P01"] = snapshot.passages_by_id["D02-P01"]
        with self.assertRaises(TypeError):
            del snapshot.documents_by_id["D01"]
        with self.assertRaises(FrozenInstanceError):
            snapshot.fingerprint = "forged"
