from collections import deque
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

from enterprise_knowledge_qa.agent import Agent
from enterprise_knowledge_qa.config import load_settings
from enterprise_knowledge_qa.models import MockModel, ModelReply, ToolCall
from enterprise_knowledge_qa.snapshots import load_snapshot


ROOT = Path(__file__).resolve().parents[1]


def snapshot():
    return load_snapshot(ROOT / "data/knowledge.json")


def call(name, args=None, ident="call-real-fixture"):
    args = {"reason": "Controlled test action", **(args or {})}
    return ModelReply((ToolCall(ident, name, json.dumps(args, ensure_ascii=False)),), "controlled-model")


def finish(*, with_ref=False, status=None, **changes):
    args = {"status": status or ("answered" if with_ref else "incomplete"),
            "answer": "材料见原文[C1]。" if with_ref else "受控测试结束。", "gaps": [], "clarification": None,
            "citation_refs": [{"marker": "[C1]", "passage_id": "D03-P01", "corpus_fingerprint": snapshot().fingerprint}] if with_ref else [],
            "anchor_snapshot": {"subject": None, "focus": None, "pending_clarification": None}}
    args.update(changes)
    return call("finish", args)


class Script:
    def __init__(self, *responses):
        self.responses = deque(responses)
        self.requests = []

    def __call__(self, messages, tools):
        self.requests.append(messages)
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


def search_result(snap, *, error=False, candidates=None):
    return {"tool": "search", "status": "error" if error else "success", "corpus_fingerprint": snap.fingerprint,
            "candidates": candidates or [], "error": {"kind": "tool_error", "code": "injected_error"} if error else None}


def make_agent(policy, *, search=None, clock=None, reader=None, **setting_changes):
    settings = replace(load_settings(ROOT / ".env.example", environ={}), **setting_changes)
    return Agent(settings, MockModel(policy), snapshot(), search=search, clock=clock, reader=reader)


class FakeClock:
    def __init__(self):
        self.value = 0.0
        self.wall = datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc)

    def monotonic(self):
        return self.value

    def now(self):
        return self.wall

    def advance(self, seconds):
        self.value += seconds
