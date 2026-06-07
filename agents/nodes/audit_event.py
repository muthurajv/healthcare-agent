"""
Node 8: Write a PHI-safe audit record for the completed workflow.
Stores decision metadata without raw PHI — uses tokens and IDs only.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import httpx

from agents.state import AppointmentState

# In production: write to Azure SQL or ADLS Gen2 with TDE + RBAC.
# Here we log to an internal audit endpoint or use a stub.
_AUDIT_FIELDS = [
    "user_id",
    "specialty",
    "insurance_plan",
    "appointment_id",
    "status",
    "consent_valid",
    "pii_detected",
    "member_id_token",
]


def audit_event(state: AppointmentState) -> dict:
    audit_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    record = {
        "audit_id": audit_id,
        "timestamp": timestamp,
        "workflow": "find_specialist_schedule",
        "access_purpose": "appointment_scheduling",
    }

    # Include only PHI-safe fields
    for field in _AUDIT_FIELDS:
        value = state.get(field)
        if value is not None:
            record[field] = value

    # Network validation outcome (no raw member data)
    in_network_count = len(state.get("in_network_providers", []))
    record["in_network_provider_count"] = in_network_count
    record["providers_searched"] = len(state.get("providers", []))
    record["slots_found"] = len(state.get("available_slots", []))

    # Write to audit store (stub — replace with Azure SQL / secure store call)
    _write_audit_record(record)

    return {
        "audit_id": audit_id,
        "status": state.get("status", "complete"),
    }


def _write_audit_record(record: dict) -> None:
    """Stub: in production, persist to encrypted Azure SQL audit table."""
    # TODO: Replace with sqlalchemy or Azure Data Factory write
    import logging
    logging.getLogger("audit").info("AUDIT: %s", record)
