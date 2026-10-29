"""Explicit corpus reloads and immutable per-task source snapshots."""

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .knowledge import Document, Passage, load_documents


@dataclass(frozen=True)
class CorpusSnapshot:
    documents: tuple[Document, ...]
    fingerprint: str = field(init=False)
    documents_by_id: Mapping[str, Document] = field(init=False, repr=False)
    passages_by_id: Mapping[str, Passage] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        canonical = json.dumps(
            {"schema_version": 1, "synthetic": True,
             "documents": [asdict(document) for document in self.documents]},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        object.__setattr__(self, "fingerprint", "sha256:" + hashlib.sha256(canonical).hexdigest())
        object.__setattr__(self, "documents_by_id", MappingProxyType({
            document.doc_id: document for document in self.documents
        }))
        object.__setattr__(self, "passages_by_id", MappingProxyType({
            passage.passage_id: passage
            for document in self.documents for passage in document.passages
        }))


def load_snapshot(path: Path | str) -> CorpusSnapshot:
    return CorpusSnapshot(load_documents(path))


class CorpusStore:
    """Acquire once at task start; tools keep that snapshot until task end.

    File changes do nothing until reload. Failed reload retains the prior valid
    snapshot and raises CorpusError. Search index rebuilding is task 4.4.
    """

    def __init__(self, path: Path | str):
        self._path = Path(path).resolve()
        self._current = load_snapshot(self._path)

    def acquire(self) -> CorpusSnapshot:
        return self._current

    def reload(self) -> CorpusSnapshot:
        candidate = load_snapshot(self._path)
        self._current = candidate
        return candidate
