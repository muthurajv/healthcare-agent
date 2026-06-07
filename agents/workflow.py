"""
LangGraph workflow: Find Specialist & Schedule Appointment.

Graph structure:
  START
  → input_phi_scan         (guardrail: detect + redact PHI in user input)
  → consent_check          (guardrail: validate patient consent)
  → parse_request          (LLM: extract specialty, location, preferences)
  → search_providers       (Azure AI Search + FHIR Practitioner)
  → validate_network       (payer eligibility API)
  → find_availability      (FHIR Schedule/Slot)
  → confirm_with_user      (human-in-the-loop interrupt)
  → schedule_appointment   (FHIR Appointment creation)
  → send_notification      (email/SMS)
  → audit_event            (PHI-safe audit log)
  → response_redaction     (output guardrail)
  → END
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from agents.state import AppointmentState

# Guardrail nodes
from agents.guardrails.response_redaction import response_redaction

# Agent nodes
from agents.nodes.parse_request import parse_request
from agents.nodes.search_providers import search_providers
from agents.nodes.validate_network import validate_network
from agents.nodes.find_availability import find_availability
from agents.nodes.confirm_with_user import confirm_with_user
from agents.nodes.schedule_appointment import schedule_appointment
from agents.nodes.send_notification import send_notification
from agents.nodes.audit_event import audit_event

# Observability wrapper
from observability.span_helpers import traced_node


def _input_phi_scan(state: AppointmentState) -> dict:
    """Inline guardrail node: detect and redact PHI in user_request."""
    from agents.guardrails.phi_scanner import redact_for_llm
    user_text = state.get("user_request", "")
    safe_text, phi_detected = redact_for_llm(user_text)
    return {
        "safe_request": safe_text,
        "pii_detected": phi_detected,
        "phi_detected": phi_detected,
        "status": "phi_scan_complete",
    }


def _consent_check(state: AppointmentState) -> dict:
    """Inline guardrail node: verify patient consent before accessing PHI systems."""
    from agents.guardrails.consent_check import check_patient_consent
    user_id = state.get("user_id", "")
    consent_valid = check_patient_consent(user_id=user_id, purpose="appointment_scheduling")
    return {
        "consent_valid": consent_valid,
        "status": "consent_validated" if consent_valid else "consent_denied",
        "response": None if consent_valid else (
            "I need verified consent before I can access your insurance or scheduling details. "
            "Please complete the consent process in your patient portal."
        ),
    }


def _route_after_consent(state: AppointmentState) -> str:
    """Route to parse_request if consented, otherwise skip to response_redaction."""
    if state.get("consent_valid"):
        return "parse_request"
    return "response_redaction"


def _route_after_providers(state: AppointmentState) -> str:
    """If no providers found, go straight to audit (which sets a helpful response)."""
    if not state.get("providers"):
        return "audit_event"
    return "validate_network"


def _route_after_network(state: AppointmentState) -> str:
    if not state.get("in_network_providers"):
        return "audit_event"
    return "find_availability"


def _route_after_availability(state: AppointmentState) -> str:
    if not state.get("available_slots"):
        return "audit_event"
    return "confirm_with_user"


def _route_after_confirm(state: AppointmentState) -> str:
    if state.get("status") in ("no_slots_to_confirm", "invalid_selection"):
        return "audit_event"
    return "schedule_appointment"


def build_graph(checkpointer=None) -> StateGraph:
    builder = StateGraph(AppointmentState)

    # Add nodes (all wrapped with observability spans)
    builder.add_node("input_phi_scan", traced_node("input_phi_scan", _input_phi_scan))
    builder.add_node("consent_check", traced_node("consent_check", _consent_check))
    builder.add_node("parse_request", traced_node("parse_request", parse_request))
    builder.add_node("search_providers", traced_node("search_providers", search_providers))
    builder.add_node("validate_network", traced_node("validate_network", validate_network))
    builder.add_node("find_availability", traced_node("find_availability", find_availability))
    builder.add_node("confirm_with_user", confirm_with_user)  # interrupt node — no tracing wrapper
    builder.add_node("schedule_appointment", traced_node("schedule_appointment", schedule_appointment))
    builder.add_node("send_notification", traced_node("send_notification", send_notification))
    builder.add_node("audit_event", traced_node("audit_event", audit_event))
    builder.add_node("response_redaction", traced_node("response_redaction", response_redaction))

    # Edges
    builder.add_edge(START, "input_phi_scan")
    builder.add_edge("input_phi_scan", "consent_check")

    builder.add_conditional_edges("consent_check", _route_after_consent)

    builder.add_conditional_edges("search_providers", _route_after_providers)
    builder.add_conditional_edges("validate_network", _route_after_network)
    builder.add_conditional_edges("find_availability", _route_after_availability)
    builder.add_conditional_edges("confirm_with_user", _route_after_confirm)

    builder.add_edge("parse_request", "search_providers")
    builder.add_edge("schedule_appointment", "send_notification")
    builder.add_edge("send_notification", "audit_event")
    builder.add_edge("audit_event", "response_redaction")
    builder.add_edge("response_redaction", END)

    return builder.compile(
        checkpointer=checkpointer or MemorySaver(),
        interrupt_before=["confirm_with_user"],
    )


# Singleton graph instance for the API layer
appointment_graph = build_graph()
