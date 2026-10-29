"""One-session orchestration without HTTP or additional model/memory calls."""

import json
from uuid import uuid4

from .context import select_history
from .sessions import StorageError


def _failed(result, code):
    result["status"] = "incomplete"
    if "incomplete" not in result["part_statuses"]:
        result["part_statuses"].append("incomplete")
    result["stop_reason"] = code
    result["execution_issues"].append({"code": code})
    result.update(anchor_snapshot=None, memory_valid=False, memory_persisted=False, memory_warning=code)
    if "memory_update" in result:
        result["memory_update"]["after"] = None
    return result


class ConversationService:
    def __init__(self, store, agent_factory):
        self.store, self.agent_factory = store, agent_factory

    def run(self, session_id, question):
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must be a non-empty string")
        agent = self.agent_factory()
        start = agent.clock.monotonic()
        deadline = start + agent.settings.task_timeout_seconds
        remaining = lambda: deadline - agent.clock.monotonic()
        ids, result = None, None
        lock = self.store.lock(session_id)
        acquired = lock.acquire(timeout=max(0, remaining()))
        try:
            if not acquired:
                raise TimeoutError
            state = self.store.get_session(session_id, remaining=remaining)
            ids = self.store.begin_run(session_id, question, remaining=remaining)
            context, selection = select_history(state, agent.settings.history_token_budget)
            before = state["anchor_snapshot"] if state["memory_valid"] else None
            context.insert(0, {"role": "system", "content": "对话锚点（仅理解对象，不是企业事实）：" +
                              json.dumps(before, ensure_ascii=False)})
            source_ids = {m["id"] for m in state["messages"]}
            source_ids.update((ids["user_message_id"], ids["assistant_message_id"]))
            result = agent.run(question, session_id=session_id, context=context,
                               request_id=ids["request_id"], message_ids=ids,
                               memory_source_ids=source_ids, started_at=start)
            result["history_selection"] = selection
            result["message_ids"] = ids
            result["memory_update"] = {"before": before, "after": result["anchor_snapshot"],
                                       "previous_valid": state["memory_valid"],
                                       "previous_warning": state["memory_warning"]}
            result["trace"].append({"kind": "memory_update", "stage": "validated_before_persistence",
                                    **result["memory_update"]})
            result["persistence"] = {"saved": True, "user_message_saved": True, "result_saved": True}
            result["memory_persisted"] = result["memory_valid"]
            # Synchronous short transaction checks the same deadline before commit;
            # no background worker can publish late SQLite writes.
            self.store.finish_run(session_id, ids, result, remaining=remaining)
            result["elapsed_seconds"] = agent.clock.monotonic() - start
            return result
        except (StorageError, TimeoutError) as error:
            if acquired:
                self.store.quarantine(session_id)
            code = "task_timeout" if isinstance(error, TimeoutError) else "storage_failed"
            if result is None:
                result = {"request_id": ids["request_id"] if ids else uuid4().hex,
                          "session_id": session_id, "mode": agent.model.mode,
                          "input": {"question": question, "context": []},
                          "part_statuses": [], "answer": "任务未完成，未能保存本次问答。",
                          "citations": [], "gaps": [], "clarification": None,
                          "execution_issues": [], "evidence": [], "read_set": [], "trace": [],
                          "counts": {"model_calls": 0, "tool_calls": 0, "recoveries": 0, "format_corrections": 0}}
            _failed(result, code)
            result["persistence"] = {"saved": False, "user_message_saved": ids is not None, "result_saved": False}
            result["elapsed_seconds"] = agent.clock.monotonic() - start
            result["trace"].append({"kind": "persistence_error", "code": code})
            return result
        finally:
            if acquired:
                lock.release()
