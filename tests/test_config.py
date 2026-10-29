import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from enterprise_knowledge_qa.config import ConfigurationError, load_settings


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".cache").mkdir(exist_ok=True)

    def test_example_mock_without_key_weights_network_or_side_effects(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            env_file = Path(directory) / ".env.example"
            env_file.write_bytes((ROOT / ".env.example").read_bytes())
            with patch.object(socket, "socket", side_effect=AssertionError("network")):
                settings = load_settings(env_file, environ={})
                settings.check_live_prerequisites()
            self.assertEqual(settings.mode, "mock")
            self.assertEqual(settings.api_key, "")
            self.assertEqual((settings.max_model_calls, settings.max_tool_calls), (8, 6))
            self.assertEqual((settings.model_timeout_seconds, settings.task_timeout_seconds), (60, 300))
            self.assertEqual(settings.history_token_budget, 8000)
            self.assertEqual(settings.sqlite_path, Path(directory) / "runtime/sessions.sqlite3")
            self.assertFalse((Path(directory) / "runtime").exists())
            self.assertFalse(settings.embedding_model_path.exists())

    def test_explicit_mode_and_invalid_values(self):
        for values in ({}, {"QA_MODE": "auto"}, {"QA_MODE": ""}):
            with self.subTest(values=values), self.assertRaises(ConfigurationError):
                load_settings(environ=values)
        for field, invalid in (
            ("QA_MAX_MODEL_CALLS", "9"), ("QA_MAX_TOOL_CALLS", "7"),
            ("QA_MODEL_TIMEOUT_SECONDS", "nan"), ("QA_TASK_TIMEOUT_SECONDS", "inf"),
            ("QA_HISTORY_TOKEN_BUDGET", "0"), ("QA_HISTORY_TOKEN_BUDGET", "bad"),
            ("QA_DATA_PATH", ""), ("DEEPSEEK_BASE_URL", "https://other.invalid"),
        ):
            with self.subTest(field=field), self.assertRaises(ConfigurationError):
                load_settings(environ={"QA_MODE": "mock", field: invalid})

    def test_env_precedence_quotes_relative_paths_and_no_interpolation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            env = Path(directory) / "test.env"
            env.write_text('QA_MODE=live\nQA_TRACE_PATH="local traces"\nDEEPSEEK_API_KEY=${EXTERNAL}\n', encoding="utf-8")
            settings = load_settings(env, environ={"QA_MODE": "mock", "QA_HISTORY_TOKEN_BUDGET": "2000"})
            self.assertEqual(settings.mode, "mock")
            self.assertEqual(settings.trace_path, Path(directory) / "local traces")
            self.assertEqual(settings.api_key, "${EXTERNAL}")
            self.assertEqual(settings.history_token_budget, 2000)

    def test_live_prerequisites_do_not_fallback_or_expose_key(self):
        with self.assertRaisesRegex(ConfigurationError, "DEEPSEEK_API_KEY"):
            load_settings(environ={"QA_MODE": "live"}).check_live_prerequisites()
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            settings = load_settings(environ={
                "QA_MODE": "live", "DEEPSEEK_API_KEY": "synthetic-test-value",
                "EMBEDDING_MODEL_PATH": directory, "EMBEDDING_REVISION": "test-only",
            })
            self.assertNotIn("synthetic-test-value", repr(settings))
            settings.check_live_prerequisites()  # Only directory/revision check, no model load.
            settings = load_settings(environ={
                "QA_MODE": "live", "DEEPSEEK_API_KEY": "synthetic-test-value",
                "EMBEDDING_MODEL_PATH": str(Path(directory) / "absent-weights"),
            })
            with self.assertRaisesRegex(ConfigurationError, "EMBEDDING_MODEL_PATH"):
                settings.check_live_prerequisites()

    def test_check_entrypoint_redacts_key_and_does_not_start_service(self):
        env = dict(os.environ, QA_MODE="mock", DEEPSEEK_API_KEY="synthetic-test-value")
        result = subprocess.run([
            sys.executable, "-I", "-m", "enterprise_knowledge_qa",
            "--env-file", str(ROOT / ".env.example"),
        ], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"service": "not_started"', result.stdout)
        self.assertNotIn("synthetic-test-value", result.stdout + result.stderr)

    def test_missing_file_fails(self):
        with self.assertRaises(ConfigurationError):
            load_settings(ROOT / "absent.env", environ={})
