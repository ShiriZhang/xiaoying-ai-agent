"""Explicit paid evaluation driver, not a business endpoint or scripted model.

Every decision is made by DeepSeek. Only corpus/date/fault test inputs are
controlled here. Outputs are append-only; status/source checks are mechanical,
and semantic conclusions require separate review.
"""

import argparse
import copy
from dataclasses import replace
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import tempfile
import time

from enterprise_knowledge_qa.agent import Agent
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.deadlines import Clock
from enterprise_knowledge_qa.embeddings import BgeEncoder, REVISION
from enterprise_knowledge_qa.models import DeepSeekModel
from enterprise_knowledge_qa.reading import ReadTool
from enterprise_knowledge_qa.retrieval import RetrievalStore
from enterprise_knowledge_qa.sessions import SessionStore


ROOT = Path(__file__).resolve().parents[2]


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprints():
    import enterprise_knowledge_qa
    package = Path(enterprise_knowledge_qa.__file__).parent
    return {p.name: hashlib.sha256(p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()
            for p in sorted(package.glob("*.py"))}


class DateClock(Clock):
    def __init__(self, date):
        self.date = date

    def now(self):
        return (datetime.fromisoformat(self.date).replace(tzinfo=super().now().tzinfo)
                if self.date else super().now())


class ReadFault:
    def __init__(self, kind):
        self.kind, self.attempts = kind, 0

    def __call__(self, passage_ids):
        self.attempts += 1
        if self.kind == "persistent_read" or (self.kind == "temporary_read" and self.attempts == 1):
            raise RuntimeError("Controlled evaluation read fault")


def changed_corpus(base, *, variant=None, replacement=None):
    payload = copy.deepcopy(base)
    if variant in {"D01", "D01-D02"}:
        ids = {"D01"} if variant == "D01" else {"D01", "D02"}
        payload["documents"] = [d for d in payload["documents"] if d["doc_id"] in ids]
    if variant == "4K":
        replacement = {"doc_id": "D10", "old": "1080p", "new": "4K"}
    if replacement:
        count = 0
        for doc in payload["documents"]:
            if doc["doc_id"] == replacement["doc_id"]:
                for passage in doc["passages"]:
                    count += passage["text"].count(replacement["old"])
                    passage["text"] = passage["text"].replace(replacement["old"], replacement["new"])
        if not count:
            raise ValueError("Replacement must match existing passage text")
    return payload


def mechanical_checks(result, case, turn, snapshot):
    expected = case["statuses"] if len(case["questions"]) == 1 else [case["statuses"][turn]]
    references = result["citations"]
    status_matches = result["status"] in expected
    if case.get("fault") == "temporary_read" and result["status"] == "incomplete":
        status_matches = status_matches and result["stop_reason"] == "finished"
    return {"status_matches_pre_run_expectation": status_matches,
            "canonical_citations_match_snapshot": all(c["text"] == snapshot.passages_by_id[c["passage_id"]].text
                and c["corpus_fingerprint"] == snapshot.fingerprint and c["passage_id"] in result["read_set"]
                for c in references),
            "required_final_passages_cited": (set(case.get("passages", [])) <= {c["passage_id"] for c in references}
                if turn == len(case["questions"]) - 1 else None),
            "fault_observed": (any(e["kind"] == "tool_observation" and e["observation"]["status"] == "error"
                                   for e in result["trace"]) if case.get("fault") else None),
            "semantic_support": "pending independent review, not proved by these checks"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--weights", default=str(ROOT / "models/bge-small-zh-v1.5"))
    parser.add_argument("--revision", default=REVISION)
    parser.add_argument("--cases-file", default=str(Path(__file__).with_name("cases.json")))
    parser.add_argument("--group", choices=("core", "regressions", "memory", "personal"), required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-known-estimated-cny", type=float, default=5.0)
    args = parser.parse_args()
    if args.repeat not in {1, 2} or not 0 < args.max_known_estimated_cny <= 30:
        parser.error("repeat must be 1/2; known-cost guard must be positive and <=30 CNY")
    cases = json.loads(Path(args.cases_file).read_text(encoding="utf-8"))[args.group]
    if args.only:
        unknown = set(args.only) - {c["id"] for c in cases}
        if unknown:
            parser.error("Unknown selected case ID")
        cases = [case for case in cases if case["id"] in args.only]
    # Explicit live flag authorizes this evaluation, not edits to private .env.
    settings = replace(load_settings(args.env_file), mode="live",
                       embedding_model_path=Path(args.weights).resolve(), embedding_revision=args.revision)
    settings.check_live_prerequisites()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    (output / "corpora").mkdir()
    base = json.loads(settings.data_path.read_text(encoding="utf-8"))
    metadata = {"started_at": datetime.now().astimezone().isoformat(), "mode": "live", "group": args.group,
                "repeat": args.repeat, "git_base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "runtime_source_fingerprints": fingerprints(), "python": platform.python_version(), "platform": platform.platform(),
                "packages": {name: importlib.metadata.version(name) for name in
                             ("torch", "transformers", "fastapi", "pydantic", "python-dotenv")},
                "requested_model": "deepseek-flash", "endpoint": "https://api.deepseek.com/chat/completions",
                "thinking_mode": "disabled", "implicit_retries": 0, "embedding_revision": args.revision,
                "temperature": DeepSeekModel.temperature,
                "known_cost_guard_cny": args.max_known_estimated_cny, "invoice_cny": None,
                "cost_guard_note": "known usage estimate only, not account balance or a bound on unknown usage"}
    write_json(output / "metadata.json", metadata)
    write_json(output / "pre-run-cases.json", cases)
    encoder = BgeEncoder(settings.embedding_model_path, settings.embedding_revision)
    rows, known_cost, unknown_calls = [], 0.0, 0
    stopped = None
    run_start = time.monotonic()
    with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
        folder = Path(folder)
        data_path = folder / "knowledge.json"
        data_path.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
        retrieval = RetrievalStore(data_path, encoder)
        store = SessionStore(folder / "sessions.sqlite3")
        for repeat in range(1, args.repeat + 1):
            for case in cases:
                if known_cost >= args.max_known_estimated_cny:
                    stopped = "known_cost_guard"
                    break
                payload = changed_corpus(base, variant=case.get("variant"))
                data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                retrieval.reload()
                session_id = store.create_session()
                fault = ReadFault(case.get("fault"))
                case_settings = replace(settings, history_token_budget=case.get("budget", settings.history_token_budget))
                def factory():
                    index = retrieval.acquire()
                    return Agent(case_settings, DeepSeekModel(settings.api_key), index.snapshot, search=index,
                                 reader=ReadTool(index.snapshot, fault_hook=fault if case.get("fault") else None),
                                 clock=DateClock(case.get("date")))
                service = ConversationService(store, factory)
                for turn, question in enumerate(case["questions"]):
                    if known_cost >= args.max_known_estimated_cny:
                        stopped = "known_cost_guard"
                        break
                    if turn and (case.get("reload_after_first") or case.get("replace_after_first")):
                        payload = changed_corpus(base, variant=case.get("reload_after_first"), replacement=case.get("replace_after_first"))
                        data_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                        retrieval.reload()
                    index = retrieval.acquire()
                    corpus_name = index.snapshot.fingerprint.split(":", 1)[1] + ".json"
                    if not (output / "corpora" / corpus_name).exists():
                        write_json(output / "corpora" / corpus_name, payload)
                    result = service.run(session_id, question)
                    filename = f'{case["id"]}-r{repeat}-t{turn + 1}-{result["request_id"]}.json'
                    checks = mechanical_checks(result, case, turn, index.snapshot)
                    write_json(output / filename, {"case_id": case["id"], "repeat": repeat, "turn": turn + 1,
                        "pre_run_expected": case["expected"], "mechanical_checks": checks,
                        "corpus_file": "corpora/" + corpus_name, "result": result})
                    known = result["usage"]["known_requests_estimated_cny"]
                    known_cost += known if known is not None else 0
                    unknown_calls += result["usage"]["requests_with_unknown_usage"]
                    row = {"case_id": case["id"], "repeat": repeat, "turn": turn + 1, "file": filename,
                           "status": result["status"], "stop_reason": result["stop_reason"], "counts": result["counts"],
                           "known_estimated_cny": known, "unknown_usage_requests": result["usage"]["requests_with_unknown_usage"],
                           "mechanical_checks": checks}
                    rows.append(row)
                    # Each row is durable immediately, including failures; never overwrite.
                    write_json(output / f"progress-{len(rows):03}.json", {"rows": rows, "known_estimated_cny": known_cost,
                        "unknown_usage_requests": unknown_calls, "total_estimated_cny": None if unknown_calls else known_cost})
                    print(json.dumps({k: row[k] for k in ("case_id", "repeat", "turn", "status", "stop_reason", "counts")}), flush=True)
                    if result["stop_reason"] in {"authentication_failed", "model_unavailable", "http_402", "http_429"}:
                        stopped = result["stop_reason"]
                        break
                if stopped:
                    break
            if stopped:
                break
    write_json(output / "summary.json", {"rows": rows, "stopped": stopped, "known_estimated_cny": known_cost,
        "unknown_usage_requests": unknown_calls, "total_estimated_cny": None if unknown_calls else known_cost,
        "invoice_cny": None, "elapsed_seconds": time.monotonic() - run_start,
        "semantic_review": "separate review required; mechanical results are not semantic pass"})
    print(json.dumps({"output": str(output), "turns": len(rows), "stopped": stopped,
                      "known_estimated_cny": known_cost, "unknown_usage_requests": unknown_calls}), flush=True)


if __name__ == "__main__":
    main()
