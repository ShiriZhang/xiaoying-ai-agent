"""Engineering configuration check, not a business CLI or service launcher."""

import argparse
import json

from .config import ConfigurationError, load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    try:
        settings = load_settings(args.env_file)
        settings.check_live_prerequisites()
    except ConfigurationError as error:
        parser.exit(2, f"Configuration error: {error}\n")
    # Deliberate allow-list: never serialize Settings or environment variables.
    print(json.dumps({
        "mode": settings.mode,
        "configuration": "valid",
        "service": "not_started",
        "model_calls_limit": settings.max_model_calls,
        "tool_calls_limit": settings.max_tool_calls,
        "model_timeout_seconds": settings.model_timeout_seconds,
        "task_timeout_seconds": settings.task_timeout_seconds,
        "history_estimated_tokens": settings.history_token_budget,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
