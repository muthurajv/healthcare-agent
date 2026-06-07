"""
Node 7: Send appointment confirmation via email/SMS.
Only passes appointment_id and notification_type — no raw contact details.
"""
from __future__ import annotations

import httpx

from agents.state import AppointmentState
from config import settings


def send_notification(state: AppointmentState) -> dict:
    appointment_id = state.get("appointment_id")
    if not appointment_id:
        return {"status": "notification_skipped"}

    if not settings.notification_api_url:
        return {"status": "notification_skipped_no_service"}

    payload = {
        "appointment_id": appointment_id,
        "notification_type": "appointment_confirmation",
    }

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{settings.notification_api_url}/send",
                headers={"x-api-key": settings.notification_api_key},
                json=payload,
            )
            resp.raise_for_status()
        return {"status": "notification_sent"}
    except httpx.HTTPError:
        # Non-fatal: appointment is still booked even if notification fails
        return {"status": "notification_failed"}
