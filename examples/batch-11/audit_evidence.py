"""Audit recorded batch-11 provenance, usage and canonical citations.

No model calls. Semantic support is reviewed separately from these checks.
"""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from enterprise_knowledge_qa.memory import validate_anchor


ROOT = Path(__file__).resolve().parents[2]
BATCH = Path(__file__).resolve().parent
FINAL = {"core-resumed": 18, "regressions-resumed": 9, "memory-validated": 7, "personal-validated": 2, "anchor-validated": 4}


def digest(path):
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()


def audit(*, require_complete=True):
    import enterprise_knowledge_qa
    source = {p.name: digest(p) for p in sorted((ROOT / "src/enterprise_knowledge_qa").glob("*.py"))}
    installed = {p.name: digest(p) for p in Path(enterprise_knowledge_qa.__file__).parent.glob("*.py")}
    assert source == installed
    rows, seen = [], set()
    failed_checks = []
    final_counts = dict.fromkeys(FINAL, 0)
    for folder in sorted((BATCH / "runs").iterdir()):
        if not folder.is_dir() or not (folder / "metadata.json").is_file():
            continue
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        is_final = folder.name in FINAL
        if is_final:
            assert metadata["runtime_source_fingerprints"] == source, folder
        for path in sorted(folder.glob("*.json")):
            document = json.loads(path.read_text(encoding="utf-8"))
            result = document.get("result") if isinstance(document, dict) else None
            if not isinstance(result, dict):
                continue
            assert result["request_id"] not in seen
            seen.add(result["request_id"])
            events = [e for e in result["trace"] if e["kind"] in {"model_response", "model_error"}]
            assert len(events) == result["counts"]["model_calls"]
            unknown = sum(not e["usage"]["usage_known"] for e in events)
            known = sum((Decimal(str(e["usage"]["estimated_cny_upper_rate"])) for e in events
                         if e["usage"]["estimated_cny_upper_rate"] is not None), Decimal(0))
            quotes = True
            if is_final:
                final_counts[folder.name] += 1
                corpus_path = folder / document["corpus_file"] if "corpus_file" in document else folder / (path.stem + "-corpus.json")
                corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
                passages = {p["passage_id"]: (d, p) for d in corpus["documents"] for p in d["passages"]}
                for c in result["citations"]:
                    doc, passage = passages[c["passage_id"]]
                    quotes = quotes and (c["text"] == passage["text"] and c["doc_id"] == doc["doc_id"]
                        and c["version_date"] == doc["version_date"] and c["corpus_fingerprint"] == result["corpus_fingerprint"]
                        and c["passage_id"] in result["read_set"])
                assert quotes
                if result["memory_valid"]:
                    proposal = result["anchor_snapshot"]
                    ids = {s for item in proposal.values() if item for s in item["source_message_ids"]}
                    validate_anchor(proposal, ids)
                checks = document.get("checks", document.get("mechanical_checks", {}))
                if any(v is False for v in checks.values()):
                    failed_checks.append(path.relative_to(BATCH).as_posix())
                    if require_complete:
                        raise AssertionError(path)
            rows.append({"file": path.relative_to(BATCH).as_posix(), "request_id": result["request_id"],
                         "case_id": document["case_id"], "repeat": document.get("repeat", 1), "turn": document["turn"],
                         "final_source": is_final, "status": result["status"], "counts": result["counts"],
                         "memory_valid": result["memory_valid"], "memory_warning": result["memory_warning"],
                         "known_estimated_cny": float(known), "unknown_usage_requests": unknown,
                         "canonical_quotes_valid": quotes if is_final else None})
    if require_complete:
        assert final_counts == FINAL, final_counts
    baseline = json.loads((BATCH / "baseline-failures.json").read_text(encoding="utf-8"))
    assert all(hashlib.sha256((ROOT / c["file"]).read_bytes()).hexdigest() == c["sha256"] for c in baseline["cases"])
    return {"base_commit": "e1e9ef2cd5376afd68aea7b38c36c755d2dbbfcc", "source_fingerprints": source,
            "installed_source_matches": True, "original_failure_files_unchanged": True, "final_counts": final_counts,
            "all_recorded_tasks": len(rows), "model_attempts": sum(r["counts"]["model_calls"] for r in rows),
            "known_estimated_cny": float(sum((Decimal(str(r["known_estimated_cny"])) for r in rows), Decimal(0))),
            "unknown_usage_requests": sum(r["unknown_usage_requests"] for r in rows), "invoice_cny": None,
            "expected_final_counts": FINAL, "failed_checks": failed_checks,
            "semantic_support": "requires separate independent answer and anchor review", "rows": rows,
            "passed": final_counts == FINAL and not failed_checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-incomplete", action="store_true", help="Record incomplete/failed coverage honestly; result is not a pass")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Use a new output filename; preserve previous results")
    report = audit(require_complete=not args.allow_incomplete)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("passed", "all_recorded_tasks", "final_counts", "known_estimated_cny", "unknown_usage_requests")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
