"""Snapshot-bound read tool and serializable observations, without retries."""

from collections.abc import Callable

from .snapshots import CorpusSnapshot


class ReadArgumentsError(ValueError):
    pass


def validate_read_ids(passage_ids: object) -> tuple[str, ...]:
    """Reusable before execution, so future executor can count correctly."""
    if not isinstance(passage_ids, list) or not 1 <= len(passage_ids) <= 3:
        raise ReadArgumentsError("passage_ids must be an array of 1 to 3 unique IDs")
    if any(not isinstance(part_id, str) or not part_id.strip() for part_id in passage_ids):
        raise ReadArgumentsError("Every passage ID must be a non-empty string")
    if len(set(passage_ids)) != len(passage_ids):
        raise ReadArgumentsError("passage_ids must not contain duplicate IDs")
    return tuple(passage_ids)


class ReadTool:
    """One instance per task. Successful reads alone update that task's read-set.

    fault_hook is internal dependency injection for tests, never a user action
    parameter. Counts, recovery and tool-call association belong to the executor.
    """

    def __init__(
        self,
        snapshot: CorpusSnapshot,
        *,
        fault_hook: Callable[[tuple[str, ...]], None] | None = None,
    ):
        self._snapshot = snapshot
        self._fault_hook = fault_hook
        self._read_set: set[str] = set()

    @property
    def snapshot(self) -> CorpusSnapshot:
        return self._snapshot

    @property
    def read_set(self) -> frozenset[str]:
        return frozenset(self._read_set)

    def _error(self, kind: str, code: str, message: str) -> dict:
        return {
            "tool": "read", "status": "error",
            "corpus_fingerprint": self._snapshot.fingerprint,
            "passages": [],
            "error": {"kind": kind, "code": code, "message": message},
        }

    def read(self, passage_ids: object) -> dict:
        try:
            ids = validate_read_ids(passage_ids)
        except ReadArgumentsError as error:
            return self._error("validation_error", "invalid_arguments", str(error))
        if any(part_id not in self._snapshot.passages_by_id for part_id in ids):
            return self._error("tool_error", "unknown_passage", "A requested passage is not in this snapshot")
        try:
            if self._fault_hook is not None:
                self._fault_hook(ids)
            result = []
            for part_id in ids:
                passage = self._snapshot.passages_by_id[part_id]
                document = self._snapshot.documents_by_id[passage.doc_id]
                result.append({
                    "passage_id": passage.passage_id,
                    "doc_id": document.doc_id,
                    "title": document.title,
                    "topic": document.topic,
                    "version_date": document.version_date,
                    "effective_date": document.effective_date,
                    "scope": document.scope,
                    "text": passage.text,
                })
        except Exception:
            # Do not copy exception details, paths, credentials or invented text
            # into model-visible observations. Interrupts still propagate.
            return self._error("tool_error", "read_failed", "Passage reading failed")
        self._read_set.update(ids)
        return {
            "tool": "read", "status": "success",
            "corpus_fingerprint": self._snapshot.fingerprint,
            "passages": result, "error": None,
        }
