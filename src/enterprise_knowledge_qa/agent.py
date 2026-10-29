"""Single native executor; live and controlled Mock share every state transition."""

import copy
import json
from uuid import uuid4

from .actions import ActionError, parse_action, tool_definitions, validate_finish
from .config import Settings
from .deadlines import Clock, bounded_call
from .models import Model, ModelError, ModelReply
from .reading import ReadTool
from .tracing import sanitize, save_trace, usage_record, usage_summary


SYSTEM = """你是公司资料问答助手。每次响应只调用一个 search、read 或 finish。
不要输出内部思维；reason只给一句简要行动依据。公司事实仅依据本轮已读原文，不能复用历史结论。
search摘要不是引用；缺口或冲突可修改查询补查。日期较新不自动优先，适用性依据正文生效和替代说明。
finish引用使用[C1]等标记及本轮资料指纹；无依据不得编造。工具/模型执行失败与资料缺失分开。
业务状态为answered、needs_clarification、insufficient_evidence、out_of_scope、incomplete。
部分已知内容可以交付，最多一个关键追问；未完成、待澄清、依据不足、超出范围、已回答为整体优先顺序。
finish同时提交anchor_snapshot：subject、focus、pending_clarification，每项为空或含value和source_message_ids。
锚点仅帮助理解对象，不是公司事实。工具错误可以结束为incomplete，或在总预算内选择一次恢复。
"""


