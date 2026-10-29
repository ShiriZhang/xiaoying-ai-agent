"""Configuration loading only: no network, weight loading or file creation."""

from dataclasses import dataclass, field
import math
import os
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values


class ConfigurationError(ValueError):
    """Safe to display: messages identify fields, never their values."""


@dataclass(frozen=True)
class Settings:
    mode: str
    api_key: str = field(repr=False)
    base_url: str
    model: str
    embedding_model_id: str
    embedding_model_path: Path
    embedding_revision: str
    data_path: Path
    sqlite_path: Path
    trace_path: Path
    max_model_calls: int
    max_tool_calls: int
    model_timeout_seconds: float
    task_timeout_seconds: float
    history_token_budget: int

    def check_live_prerequisites(self) -> None:
        """Check local prerequisites, not authentication or model compatibility."""
        if self.mode != "live":
            return
        if not self.api_key or self.api_key.lower() in {"placeholder", "your-api-key"}:
            raise ConfigurationError("DEEPSEEK_API_KEY is required for live mode")
        if not self.embedding_model_path.is_dir():
            raise ConfigurationError("EMBEDDING_MODEL_PATH must be a local directory")
        if not self.embedding_revision:
            raise ConfigurationError("EMBEDDING_REVISION is required for live mode")


def load_settings(
    env_file: Path | str | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Explicit file only; process environment wins, no parent .env discovery.

    Relative paths use the env file's directory, or cwd when no file is given.
    Variable interpolation is disabled to avoid implicit external values.
    """
    values: dict[str, str | None] = {}
    root = Path.cwd()
    if env_file is not None:
        path = Path(env_file).resolve()
        if not path.is_file():
            raise ConfigurationError("Configuration file does not exist")
        try:
            values.update(dotenv_values(path, encoding="utf-8-sig", interpolate=False))
        except OSError:
            raise ConfigurationError("Cannot read configuration file") from None
        root = path.parent
    values.update(os.environ if environ is None else environ)

    def value(name: str, default: str = "") -> str:
        raw = values.get(name, default)
        return raw.strip() if raw is not None else ""

    def integer(name: str, default: str) -> int:
        try:
            result = int(value(name, default))
        except ValueError:
            raise ConfigurationError(f"{name} must be a positive integer") from None
        if result <= 0:
            raise ConfigurationError(f"{name} must be a positive integer")
        return result

    def seconds(name: str, default: str) -> float:
        try:
            result = float(value(name, default))
        except ValueError:
            raise ConfigurationError(f"{name} must be positive finite seconds") from None
        if not math.isfinite(result) or result <= 0:
            raise ConfigurationError(f"{name} must be positive finite seconds")
        return result

    def local_path(name: str, default: str) -> Path:
        raw = value(name, default)
        if not raw:
            raise ConfigurationError(f"{name} must not be empty")
        return (root / Path(raw)).resolve()

    mode = value("QA_MODE")
    if mode not in {"live", "mock"}:
        raise ConfigurationError("QA_MODE must explicitly be live or mock")
    model_calls = integer("QA_MAX_MODEL_CALLS", "8")
    tool_calls = integer("QA_MAX_TOOL_CALLS", "6")
    if (model_calls, tool_calls) != (8, 6):
        raise ConfigurationError("QA_MAX_MODEL_CALLS/QA_MAX_TOOL_CALLS must remain 8/6")
    base_url = value("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    if base_url != "https://api.deepseek.com":
        raise ConfigurationError("DEEPSEEK_BASE_URL must use the official endpoint")
    model = value("DEEPSEEK_MODEL", "deepseek-flash")
    if model != "deepseek-flash":
        raise ConfigurationError("DEEPSEEK_MODEL must remain deepseek-flash")
    embedding_id = value("EMBEDDING_MODEL_ID", "BAAI/bge-small-zh-v1.5")
    if embedding_id != "BAAI/bge-small-zh-v1.5":
        raise ConfigurationError("EMBEDDING_MODEL_ID must remain BAAI/bge-small-zh-v1.5")
    return Settings(
        mode=mode,
        api_key=value("DEEPSEEK_API_KEY"),
        base_url=base_url,
        model=model,
        embedding_model_id=embedding_id,
        embedding_model_path=local_path("EMBEDDING_MODEL_PATH", "models/bge-small-zh-v1.5"),
        embedding_revision=value("EMBEDDING_REVISION"),
        data_path=local_path("QA_DATA_PATH", "data/knowledge.json"),
        sqlite_path=local_path("QA_SQLITE_PATH", "runtime/sessions.sqlite3"),
        trace_path=local_path("QA_TRACE_PATH", "runtime/traces"),
        max_model_calls=model_calls,
        max_tool_calls=tool_calls,
        model_timeout_seconds=seconds("QA_MODEL_TIMEOUT_SECONDS", "60"),
        task_timeout_seconds=seconds("QA_TASK_TIMEOUT_SECONDS", "300"),
        history_token_budget=integer("QA_HISTORY_TOKEN_BUDGET", "8000"),
    )
