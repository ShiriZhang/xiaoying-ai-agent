"""Run real local embedding retrieval evidence without calling a generation API."""

import argparse
import hashlib
import json
from pathlib import Path
import socket
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4

from .embeddings import BgeEncoder, EncodingError, REVISION
from .retrieval import HybridIndex, RetrievalStore
from .snapshots import load_snapshot


def _vector_digest(index):
    return hashlib.sha256(json.dumps(index.vectors).encode()).hexdigest()


def boundary_checks(encoder, source: Path, index: HybridIndex, temporary_root: Path) -> dict:
    try:
        encoder.encode(["长" * 600])
    except EncodingError:
        long_document_rejected = True
    else:
        long_document_rejected = False
    try:
        encoder.encode(["长" * 600], query=True)
    except EncodingError:
        long_query_rejected = True
    else:
        long_query_rejected = False
    with patch.object(encoder, "encode", side_effect=RuntimeError("controlled real encoder fault")):
        fault = index.search("报销材料")
    raw = json.loads(source.read_text(encoding="utf-8"))
    before = source.read_bytes()
    with tempfile.TemporaryDirectory(dir=temporary_root) as directory:
        path = Path(directory) / "variant.json"
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        store = RetrievalStore(path, encoder)
        old = store.acquire()
        doc = next(d for d in raw["documents"] if d["doc_id"] == "D10")
        doc["passages"][0]["text"] = doc["passages"][0]["text"].replace("1080p", "1440p")
        path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        changed = store.reload()
        changed_observation = changed.search("1440p视频导出分辨率", 6)
        original_observation = old.search("1080p视频导出分辨率", 6)
        raw["documents"] = [d for d in raw["documents"] if d["doc_id"] in {"D01", "D02"}]
        two = list(raw["documents"])
        raw["documents"] = two[:1]
        path.write_text(json.dumps(raw), encoding="utf-8")
        single_store = RetrievalStore(path, encoder)
        single = single_store.acquire()
        single_observation = single.search("报销期限", 6)
        raw["documents"] = two
        path.write_text(json.dumps(raw), encoding="utf-8")
        conflict = single_store.reload()
        conflict_observation = conflict.search("报销期限", 6)
    source_unchanged = source.read_bytes() == before
    old_original = old.snapshot.passages_by_id["D10-P01"].text
    new_original = changed.snapshot.passages_by_id["D10-P01"].text
    checks = {"long_document_rejected": long_document_rejected, "long_query_rejected": long_query_rejected,
              "injected_real_encoding_error_is_tool_error": fault["status"] == "error" and fault["candidates"] == [],
              "source_unchanged": source_unchanged,
              "both_indices_rebuilt": old.snapshot.fingerprint != changed.snapshot.fingerprint and
                  _vector_digest(old) != _vector_digest(changed) and "1440p" in changed.term_counts[9],
              "old_task_keeps_original": "1080p" in old_original and "1440p" in new_original,
              "single_D01_recalled": [c["doc_id"] for c in single_observation["candidates"]] == ["D01"],
              "conflict_both_recalled": {c["doc_id"] for c in conflict_observation["candidates"]} == {"D01", "D02"}}
    return {"checks": checks, "passed": all(checks.values()), "fault_observation": fault,
            "old_fingerprint": old.snapshot.fingerprint, "new_fingerprint": changed.snapshot.fingerprint,
            "old_vector_sha256": _vector_digest(old), "new_vector_sha256": _vector_digest(changed),
            "old_original": old_original, "new_original": new_original,
            "old_search": original_observation, "new_search": changed_observation,
            "single_D01": single_observation, "D01_D02": conflict_observation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument("--data", default="data/knowledge.json")
    parser.add_argument("--cases", default="examples/batch-4/retrieval-cases.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    report = {"run_id": uuid4().hex, "layer": "real local CPU embedding + BM25/RRF; no generation API",
              "passed": False, "cases": []}
    start = time.monotonic()
    try:
        with patch.object(socket.socket, "connect", side_effect=AssertionError("Runtime network forbidden")):
            encoder = BgeEncoder(args.weights, args.revision)
            snapshot = load_snapshot(args.data)
            index = HybridIndex.build(snapshot, encoder)
            report.update(corpus_fingerprint=snapshot.fingerprint, configuration=index.configuration)
            cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))["cases"]
            for case in cases:
                for limit in (6, 12):
                    observation = index.search(case["query"], limit)
                    found = {c["passage_id"] for c in observation["candidates"]}
                    missing = sorted(set(case["expected_passage_ids"]) - found)
                    report["cases"].append({**case, "limit": limit, "missing": missing, "observation": observation,
                                             "passed": observation["status"] == "success" and not missing})
            temporary_root = Path(".cache")
            temporary_root.mkdir(exist_ok=True)
            report["boundaries"] = boundary_checks(encoder, Path(args.data), index, temporary_root)
            report["passed"] = all(c["passed"] for c in report["cases"]) and report["boundaries"]["passed"]
    except Exception as error:
        report["error_type"] = type(error).__name__  # Do not expose local paths or credentials.
    report["elapsed_seconds"] = time.monotonic() - start
    output = folder / (report["run_id"] + ".json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": report["run_id"], "passed": report["passed"],
                      "case_results": len(report["cases"]), "missing": {
                          c["id"] + "/" + str(c["limit"]): c["missing"] for c in report["cases"] if c["missing"]},
                      "error_type": report.get("error_type"), "elapsed_seconds": report["elapsed_seconds"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
