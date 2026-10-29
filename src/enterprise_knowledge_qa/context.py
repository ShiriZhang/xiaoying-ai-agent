"""Select complete recent message pairs with a documented token estimate."""

import json
import math


ESTIMATE_METHOD = "ceil(UTF-8 serialized message bytes / 3) + 8 per message; heuristic, not model tokenizer"


def estimate_messages(messages):
    return sum(math.ceil(len(json.dumps(message, ensure_ascii=False).encode("utf-8")) / 3) + 8
               for message in messages)


def history_message(message):
    # IDs accompany, rather than replace or truncate, the original message text.
    return {"role": message["role"], "content": json.dumps(
        {"message_id": message["id"], "content": message["content"]}, ensure_ascii=False)}


def select_history(state, budget):
    if type(budget) is not int or budget <= 0:
        raise ValueError("History token budget must be positive")
    by_run = {}
    for message in state["messages"]:
        by_run.setdefault(message["run_id"], []).append(message)
    pairs = [by_run[run["id"]] for run in state["runs"] if run["state"] == "completed"
             and len(by_run.get(run["id"], [])) == 2
             and [m["role"] for m in by_run[run["id"]]] == ["user", "assistant"]]
    selected, total = [], 0
    for pair in reversed(pairs):
        count = estimate_messages([history_message(m) for m in pair])
        if total + count > budget:
            break  # Do not jump over an oversized recent pair to older history.
        total += count
        selected[:0] = pair
    chosen_ids = [m["id"] for m in selected]
    return [history_message(m) for m in selected], {
        "budget": budget, "estimated_tokens": total, "estimate_method": ESTIMATE_METHOD,
        "selected_message_ids": chosen_ids,
        "omitted_message_ids": [m["id"] for m in state["messages"] if m["id"] not in set(chosen_ids)],
        "boundary": "complete recent business message pairs; run traces stored separately",
    }
