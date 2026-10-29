"""Validated synthetic documents. No ranking or business-rule adjudication."""

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import re


class CorpusError(ValueError):
    """Invalid or unavailable corpus; no unvalidated documents are returned."""


@dataclass(frozen=True)
class Passage:
    passage_id: str
    doc_id: str
    text: str


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    topic: str
    version_date: str
    effective_date: str
    scope: str
    passages: tuple[Passage, ...]


def _fields(value: object, fields: set[str], location: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise CorpusError(f"{location}: fields do not match schema")
    return value


def _text(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CorpusError(f"{location}: non-empty string required")
    return value  # Canonical original text is never stripped or normalized.


def _date(value: object, location: str) -> str:
    text = _text(value, location)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError:
        raise CorpusError(f"{location}: YYYY-MM-DD date required") from None
    return text


def parse_documents(value: object) -> tuple[Document, ...]:
    """Validate general corpus shape, including small isolated test variants.

    The base corpus's 12-document/three-topic coverage is checked separately in
    tests. Header matching verifies metadata transcription, not prose semantics.
    """
    root = _fields(value, {"schema_version", "synthetic", "documents"}, "corpus")
    if type(root["schema_version"]) is not int or root["schema_version"] != 1:
        raise CorpusError("corpus: unsupported schema_version")
    if root["synthetic"] is not True:
        raise CorpusError("corpus: synthetic must be true")
    raw_documents = root["documents"]
    if not isinstance(raw_documents, list) or not raw_documents:
        raise CorpusError("corpus: non-empty documents list required")
    documents = []
    doc_ids: set[str] = set()
    passage_ids: set[str] = set()
    scopes: set[str] = set()
    for index, raw in enumerate(raw_documents):
        location = f"documents[{index}]"
        doc = _fields(raw, {
            "doc_id", "title", "topic", "version_date", "effective_date", "scope", "passages",
        }, location)
        doc_id = _text(doc["doc_id"], location + ".doc_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", doc_id) or doc_id in doc_ids:
            raise CorpusError(f"{location}: invalid or duplicate doc_id")
        doc_ids.add(doc_id)
        title = _text(doc["title"], location + ".title")
        topic = _text(doc["topic"], location + ".topic")
        scope = _text(doc["scope"], location + ".scope")
        scopes.add(scope)
        version = _date(doc["version_date"], location + ".version_date")
        effective = _date(doc["effective_date"], location + ".effective_date")
        raw_passages = doc["passages"]
        if not isinstance(raw_passages, list) or not raw_passages:
            raise CorpusError(f"{location}: non-empty passages list required")
        passages = []
        for part_index, raw_passage in enumerate(raw_passages):
            part_location = f"{location}.passages[{part_index}]"
            part = _fields(raw_passage, {"passage_id", "doc_id", "text"}, part_location)
            part_id = _text(part["passage_id"], part_location + ".passage_id")
            if not re.fullmatch(re.escape(doc_id) + r"-P[0-9]+", part_id):
                raise CorpusError(f"{part_location}: passage_id must belong to document")
            if part_id in passage_ids:
                raise CorpusError(f"{part_location}: duplicate passage_id")
            passage_ids.add(part_id)
            if part["doc_id"] != doc_id:
                raise CorpusError(f"{part_location}: doc_id reference mismatch")
            original = _text(part["text"], part_location + ".text")
            header = (
                f"文档：{title}（{doc_id}）。主题：{topic}。版本日期：{version}。"
                f"生效日期：{effective}。适用范围：{scope}。\n"
            )
            if not original.startswith(header) or not original[len(header):].strip():
                raise CorpusError(f"{part_location}: metadata/body mismatch or missing body")
            passages.append(Passage(part_id, doc_id, original))
        documents.append(Document(doc_id, title, topic, version, effective, scope, tuple(passages)))
    if len(scopes) != 1:
        raise CorpusError("corpus: documents must share one applicability scope")
    return tuple(documents)


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise CorpusError("corpus: duplicate JSON key")
        result[key] = value
    return result


def load_documents(path: Path | str) -> tuple[Document, ...]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise CorpusError("Cannot read a valid UTF-8 JSON corpus") from None
    return parse_documents(value)
