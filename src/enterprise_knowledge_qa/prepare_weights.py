"""The only network-enabled step for preparing pinned local model weights."""

import argparse
import hashlib
import json
from pathlib import Path

from .embeddings import MODEL_FILES, MODEL_ID, REVISION, verify_weights


def prepare(path: Path | str) -> dict:
    from huggingface_hub import snapshot_download
    folder = Path(path).resolve()
    snapshot_download(repo_id=MODEL_ID, revision=REVISION, local_dir=folder,
                      cache_dir=folder.parent / ".download-cache", allow_patterns=list(MODEL_FILES), token=False)
    manifest = {"model_id": MODEL_ID, "revision": REVISION,
                "sha256": {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in MODEL_FILES}}
    (folder / "weights-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return verify_weights(folder, REVISION)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = prepare(args.output)
    print(json.dumps({"model_id": manifest["model_id"], "revision": manifest["revision"],
                      "verified_files": len(manifest["sha256"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
