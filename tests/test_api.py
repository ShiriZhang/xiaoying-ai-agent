from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from agent_support import ROOT, Script, finish, snapshot
from enterprise_knowledge_qa.api import create_app
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.models import MockModel, ModelError


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".cache")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.settings = replace(load_settings(ROOT / ".env.example", environ={}),
                                sqlite_path=self.folder / "sessions.sqlite3")

    def session(self, client):
        response = client.post("/sessions", json={})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["mode"], "mock")
        return response.json()["session_id"]

    def test_create_message_history_and_health_share_real_executor(self):
        with TestClient(create_app(self.settings)) as client:
            self.assertEqual(client.get("/health").json()["mode"], "mock")
            session = self.session(client)
            result = client.post(f"/sessions/{session}/messages", json={"question": "星帆剪辑支持什么导出格式？"})
            self.assertEqual(result.status_code, 200)
            result = result.json()
            self.assertEqual(result["status"], "answered")
            self.assertEqual(result["read_set"], ["D09-P01"])
            self.assertEqual(result["counts"]["model_calls"], 3)
            self.assertEqual(result["counts"]["tool_calls"], 2)
            self.assertEqual(result["citations"][0]["text"], snapshot().passages_by_id["D09-P01"].text)
            history = client.get(f"/sessions/{session}").json()
            self.assertEqual(len(history["messages"]), 2)
            self.assertIsInstance(history["messages"][1]["content"], dict)
            self.assertEqual(history["requests"][0]["result"]["trace"], result["trace"])
            self.assertTrue(history["memory_valid"])

    def test_health_and_session_management_never_create_or_call_live_model(self):
        settings = replace(self.settings, mode="live", api_key="synthetic-test-key",
                           embedding_model_path=self.folder)
        def forbidden_factory():
            self.fail("Model factory must not run for health/create/history")
        retrieval = SimpleNamespace(acquire=lambda: SimpleNamespace(snapshot=snapshot()))
        with TestClient(create_app(settings, retrieval=retrieval, model_factory=forbidden_factory)) as client:
            for _ in range(2):
                response = client.get("/health")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["mode"], "live")
            session = client.post("/sessions").json()["session_id"]
            self.assertEqual(client.get(f"/sessions/{session}").status_code, 200)

    def test_invalid_requests_unknown_sessions_and_fault_parameters_are_rejected(self):
        script = Script(finish())
        with TestClient(create_app(self.settings, model_factory=lambda: MockModel(script))) as client:
            session = self.session(client)
            for body in ({}, {"question": " "}, {"question": 1}, {"question": None},
                         {"question": "q", "mode": "live"}, {"question": "q", "fault": "read"},
                         {"question": "q", "context": []}, ["q"]):
                with self.subTest(body=body):
                    response = client.post(f"/sessions/{session}/messages", json=body)
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.json()["error"]["code"], "invalid_request")
            self.assertEqual(client.post("/sessions", json={"fault": True}).status_code, 422)
            self.assertEqual(client.post(f"/sessions/{session}/messages", content="{").status_code, 422)
            for response in (client.get("/sessions/missing"),
                             client.post("/sessions/missing/messages", json={"question": "q"})):
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "unknown_session")
            self.assertEqual(script.requests, [])
            self.assertEqual(client.get(f"/sessions/{session}").json()["messages"], [])

    def test_model_error_is_business_incomplete_and_storage_error_is_http_503(self):
        script = Script(ModelError("model_failed"))
        with TestClient(create_app(self.settings, model_factory=lambda: MockModel(script))) as client:
            session = self.session(client)
            response = client.post(f"/sessions/{session}/messages", json={"question": "q"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "incomplete")
            self.assertTrue(response.json()["persistence"]["saved"])
        with closing(sqlite3.connect(self.settings.sqlite_path)) as db:
            db.execute("CREATE TRIGGER fail_write BEFORE INSERT ON messages WHEN NEW.role='assistant' "
                       "BEGIN SELECT RAISE(ABORT, 'private database details'); END")
            db.commit()
        with TestClient(create_app(self.settings)) as client:
            response = client.post(f"/sessions/{session}/messages", json={"question": "报销材料是什么？"})
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "storage_failed")
            self.assertFalse(response.json()["result"]["persistence"]["saved"])
            self.assertFalse(response.json()["result"]["memory_valid"])
            self.assertNotIn("private database details", response.text)

    def test_mock_restart_follow_up_isolation_and_no_external_access(self):
        with patch.object(socket, "create_connection", side_effect=AssertionError("outbound network")), \
                patch("enterprise_knowledge_qa.embeddings.BgeEncoder", side_effect=AssertionError("weight access")):
            with TestClient(create_app(self.settings)) as client:
                first, other = self.session(client), self.session(client)
                one = client.post(f"/sessions/{first}/messages", json={"question": "星帆剪辑支持什么导出格式？"}).json()
                self.assertEqual(one["status"], "answered")
            with TestClient(create_app(self.settings)) as client:
                follow = client.post(f"/sessions/{first}/messages", json={"question": "那最高支持多大分辨率？"}).json()
                self.assertEqual(follow["status"], "answered")
                self.assertEqual(follow["read_set"], ["D10-P01"])
                self.assertEqual(follow["memory_update"]["before"], one["anchor_snapshot"])
                isolated = client.post(f"/sessions/{other}/messages", json={"question": "那最高支持多大分辨率？"}).json()
                self.assertEqual(isolated["status"], "needs_clarification")
                self.assertIsNone(isolated["memory_update"]["before"])
                self.assertEqual(isolated["read_set"], [])

    def test_api_has_no_independent_question_length_cap(self):
        question = "完整原始问题" * 4000
        with TestClient(create_app(self.settings)) as client:
            session = self.session(client)
            response = client.post(f"/sessions/{session}/messages", json={"question": question})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["input"]["question"], question)
            self.assertEqual(client.get(f"/sessions/{session}").json()["messages"][0]["content"], question)

    def test_live_startup_failure_is_explicit_without_mock_fallback_or_secret(self):
        environment = dict(os.environ, QA_MODE="live", DEEPSEEK_API_KEY="synthetic-private-test-key",
                           EMBEDDING_MODEL_PATH=str(self.folder / "absent-weights"))
        result = subprocess.run([sys.executable, "-I", "-m", "enterprise_knowledge_qa.server",
                                 "--env-file", str(ROOT / ".env.example")],
                                env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Service preparation failed", result.stderr)
        self.assertNotIn("synthetic-private-test-key", result.stdout + result.stderr)
        self.assertNotIn("mock", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
