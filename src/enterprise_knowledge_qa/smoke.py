"""Small explicitly live protocol check; not a business CLI or acceptance suite."""

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .agent import Agent
from .config import ConfigurationError, load_settings
from .knowledge import CorpusError
from .models import DeepSeekModel
from .snapshots import load_snapshot


QUESTION = (
    "这是工具协议冒烟，不是最终业务验收。请先调用read读取D03-P01，"
    "再根据返回原文回答报销材料，并调用finish结束。search尚未接入，不需要搜索。"
    "引用用[C1]，citation_refs内带本任务corpus_fingerprint；"
    "anchor_snapshot请用subject、focus、pending_clarification三字段，暂不明确的值填null。"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--live", action="store_true", required=True,
                        help="Explicitly authorize a small paid live protocol run")
    args = parser.parse_args()
    try:
        settings = replace(load_settings(args.env_file), mode="live")
        model = DeepSeekModel(settings.api_key)
        snapshot = load_snapshot(settings.data_path)
    except (ConfigurationError, CorpusError) as error:
        parser.exit(2, f"Preparation failed: {error}\n")
    result = Agent(settings, model, snapshot).run(QUESTION, trace_directory=args.output)
    actions = [e["action"] for e in result["trace"] if e["kind"] == "action"]
    verified = result["status"] == "answered" and "read" in actions and actions[-1:] == ["finish"]
    summary = {"scope": "live protocol smoke; no embedding or six-scenario acceptance",
               "protocol_verified": verified, "request_id": result["request_id"],
               "mode": result["mode"], "status": result["status"], "stop_reason": result["stop_reason"],
               "counts": result["counts"], "usage": result["usage"],
               "actual_models": sorted({e["actual_model"] for e in result["trace"]
                                         if e["kind"] == "model_response" and e["actual_model"]})}
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (result["request_id"] + "-summary.json")).open("x", encoding="utf-8") as output:
        json.dump(summary, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
