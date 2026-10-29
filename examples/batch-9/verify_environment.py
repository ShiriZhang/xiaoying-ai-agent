"""Record installed-package provenance and run tests with external sockets denied.

Run inside a clean checkout using its isolated Python, with no real key.
The HTTP example separately starts guarded child servers and tests restart.
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
import sys
import unittest
from unittest.mock import patch


def fingerprints(folder):
    return {p.name: hashlib.sha256(p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()).hexdigest()
            for p in sorted(folder.glob("*.py"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Choose a new output directory; preserve previous evidence")
    output.mkdir(parents=True)
    import enterprise_knowledge_qa
    package = Path(enterprise_knowledge_qa.__file__).parent
    root = Path.cwd()
    cache = root / ".cache/empty-model-cache"
    cache.mkdir(parents=True, exist_ok=False)
    os.environ.update(QA_MODE="mock", DEEPSEEK_API_KEY="", HF_HOME=str(cache),
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    assert sys.prefix != sys.base_prefix
    assert "include-system-site-packages = false" in (Path(sys.prefix) / "pyvenv.cfg").read_text()
    assert fingerprints(package) == fingerprints(root / "src/enterprise_knowledge_qa")
    assert not (root / ".env").exists() and not (root / "models").exists()
    denied = []
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_resolve = socket.getaddrinfo

    def check(host):
        if host not in {"127.0.0.1", "::1", "localhost", None}:
            denied.append(str(host))
            raise AssertionError("External network forbidden")

    def connect(sock, address):
        check(address[0])
        return original_connect(sock, address)

    def connect_ex(sock, address):
        check(address[0])
        return original_connect_ex(sock, address)

    def resolve(host, *a, **kw):
        check(host)
        return original_resolve(host, *a, **kw)

    with (output / "tests.txt").open("x", encoding="utf-8") as stream:
        with patch.object(socket.socket, "connect", connect), patch.object(socket.socket, "connect_ex", connect_ex), \
                patch.object(socket, "getaddrinfo", resolve):
            suite = unittest.defaultTestLoader.discover("tests")
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {"recorded_at": datetime.now().astimezone().isoformat(),
              "python": sys.version, "platform": platform.platform(), "executable": sys.executable,
              "prefix": sys.prefix, "base_prefix": sys.base_prefix, "installed_package": str(package),
              "system_site_packages": False, "real_key_present": bool(os.environ["DEEPSEEK_API_KEY"]),
              "model_cache_entries": list(cache.iterdir()), "external_network_guard": True,
              "blocked_external_attempts": denied, "source_fingerprints": fingerprints(package),
              "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "passed": result.wasSuccessful() and not denied}
    (output / "environment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("tests_run", "failures", "errors", "skipped", "passed")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
