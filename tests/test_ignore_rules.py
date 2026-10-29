"""Exercise Git's actual ignore matching without initializing this project."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class IgnoreTests(unittest.TestCase):
    def test_secrets_weights_and_runtime_ignored_but_templates_and_evidence_kept(self):
        ignored = [
            "openspec/config.yaml", "openspec/changes/example/tasks.md",
            "openspec/specs/example/spec.md", ".agents/skills/example/SKILL.md",
            ".env", ".env.local", ".env.production", "models/weights.json",
            "weights/model.safetensors", "weights/model.bin", "runtime/traces/run.json",
            "local/sessions.sqlite3", "local/sessions.sqlite3-wal", "local/sessions.db",
            "local/sessions.db-shm", ".venv/pyvenv.cfg", ".cache/uv/cache",
        ]
        kept = [".env.example", "data/knowledge.json", "examples/run/trace.json", "README.md"]
        (ROOT / ".cache").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            subprocess.run(["git", "init", "--quiet", directory], check=True, capture_output=True)
            result = subprocess.run([
                "git", "--git-dir", str(Path(directory) / ".git"),
                "--work-tree", str(ROOT), "check-ignore", "--no-index", "--stdin", "-z",
            ], input=("\0".join(ignored + kept) + "\0").encode(), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(result.stdout.decode().rstrip("\0").split("\0")), set(ignored))
