"""
Node 6: Create a FHIR Appointment resource. Only runs after user confirmation.
Uses patient_token (opaque reference) — not raw member ID.
"""
from __future__ import annotations

from agents.state import AppointmentState
from agents.tools.fhir_client import create_appointment


def schedule_appointment(state: AppointmentState) -> dict:
    selected_slot = state.get("selected_slot")
    if not selected_slot:
        return {"status": "no_slot_selected"}

    member_id_token = state.get("member_id_token", "")
    specialty = state.get("specialty", "")

    # Resolve the FHIR practitioner ID from in_network_providers
    provider_id = selected_slot.get("provider_id", "")
    in_network = state.get("in_network_providers", [])
    provider = next((p for p in in_network if p["id"] == provider_id), {})
    practitioner_fhir_id = provider.get("fhir_id", "")

    slot_fhir_id = selected_slot.get("slot_fhir_id", "")

    if not practitioner_fhir_id or not slot_fhir_id:
        return {
            "status": "scheduling_failed",
            "response": "Unable to book: missing FHIR resource references.",
        }

    fhir_appointment = create_appointment(
        patient_token=member_id_token,
        practitioner_fhir_id=practitioner_fhir_id,
        slot_fhir_id=slot_fhir_id,
        specialty=specialty,
    )

    appointment_id = fhir_appointment.get("id", "")

    return {
        "appointment_id": appointment_id,
        "response": (
            f"Your appointment has been booked for "
            f"{selected_slot['date']} at {selected_slot['time']} "
            f"at {selected_slot.get('location', 'the clinic')}. "
            f"Confirmation ID: {appointment_id}"
        ),
        "status": "scheduled",
    }
