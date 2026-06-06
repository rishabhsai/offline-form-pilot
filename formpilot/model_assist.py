"""Optional small-model assist for form analysis."""

from __future__ import annotations

import json
import os
from typing import Any


DEFAULT_SMALL_MODEL = os.getenv("FORMPILOT_MODEL", "openbmb/MiniCPM5-1B")


def build_model_prompt(form_text: str, user_facts: str) -> str:
    """Prompt a small model to return conservative form-fill JSON."""

    return f"""You are helping prepare a form for human review. Do not submit anything.

Return only JSON with this schema:
{{
  "fields": [
    {{
      "field": "field label",
      "proposed_value": "value or empty string",
      "status": "ready|review|missing",
      "confidence": 0,
      "source": "fact used or empty",
      "note": "short reason"
    }}
  ],
  "questions": ["questions for missing fields"],
  "risk_summary": ["review warnings"]
}}

Rules:
- Use only the user facts.
- If a value is absent, mark missing.
- Sensitive fields must be review, not ready.
- Never invent account numbers, IDs, dates, signatures, addresses, or legal facts.

FORM:
{form_text}

USER FACTS:
{user_facts}
"""


def try_hf_model_assist(form_text: str, user_facts: str, model_id: str = DEFAULT_SMALL_MODEL) -> dict[str, Any]:
    """Call a small Hugging Face model and parse its JSON response."""

    try:
        from huggingface_hub import InferenceClient
    except ImportError as exc:
        raise RuntimeError("huggingface_hub is not installed.") from exc

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")
    client = InferenceClient(model=model_id, token=token)
    prompt = build_model_prompt(form_text, user_facts)
    response = client.text_generation(
        prompt,
        max_new_tokens=700,
        temperature=0.1,
        return_full_text=False,
    )
    return _parse_json_response(str(response))


def _parse_json_response(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return a JSON object.")
    return json.loads(raw[start : end + 1])
