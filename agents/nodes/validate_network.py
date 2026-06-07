"""
Node 3: Confirm each provider is in-network using the payer eligibility API.
Uses member_id_token (opaque reference) — no raw member ID touches this node.
"""
from __future__ import annotations

from agents.state import AppointmentState
from agents.tools.network_validator import filter_in_network


def validate_network(state: AppointmentState) -> dict:
    providers = state.get("providers", [])
    member_id_token = state.get("member_id_token", "")
    insurance_plan = state.get("insurance_plan", "")

    if not providers:
        return {"in_network_providers": [], "status": "no_providers_to_validate"}

    if not member_id_token or not insurance_plan:
        # Without eligibility credentials, pass all providers through unvalidated
        return {
            "in_network_providers": providers,
            "status": "network_validation_skipped",
        }

    in_network = filter_in_network(
        providers=providers,
        member_id_token=member_id_token,
        insurance_plan=insurance_plan,
    )

    return {
        "in_network_providers": in_network,
        "status": "network_validated" if in_network else "no_in_network_providers",
    }
