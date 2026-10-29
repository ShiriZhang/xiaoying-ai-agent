"""One-attempt official DeepSeek transport and explicit offline test adapters."""

from collections.abc import Callable
import copy
from dataclasses import dataclass, field
import json
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .config import ConfigurationError, Settings


class ModelError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str

    def message(self) -> dict:
        return {"id": self.id, "type": "function", "function": {
            "name": self.name, "arguments": self.arguments,
        }}


@dataclass(frozen=True)
class ModelReply:
    calls: tuple[ToolCall, ...]
    actual_model: str | None = None
    usage: dict | None = None
    # Free assistant content and reasoning_content are deliberately not retained.


class Model(Protocol):
    mode: str
    requested_model: str
    secrets: tuple[str, ...]

    def generate(self, messages: list[dict], tools: list[dict], timeout: float) -> ModelReply: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Never forward an authorization header to another service.


def official_transport(url: str, payload: dict, api_key: str, timeout: float) -> dict:
    request = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST", headers={
        "Authorization": "Bearer " + api_key, "Content-Type": "application/json",
    })
    # urllib has no SDK retry loop. One invocation makes one request, redirects disabled.
    with build_opener(_NoRedirect()).open(request, timeout=timeout) as response:
        return json.load(response)


@dataclass
class DeepSeekModel:
    api_key: str = field(repr=False)
    transport: Callable = field(default=official_transport, repr=False)
    mode: str = field(default="live", init=False)
    requested_model: str = field(default="deepseek-flash", init=False)

    def __post_init__(self):
        if not self.api_key.strip():
            raise ConfigurationError("DEEPSEEK_API_KEY is required for live mode")

    @property
    def secrets(self) -> tuple[str, ...]:
        return (self.api_key,)

    def generate(self, messages: list[dict], tools: list[dict], timeout: float) -> ModelReply:
        payload = {
            "model": self.requested_model, "messages": copy.deepcopy(messages),
            "tools": copy.deepcopy(tools), "tool_choice": "auto", "stream": False,
            "thinking": {"type": "disabled"}, "max_tokens": 4096,
        }
        try:
            raw = self.transport("https://api.deepseek.com/chat/completions", payload, self.api_key, timeout)
        except HTTPError as error:
            raise ModelError("authentication_failed" if error.code in {401, 403} else f"http_{error.code}") from None
        except (TimeoutError, socket.timeout):
            raise ModelError("model_timeout") from None
        except (URLError, OSError):
            raise ModelError("model_unavailable") from None
        except (ValueError, TypeError):
            raise ModelError("model_protocol_error") from None
        try:
            if len(raw["choices"]) != 1:
                raise ValueError
            message = raw["choices"][0]["message"]
            calls = tuple(ToolCall(c["id"], c["function"]["name"], c["function"]["arguments"])
                          for c in (message.get("tool_calls") or []))
            actual = raw.get("model")
            if actual is not None and not isinstance(actual, str):
                raise ValueError
            usage = raw.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise ValueError
            return ModelReply(calls, actual, usage)
        except (KeyError, TypeError, ValueError):
            raise ModelError("model_protocol_error") from None


class MockModel:
    """Caller supplies a controlled policy; it receives actual tool observations."""

    mode = "mock"
    requested_model = "mock-policy"
    secrets = ()

    def __init__(self, policy: Callable[[list[dict], list[dict]], ModelReply]):
        self._policy = policy

    def generate(self, messages: list[dict], tools: list[dict], timeout: float) -> ModelReply:
        return self._policy(copy.deepcopy(messages), copy.deepcopy(tools))


def make_model(settings: Settings, *, mock_policy: Callable | None = None) -> Model:
    if settings.mode == "mock":
        if mock_policy is None:
            raise ConfigurationError("Mock mode requires an explicit action policy")
        return MockModel(mock_policy)
    return DeepSeekModel(settings.api_key)
