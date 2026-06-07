"""
Validates patient consent before the agent accesses insurance or scheduling data.
"""
from __future__ import annotations

import httpx

from config import settings


def check_patient_consent(user_id: str, purpose: str = "appointment_scheduling") -> bool:
    """
    Call the consent service to verify the patient has given consent for the given purpose.
    Returns True if consent is valid, False otherwise.
    """
    if not settings.consent_service_url:
        # In development without a consent service, default to True
        return True

    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(
                f"{settings.consent_service_url}/check",
                params={"user_id": user_id, "purpose": purpose},
            )
            resp.raise_for_status()
            return resp.json().get("consent_valid", False)
    except httpx.HTTPError:
        # Fail closed — if the consent service is unreachable, deny access
        return False
