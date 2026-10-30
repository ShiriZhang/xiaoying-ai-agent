"""Structural anchor validation, independent of business-result validation."""

import copy
import re
import unicodedata


ANCHOR_FIELDS = ("subject", "focus", "pending_clarification")


class AnchorError(ValueError):
    pass


def validate_anchor_content(value):
    """Reject recognizable assertions, not all numbers or all natural language.

    Topic/question forms are allowed, including numeric user interests. Split
    parenthetical facts so appending a question cannot hide a separate claim.
    Prompting and recorded semantic review remain necessary for other wording.
    """
    text = unicodedata.normalize("NFKC", value).casefold()
    for clause in re.split(r"[，,。;；:：（）()\n]|以及|另外|同时|并且|但是", text):
        question = re.search(
            r"是否|有无|能否|可否|多少|多久|什么|哪些|如何|怎么|怎样|吗"
            r"|支持情况$|适用情况$|冲突处理$|^(?:待)?确认(?:适用)?(?:的)?(?:制度|规则|口径|对象)$"
            r"|所需(?:提交|提供)(?:材料|凭证|信息)$|(?:需|需要|必须)(?:提交|提供)的(?:材料|凭证|信息)$", clause)
        if question:
            continue
        conflict = re.search(r"冲突|矛盾|不一致|相互抵触", clause)
        quantity = re.search(r"\d+(?:\.\d+)?\s*(?:个\s*)?(?:工作日|天|小时|元|%|p\b|k\b)", clause)
        assertion = re.search(r"(?:为|是|应在|应当|必须|最高|最低|最多|至少|提前|不超过|不得超过|只能)|(?:需|需要)(?:提交|提供)|支持(?!的|情况|能力|范围|方式)|导出为|保存于", clause)
        if conflict or (quantity and assertion) or re.search(r"(?:需|需要|必须)(?:提交|提供).+|支持(?!的|情况|能力|范围|方式)\s*[a-z0-9]|导出为\s*[a-z0-9]", clause):
            raise AnchorError("anchor_contains_company_conclusion")


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
        validate_anchor_content(item["value"])
    return copy.deepcopy(proposal)
