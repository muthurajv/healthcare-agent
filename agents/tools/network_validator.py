"""
Payer/eligibility API client for network and coverage validation.
Uses a member token (not raw member ID) to keep PHI out of this service's logs.
"""
from __future__ import annotations

import httpx

from config import settings


def validate_network(
    member_id_token: str,
    insurance_plan: str,
    provider_id: str,
    appointment_type: str = "new_patient",
) -> dict:
    """
    Call the payer network/eligibility API.
    Returns network status, referral requirement, and prior-auth requirement.
    """
    headers = {
        "x-api-key": settings.payer_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "member_token": member_id_token,
        "plan_id": insurance_plan,
        "provider_id": provider_id,
        "appointment_type": appointment_type,
    }

    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{settings.payer_api_base_url}/eligibility/validate",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "provider_id": provider_id,
        "network_status": data.get("network_status", "unknown"),
        "referral_required": data.get("referral_required", False),
        "prior_auth_required": data.get("prior_auth_required", False),
        "contract_active": data.get("contract_active", False),
        "copay_estimate": data.get("copay_estimate"),
    }


def filter_in_network(
    providers: list[dict],
    member_id_token: str,
    insurance_plan: str,
) -> list[dict]:
    """Validate each provider and return only in-network ones."""
    in_network = []
    for provider in providers:
        try:
            result = validate_network(member_id_token, insurance_plan, provider["id"])
            if result["network_status"] == "in_network" and result["contract_active"]:
                enriched = {**provider, **result}
                in_network.append(enriched)
        except httpx.HTTPError:
            # Skip providers where eligibility check fails; do not surface PHI in error
            continue
    return in_network
