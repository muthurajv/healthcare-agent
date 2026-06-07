"""
Node 2: Find matching specialists via Azure AI Search and FHIR Practitioner lookup.
"""
from __future__ import annotations

from agents.state import AppointmentState
from agents.tools.provider_search import search_providers as ai_search_providers
from agents.tools.fhir_client import search_practitioners


def search_providers(state: AppointmentState) -> dict:
    specialty = state.get("specialty") or ""
    location = state.get("location") or ""
    language = state.get("language_preference")
    gender = state.get("gender_preference")

    # Primary: Azure AI Search provider directory
    providers = ai_search_providers(
        specialty=specialty,
        location=location,
        accepting_new_patients=True,
        language=language,
        gender=gender,
        top=10,
    )

    # Enrich with FHIR data if provider directory returned results
    if providers:
        try:
            fhir_roles = search_practitioners(specialty=specialty, location=location)
            fhir_by_npi = {r.get("npi", ""): r for r in fhir_roles if r.get("npi")}
            for p in providers:
                fhir_data = fhir_by_npi.get(p.get("npi", ""), {})
                if fhir_data:
                    p["fhir_id"] = fhir_data.get("fhir_id")
        except Exception:
            # FHIR enrichment is best-effort; don't fail the node
            pass

    return {
        "providers": providers,
        "status": "providers_found" if providers else "no_providers_found",
    }
