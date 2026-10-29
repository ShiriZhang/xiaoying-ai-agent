"""Structural anchor validation, independent of business-result validation."""

import copy


ANCHOR_FIELDS = ("subject", "focus", "pending_clarification")


class AnchorError(ValueError):
    pass


def validate_anchor(proposal, source_ids):
    if not isinstance(proposal, dict) or set(proposal) != set(ANCHOR_FIELDS):
        raise AnchorError("anchor_requires_complete_three_field_snapshot")
    for field in ANCHOR_FIELDS:
        item = proposal[field]
        if item is None:
            continue
        if not isinstance(item, dict) or set(item) != {"value", "source_message_ids"}:
            raise AnchorError("anchor_item_requires_value_and_message_sources")
        if not isinstance(item["value"], str) or not item["value"].strip():
            raise AnchorError("anchor_value_must_be_nonempty_text")
        sources = item["source_message_ids"]
        if (not isinstance(sources, list) or not sources or
                any(not isinstance(source, str) or source not in source_ids for source in sources)):
            raise AnchorError("anchor_sources_must_belong_to_this_session")
        if len(set(sources)) != len(sources):
            raise AnchorError("anchor_sources_must_be_unique")
    return copy.deepcopy(proposal)