class Agent:
    def __init__(self, settings: Settings, model: Model, snapshot, *, search=None,
                 reader: ReadTool | None = None, clock: Clock | None = None):
        if model.mode != settings.mode:
            raise ValueError("Model and configured mode must match")
        if (settings.max_model_calls, settings.max_tool_calls) != (8, 6):
            raise ValueError("Execution caps must remain 8/6")
        self.settings, self.model, self.snapshot = settings, model, snapshot
        self.search = search
        self.reader = reader or ReadTool(snapshot)
        if self.reader.snapshot.fingerprint != snapshot.fingerprint:
            raise ValueError("Read tool must use the task snapshot")
        self.clock = clock or Clock()

    def run(self, question: str, *, session_id: str | None = None, context: list[dict] | None = None,
            trace_directory=None) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must be a non-empty string")
        start = self.clock.monotonic()
        deadline = start + self.settings.task_timeout_seconds
        now = self.clock.now()
        date_context = {"as_of_date": now.date().isoformat(), "time_zone": str(now.tzinfo),
                        "corpus_fingerprint": self.snapshot.fingerprint}
        messages = [{"role": "system", "content": SYSTEM + "\n" + json.dumps(date_context)}]
        messages.extend(copy.deepcopy(context or []))
        messages.append({"role": "user", "content": question})
        tools = tool_definitions()
        events, usages, issues = [], [], []
        model_calls = tool_calls = recoveries = corrections = 0
        pending_error = False
        read_ids: set[str] = set()
        business = None
        anchor = None
        stop = "unknown"

        def remaining():
            return deadline - self.clock.monotonic()

        def event(kind, **fields):
            events.append({"kind": kind, "at_seconds": self.clock.monotonic() - start,
                           "model_calls": model_calls, "tool_calls": tool_calls, **fields})

        def feedback(reply: ModelReply, observation: dict):
            # Preserve every genuine call ID, including rejected multi-action calls.
            calls = [c for c in reply.calls if isinstance(c.id, str) and c.id and
                     isinstance(c.name, str) and isinstance(c.arguments, str)]
            if calls:
                messages.append({"role": "assistant", "content": None,
                                 "tool_calls": [call.message() for call in calls]})
                for call in calls:
                    messages.append({"role": "tool", "tool_call_id": call.id,
                                     "content": json.dumps(observation, ensure_ascii=False)})
            else:
                messages.append({"role": "user", "content": json.dumps(observation, ensure_ascii=False)})

        while True:
            if remaining() <= 0:
                stop = "task_timeout"
                break
            if model_calls >= 8:
                stop = "model_limit"
                break
            if tool_calls >= 6:
                stop = "tool_limit"
                break
            timeout = min(self.settings.model_timeout_seconds, remaining())
            model_calls += 1
            event("model_request", requested_model=self.model.requested_model, timeout_seconds=timeout)
            request_start = self.clock.monotonic()
            try:
                # Worker only receives a private history copy, not the mutable run state.
                private_messages = copy.deepcopy(messages)
                reply = bounded_call(lambda: self.model.generate(private_messages, copy.deepcopy(tools), timeout), timeout)
            except Exception as error:
                usages.append(usage_record(None, self.model.mode))
                stop = ("task_timeout" if remaining() <= 0 else
                        "model_timeout" if isinstance(error, TimeoutError) else
                        error.code if isinstance(error, ModelError) else "model_failed")
                event("model_error", code=stop, elapsed_seconds=self.clock.monotonic() - request_start,
                      usage=usages[-1])
                break
            usage = usage_record(reply.usage, self.model.mode)
            usages.append(usage)
            event("model_response", actual_model=reply.actual_model, usage=usage,
                  elapsed_seconds=self.clock.monotonic() - request_start,
                  calls=[{"id": c.id, "name": c.name} for c in reply.calls])
            if remaining() <= 0 or self.clock.monotonic() - request_start >= timeout:
                stop = "task_timeout" if remaining() <= 0 else "model_timeout"
                event("late_model_result_rejected", code=stop)
                break
            try:
                action, args = parse_action(reply)
                event("action", tool_call_id=reply.calls[0].id, action=action,
                      arguments=args, rationale=args["reason"])
                if action == "finish":
                    candidate = validate_finish(args, self.snapshot, read_ids)
                    if pending_error and candidate["status"] != "incomplete":
                        raise ActionError("Unrecovered tool failure requires incomplete status")
                    if remaining() <= 0:
                        stop = "task_timeout"
                        break
                    business, anchor = candidate, args.get("anchor_snapshot")
                    stop = "finished"
                    break
            except ActionError as error:
                event("validation_error", message=str(error), tool_call_ids=[c.id for c in reply.calls])
                if corrections >= 1 or model_calls >= 8:
                    stop = "format_repair_failed" if corrections else "model_limit"
                    break
                corrections += 1
                feedback(reply, {"status": "error", "error": {
                    "kind": "validation_error", "code": "invalid_action", "message": str(error),
                }, "instruction": "Correct the action once; choose exactly one valid tool call."})
                continue
            # An eighth non-finish action cannot initiate any further tool work.
            if model_calls >= 8:
                stop = "model_limit"
                break
            if pending_error:
                if recoveries >= 1:
                    stop = "recovery_exhausted"
                    break
                recoveries += 1
                event("tool_recovery", recovery_number=recoveries)
            tool_calls += 1
            tool_start = self.clock.monotonic()
            try:
                if action == "read":
                    # Trial instance owns any late read-set writes; accepted run owns read_ids.
                    trial = self.reader.fork()
                    function = lambda: trial.read(args["passage_ids"])
                else:
                    if self.search is None:
                        raise RuntimeError("Search adapter not installed")
                    function = lambda: self.search(args["query"], args.get("limit", 6), self.snapshot)
                observation = bounded_call(function, remaining())
                if not isinstance(observation, dict) or observation.get("status") not in {"success", "error"}:
                    raise ValueError("Invalid tool observation")
                if observation.get("corpus_fingerprint") != self.snapshot.fingerprint:
                    raise ValueError("Cross-snapshot tool result")
            except TimeoutError:
                stop = "task_timeout"
                event("tool_timeout", action=action)
                break
            except Exception:
                observation = {"tool": action, "status": "error", "corpus_fingerprint": self.snapshot.fingerprint,
                               "error": {"kind": "tool_error", "code": "tool_failed", "message": "Tool execution failed"}}
            if remaining() <= 0:
                stop = "task_timeout"
                event("late_tool_result_rejected", action=action)
                break
            event("tool_observation", tool_call_id=reply.calls[0].id, action=action,
                  observation=observation, elapsed_seconds=self.clock.monotonic() - tool_start)
            if action == "read" and observation["status"] == "success":
                read_ids.update(args["passage_ids"])
            pending_error = observation["status"] == "error"
            if pending_error:
                issues.append({"code": "tool_error", "tool": action, "tool_call_id": reply.calls[0].id})
                if recoveries >= 1:
                    stop = "recovery_exhausted"
                    break
            feedback(reply, observation)
        if business is None:
            business = {"status": "incomplete", "answer": "任务未完成，保留已获取证据与执行记录。",
                        "gaps": [], "clarification": None, "citations": []}
            issues.append({"code": stop})
        event("stop", reason=stop, recoveries=recoveries, corrections=corrections)
        encoder_metadata = getattr(self.search, "encoder_metadata", None)
        embedding_record = (copy.deepcopy(encoder_metadata) if isinstance(encoder_metadata, dict) else
                            {"model_id": self.settings.embedding_model_id,
                             "revision": self.settings.embedding_revision or None,
                             "status": "not_loaded_by_executor"})
        result = {
            **business, "request_id": uuid4().hex, "session_id": session_id, "mode": self.model.mode,
            **date_context, "requested_model": self.model.requested_model,
            "model_configuration": {"endpoint": "https://api.deepseek.com/chat/completions" if self.model.mode == "live" else None,
                                    "thinking_mode": "disabled", "implicit_retries": 0},
            "embedding": embedding_record,
            "input": {"question": question, "context": context or []},
            "limits": {"model_calls": 8, "tool_calls": 6,
                       "model_timeout_seconds": self.settings.model_timeout_seconds,
                       "task_timeout_seconds": self.settings.task_timeout_seconds},
            "counts": {"model_calls": model_calls, "tool_calls": tool_calls,
                       "recoveries": recoveries, "format_corrections": corrections},
            "stop_reason": stop, "execution_issues": issues, "trace": events,
            "elapsed_seconds": self.clock.monotonic() - start,
            "usage": usage_summary(usages), "read_set": sorted(read_ids),
            "evidence": [{"passage_id": p, "doc_id": self.snapshot.passages_by_id[p].doc_id,
                          "text": self.snapshot.passages_by_id[p].text} for p in sorted(read_ids)],
            "anchor_snapshot_proposal": anchor, "memory_valid": False,
            "memory_warning": "memory_validation_and_persistence_pending_batch_6",
        }
        result = sanitize(result, self.model.secrets)
        if trace_directory is not None:
            if remaining() <= 0:
                result["execution_issues"].append({"code": "trace_not_saved_after_deadline"})
            else:
                try:
                    private_result = copy.deepcopy(result)
                    bounded_call(lambda: save_trace(trace_directory, private_result, self.model.secrets,
                                                     can_commit=lambda: remaining() > 0), remaining())
                except TimeoutError:
                    result["status"] = "incomplete"
                    result["stop_reason"] = "task_timeout"
                    result["execution_issues"].append({"code": "trace_not_saved_after_deadline"})
                    result["trace"].append({"kind": "stop", "reason": "task_timeout", "stage": "trace_save",
                                             "model_calls": model_calls, "tool_calls": tool_calls,
                                             "at_seconds": self.clock.monotonic() - start})
                except (OSError, ValueError):
                    result["execution_issues"].append({"code": "trace_save_failed"})
            result["elapsed_seconds"] = self.clock.monotonic() - start
        return result
