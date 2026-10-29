"""Four local REST routes using the existing conversation service and executor."""

import json

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from .conversations import ConversationService
from .demo_policy import demo_policy
from .models import make_model
from .retrieval import create_agent, make_retrieval
from .sessions import SessionNotFound, SessionStore, StorageError


class EmptyBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MessageBody(EmptyBody):
    question: str

    @field_validator("question")
    @classmethod
    def nonempty_question(cls, value):
        if not value.strip():
            raise ValueError("Question must be non-empty")
        return value  # Preserve the complete original question, no character cap.


def _error(status, code, message, *, result=None):
    body = {"error": {"code": code, "message": message}}
    if result is not None:
        body["result"] = result
    return JSONResponse(status_code=status, content=body)


def create_app(settings, *, store=None, retrieval=None, model_factory=None):
    settings.check_live_prerequisites()
    store = store if store is not None else SessionStore(settings.sqlite_path)
    retrieval = retrieval if retrieval is not None else make_retrieval(settings)
    if model_factory is None:
        model_factory = lambda: make_model(settings, mock_policy=demo_policy if settings.mode == "mock" else None)
    service = ConversationService(store, lambda: create_agent(settings, model_factory(), retrieval.acquire()))
    app = FastAPI(title="企业知识问答", docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        return _error(422, "invalid_request", "请求格式不合法；仅提交当前问题。")

    @app.exception_handler(SessionNotFound)
    async def missing_session(request, error):
        return _error(404, "unknown_session", "会话不存在。")

    @app.exception_handler(StorageError)
    async def storage_error(request, error):
        return _error(503, "storage_failed", "会话存储不可用，未确认保存成功。")

    @app.get("/health")
    def health():
        return {"status": "ok", "mode": settings.mode,
                "corpus_fingerprint": retrieval.acquire().snapshot.fingerprint}

    @app.post("/sessions", status_code=201)
    def create_session(body: EmptyBody | None = None):
        return {"session_id": store.create_session(), "mode": settings.mode}

    @app.post("/sessions/{session_id}/messages")
    def message(session_id: str, body: MessageBody):
        result = service.run(session_id, body.question)
        if any(issue["code"] == "storage_failed" for issue in result["execution_issues"]):
            return _error(503, "storage_failed", "本轮未能完整保存，详情见结果。", result=result)
        return result

    @app.get("/sessions/{session_id}")
    def history(session_id: str):
        state = store.get_session(session_id)
        return {"session_id": session_id, "mode": settings.mode,
                "messages": [{"message_id": m["id"], "request_id": m["run_id"], "role": m["role"],
                              "content": m["content"] if m["role"] == "user" else json.loads(m["content"])}
                             for m in state["messages"]],
                "requests": [{"request_id": r["id"], "state": r["state"],
                              "result": json.loads(r["result_json"]) if r["result_json"] else None}
                             for r in state["runs"]],
                "anchor_snapshot": state["anchor_snapshot"] if state["memory_valid"] else None,
                "memory_valid": state["memory_valid"], "memory_warning": state["memory_warning"]}
    return app
