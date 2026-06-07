"""
Node 1: Extract structured intent from the PHI-redacted user request via Azure OpenAI.
The LLM sees only the safe_request — no raw PHI.
"""
from __future__ import annotations

import json

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.guardrails.phi_scanner import redact_for_llm
from agents.state import AppointmentState
from config import settings

_llm: AzureChatOpenAI | None = None


def _get_llm() -> AzureChatOpenAI:
    global _llm
    if _llm is None:
        _llm = AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            temperature=0,
        )
    return _llm

_SYSTEM_PROMPT = """You are a healthcare assistant that extracts structured information from patient requests.
Extract ONLY these fields from the user's message and return valid JSON:
- specialty: medical specialty requested (string)
- location: city or area (string, no street address)
- insurance_plan: insurance plan name if mentioned (string or null)
- preferred_date: date preference like "next week", "Tuesday" (string or null)
- gender_preference: "male", "female", or null
- language_preference: language if mentioned (string or null)

Return ONLY a JSON object. No explanation."""


def parse_request(state: AppointmentState) -> dict:
    user_request = state.get("user_request", "")

    # Redact PHI before sending to LLM
    safe_request, phi_detected = redact_for_llm(user_request)

    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=safe_request),
    ]

    response = _get_llm().invoke(messages)
    content = response.content.strip()

    # Strip markdown code fences if present
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}

    usage = response.response_metadata.get("token_usage", {})

    return {
        "safe_request": safe_request,
        "pii_detected": phi_detected,
        "phi_detected": phi_detected,
        "specialty": parsed.get("specialty"),
        "location": parsed.get("location"),
        "insurance_plan": parsed.get("insurance_plan"),
        "preferred_date": parsed.get("preferred_date"),
        "gender_preference": parsed.get("gender_preference"),
        "language_preference": parsed.get("language_preference"),
        "llm_usage": {
            "model": settings.azure_openai_deployment,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
        "status": "parsed",
    }
