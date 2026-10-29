import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from enterprise_knowledge_qa.reading import ReadArgumentsError, ReadTool, validate_read_ids
from enterprise_knowledge_qa.snapshots import CorpusStore, load_snapshot


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/knowledge.json"


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = load_snapshot(CORPUS)
        (ROOT / ".cache").mkdir(exist_ok=True)

    def test_conflicting_originals_and_provenance_returned_verbatim(self):
        tool = ReadTool(self.snapshot)
        response = tool.read(["D02-P01", "D01-P01", "D03-P01"])
        self.assertEqual(response["status"], "success")
        self.assertIsNone(response["error"])
        self.assertEqual(response["corpus_fingerprint"], self.snapshot.fingerprint)
        self.assertEqual([p["passage_id"] for p in response["passages"]], ["D02-P01", "D01-P01", "D03-P01"])
        for item in response["passages"]:
            doc = self.snapshot.documents_by_id[item["doc_id"]]
            self.assertEqual(item["text"], self.snapshot.passages_by_id[item["passage_id"]].text)
            self.assertEqual(item["version_date"], doc.version_date)
            self.assertEqual(item["effective_date"], doc.effective_date)
            self.assertEqual(item["title"], doc.title)
        self.assertEqual(tool.read_set, frozenset(["D01-P01", "D02-P01", "D03-P01"]))
        json.dumps(response, ensure_ascii=False)  # Observation is directly serializable.

    def test_invalid_requests_do_not_execute_hook_or_partially_read(self):
        hook = Mock()
        tool = ReadTool(self.snapshot, fault_hook=hook)
        for request in (None, "D01-P01", {}, [], ["D01-P01"] * 4,
                        ["D01-P01", "D01-P01"], [1], [False], [""], [["D01-P01"]]):
            with self.subTest(request=request):
                result = tool.read(request)
                self.assertEqual(result["status"], "error")
                self.assertEqual(result["error"]["kind"], "validation_error")
                self.assertEqual(result["passages"], [])
                with self.assertRaises(ReadArgumentsError):
                    validate_read_ids(request)
        hook.assert_not_called()
        self.assertEqual(tool.read_set, frozenset())

    def test_unknown_id_rejects_whole_request_without_fabrication(self):
        tool = ReadTool(self.snapshot)
        response = tool.read(["D01-P01", "D99-P01"])
        self.assertEqual(response["error"]["code"], "unknown_passage")
        self.assertEqual(response["passages"], [])
        self.assertEqual(tool.read_set, frozenset())

    def test_fault_is_real_sanitized_no_retry_and_preserves_prior_read_set(self):
        hook = Mock(side_effect=[None, OSError("private-test-detail")])
        tool = ReadTool(self.snapshot, fault_hook=hook)
        self.assertEqual(tool.read(["D03-P01"])["status"], "success")
        response = tool.read(["D01-P01", "D02-P01"])
        self.assertEqual(hook.call_count, 2)
        self.assertEqual(response["error"]["code"], "read_failed")
        self.assertNotIn("private-test-detail", json.dumps(response))
        self.assertEqual(response["passages"], [])
        self.assertEqual(tool.read_set, frozenset(["D03-P01"]))

    def test_response_mutation_does_not_change_original_or_grant_other_task_reads(self):
        first, second = ReadTool(self.snapshot), ReadTool(self.snapshot)
        response = first.read(["D01-P01"])
        original = response["passages"][0]["text"]
        response["passages"][0]["text"] = "changed"
        self.assertEqual(first.read(["D01-P01"])["passages"][0]["text"], original)
        self.assertEqual(second.read_set, frozenset())

    def test_bound_task_reads_do_not_reopen_file_or_follow_reload(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            path = Path(directory) / "variant.json"
            raw = json.loads(CORPUS.read_text(encoding="utf-8"))
            path.write_text(json.dumps(raw), encoding="utf-8")
            store = CorpusStore(path)
            old_tool = ReadTool(store.acquire())
            original = old_tool.read(["D10-P01"])["passages"][0]["text"]
            raw["documents"][9]["passages"][0]["text"] = original.replace("1080p", "1440p")
            path.write_text(json.dumps(raw), encoding="utf-8")
            new_tool = ReadTool(store.reload())
            path.unlink()
            with patch.object(socket, "socket", side_effect=AssertionError("network")):
                old = old_tool.read(["D10-P01"])
                new = new_tool.read(["D10-P01"])
            self.assertEqual(old["passages"][0]["text"], original)
            self.assertIn("1440p", new["passages"][0]["text"])
            self.assertNotEqual(old["corpus_fingerprint"], new["corpus_fingerprint"])
