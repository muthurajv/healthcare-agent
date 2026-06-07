"""
Output guardrail: strip any residual PHI/PII from the final response
before it is returned to the user through the API layer.
"""
from __future__ import annotations

from agents.guardrails.phi_scanner import redact_for_llm
from agents.state import AppointmentState


def response_redaction(state: AppointmentState) -> dict:
    """LangGraph node: scan and redact the outgoing response."""
    raw_response = state.get("response", "") or ""

    if not raw_response:
        return {"status": "redaction_skipped"}

    cleaned, phi_found = redact_for_llm(raw_response)

    return {
        "response": cleaned,
        "status": "redacted" if phi_found else state.get("status", "complete"),
    }
