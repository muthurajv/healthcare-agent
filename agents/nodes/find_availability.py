"""
Node 4: Query FHIR Schedule/Slot APIs to find open appointment slots for in-network providers.
"""
from __future__ import annotations

from datetime import date, timedelta

from agents.state import AppointmentState, ProviderSlot
from agents.tools.fhir_client import get_available_slots


def find_availability(state: AppointmentState) -> dict:
    in_network_providers = state.get("in_network_providers", [])
    preferred_date = state.get("preferred_date", "next week")

    # Resolve date range from natural language preference
    start_date, end_date = _resolve_date_range(preferred_date)

    all_slots: list[ProviderSlot] = []

    for provider in in_network_providers[:5]:  # Check top 5 in-network providers
        fhir_id = provider.get("fhir_id")
        if not fhir_id:
            continue

        try:
            raw_slots = get_available_slots(
                practitioner_fhir_id=fhir_id,
                start_date=start_date,
                end_date=end_date,
            )
            for slot in raw_slots[:3]:  # Max 3 slots per provider
                all_slots.append({
                    "provider_id": provider["id"],
                    "date": slot["start"][:10],
                    "time": slot["start"][11:16],
                    "location": provider.get("location", ""),
                    "slot_fhir_id": slot["slot_fhir_id"],
                })
        except Exception:
            continue

    return {
        "available_slots": all_slots,
        "status": "availability_found" if all_slots else "no_slots_found",
    }


def _resolve_date_range(preference: str | None) -> tuple[str, str]:
    today = date.today()
    if not preference or "next week" in (preference or "").lower():
        start = today + timedelta(days=(7 - today.weekday()))
        end = start + timedelta(days=6)
    elif "this week" in (preference or "").lower():
        start = today
        end = today + timedelta(days=(6 - today.weekday()))
    else:
        # Default: next 14 days
        start = today + timedelta(days=1)
        end = today + timedelta(days=14)
    return start.isoformat(), end.isoformat()
