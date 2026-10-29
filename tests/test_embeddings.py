import json
import math
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_support import ROOT
from enterprise_knowledge_qa.embeddings import BgeEncoder, EncodingError, MockEncoder, REVISION, unit_vector


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)

    def test_mock_is_stable_normalized_and_does_not_load_model_libraries(self):
        with patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
            encoder = MockEncoder()
            vectors = encoder.encode(["报销材料", "报销材料"])
        self.assertEqual(vectors[0], vectors[1])
        self.assertAlmostEqual(sum(x*x for x in vectors[0]), 1)
        self.assertEqual(vectors, MockEncoder().encode(["报销材料", "报销材料"]))
        result = subprocess.run([sys.executable, "-I", "-c",
            'import sys; from enterprise_knowledge_qa.embeddings import MockEncoder; MockEncoder().encode(["test"]); '
            'assert "torch" not in sys.modules and "transformers" not in sys.modules; print("offline mock only")'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_weights_fail_before_network_or_model_import(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            with patch.object(socket.socket, "connect", side_effect=AssertionError("network")):
                with self.assertRaises(EncodingError):
                    BgeEncoder(directory, REVISION)

    def test_invalid_vectors_and_inputs_fail(self):
        for vector in ([], [0, 0], [float("nan")], [float("inf")], [1e300]):
            with self.subTest(vector=vector), self.assertRaises(EncodingError):
                unit_vector(vector)
        for texts in ([""], [None], "not a batch"):
            with self.subTest(texts=texts), self.assertRaises(EncodingError):
                MockEncoder().encode(texts)

    def test_manifest_must_match_fixed_revision_and_required_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            path = Path(directory)
            (path / "weights-manifest.json").write_text(json.dumps({"model_id": "other", "revision": "other", "sha256": {}}))
            with self.assertRaises(EncodingError):
                BgeEncoder(path, REVISION)
