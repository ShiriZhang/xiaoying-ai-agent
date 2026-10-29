"""Sanitized run traces, conservative usage estimates, explicit unknowns."""

import json
from pathlib import Path
import re
from uuid import uuid4


SENSITIVE_KEYS = {"api_key", "authorization", "reasoning_content", "chain_of_thought", "thinking"}


def sanitize(value, secrets=()):
    if isinstance(value, dict):
        return {key: sanitize(item, secrets) for key, item in value.items() if key.lower() not in SENSITIVE_KEYS}
    if isinstance(value, (tuple, list)):
        return [sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"(?i)Bearer\s+[^\s\"']+", "Bearer [REDACTED]", value)
    return value


def usage_record(raw: dict | None, mode: str) -> dict:
    def number(key):
        value = raw.get(key) if raw else None
        return value if type(value) is int and value >= 0 else None
    prompt, completion = number("prompt_tokens"), number("completion_tokens")
    hit, miss = number("prompt_cache_hit_tokens"), number("prompt_cache_miss_tokens")
    complete = prompt is not None and completion is not None
    # Peak, fully uncached upper-rate estimate. No inference of holidays/cache hits.
    cost = (prompt * 2 + completion * 8) / 1_000_000 if complete and mode == "live" else None
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "prompt_cache_hit_tokens": hit, "prompt_cache_miss_tokens": miss,
            "usage_known": complete, "estimated_cny_upper_rate": cost,
            "estimate_basis": "2026-10-29 official Flash peak uncached input 2/output 8 CNY per million; not invoice"}


def usage_summary(records: list[dict]) -> dict:
    known = [r for r in records if r["estimated_cny_upper_rate"] is not None]
    return {"requests_with_unknown_usage": sum(not r["usage_known"] for r in records),
            "known_requests_estimated_cny": sum(r["estimated_cny_upper_rate"] for r in known) if known else None,
            "total_estimated_cny": sum(r["estimated_cny_upper_rate"] for r in known) if len(known) == len(records) and records else None,
            "invoice_cny": None}


def save_trace(directory: Path | str, result: dict, secrets=(), *, can_commit=None) -> Path:
    """Write a safe caller-owned copy; errors propagate for explicit reporting."""
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    # Use only generated/request IDs that cannot escape the trace folder.
    request_id = result["request_id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", request_id):
        raise ValueError("Invalid request_id for trace path")
    target = folder / (request_id + ".json")
    temporary = folder / (request_id + "-" + uuid4().hex + ".partial")
    try:
        with temporary.open("x", encoding="utf-8") as output:
            json.dump(sanitize(result, secrets), output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
        if can_commit is not None and not can_commit():
            raise TimeoutError("Trace deadline exceeded")
        if target.exists():
            raise FileExistsError("Trace already exists")
        # Supported Windows platform: rename fails if the target already exists.
        # Do not depend on hardlink privileges or cross-volume cache behavior.
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
