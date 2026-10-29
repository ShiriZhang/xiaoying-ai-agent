"""SQLite repository. Connections and write transactions never span model work."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from threading import Lock, RLock
from uuid import uuid4


class SessionNotFound(LookupError):
    pass


class StorageError(RuntimeError):
    """Safe public storage error, without paths or underlying exception values."""


class SessionStore:
    _locks_guard = Lock()
    _locks = {}
    _unsafe_sessions = set()

    def __init__(self, path):
        self.path = Path(path).resolve()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connection() as db:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY, anchor_json TEXT, anchor_valid INTEGER NOT NULL DEFAULT 0,
                        memory_warning TEXT);
                    CREATE TABLE IF NOT EXISTS runs (
                        id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id),
                        user_id TEXT NOT NULL, assistant_id TEXT NOT NULL,
                        state TEXT NOT NULL, result_json TEXT);
                    CREATE TABLE IF NOT EXISTS messages (
                        sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                        session_id TEXT NOT NULL REFERENCES sessions(id),
                        run_id TEXT NOT NULL REFERENCES runs(id), role TEXT NOT NULL, content TEXT NOT NULL);
                """)
        except OSError:
            raise StorageError("storage_initialization_failed") from None

    def lock(self, session_id):
        """Shared by store instances in this process; no multi-process promise."""
        with self._locks_guard:
            return self._locks.setdefault((str(self.path), session_id), RLock())

    def quarantine(self, session_id):
        """Remember uncertainty even when SQLite cannot persist invalidation."""
        with self._locks_guard:
            self._unsafe_sessions.add((str(self.path), session_id))

    @contextmanager
    def _connection(self, remaining=None):
        db = None
        try:
            if remaining is not None and remaining() <= 0:
                raise TimeoutError
            timeout = min(5.0, remaining()) if remaining is not None else 5.0
            db = sqlite3.connect(self.path, timeout=max(0.001, timeout))
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys = ON")
            yield db
            if remaining is not None and remaining() <= 0:
                raise TimeoutError
            db.commit()
        except TimeoutError:
            raise
        except (sqlite3.Error, OSError, ValueError):
            raise StorageError("storage_failed") from None
        finally:
            if db is not None:
                db.close()  # Uncommitted transactions roll back, also on deadline.

    def create_session(self):
        ident = uuid4().hex
        with self._connection() as db:
            db.execute("INSERT INTO sessions(id) VALUES (?)", (ident,))
        return ident

    def get_session(self, session_id, *, remaining=None):
        with self._connection(remaining) as db:
            db.execute("BEGIN")
            row = db.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
            if row is None:
                raise SessionNotFound("unknown_session")
            messages = [dict(r) for r in db.execute(
                "SELECT * FROM messages WHERE session_id=? ORDER BY sequence", (session_id,))]
            runs = [dict(r) for r in db.execute("SELECT * FROM runs WHERE session_id=? ORDER BY rowid", (session_id,))]
        running = any(r["state"] == "running" for r in runs)
        with self._locks_guard:
            unsafe = (str(self.path), session_id) in self._unsafe_sessions
        return {"session_id": session_id, "messages": messages, "runs": runs,
                "anchor_snapshot": json.loads(row["anchor_json"]) if row["anchor_json"] else None,
                "memory_valid": bool(row["anchor_valid"]) and not running and not unsafe,
                "memory_warning": "unfinished_request" if running else "storage_uncertain" if unsafe else row["memory_warning"]}

    def begin_run(self, session_id, question, *, remaining=None):
        request_id, user_id, assistant_id = (uuid4().hex for _ in range(3))
        self.quarantine(session_id)
        # Commit invalidation first: failure while registering the user message
        # must not roll back to a previously valid, potentially stale anchor.
        with self._connection(remaining) as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT id FROM sessions WHERE id=?", (session_id,)).fetchone() is None:
                raise SessionNotFound("unknown_session")
            db.execute("UPDATE sessions SET anchor_valid=0, memory_warning='request_in_progress' WHERE id=?", (session_id,))
        with self._connection(remaining) as db:
            db.execute("BEGIN IMMEDIATE")
            # A previous interrupted process cannot leave usable old anchors.
            db.execute("UPDATE runs SET state='abandoned' WHERE session_id=? AND state='running'", (session_id,))
            db.execute("INSERT INTO runs VALUES (?, ?, ?, ?, 'running', NULL)",
                       (request_id, session_id, user_id, assistant_id))
            db.execute("INSERT INTO messages(id,session_id,run_id,role,content) VALUES (?,?,?,'user',?)",
                       (user_id, session_id, request_id, question))
        return {"request_id": request_id, "user_message_id": user_id, "assistant_message_id": assistant_id}

    def finish_run(self, session_id, ids, result, *, remaining=None):
        """Publish assistant, full run result and replacement/invalid memory atomically."""
        business = {key: result[key] for key in (
            "status", "part_statuses", "answer", "citations", "gaps", "clarification",
            "execution_issues", "memory_warning")}
        with self._connection(remaining) as db:
            db.execute("BEGIN IMMEDIATE")
            run = db.execute("SELECT * FROM runs WHERE id=? AND session_id=? AND state='running'",
                             (ids["request_id"], session_id)).fetchone()
            if run is None or run["assistant_id"] != ids["assistant_message_id"]:
                raise StorageError("request_not_pending")
            db.execute("INSERT INTO messages(id,session_id,run_id,role,content) VALUES (?,?,?,'assistant',?)",
                       (ids["assistant_message_id"], session_id, ids["request_id"],
                        json.dumps(business, ensure_ascii=False, allow_nan=False)))
            db.execute("UPDATE runs SET state='completed', result_json=? WHERE id=?",
                       (json.dumps(result, ensure_ascii=False, allow_nan=False), ids["request_id"]))
            db.execute("UPDATE sessions SET anchor_json=?, anchor_valid=?, memory_warning=? WHERE id=?",
                       (json.dumps(result["anchor_snapshot"], ensure_ascii=False) if result["memory_valid"] else None,
                        int(result["memory_valid"]), result["memory_warning"], session_id))
        with self._locks_guard:
            self._unsafe_sessions.discard((str(self.path), session_id))
