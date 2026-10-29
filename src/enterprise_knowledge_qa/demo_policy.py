"""Explicit controlled Mock demo, never a substitute for live model semantics.

Only export-format, resolution and reimbursement-material demonstrations are
supported. Branches select demo actions; facts always come from actual reads.
"""

import json
from uuid import uuid4

from .models import ModelReply, ToolCall


def _action(name, **arguments):
    arguments["reason"] = "受控Mock演示策略选择动作，不代表真实模型判断。"
    return ModelReply((ToolCall(uuid4().hex, name, json.dumps(arguments, ensure_ascii=False)),), "mock-demo-policy")


def demo_policy(messages, tools):
    question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
    ids = json.loads(next(m["content"].split("：", 1)[1] for m in messages
                         if m["role"] == "system" and m["content"].startswith("本轮消息标识：")))
    memory = json.loads(next(m["content"].split("：", 1)[1] for m in messages
                            if m["role"] == "system" and m["content"].startswith("对话锚点")))
    subject = memory.get("subject") if isinstance(memory, dict) else None
    product = "星帆剪辑" in question or (isinstance(subject, dict) and subject.get("value") == "星帆剪辑")
    anchor = {"subject": None, "focus": None, "pending_clarification": None}
    def finish(status, answer, *, refs=None, gaps=None, clarification=None):
        return _action("finish", status=status, part_statuses=[status], answer=answer,
                       citation_refs=refs or [], gaps=gaps or [], clarification=clarification,
                       anchor_snapshot=anchor)
    if "报销" in question and "材料" in question:
        topic, focus, terms = "报销", "材料", ("发票", "审批单")
    elif "分辨率" in question or ("导出" in question and "格式" in question):
        if not product:
            anchor["pending_clarification"] = {"value": "确认产品对象", "source_message_ids": [ids["user_message_id"]]}
            return finish("needs_clarification", "Mock演示需要先确认产品对象。", gaps=["讨论对象不明确。"],
                          clarification="你问的是哪个产品？")
        topic = "星帆剪辑"
        focus, terms = ("分辨率", ("分辨率",)) if "分辨率" in question else ("导出格式", ("导出", "格式"))
    else:
        return finish("incomplete", "受控Mock仅演示导出格式、分辨率和报销材料；本问题未执行语义判断。")
    anchor["subject"] = {"value": topic, "source_message_ids": [ids["user_message_id"]]}
    anchor["focus"] = {"value": focus, "source_message_ids": [ids["user_message_id"]]}
    observations = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
    if not observations:
        return _action("search", query=f"{topic} {focus}", limit=6)
    last = observations[-1]
    if last.get("status") == "error":
        return finish("incomplete", "Mock演示遇到工具错误，任务未完成。")
    if last.get("tool") == "search":
        found = next((c for c in last["candidates"] if all(term in c["summary"] for term in terms)), None)
        if found:
            return _action("read", passage_ids=[found["passage_id"]])
        if sum(o.get("tool") == "search" for o in observations) == 1:
            return _action("search", query=f"{topic} {focus}", limit=12)
        return finish("insufficient_evidence", "Mock演示未取得所需原文。", gaps=["本轮候选未覆盖演示所需内容。"])
    passage = last["passages"][0]
    return finish("answered", "Mock逐字原文展示（不作规则裁决）：\n" + passage["text"] + "[C1]", refs=[{
        "marker": "[C1]", "passage_id": passage["passage_id"], "corpus_fingerprint": last["corpus_fingerprint"]}])
