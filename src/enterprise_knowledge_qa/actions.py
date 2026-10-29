"""Tool contracts and mechanical action/result validation for the executor."""

import json
import re

from .models import ModelReply
from .reading import validate_read_ids


STATUSES = ["answered", "needs_clarification", "insufficient_evidence", "out_of_scope", "incomplete"]


def _object(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
REASON = {"type": "string", "description": "一句简要行动依据（最多240字符）；不要输出内部思维过程。"}
REF = _object({"marker": STRING, "passage_id": STRING, "corpus_fingerprint": STRING})
ANCHOR = {"type": "object", "description": "当前对象、关注事项、待澄清事项完整快照；各项为空或附来源消息标识。"}


def tool_definitions() -> list[dict]:
    definitions = [
        ("search", "检索公司资料候选；不能将候选摘要直接引用。", _object({
            "query": STRING, "limit": {"type": "integer", "enum": [6, 12]}, "reason": REASON,
        }, ["query", "reason"])),
        ("read", "一次读取1至3个唯一片段ID的完整原文。", _object({"passage_ids": STRINGS, "reason": REASON})),
        ("finish", "结束本轮，提交业务结果和完整锚点；引用只选本轮已读原文。", _object({
            "status": {"type": "string", "enum": STATUSES}, "answer": STRING,
            "citation_refs": {"type": "array", "items": REF}, "gaps": STRINGS,
            "clarification": {"type": ["string", "null"]}, "anchor_snapshot": ANCHOR, "reason": REASON,
        })),
    ]
    return [{"type": "function", "function": {"name": name, "description": description, "parameters": schema}}
            for name, description, schema in definitions]


class ActionError(ValueError):
    """Safe validation feedback: contains field names, never supplied values."""


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ActionError("Duplicate JSON argument key")
        result[key] = value
    return result


def parse_action(reply: ModelReply) -> tuple[str, dict]:
    if len(reply.calls) != 1:
        raise ActionError("Exactly one search/read/finish tool call is required")
    call = reply.calls[0]
    if not isinstance(call.id, str) or not call.id or not isinstance(call.arguments, str):
        raise ActionError("A valid tool-call ID and JSON argument string are required")
    if not isinstance(call.name, str) or call.name not in {"search", "read", "finish"}:
        raise ActionError("Unknown action; choose search/read/finish")
    try:
        args = json.loads(call.arguments, object_pairs_hook=_unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(ActionError("Non-finite JSON number")))
    except (ValueError, TypeError):
        raise ActionError("Arguments must be one valid JSON object without duplicate keys") from None
    if not isinstance(args, dict):
        raise ActionError("Arguments must be a JSON object")
    reason = args.get("reason")
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 240:
        raise ActionError("reason must be a brief non-empty statement of at most 240 characters")
    allowed = {"reason", "query", "limit"} if call.name == "search" else {"reason", "passage_ids"}
    if call.name == "finish":
        allowed = {"reason", "status", "answer", "citation_refs", "gaps", "clarification", "anchor_snapshot"}
    if set(args) - allowed:
        raise ActionError("Unknown argument fields")
    if call.name == "read":
        try:
            validate_read_ids(args.get("passage_ids"))
        except ValueError as error:
            raise ActionError(str(error)) from None
    if call.name == "search":
        if not isinstance(args.get("query"), str) or not args["query"].strip():
            raise ActionError("query must be a non-empty string")
        if type(args.get("limit", 6)) is not int or args.get("limit", 6) not in {6, 12}:
            raise ActionError("limit must be 6 or 12")
    return call.name, args


def validate_finish(args: dict, snapshot, read_set: set[str]) -> dict:
    """Initial mechanical finish guard needed for format-repair tests in 3.5.

    Semantic support, mixed-result rendering and memory validation remain later
    tasks. No business rule values are embedded in this guard.
    """
    if args.get("status") not in STATUSES:
        raise ActionError("Invalid business status")
    if not isinstance(args.get("answer"), str) or not args["answer"].strip():
        raise ActionError("answer must be a non-empty string")
    if not isinstance(args.get("gaps"), list) or any(not isinstance(x, str) for x in args["gaps"]):
        raise ActionError("gaps must be an array of strings")
    if "clarification" not in args or (args["clarification"] is not None and
            (not isinstance(args["clarification"], str) or not args["clarification"].strip())):
        raise ActionError("clarification must be null or one non-empty question")
    refs = args.get("citation_refs")
    if not isinstance(refs, list):
        raise ActionError("citation_refs must be an array")
    markers = set()
    citations = []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"marker", "passage_id", "corpus_fingerprint"}:
            raise ActionError("Each reference needs marker, passage_id and corpus_fingerprint")
        marker, part_id = ref["marker"], ref["passage_id"]
        if not isinstance(marker, str) or not re.fullmatch(r"\[C[1-9][0-9]*\]", marker) or marker in markers:
            raise ActionError("Citation marker is invalid or duplicated")
        if not isinstance(part_id, str) or part_id not in read_set or part_id not in snapshot.passages_by_id:
            raise ActionError("Citation passage must have been successfully read in this task")
        if ref["corpus_fingerprint"] != snapshot.fingerprint:
            raise ActionError("Citation must belong to this corpus snapshot")
        markers.add(marker)
        passage = snapshot.passages_by_id[part_id]
        doc = snapshot.documents_by_id[passage.doc_id]
        citations.append({**ref, "doc_id": doc.doc_id, "version_date": doc.version_date,
                          "title": doc.title, "text": passage.text})
    if set(re.findall(r"\[C[0-9]+\]", args["answer"])) != markers:
        raise ActionError("Answer citation markers must match citation_refs")
    if args["status"] == "answered" and not refs:
        raise ActionError("An answered company question requires read evidence")
    return {key: args[key] for key in ("status", "answer", "gaps", "clarification")} | {"citations": citations}
