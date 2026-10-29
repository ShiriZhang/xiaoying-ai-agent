"""Explicit single-process, loopback-only HTTP service launcher."""

import argparse

import uvicorn

from .api import create_app
from .config import ConfigurationError, load_settings
from .embeddings import EncodingError
from .knowledge import CorpusError
from .sessions import StorageError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        app = create_app(load_settings(args.env_file))
    except (ConfigurationError, CorpusError, EncodingError, StorageError):
        parser.exit(2, "Service preparation failed: check mode, local data/weights and storage configuration.\n")
    uvicorn.run(app, host="127.0.0.1", port=args.port, workers=1, access_log=False, log_level="warning")


if __name__ == "__main__":
    main()
