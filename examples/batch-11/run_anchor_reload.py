"""Explicit paid synthetic-corpus regression; no public fault injection API.

Record actual model input messages without authorization headers or hidden
reasoning. Old anchor injection is a labelled historical test fixture.
"""

import argparse
import copy
from contextlib import closing
from dataclasses import replace
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile

from enterprise_knowledge_qa.agent import Agent
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.embeddings import BgeEncoder, REVISION
from enterprise_knowledge_qa.models import DeepSeekModel
from enterprise_knowledge_qa.retrieval import RetrievalStore
from enterprise_knowledge_qa.sessions import SessionStore
from enterprise_knowledge_qa.tracing import sanitize


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("evaluation_helpers", ROOT / "examples/batch-8/run_live.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--weights", default=str(ROOT / "models/bge-small-zh-v1.5"))
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    settings = replace(load_settings(args.env_file), mode="live",
                       embedding_model_path=Path(args.weights).resolve(), embedding_revision=args.revision)
    settings.check_live_prerequisites()
    base = json.loads(settings.data_path.read_text(encoding="utf-8"))
    assert base["synthetic"] is True
    expectation = {"before": "30/15 conflict requires clarification and original quotes; anchor only topics",
                   "change": "isolated D02 now45days with explicit replacement of D01, effective2026-03-01",
                   "after": "same session asks which now; new D02 quote supports45days; no old conflict reused",
                   "paths": ["new_safe_anchor", "injected_historical_pollution"],
                   "date": "2026-10-29", "history": "retain full original business history",
                   "semantic_review": "separate actual answer/anchor review required"}
    helpers.write_json(output / "pre-run-expectations.json", expectation)
    helpers.write_json(output / "metadata.json", {"started_at": datetime.now().astimezone().isoformat(),
        "runtime_source_fingerprints": helpers.fingerprints(), "mode": "live", "invoice_cny": None,
        "known_cost_guard_cny": 5, "cost_guard_note": "known usage only, not invoice or balance"})
    encoder = BgeEncoder(settings.embedding_model_path, settings.embedding_revision)
    summary = []
    known, unknown = 0.0, 0
    for legacy in (False, True):
        name = "legacy" if legacy else "fresh"
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
            folder = Path(folder)
            path = folder / "knowledge.json"
            path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
            retrieval = RetrievalStore(path, encoder)
            store = SessionStore(folder / "sessions.sqlite3")
            session = store.create_session()
            input_records = []
            class RecordingModel(DeepSeekModel):
                def generate(self, messages, tools, timeout):
                    input_records.append(copy.deepcopy(messages))
                    return super().generate(messages, tools, timeout)
            def factory():
                index = retrieval.acquire()
                return Agent(settings, RecordingModel(settings.api_key), index.snapshot, search=index,
                             clock=helpers.DateClock("2026-10-29"))
            service = ConversationService(store, factory)
            before_fingerprint = retrieval.acquire().snapshot.fingerprint
            for turn, question in enumerate(("报销期限是多少天？", "那现在应该按哪个？"), 1):
                if known >= 5 or unknown:
                    raise RuntimeError("Cost guard reached or usage unknown; inspect preserved prior outputs")
                input_records.clear()
                fixture = None
                if turn == 2:
                    if legacy:
                        fixture = {"subject": {"value": "差旅报销", "source_message_ids": [first["message_ids"]["user_message_id"]]},
                                   "focus": {"value": "差旅报销提交期限（15天与30天规定冲突）", "source_message_ids": [first["message_ids"]["assistant_message_id"]]},
                                   "pending_clarification": None}
                        helpers.write_json(output / "legacy-fixture.json", {"kind": "controlled injection, not new model output",
                            "based_on": "examples/batch-8/runs/core-validated/A02-r1-t1-97edf89e80624707aca3cc60ae44fcf3.json",
                            "anchor": fixture})
                        with closing(sqlite3.connect(store.path)) as db:
                            db.execute("UPDATE sessions SET anchor_json=?,anchor_valid=1 WHERE id=?", (json.dumps(fixture, ensure_ascii=False), session))
                            db.commit()
                        store = SessionStore(store.path)
                        service = ConversationService(store, factory)
                    changed = copy.deepcopy(base)
                    doc = next(d for d in changed["documents"] if d["doc_id"] == "D02")
                    text = doc["passages"][0]["text"].replace("15 天", "45 天")
                    doc["passages"][0]["text"] = text + "\n本规定自2026-03-01起明确替代《差旅报销期限规定》（D01）中提交期限的规定；现行期限为出差结束后45天。"
                    path.write_text(json.dumps(changed, ensure_ascii=False), encoding="utf-8")
                    retrieval.reload()
                corpus = json.loads(path.read_text(encoding="utf-8"))
                index = retrieval.acquire()
                helpers.write_json(output / f"{name}-t{turn}-corpus.json", corpus)
                result = service.run(session, question)
                checks = {"expected_status": result["status"] == ("needs_clarification" if turn == 1 else "answered"),
                          "anchor_valid": result["memory_valid"],
                          "citations_match_current_snapshot": all(c["text"] == index.snapshot.passages_by_id[c["passage_id"]].text
                              and c["corpus_fingerprint"] == index.snapshot.fingerprint and c["passage_id"] in result["read_set"] for c in result["citations"])}
                if turn == 2:
                    checks.update(fingerprint_changed=index.snapshot.fingerprint != before_fingerprint,
                                  new_D02_read="D02-P01" in result["read_set"],
                                  history_retained=len(result["history_selection"]["selected_message_ids"]) == 2,
                                  new_value_in_answer="45" in result["answer"],
                                  legacy_not_injected=(result["memory_update"]["before"] is None and
                                      result["memory_update"]["previous_warning"] == "anchor_contains_company_conclusion") if legacy else True)
                helpers.write_json(output / f"{name}-t{turn}.json", sanitize({"case_id": name, "turn": turn,
                    "result": result, "actual_model_inputs": input_records, "checks": checks}, (settings.api_key,)))
                known += result["usage"]["known_requests_estimated_cny"] or 0
                unknown += result["usage"]["requests_with_unknown_usage"]
                summary.append({"case": name, "turn": turn, "checks": checks, "request_id": result["request_id"]})
                first = result
                print(json.dumps({"case": name, "turn": turn, "status": result["status"], "checks": checks}), flush=True)
    report = {"rows": summary, "passed": all(all(r["checks"].values()) for r in summary),
              "known_estimated_cny": known, "unknown_usage_requests": unknown, "invoice_cny": None,
              "semantic_review": "separate review required; mechanical checks alone do not prove meaning"}
    helpers.write_json(output / "summary.json", report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
