"""Situation brief orchestration: Amazon Bedrock when available, deterministic fallback otherwise."""
from __future__ import annotations

import json
import re

from .bedrock_client import BedrockUnavailable, bedrock_enabled, converse, model_id
from .fallback_brief import fallback_brief
from .prompt_templates import ID_PATTERN, LIST_KEYS, SECTION_KEYS, SYSTEM_PROMPT, allowed_ids, build_facts, user_prompt


def _parse(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no json object")
    return json.loads(t[start:end + 1])


def validate_brief(obj: dict, facts: dict) -> dict:
    """Structure + grounding validation. Raises ValueError when the model output is unusable."""
    out = {}
    for k in SECTION_KEYS:
        if k not in obj:
            raise ValueError(f"missing {k}")
        v = obj[k]
        if k in LIST_KEYS:
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v) or not v:
                raise ValueError(f"bad list {k}")
            out[k] = [x.strip()[:600] for x in v][:8]
        else:
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"bad text {k}")
            out[k] = v.strip()[:1200]
    allowed = allowed_ids(facts)
    cited = set(ID_PATTERN.findall(json.dumps(out)))
    unknown = cited - allowed
    if unknown:
        raise ValueError(f"ungrounded identifiers: {sorted(unknown)[:5]}")
    return out


def generate_brief(sim: dict, brief_type: str = "situation", allow_ai: bool = True, client=None) -> dict:
    facts = build_facts(sim)
    meta = {"simulation_version": sim["simulation_version"], "dataset_version": sim["dataset_version"], "synthetic_data": True,
            "brief_type": brief_type}
    if allow_ai and bedrock_enabled():
        try:
            text = converse(SYSTEM_PROMPT, user_prompt(facts, brief_type), client=client)
            sections = validate_brief(_parse(text), facts)
            return {"provider": "bedrock", "provider_label": "Amazon Bedrock (AI-generated, grounded in simulation output)",
                    "model_id": model_id(), "sections": sections, "fallback_reason": None, **meta}
        except BedrockUnavailable as exc:
            reason = exc.category
        except (ValueError, KeyError, json.JSONDecodeError):
            reason = "invalid_model_output"
    else:
        reason = "ai_not_requested" if not allow_ai else "disabled"
    return {"provider": "rule_based", "provider_label": "Rule-based situation brief (deterministic; not AI-generated)",
            "model_id": None, "sections": fallback_brief(facts), "fallback_reason": reason, **meta}
