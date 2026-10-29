"""Explicit local CPU BGE encoding and deterministic offline test vectors."""

from collections import Counter
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
from threading import Lock
import unicodedata


MODEL_ID = "BAAI/bge-small-zh-v1.5"
REVISION = "7999e1d3359715c523056ef9478215996d62a620"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
MODEL_FILES = ("config.json", "model.safetensors", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt")


class EncodingError(ValueError):
    pass


def unit_vector(values) -> tuple[float, ...]:
    vector = tuple(float(x) for x in values)
    if not vector or not all(math.isfinite(x) for x in vector):
        raise EncodingError("Embedding must contain finite numeric values")
    norm = math.sqrt(sum(x * x for x in vector))
    if not math.isfinite(norm) or norm == 0:
        raise EncodingError("Embedding must have non-zero norm")
    return tuple(x / norm for x in vector)


def validate_texts(texts) -> None:
    if not isinstance(texts, (list, tuple)) or any(not isinstance(t, str) or not t.strip() for t in texts):
        raise EncodingError("Encoding requires non-empty strings")


def verify_weights(path: Path | str, revision: str) -> dict:
    folder = Path(path)
    try:
        manifest = json.loads((folder / "weights-manifest.json").read_text(encoding="utf-8"))
        if manifest["model_id"] != MODEL_ID or manifest["revision"] != revision or revision != REVISION:
            raise EncodingError("Local embedding revision does not match the pinned revision")
        if set(manifest["sha256"]) != set(MODEL_FILES):
            raise EncodingError("Local embedding file manifest is incomplete")
        for name in MODEL_FILES:
            if hashlib.sha256((folder / name).read_bytes()).hexdigest() != manifest["sha256"][name]:
                raise EncodingError("Local embedding file fingerprint mismatch")
    except (OSError, ValueError, KeyError, TypeError):
        raise EncodingError("Local embedding weights/manifest are missing or invalid; run explicit preparation") from None
    return manifest


class MockEncoder:
    """Stable hashed character vectors; no claim of semantic model quality."""

    mode = "mock"
    metadata = {"mode": "mock", "model_id": "mock-hash-characters", "revision": "1", "dimension": 64}

    def encode(self, texts, *, query=False) -> tuple[tuple[float, ...], ...]:
        validate_texts(texts)
        results = []
        for text in texts:
            counts = Counter(unicodedata.normalize("NFKC", text).casefold())
            vector = [0.0] * 64
            for char, count in counts.items():
                digest = hashlib.sha256(char.encode("utf-8")).digest()
                vector[int.from_bytes(digest[:2], "big") % 64] += count
            results.append(unit_vector(vector))
        return tuple(results)


class BgeEncoder:
    mode = "live"

    def __init__(self, path: Path | str, revision: str):
        manifest = verify_weights(path, revision)  # Missing weights fail before imports/downloads.
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError:
            raise EncodingError("Install the locked embedding extra before loading local weights") from None
        try:
            torch.set_num_threads(1)
            self._tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False)
            self._model = AutoModel.from_pretrained(str(path), local_files_only=True, trust_remote_code=False,
                                                     use_safetensors=True).to("cpu").eval()
        except Exception:
            raise EncodingError("Local BGE model/tokenizer could not be loaded") from None
        self._torch = torch
        self._lock = Lock()
        self._max_tokens = min(512, self._model.config.max_position_embeddings, self._tokenizer.model_max_length)
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        self.metadata = {"mode": "live", "model_id": MODEL_ID, "revision": revision,
                         "weights_fingerprint": "sha256:" + digest, "device": "cpu", "threads": 1,
                         "pooling": "CLS", "normalized": True, "query_prefix": QUERY_PREFIX,
                         "max_input_tokens": self._max_tokens, "dimension": self._model.config.hidden_size,
                         "packages": {name: importlib.metadata.version(name) for name in
                                      ("torch", "transformers", "tokenizers", "safetensors", "huggingface-hub")}}

    def encode(self, texts, *, query=False) -> tuple[tuple[float, ...], ...]:
        validate_texts(texts)
        if not texts:
            return ()
        inputs = [QUERY_PREFIX + t if query else t for t in texts]
        with self._lock:
            encoded = self._tokenizer(inputs, truncation=False, padding=False, add_special_tokens=True)
            if any(len(ids) > self._max_tokens for ids in encoded["input_ids"]):
                raise EncodingError("Embedding input exceeds local tokenizer capacity; input was not truncated")
            tensors = self._tokenizer.pad(encoded, padding=True, return_tensors="pt")
            with self._torch.inference_mode():
                output = self._model(**tensors).last_hidden_state[:, 0]
                return tuple(unit_vector(row) for row in output.tolist())


def make_encoder(settings):
    if settings.mode == "mock":
        return MockEncoder()
    return BgeEncoder(settings.embedding_model_path, settings.embedding_revision)
