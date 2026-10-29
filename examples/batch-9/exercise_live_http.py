"""Paid minimal live HTTP check with explicitly prepared local weights.

The credential is read only from the specified local env file; it is passed
to the child process in memory and is never copied into the clean checkout.
"""

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.snapshots import load_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Choose a new output filename")
    root = Path.cwd()
    weights = Path(args.weights).resolve()
    assert (weights / "weights-manifest.json").is_file()
    settings = load_settings(args.env_file, environ={})
    assert settings.api_key, "A real key must be explicitly configured"
    import enterprise_knowledge_qa
    package = Path(enterprise_knowledge_qa.__file__).parent
    report = {"recorded_at": datetime.now().astimezone().isoformat(), "mode": "live",
              "python": sys.version, "platform": platform.platform(), "weights": str(weights),
              "weights_manifest": json.loads((weights / "weights-manifest.json").read_text()),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "source_fingerprints": {p.name: hashlib.sha256(p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()
                                      for p in sorted(package.glob("*.py"))},
              "passed": False, "records": [], "invoice_cny": None}
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))

    def request(method, path, body=None, expected=200):
        data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        req = Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        with opener.open(req, timeout=310) as response:
            payload, status = json.load(response), response.status
        report["records"].append({"method": method, "path": path, "body": body, "http_status": status, "response": payload})
        assert status == expected
        return payload

    with tempfile.TemporaryDirectory(dir=root / ".cache") as folder:
        environment = {k: v for k, v in os.environ.items() if not k.startswith(("QA_", "DEEPSEEK_", "EMBEDDING_", "HF_", "TRANSFORMERS_"))}
        environment.update(QA_MODE="live", DEEPSEEK_API_KEY=settings.api_key,
                           EMBEDDING_MODEL_PATH=str(weights), HF_HOME=str(root / ".cache/live-runtime-cache"),
                           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                           QA_SQLITE_PATH=str(Path(folder) / "sessions.sqlite3"))
        process = subprocess.Popen([sys.executable, "-I", "-m", "enterprise_knowledge_qa.server",
                                    "--env-file", str(root / ".env.example"), "--port", str(port)],
                                   env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            deadline = time.monotonic() + 90
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Live server exited before readiness")
                try:
                    with opener.open(base + "/health", timeout=0.5):
                        break
                except URLError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Live server startup timed out")
                    time.sleep(0.1)
            assert request("GET", "/health")["mode"] == "live"
            session = request("POST", "/sessions", {}, 201)["session_id"]
            result = request("POST", f"/sessions/{session}/messages", {"question": "星帆剪辑支持什么导出格式？"})
            history = request("GET", f"/sessions/{session}")
            snapshot = load_snapshot(root / "data/knowledge.json")
            checks = {"answered": result["status"] == "answered", "live": result["mode"] == "live",
                      "persisted": len(history["messages"]) == 2 and result["persistence"]["saved"],
                      "cites_export_rule": "D09-P01" in {c["passage_id"] for c in result["citations"]},
                      "canonical_citations": bool(result["citations"]) and all(
                          c["text"] == snapshot.passages_by_id[c["passage_id"]].text
                          and c["passage_id"] in result["read_set"]
                          and c["corpus_fingerprint"] == snapshot.fingerprint for c in result["citations"])}
            report.update(checks=checks, passed=all(checks.values()))
        except Exception as error:
            report["error_type"] = type(error).__name__
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "requests": len(report["records"]), "error_type": report.get("error_type")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
