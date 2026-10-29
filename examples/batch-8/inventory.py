"""Index direct live results once; never count nested histories or progress copies."""

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path


def collect(root):
    root = Path(root)
    unique = {}
    for path in sorted(root.rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        result = document.get("result") if isinstance(document, dict) else None
        if not isinstance(result, dict):
            continue
        if result.get("mode") != "live":
            raise ValueError("Non-live result inside live evidence tree")
        request_id = result["request_id"]
        if request_id in unique:
            if unique[request_id]["result"] != result:
                raise ValueError("Conflicting content for one request ID")
            unique[request_id]["copies"].append(path.relative_to(root.parent).as_posix())
            continue
        unique[request_id] = {"result": result, "path": path, "document": document, "copies": []}
    rows, known, unknown, calls = [], Decimal(0), 0, 0
    for request_id, item in unique.items():
        result = item["result"]
        events = [e for e in result["trace"] if e["kind"] in {"model_response", "model_error"}]
        if len(events) != result["counts"]["model_calls"]:
            raise ValueError("Model attempt count does not match top-level usage events")
        subtotal, missing = Decimal(0), 0
        for event in events:
            usage = event["usage"]
            if usage["estimated_cny_upper_rate"] is None:
                missing += 1
            else:
                subtotal += Decimal(str(usage["estimated_cny_upper_rate"]))
        subtotal = subtotal.quantize(Decimal("0.000001"))
        known += subtotal
        unknown += missing
        calls += len(events)
        rows.append({"request_id": request_id, "file": item["path"].relative_to(root.parent).as_posix(), "copies_not_counted": item["copies"],
                     "case_id": item["document"]["case_id"], "repeat": item["document"]["repeat"],
                     "turn": item["document"]["turn"], "status": result["status"], "stop_reason": result["stop_reason"],
                     "counts": result["counts"], "known_estimated_cny": float(subtotal),
                     "unknown_usage_requests": missing, "semantic_review": "see independent audit, not inferred here"})
    return {"created_at": datetime.now().astimezone().isoformat(), "unique_tasks": len(rows),
            "model_attempts": calls, "known_requests_estimated_cny": float(known),
            "requests_with_unknown_usage": unknown, "total_estimated_cny": None if unknown else float(known),
            "invoice_cny": None, "basis": "per-event recorded peak uncached estimate; not invoice or balance",
            "rows": rows}


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    inventory = collect(root / "runs")
    (root / "evidence-index.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: inventory[k] for k in ("unique_tasks", "model_attempts", "known_requests_estimated_cny",
                                               "requests_with_unknown_usage", "total_estimated_cny")}))
