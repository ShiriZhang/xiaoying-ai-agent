"""Recheck saved personal-delegate evidence without new paid requests."""

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", default=str(ROOT / "examples/batch-8/runs/personal-initial"))
    run = Path(parser.parse_args().run).resolve()
    records = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted(run.glob("delegate-export-format-change-r1-t*.json"))]
    assert len(records) == 2
    first, second = [record["result"] for record in records]
    assert first["mode"] == second["mode"] == "live"
    assert first["session_id"] == second["session_id"]
    assert first["status"] == second["status"] == "answered"
    assert first["read_set"] == second["read_set"] == ["D09-P01"]
    assert "MP4" in first["answer"] and "MOV" in first["answer"]
    assert "MP4" in second["answer"] and "WEBM" in second["answer"] and "MOV" not in second["answer"]
    assert first["corpus_fingerprint"] != second["corpus_fingerprint"]
    corpora = [json.loads((run / record["corpus_file"]).read_text(encoding="utf-8")) for record in records]
    for result, corpus in zip((first, second), corpora):
        source = next(d for d in corpus["documents"] if d["doc_id"] == "D09")
        citation = result["citations"][0]
        assert citation["passage_id"] == "D09-P01" and citation["marker"] == "[C1]"
        assert citation["text"] == source["passages"][0]["text"]
        assert citation["version_date"] == citation["effective_date"] == "2026-01-01"
        assert citation["corpus_fingerprint"] == result["corpus_fingerprint"]
        actions = [event["action"] for event in result["trace"] if event["kind"] == "action"]
        assert "search" in actions and "read" in actions
        assert result["counts"] == {"model_calls": 3, "tool_calls": 2, "recoveries": 0, "format_corrections": 0}
        assert result["memory_valid"] and result["memory_persisted"] and result["persistence"]["saved"]
    for old, new in zip(corpora[0]["documents"], corpora[1]["documents"]):
        if old["doc_id"] != "D09":
            assert old == new
        else:
            assert old["passages"][0]["text"].replace("MP4、MOV", "MP4、WEBM") == new["passages"][0]["text"]
            assert {k: v for k, v in old.items() if k != "passages"} == {k: v for k, v in new.items() if k != "passages"}
    base = json.loads((ROOT / "data/knowledge.json").read_text(encoding="utf-8"))
    assert base == corpora[0]
    assert "MOV" in next(d for d in base["documents"] if d["doc_id"] == "D09")["passages"][0]["text"]
    assert first["message_ids"]["user_message_id"] in second["history_selection"]["selected_message_ids"]
    assert first["anchor_snapshot"] == second["memory_update"]["before"]
    assert "MOV" in "\n".join(m["content"] for m in second["input"]["context"])
    models = sorted({event["actual_model"] for r in (first, second) for event in r["trace"]
                     if event["kind"] == "model_response"})
    print(json.dumps({"checks": "passed", "actual_models": models,
                      "actions": [[e["action"] for e in r["trace"] if e["kind"] == "action"] for r in (first, second)],
                      "fingerprints": [first["corpus_fingerprint"], second["corpus_fingerprint"]],
                      "cost": json.loads((run / "summary.json").read_text(encoding="utf-8"))["total_estimated_cny"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
