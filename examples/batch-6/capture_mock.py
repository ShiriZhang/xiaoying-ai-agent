"""Capture actual offline session runs using controlled test policies.

Run from the repository root with the installed project package:
.venv/Scripts/python.exe -I examples/batch-6/capture_mock.py
"""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))  # Only fixtures; production imports use the installed package.
from agent_support import Script, finish, make_agent, snapshot
from test_memory import anchor, current_ids, product_policy
from enterprise_knowledge_qa.conversations import ConversationService
from enterprise_knowledge_qa.embeddings import MockEncoder
from enterprise_knowledge_qa.models import ModelError
from enterprise_knowledge_qa.retrieval import HybridIndex
from enterprise_knowledge_qa.sessions import SessionStore


def main():
    output = Path(__file__).resolve().parent
    index = HybridIndex.build(snapshot(), MockEncoder())
    with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as folder:
        path = Path(folder) / "sessions.sqlite3"
        store = SessionStore(path)
        session = store.create_session()
        def run(policy, question, *, budget=8000):
            return ConversationService(store, lambda: make_agent(policy, search=index,
                history_token_budget=budget)).run(session, question)
        records = {}
        records["first-round"] = run(product_policy(), "星帆剪辑支持什么导出格式？")
        store = SessionStore(path)  # Real close/reopen, not an in-memory history substitute.
        records["restarted-follow-up"] = run(product_policy(passage="D10-P01", text="最高1080p[C1]",
            expect_subject="星帆剪辑"), "那最高支持多大分辨率？", budget=1)
        def bad_anchor(messages, tools):
            return finish(status="out_of_scope", answer="天气超出公司资料服务范围。",
                anchor_snapshot=anchor("天气", "not-a-session-message"))
        records["invalid-anchor"] = run(bad_anchor, "今天天气怎样？")
        records["model-failure"] = run(Script(ModelError("model_failed")), "改问报销")
        def rebuilt(messages, tools):
            return finish(anchor_snapshot=anchor("人事", current_ids(messages)["user_message_id"]))
        records["rebuilt-anchor"] = run(rebuilt, "再改问人事")
        with closing(sqlite3.connect(path)) as db:
            db.execute("CREATE TRIGGER fail_assistant BEFORE INSERT ON messages WHEN NEW.role='assistant' "
                "BEGIN SELECT RAISE(ABORT, 'controlled write failure'); END")
            db.commit()
        records["storage-failure"] = run(Script(finish()), "保存失败演示")
        state = SessionStore(path).get_session(session)
        summary = {"memory_valid": state["memory_valid"], "memory_warning": state["memory_warning"],
                   "messages": state["messages"],
                   "runs": [{k: r[k] for k in ("id", "state", "user_id", "assistant_id")} for r in state["runs"]]}
        (output / "persisted-state.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for name, result in records.items():
            (output / (name + ".json")).write_text(json.dumps({
                "evidence_kind": "actual SQLite/executor run with controlled Mock policy; not live semantic acceptance",
                "result": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({name: {"status": r["status"], "memory_valid": r["memory_valid"],
            "saved": r["persistence"]["saved"]} for name, r in records.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
