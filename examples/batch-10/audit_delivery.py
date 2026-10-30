"""Check delivery files and recorded evidence without network or model calls.

Run from the repository root with installed project dependencies. This checks
provenance and completeness; linked independent reviews assess semantics.
"""

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def audit():
    import enterprise_knowledge_qa
    package = Path(enterprise_knowledge_qa.__file__).parent
    source = {p.name: digest(p) for p in sorted((ROOT / "src/enterprise_knowledge_qa").glob("*.py"))}
    checks = {"installed_package_matches_source": source == {p.name: digest(p) for p in package.glob("*.py")}}
    prior = read("examples/batch-8/source-fingerprints.json")["files"]
    checks["prior_56_evidence_inputs_unchanged"] = all(digest(ROOT / p) == v for p, v in prior.items())
    scenarios = read("examples/batch-10/acceptance-matrix.json")["scenarios"]
    checks["matrix_has_74_distinct_scenarios"] = len(scenarios) == len({r["id"] for r in scenarios}) == 74
    checks["all_matrix_files_exist"] = all((ROOT / p).is_file() for r in scenarios for p in r["tests"] + r["evidence"])
    groups = ("core-validated", "regressions-validated", "memory-validated", "personal-validated")
    live_rows = []
    for group in groups:
        folder = "examples/batch-8/runs/" + group
        metadata = read(folder + "/metadata.json")
        checks[group + "_source_matches"] = metadata["runtime_source_fingerprints"] == source
        summary = read(folder + "/summary.json")
        for row in summary["rows"]:
            document = read(folder + "/" + row["file"])
            result = document["result"]
            corpus_path = folder + "/corpora/" + result["corpus_fingerprint"].split(":", 1)[1] + ".json"
            corpus = read(corpus_path)
            passages = {p["passage_id"]: (d, p) for d in corpus["documents"] for p in d["passages"]}
            citations_valid = all(c["passage_id"] in result["read_set"]
                and c["text"] == passages[c["passage_id"]][1]["text"]
                and c["doc_id"] == passages[c["passage_id"]][0]["doc_id"]
                and c["version_date"] == passages[c["passage_id"]][0]["version_date"]
                and c["corpus_fingerprint"] == result["corpus_fingerprint"] for c in result["citations"])
            mechanical = all(v is not False for v in row["mechanical_checks"].values())
            assert result["mode"] == "live" and citations_valid and mechanical
            live_rows.append({"group": group, "case_id": row["case_id"], "repeat": row["repeat"],
                              "turn": row["turn"], "file": folder + "/" + row["file"],
                              "status": result["status"], "canonical_citations_valid": citations_valid})
    checks["final_live_tasks_match_expected_count"] = len(live_rows) == 36
    core = [r for r in live_rows if r["group"] == "core-validated"]
    expected = {"A01", "A02", "A03-missing", "A03-weather", "A04", "A05", "A06-temporary", "A06-persistent"}
    checks["core_cases_each_repeat_twice"] = {r["case_id"] for r in core} == expected and all(
        {r["repeat"] for r in core if r["case_id"] == case} == {1, 2} for case in expected)
    checks["both_followups_have_two_turns"] = all(
        {r["turn"] for r in core if r["case_id"] == "A05" and r["repeat"] == repeat} == {1, 2} for repeat in (1, 2))
    for name in ("offline-initial", "offline-recheck"):
        environment = read("examples/batch-9/" + name + "/environment.json")
        checks[name + "_passed"] = (environment["passed"] and environment["tests_run"] == 120
            and environment["skipped"] == 0 and not environment["system_site_packages"]
            and not environment["real_key_present"] and not environment["model_cache_entries"]
            and not environment["blocked_external_attempts"] and environment["source_fingerprints"] == source)
    live_http = read("examples/batch-9/live-http.json")
    checks["cold_live_http_passed_same_source"] = live_http["passed"] and live_http["source_fingerprints"] == source
    retrieval_reports = list((ROOT / "examples/batch-9/real-retrieval").glob("*.json"))
    checks["cold_real_embedding_passed"] = bool(retrieval_reports) and all(
        read(p.relative_to(ROOT))["passed"] for p in retrieval_reports)
    tests = (ROOT / "examples/batch-10/offline-tests.txt").read_text(encoding="utf-8-sig")
    checks["current_suite_passed_120_without_skips"] = bool(re.search(r"Ran 120 tests .*\n\s*\nOK\s*$", tests))
    tracked = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().rstrip("\0").split("\0")
    paths = sorted(p for p in set(tracked) if (ROOT / p).is_file())
    forbidden = [p for p in paths if p.startswith((".venv/", ".cache/", "models/", "runtime/", ".agents/"))
                 or (Path(p).name.startswith(".env") and Path(p).name != ".env.example")
                 or Path(p).suffix in {".sqlite", ".sqlite3", ".db", ".safetensors", ".bin", ".pem", ".key"}]
    checks["no_private_runtime_or_weight_files"] = not forbidden
    key = dotenv_values(ROOT / ".env", interpolate=False).get("DEEPSEEK_API_KEY") if (ROOT / ".env").is_file() else None
    secret_files = []
    for p in paths:
        content = (ROOT / p).read_text(encoding="utf-8-sig")
        if (key and key in content) or re.search(r"sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", content):
            secret_files.append(p)
    checks["no_detected_secrets"] = not secret_files
    required = ["README.md", "pyproject.toml", "uv.lock", ".env.example", "data/knowledge.json"] + [
        "docs/" + name for name in ("01-requirements.md", "02-solution.md", "03-evaluation.md", "04-ai-usage.md", "05-retrospective.md")]
    checks["required_delivery_files_present"] = all(p in paths for p in required) and all(
        any(p.startswith(folder + "/") for p in paths) for folder in ("src", "tests", "data", "examples"))
    report = {"recorded_at": datetime.now().astimezone().isoformat(), "question_number": 3,
              "acceptance_base_commit": "3fc7e673692ff155e8f64c653160f3a9aa92edfc",
              "repository": read("examples/batch-10/repository.json"), "python": sys.version,
              "platform": platform.platform(), "installed_package": str(package),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "source_fingerprints": source, "checks": checks, "scenario_count": len(scenarios),
              "candidate_file_count": len(paths), "configured_secret_available_for_scan": bool(key),
              "forbidden_files": forbidden, "secret_files": secret_files,
              "final_live_rows": live_rows, "passed": all(checks.values()),
              "limits": ["Mechanical provenance checks do not prove semantics; see independent batch-8 audit.",
                         "Invoice and personal work hours are unverified; historical unknown usage remains unknown.",
                         "Final commit SHA and remote verification are supplied after commit, not embedded in itself."]}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Choose a new filename; preserve earlier evidence")
    report = audit()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "checks": report["checks"]}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
