import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from agent_support import ROOT


spec = importlib.util.spec_from_file_location("batch8_inventory", ROOT / "examples/batch-8/inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class EvidenceInventoryTests(unittest.TestCase):
    def record(self):
        return {"case_id": "case", "repeat": 1, "turn": 1, "result": {
            "mode": "live", "request_id": "task", "status": "answered", "stop_reason": "finished",
            "counts": {"model_calls": 1}, "trace": [{"kind": "model_response", "usage": {
                "estimated_cny_upper_rate": 0.001234}}]}}

    def test_progress_nested_history_and_copied_output_are_not_double_counted(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            folder = Path(folder)
            record = self.record()
            for name, payload in (("one.json", record), ("copy.json", record),
                                  ("progress.json", {"rows": [record]}), ("nested.json", {"history": [record]})):
                (folder / name).write_text(json.dumps(payload), encoding="utf-8")
            result = inventory.collect(folder)
        self.assertEqual(result["unique_tasks"], 1)
        self.assertEqual(result["model_attempts"], 1)
        self.assertEqual(result["total_estimated_cny"], 0.001234)

    def test_unknown_usage_and_conflicting_request_copies_are_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            folder = Path(folder)
            record = self.record()
            record["result"]["trace"][0]["usage"]["estimated_cny_upper_rate"] = None
            (folder / "one.json").write_text(json.dumps(record), encoding="utf-8")
            result = inventory.collect(folder)
            self.assertIsNone(result["total_estimated_cny"])
            self.assertEqual(result["requests_with_unknown_usage"], 1)
            conflicting = copy.deepcopy(record)
            conflicting["result"]["status"] = "incomplete"
            (folder / "bad-copy.json").write_text(json.dumps(conflicting), encoding="utf-8")
            with self.assertRaises(ValueError):
                inventory.collect(folder)


if __name__ == "__main__":
    unittest.main()
