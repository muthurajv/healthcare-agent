"""
Authorization wrapper that enforces role-based access and data minimization
before any enterprise API call. The LLM never calls APIs directly.
"""
from __future__ import annotations

from typing import Any, Callable

# Allowlist: which roles may invoke which tools with which fields
_TOOL_POLICY: dict[str, dict] = {
    "provider_search": {
        "allowed_roles": {"member", "agent", "admin"},
        "allowed_fields": {"specialty", "location", "accepting_new_patients", "language", "gender", "top"},
    },
    "network_validation": {
        "allowed_roles": {"member", "agent", "admin"},
        "allowed_fields": {"member_id_token", "insurance_plan", "provider_id", "appointment_type"},
    },
    "availability_search": {
        "allowed_roles": {"member", "agent", "admin"},
        "allowed_fields": {"practitioner_fhir_id", "start_date", "end_date"},
    },
    "schedule_appointment": {
        "allowed_roles": {"member", "admin"},
        "allowed_fields": {"patient_token", "practitioner_fhir_id", "slot_fhir_id", "specialty"},
    },
    "send_notification": {
        "allowed_roles": {"member", "agent", "admin"},
        "allowed_fields": {"appointment_id", "notification_type"},
    },
}


class ToolAuthorizationError(PermissionError):
    pass


def secure_tool_call(
    tool_name: str,
    payload: dict[str, Any],
    user_context: dict[str, Any],
    fn: Callable[..., Any],
) -> Any:
    """
    Validate role, strip disallowed fields, then call the underlying API function.

    Args:
        tool_name: Key in _TOOL_POLICY.
        payload: Data to pass to the API (will be minimized).
        user_context: Must contain 'user_id' and 'role'.
        fn: The actual API callable to invoke with minimized payload.
    """
    policy = _TOOL_POLICY.get(tool_name)
    if not policy:
        raise ToolAuthorizationError(f"Unknown tool: {tool_name}")

    role = user_context.get("role", "")
    if role not in policy["allowed_roles"]:
        raise ToolAuthorizationError(
            f"Role '{role}' is not authorized to call '{tool_name}'"
        )

    # Strip any fields not on the allowlist (data minimization)
    minimized = {k: v for k, v in payload.items() if k in policy["allowed_fields"]}

    return fn(**minimized)
