import io
import json
import socket
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from enterprise_knowledge_qa.config import ConfigurationError, load_settings
from enterprise_knowledge_qa.models import DeepSeekModel, MockModel, ModelError, ModelReply, make_model


class ModelTests(unittest.TestCase):
    def test_official_payload_identifiers_timeout_and_no_reasoning_retained(self):
        transport = Mock(return_value={"model": "actual-version", "usage": {"prompt_tokens": 10},
            "choices": [{"message": {"reasoning_content": "private reasoning", "content": "not a tool",
                "tool_calls": [{"id": "real-id", "function": {"name": "read", "arguments": "{}"}}]}}]})
        model = DeepSeekModel("synthetic-key", transport)
        reply = model.generate([{"role": "user", "content": "question"}], [], 12.5)
        url, payload, key, timeout = transport.call_args.args
        self.assertEqual(url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertEqual(timeout, 12.5)
        self.assertEqual(reply.actual_model, "actual-version")
        self.assertEqual(reply.calls[0].id, "real-id")
        self.assertNotIn("private reasoning", repr(reply))
        self.assertNotIn("synthetic-key", repr(model))

    def test_model_failures_one_attempt_no_fallback_no_private_error(self):
        for error, expected in [
            (HTTPError("x", 401, "secret-detail", {}, io.BytesIO()), "authentication_failed"),
            (HTTPError("x", 503, "secret-detail", {}, io.BytesIO()), "http_503"),
            (URLError("secret-detail"), "model_unavailable"),
            (TimeoutError("secret-detail"), "model_timeout"),
        ]:
            with self.subTest(expected=expected):
                transport = Mock(side_effect=error)
                model = DeepSeekModel("synthetic-key", transport)
                with self.assertRaises(ModelError) as caught:
                    model.generate([], [], 60)
                self.assertEqual(caught.exception.code, expected)
                self.assertEqual(transport.call_count, 1)
                self.assertNotIn("secret", str(caught.exception))

    def test_mock_is_explicit_and_offline(self):
        with patch.object(socket, "socket", side_effect=AssertionError("network")):
            model = make_model(load_settings(environ={"QA_MODE": "mock"}),
                               mock_policy=lambda messages, tools: ModelReply(()))
            self.assertEqual(model.generate([], [], 60).calls, ())
        with self.assertRaises(ConfigurationError):
            make_model(load_settings(environ={"QA_MODE": "mock"}))
        with self.assertRaises(ConfigurationError):
            DeepSeekModel("")

    def test_malformed_response_and_unknown_usage(self):
        for raw in ({}, {"choices": []}, {"choices": [{"message": {}}, {"message": {}}]}):
            with self.subTest(raw=raw), self.assertRaises(ModelError):
                DeepSeekModel("synthetic", Mock(return_value=raw)).generate([], [], 60)
        reply = DeepSeekModel("synthetic", Mock(return_value={"choices": [{"message": {}}]})).generate([], [], 60)
        self.assertIsNone(reply.usage)
        self.assertIsNone(reply.actual_model)
