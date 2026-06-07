"""
Azure AI Search client for the provider directory index.
Returns structured provider records matching specialty, location, and preferences.
"""
from __future__ import annotations

import httpx

from config import settings


def search_providers(
    specialty: str,
    location: str,
    accepting_new_patients: bool = True,
    language: str | None = None,
    gender: str | None = None,
    top: int = 10,
) -> list[dict]:
    """Full-text + filter search against the Azure AI Search provider index."""
    filters = [f"accepting_new_patients eq {str(accepting_new_patients).lower()}"]
    if language:
        filters.append(f"languages/any(l: l eq '{language}')")
    if gender:
        filters.append(f"gender eq '{gender}'")

    body = {
        "search": f"{specialty} {location}",
        "filter": " and ".join(filters),
        "select": "provider_id,name,specialty,location,accepting_new_patients,npi,rating,hospital_affiliation",
        "top": top,
        "queryType": "semantic",
        "semanticConfiguration": "provider-semantic",
    }

    headers = {
        "api-key": settings.azure_search_api_key,
        "Content-Type": "application/json",
    }
    url = (
        f"{settings.azure_search_endpoint}/indexes/"
        f"{settings.azure_search_provider_index}/docs/search"
        "?api-version=2024-05-01-preview"
    )

    with httpx.Client(timeout=10) as client:
        resp = client.post(url, headers=headers, json=body)
        resp.raise_for_status()

    results = resp.json().get("value", [])
    return [
        {
            "id": r.get("provider_id", ""),
            "name": r.get("name", ""),
            "specialty": r.get("specialty", ""),
            "location": r.get("location", ""),
            "accepting_new_patients": r.get("accepting_new_patients", False),
            "npi": r.get("npi", ""),
            "rating": r.get("rating"),
            "hospital_affiliation": r.get("hospital_affiliation", ""),
        }
        for r in results
    ]
