"""Immutable BM25 + cosine indices, deterministic RRF, explicit atomic reloads."""

from collections import Counter
import copy
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from threading import Lock
from types import MappingProxyType
from typing import Mapping
import unicodedata

from .embeddings import EncodingError, make_encoder, unit_vector
from .snapshots import CorpusSnapshot, load_snapshot


BM25_K1, BM25_B, RRF_K = 1.5, 0.75, 60
BRANCH_LIMIT = 12
SUMMARY_CHARACTERS = 160


def tokenize(text: str) -> tuple[str, ...]:
    """NFKC/casefold, Latin words/numbers, Han unigrams and adjacent bigrams."""
    tokens = []
    for run in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", unicodedata.normalize("NFKC", text).casefold()):
        if "\u3400" <= run[0] <= "\u9fff":
            tokens.extend(run)
            tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
        else:
            tokens.append(run)
    return tuple(tokens)


def _error(snapshot, code: str, message: str, *, kind="tool_error") -> dict:
    return {"tool": "search", "status": "error", "corpus_fingerprint": snapshot.fingerprint,
            "candidates": [], "error": {"kind": kind, "code": code, "message": message}}


def _rows(vectors, count: int, dimension: int | None = None) -> tuple[tuple[float, ...], ...]:
    if len(vectors) != count:
        raise EncodingError("Embedding count does not match input count")
    result = tuple(unit_vector(vector) for vector in vectors)
    sizes = {len(row) for row in result}
    if len(sizes) > 1 or (dimension is not None and sizes and sizes != {dimension}):
        raise EncodingError("Embedding dimensions do not match the index")
    return result


