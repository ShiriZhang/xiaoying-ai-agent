"""Run the installed Mock HTTP service twice and capture real loopback requests.

The child uses the production server entrypoint with test-only guards against
external sockets and BGE construction. No such switches exist in public API.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


ROOT = Path(__file__).resolve().parents[2]


def child(env_file, port):
    from enterprise_knowledge_qa import server
    original_connect, original_connect_ex, original_resolve = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo
    def check(host):
        if host not in {"127.0.0.1", "::1", "localhost", None}:
            raise AssertionError("External network access is forbidden in Mock HTTP verification")
    def connect(sock, address):
        check(address[0])
        return original_connect(sock, address)
    def connect_ex(sock, address):
        check(address[0])
        return original_connect_ex(sock, address)
    def resolve(host, *args, **kwargs):
        check(host)
        return original_resolve(host, *args, **kwargs)
    sys.argv = ["server", "--env-file", env_file, "--port", str(port)]
    with patch.object(socket.socket, "connect", connect), patch.object(socket.socket, "connect_ex", connect_ex), \
            patch.object(socket, "getaddrinfo", resolve), \
            patch("enterprise_knowledge_qa.embeddings.BgeEncoder", side_effect=AssertionError("BGE access forbidden")):
        server.main()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--env-file")
    parser.add_argument("--port", type=int)
    parser.add_argument("--output", default=str(Path(__file__).with_name("http-demo.json")))
    parser.add_argument("--powershell-output", help="Also execute the README PowerShell requests and save their response")
    args = parser.parse_args()
    if args.child:
        child(args.env_file, args.port)
        return
    if Path(args.output).exists() or (args.powershell_output and Path(args.powershell_output).exists()):
        parser.error("Choose new output filenames; previous evidence is preserved")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    opener = build_opener(ProxyHandler({}))
    records = []
    def request(method, path, body=None, expected=200):
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            response = opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            status, payload = response.status, json.load(response)
        assert status == expected, (method, path, status, payload)
        records.append({"method": method, "path": path, "body": body, "http_status": status, "response": payload})
        return payload
    with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
        folder = Path(folder)
        env_file = folder / "mock.env"
        env_file.write_text("QA_MODE=mock\n", encoding="utf-8")
        environment = {k: v for k, v in os.environ.items()
                       if not k.startswith(("QA_", "DEEPSEEK_", "EMBEDDING_"))}
        environment.update(QA_MODE="mock", DEEPSEEK_API_KEY="", QA_DATA_PATH=str(ROOT / "data/knowledge.json"),
            QA_SQLITE_PATH=str(folder / "sessions.sqlite3"), QA_TRACE_PATH=str(folder / "traces"),
            EMBEDDING_MODEL_PATH=str(folder / "absent-weights"), HF_HOME=str(folder / "empty-cache"))
        def start():
            process = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), "--child",
                "--env-file", str(env_file), "--port", str(port)], env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError("HTTP child exited before startup")
                    try:
                        with opener.open(base + "/health", timeout=0.2):
                            return process
                    except URLError:
                        time.sleep(0.05)
                raise TimeoutError("HTTP startup timed out")
            except BaseException:
                stop(process)
                raise
        def stop(process):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        process = start()
        try:
            if args.powershell_output:
                subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(Path(__file__).with_name("readme_requests.ps1")), "-BaseUrl", base,
                    "-Output", str(Path(args.powershell_output).resolve())], check=True,
                    timeout=30, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            assert request("GET", "/health")["mode"] == "mock"
            first = request("POST", "/sessions", {}, expected=201)["session_id"]
            other = request("POST", "/sessions", {}, expected=201)["session_id"]
            one = request("POST", f"/sessions/{first}/messages", {"question": "星帆剪辑支持什么导出格式？"})
            two = request("POST", f"/sessions/{first}/messages", {"question": "那最高支持多大分辨率？"})
            assert one["read_set"] == ["D09-P01"] and two["read_set"] == ["D10-P01"]
            isolated = request("POST", f"/sessions/{other}/messages", {"question": "那最高支持多大分辨率？"})
            assert isolated["status"] == "needs_clarification" and not isolated["read_set"]
            assert len(request("GET", f"/sessions/{first}")["messages"]) == 4
            request("POST", f"/sessions/{first}/messages", {"question": ""}, expected=422)
            request("POST", f"/sessions/{first}/messages", {"question": "q", "fault": True}, expected=422)
            request("GET", "/sessions/not-found", expected=404)
        finally:
            stop(process)
        process = start()
        try:
            assert len(request("GET", f"/sessions/{first}")["messages"]) == 4
            after = request("POST", f"/sessions/{first}/messages", {"question": "那最高支持多大分辨率？"})
            assert after["read_set"] == ["D10-P01"] and after["memory_update"]["before"] is not None
            assert len(request("GET", f"/sessions/{first}")["messages"]) == 6
        finally:
            stop(process)
        assert not (folder / "absent-weights").exists()
        report = {"recorded_at": datetime.now().astimezone().isoformat(), "mode": "mock",
                  "external_socket_guard": True, "bge_constructor_guard": True, "server_restarted": True,
                  "scope": "actual loopback HTTP and SQLite; controlled policy, not live semantic acceptance",
                  "records": records}
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"requests": len(records), "server_restarted": True, "mode": "mock", "output": args.output}))


if __name__ == "__main__":
    main()
