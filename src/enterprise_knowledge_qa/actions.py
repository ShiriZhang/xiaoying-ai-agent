"""Tool contracts and mechanical action/result validation for the executor."""

import json
import re

from .models import ModelReply
from .reading import validate_read_ids


STATUSES = ["answered", "needs_clarification", "insufficient_evidence", "out_of_scope", "incomplete"]
STATUS_PRIORITY = ["incomplete", "needs_clarification", "insufficient_evidence", "out_of_scope", "answered"]


def _object(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required, "additionalProperties": False}


STRING = {"type": "string"}
STRINGS = {"type": "array", "items": STRING}
REASON = {"type": "string", "description": "一句简要行动依据（最多240字符）；不要输出内部思维过程。"}
REF = _object({"marker": STRING, "passage_id": STRING, "corpus_fingerprint": STRING})
ANCHOR_ITEM = {"anyOf": [{"type": "null"}, _object({"value": STRING,
    "source_message_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": STRING}})]}
ANCHOR = _object({field: ANCHOR_ITEM for field in ("subject", "focus", "pending_clarification")})


def tool_definitions() -> list[dict]:
    definitions = [
        ("search", "检索公司资料候选；默认6可扩大12。缺口/冲突时改写查询补查，读取新候选；摘要与排名不能直接引用或裁决规则。", _object({
            "query": STRING, "limit": {"type": "integer", "enum": [6, 12]}, "reason": REASON,
        }, ["query", "reason"])),
        ("read", "一次读取1至3个唯一片段ID的完整原文；冲突读取双方。只有本轮成功读取的片段可引用。", _object({"passage_ids": STRINGS, "reason": REASON})),
        ("finish", "结束本轮，提交业务结果和完整锚点；引用只选本轮已读原文。", _object({
            "status": {"type": "string", "enum": STATUSES}, "answer": STRING,
            "part_statuses": {"type": "array", "minItems": 1,
                              "items": {"type": "string", "enum": STATUSES},
                              "description": "按answer分项顺序列出状态；整体status必须取最高优先级。"},
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
        allowed = {"reason", "status", "part_statuses", "answer", "citation_refs", "gaps", "clarification", "anchor_snapshot"}
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
    """Validate provenance and structure, never infer semantic support or policy."""
    if not isinstance(args.get("status"), str) or args["status"] not in STATUSES:
        raise ActionError("Invalid business status")
    parts = args.get("part_statuses")
    if (not isinstance(parts, list) or not parts or
            any(not isinstance(part, str) or part not in STATUSES for part in parts)):
        raise ActionError("part_statuses must be a non-empty array of business statuses")
    if args["status"] != min(parts, key=STATUS_PRIORITY.index):
        raise ActionError("Overall status must follow incomplete > needs_clarification > insufficient_evidence > out_of_scope > answered")
    if not isinstance(args.get("answer"), str) or not args["answer"].strip():
        raise ActionError("answer must be a non-empty string")
    if not isinstance(args.get("gaps"), list) or any(not isinstance(x, str) or not x.strip() for x in args["gaps"]):
        raise ActionError("gaps must be an array of non-empty strings")
    if "clarification" not in args or (args["clarification"] is not None and
            (not isinstance(args["clarification"], str) or not args["clarification"].strip())):
        raise ActionError("clarification must be null or one non-empty question")
    clarification = args["clarification"]
    if clarification is not None and len(re.findall(r"[?？]", clarification)) > 1:
        raise ActionError("clarification must contain at most one question")
    if "needs_clarification" in parts and (clarification is None or not args["gaps"]):
        raise ActionError("A clarification result needs a gap and one key question")
    if "insufficient_evidence" in parts and not args["gaps"]:
        raise ActionError("Insufficient evidence requires an explicit material gap")
    if set(parts) == {"out_of_scope"} and clarification is not None:
        raise ActionError("A purely out-of-scope request needs no clarification")
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
                          "title": doc.title, "effective_date": doc.effective_date,
                          "text": passage.text})
    # Also reject malformed C-prefixed markers, rather than silently ignoring
    # [C0], [C01], [Cfoo], [C-1] or an unclosed marker.
    answer_markers = re.findall(r"\[C[^\]\s]*(?:\]|(?=\s|$))", args["answer"])
    if set(answer_markers) != markers:
        raise ActionError("Answer citation markers must match citation_refs")
    if "answered" in parts and not refs:
        raise ActionError("An answered company question requires read evidence")
    return {key: args[key] for key in ("status", "part_statuses", "answer", "gaps", "clarification")} | {"citations": citations}