@dataclass(frozen=True)
class HybridIndex:
    snapshot: CorpusSnapshot
    passage_ids: tuple[str, ...]
    term_counts: tuple[Mapping[str, int], ...]
    lengths: tuple[int, ...]
    document_frequency: Mapping[str, int]
    vectors: tuple[tuple[float, ...], ...]
    encoder: object
    _encoder_metadata_json: str

    @property
    def encoder_metadata(self) -> dict:
        return json.loads(self._encoder_metadata_json)

    @classmethod
    def build(cls, snapshot: CorpusSnapshot, encoder):
        part_ids = tuple(sorted(snapshot.passages_by_id))
        texts = []
        for part_id in part_ids:
            part = snapshot.passages_by_id[part_id]
            doc = snapshot.documents_by_id[part.doc_id]
            # Keep long provenance headers out of ranking, never change canonical text.
            texts.append(doc.title + "\n" + part.text.split("\n", 1)[-1])
        counts = tuple(Counter(tokenize(text)) for text in texts)
        frequency = Counter(term for row in counts for term in row)
        vectors = _rows(encoder.encode(texts, query=False), len(texts)) if texts else ()
        return cls(snapshot, part_ids, tuple(MappingProxyType(dict(row)) for row in counts),
                   tuple(sum(row.values()) for row in counts), MappingProxyType(dict(frequency)),
                   vectors, encoder, json.dumps(encoder.metadata, sort_keys=True))

    @property
    def configuration(self) -> dict:
        return {"bm25": {"k1": BM25_K1, "b": BM25_B, "idf": "log1p((N-df+0.5)/(df+0.5))"},
                "tokenizer": "NFKC/casefold + Han unigram/bigram + Latin/number runs v1",
                "input": "title + newline + passage body; canonical provenance preserved separately",
                "branch_limit": BRANCH_LIMIT, "rrf_k": RRF_K, "summary_characters": SUMMARY_CHARACTERS,
                "tie_break": "passage_id ascending", "embedding": copy.deepcopy(self.encoder_metadata)}

    def _bm25(self, query: str) -> list[tuple[int, float]]:
        n = len(self.passage_ids)
        average = sum(self.lengths) / n if n else 0
        scored = []
        for index, row in enumerate(self.term_counts):
            score = 0.0
            for term in sorted(set(tokenize(query))):
                tf = row.get(term, 0)
                if not tf:
                    continue
                df = self.document_frequency[term]
                idf = math.log1p((n - df + 0.5) / (df + 0.5))
                score += idf * tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * self.lengths[index] / average))
            if score > 0:
                scored.append((index, score))
        return sorted(scored, key=lambda item: (-item[1], self.passage_ids[item[0]]))[:BRANCH_LIMIT]

    def search(self, query: str, limit: int = 6) -> dict:
        if not isinstance(query, str) or not query.strip() or type(limit) is not int or limit not in {6, 12}:
            return _error(self.snapshot, "invalid_arguments", "query is required and limit must be 6 or 12", kind="validation_error")
        try:
            query_vector = _rows(self.encoder.encode([query], query=True), 1,
                                 len(self.vectors[0]) if self.vectors else None)[0]
            keyword = self._bm25(query)
            semantic = sorted(
                ((i, sum(a * b for a, b in zip(query_vector, vector))) for i, vector in enumerate(self.vectors)),
                key=lambda item: (-item[1], self.passage_ids[item[0]]),
            )[:BRANCH_LIMIT]
        except Exception:
            return _error(self.snapshot, "retrieval_failed", "Hybrid retrieval failed; no single-route or Mock fallback")
        ranks: dict[int, dict] = {}
        for branch, items in (("bm25", keyword), ("semantic", semantic)):
            for rank, (index, score) in enumerate(items, 1):
                ranks.setdefault(index, {})[branch] = {"rank": rank, "score": score}
        rrf_scores = {index: sum(1 / (RRF_K + row["rank"]) for row in branches.values())
                      for index, branches in ranks.items()}
        fused = sorted(ranks, key=lambda i: (-rrf_scores[i], self.passage_ids[i]))
        candidates = []
        for rank, index in enumerate(fused[:limit], 1):
            passage = self.snapshot.passages_by_id[self.passage_ids[index]]
            doc = self.snapshot.documents_by_id[passage.doc_id]
            candidates.append({"passage_id": passage.passage_id, "doc_id": doc.doc_id, "title": doc.title,
                               "topic": doc.topic, "version_date": doc.version_date, "effective_date": doc.effective_date,
                               "summary": passage.text.split("\n", 1)[-1][:SUMMARY_CHARACTERS], "rank": rank,
                               "rrf_score": rrf_scores[index],
                               "branches": ranks[index]})
        return {"tool": "search", "status": "success", "corpus_fingerprint": self.snapshot.fingerprint,
                "candidates": candidates, "branch_rankings": {
                    "bm25": [{"passage_id": self.passage_ids[i], "score": score} for i, score in keyword],
                    "semantic": [{"passage_id": self.passage_ids[i], "score": score} for i, score in semantic]},
                "configuration": self.configuration, "error": None}

    def __call__(self, query: str, limit: int, snapshot: CorpusSnapshot) -> dict:
        if snapshot.fingerprint != self.snapshot.fingerprint:
            return _error(snapshot, "snapshot_mismatch", "Search index does not match the task snapshot")
        return self.search(query, limit)


class RetrievalStore:
    """Publish one complete snapshot/index pair. Acquire once for the whole task."""

    def __init__(self, path: Path | str, encoder):
        self._path, self._encoder = Path(path).resolve(), encoder
        self._reload_lock = Lock()
        self._current = HybridIndex.build(load_snapshot(self._path), encoder)

    def acquire(self) -> HybridIndex:
        return self._current

    def reload(self) -> HybridIndex:
        with self._reload_lock:
            candidate = HybridIndex.build(load_snapshot(self._path), self._encoder)
            self._current = candidate
        return candidate


def make_retrieval(settings) -> RetrievalStore:
    return RetrievalStore(settings.data_path, make_encoder(settings))


def create_agent(settings, model, index: HybridIndex, *, clock=None):
    from .agent import Agent
    if settings.mode != index.encoder_metadata["mode"]:
        raise ValueError("Generation and embedding modes must match explicitly")
    return Agent(settings, model, index.snapshot, search=index, clock=clock)
