"""
Wraps LangGraph nodes with OpenTelemetry spans.
Only PHI-safe attributes are recorded — never name, DOB, member ID, SSN, phone, email.
"""
from __future__ import annotations

from typing import Any, Callable

from opentelemetry.trace import Status, StatusCode

from observability.tracing import get_tracer

_WORKFLOW_NAME = "find_specialist_schedule"


def traced_node(node_name: str, fn: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Decorator that wraps a LangGraph node function in an OTEL span."""
    tracer = get_tracer()

    def wrapper(state: Any) -> Any:
        with tracer.start_as_current_span(node_name) as span:
            span.set_attribute("agent.node", node_name)
            span.set_attribute("workflow.name", _WORKFLOW_NAME)

            # Pre-call safe context attributes
            if state.get("specialty"):
                span.set_attribute("request.specialty", state["specialty"])
            if state.get("location"):
                # Truncate to city-level only — no street address
                span.set_attribute("request.location", state["location"].split(",")[0].strip())
            if state.get("insurance_plan"):
                span.set_attribute("request.insurance_plan", state["insurance_plan"])

            try:
                result = fn(state)

                span.set_attribute("agent.status", result.get("status", "unknown"))

                if "providers" in result:
                    span.set_attribute("provider.count", len(result["providers"]))
                if "in_network_providers" in result:
                    span.set_attribute("in_network.count", len(result["in_network_providers"]))
                if "available_slots" in result:
                    span.set_attribute("slot.count", len(result["available_slots"]))
                if result.get("appointment_id"):
                    span.set_attribute("appointment.booked", True)
                if result.get("pii_detected") is not None:
                    span.set_attribute("guardrail.pii_detected", bool(result["pii_detected"]))
                if result.get("consent_valid") is not None:
                    span.set_attribute("guardrail.consent_valid", bool(result["consent_valid"]))

                # LLM usage if present
                usage = result.get("llm_usage", {})
                if usage:
                    span.set_attribute("llm.model", usage.get("model", ""))
                    span.set_attribute("llm.prompt_tokens", usage.get("prompt_tokens", 0))
                    span.set_attribute("llm.completion_tokens", usage.get("completion_tokens", 0))

                return result

            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise

    wrapper.__name__ = fn.__name__
    return wrapper


def safe_zip3(zip_code: str) -> str:
    """Return only first 3 digits of a ZIP code for PHI-safe span attributes."""
    return zip_code[:3] if zip_code else ""
