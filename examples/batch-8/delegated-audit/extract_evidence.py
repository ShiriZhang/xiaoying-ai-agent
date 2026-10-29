"""Read-only derivative evidence inventory and cost deduplication.

This does not classify semantic correctness. Review the extracted actual
answers, cited text and actions independently before writing review findings.
"""

import argparse
import json
from pathlib import Path

from enterprise_knowledge_qa.snapshots import load_snapshot


def collect(roots):
    seen, records, corpus_fingerprints = {}, [], {}
    totals = {"model_attempts": 0, "model_outcomes_with_unknown_usage": 0,
              "known_prompt_tokens": 0, "known_completion_tokens": 0,
              "known_requests_estimated_cny": 0.0, "invoice_cny": None}
    for root in roots:
        for path in sorted(Path(root).rglob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict) or "case_id" not in payload or not isinstance(payload.get("result"), dict):
                continue
            result = payload["result"]
            request_id = result["request_id"]
            if request_id in seen:
                if seen[request_id] != result:
                    raise ValueError("Duplicate request_id has inconsistent results")
                continue
            seen[request_id] = result
            corpus_path = path.parent / payload["corpus_file"]
            corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
            if corpus_path not in corpus_fingerprints:
                corpus_fingerprints[corpus_path] = load_snapshot(corpus_path).fingerprint
            if result["corpus_fingerprint"] != corpus_fingerprints[corpus_path]:
                raise ValueError("Recorded result fingerprint does not match its actual corpus file")
            sources = {p["passage_id"]: (doc, p) for doc in corpus["documents"] for p in doc["passages"]}
            citation_checks = []
            for citation in result["citations"]:
                doc, passage = sources[citation["passage_id"]]
                citation_checks.append({"marker": citation["marker"], "passage_id": citation["passage_id"],
                    "source_fields_match": citation["doc_id"] == doc["doc_id"] and citation["version_date"] == doc["version_date"],
                    "verbatim_text_match": citation["text"] == passage["text"],
                    "snapshot_and_read_set_match": citation["corpus_fingerprint"] == result["corpus_fingerprint"]
                        and citation["passage_id"] in result["read_set"]})
            outcomes = [e for e in result["trace"] if e["kind"] in {"model_response", "model_error"}]
            if len(outcomes) != result["counts"]["model_calls"]:
                raise ValueError("Model attempt/outcome count mismatch")
            totals["model_attempts"] += len(outcomes)
            per_result_known = 0.0
            for event in outcomes:
                usage = event["usage"]
                if not usage["usage_known"]:
                    totals["model_outcomes_with_unknown_usage"] += 1
                if usage["prompt_tokens"] is not None:
                    totals["known_prompt_tokens"] += usage["prompt_tokens"]
                if usage["completion_tokens"] is not None:
                    totals["known_completion_tokens"] += usage["completion_tokens"]
                if usage["estimated_cny_upper_rate"] is not None:
                    per_result_known += usage["estimated_cny_upper_rate"]
            totals["known_requests_estimated_cny"] += per_result_known
            summary_known = result["usage"]["known_requests_estimated_cny"]
            if summary_known is not None and abs(summary_known - per_result_known) > 1e-9:
                raise ValueError("Usage summary does not match top-level model event usage")
            records.append({"file": path.as_posix(), "case_id": payload["case_id"], "repeat": payload["repeat"],
                "turn": payload["turn"], "request_id": request_id, "status": result["status"],
                "answer": result["answer"], "gaps": result["gaps"], "clarification": result["clarification"],
                "citations": result["citations"], "citation_checks": citation_checks,
                "actions": [{"action": e["action"], "arguments": e["arguments"]} for e in result["trace"] if e["kind"] == "action"],
                "tool_errors": [e for e in result["trace"] if e["kind"] == "tool_observation" and e["observation"]["status"] == "error"],
                "execution_issues": result["execution_issues"], "counts": result["counts"],
                "history_selection": result.get("history_selection"), "memory_update": result.get("memory_update"),
                "memory_valid": result["memory_valid"], "memory_warning": result["memory_warning"],
                "known_estimated_cny": round(per_result_known, 6),
                "unknown_usage_requests": result["usage"]["requests_with_unknown_usage"],
                "semantic_review": "pending independent reading"})
    totals["unique_task_requests"] = len(records)
    totals["known_requests_estimated_cny"] = round(totals["known_requests_estimated_cny"], 6)
    totals["total_estimated_cny"] = (totals["known_requests_estimated_cny"]
        if totals["model_outcomes_with_unknown_usage"] == 0 else None)
    groups = {}
    for row in records:
        key = Path(row["file"]).parent.as_posix()
        group = groups.setdefault(key, {"unique_task_requests": 0, "model_attempts": 0,
                                       "unknown_usage_requests": 0, "known_estimated_cny": 0.0})
        group["unique_task_requests"] += 1
        group["model_attempts"] += row["counts"]["model_calls"]
        group["unknown_usage_requests"] += row["unknown_usage_requests"]
        group["known_estimated_cny"] += row["known_estimated_cny"]
    for group in groups.values():
        group["known_estimated_cny"] = round(group["known_estimated_cny"], 6)
    return {"scope": "Derived inventory, not semantic pass/fail; invoice and user work time unverified",
            "deduplication": "top-level result.request_id only; rolling progress and nested context excluded",
            "costs": totals, "run_groups": groups, "records": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roots", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    value = collect(args.roots)
    with Path(args.output).open("w", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(value["costs"]))


if __name__ == "__main__":
    main()
