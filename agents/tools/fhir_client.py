"""
FHIR REST client for Azure Health Data Services.
Handles auth via Azure AD client-credentials and wraps key FHIR resources.
"""
from __future__ import annotations

import httpx
from azure.identity import ClientSecretCredential

from config import settings

_FHIR_SCOPE = "https://healthcareapis.azure.com/.default"


def _get_access_token() -> str:
    credential = ClientSecretCredential(
        tenant_id=settings.fhir_tenant_id,
        client_id=settings.fhir_client_id,
        client_secret=settings.fhir_client_secret,
    )
    token = credential.get_token(_FHIR_SCOPE)
    return token.token


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_access_token()}",
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }


def search_practitioners(specialty: str, location: str) -> list[dict]:
    """Search FHIR Practitioner + PractitionerRole by specialty and location."""
    params = {
        "specialty": specialty,
        "location": location,
        "_include": "PractitionerRole:practitioner",
        "_count": "20",
    }
    with httpx.Client(timeout=10) as client:
        resp = client.get(
            f"{settings.fhir_base_url}/PractitionerRole",
            headers=_headers(),
            params=params,
        )
        resp.raise_for_status()
        bundle = resp.json()

    practitioners = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "PractitionerRole":
            practitioners.append({
                "fhir_id": resource.get("id"),
                "practitioner_ref": resource.get("practitioner", {}).get("reference", ""),
                "specialty": _extract_specialty(resource),
                "location_ref": resource.get("location", [{}])[0].get("reference", ""),
                "accepting_new_patients": resource.get("availableTime") is not None,
            })
    return practitioners


def get_available_slots(practitioner_fhir_id: str, start_date: str, end_date: str) -> list[dict]:
    """Query FHIR Schedule + Slot for open appointment slots."""
    # First find the Schedule for the practitioner
    with httpx.Client(timeout=10) as client:
        sched_resp = client.get(
            f"{settings.fhir_base_url}/Schedule",
            headers=_headers(),
            params={"actor": f"Practitioner/{practitioner_fhir_id}"},
        )
        sched_resp.raise_for_status()
        sched_bundle = sched_resp.json()

    schedule_ids = [
        e["resource"]["id"]
        for e in sched_bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == "Schedule"
    ]

    slots = []
    with httpx.Client(timeout=10) as client:
        for sched_id in schedule_ids:
            slot_resp = client.get(
                f"{settings.fhir_base_url}/Slot",
                headers=_headers(),
                params={
                    "schedule": sched_id,
                    "status": "free",
                    "start": f"ge{start_date}",
                    "end": f"le{end_date}",
                    "_count": "10",
                },
            )
            slot_resp.raise_for_status()
            for entry in slot_resp.json().get("entry", []):
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Slot":
                    slots.append({
                        "slot_fhir_id": resource.get("id"),
                        "start": resource.get("start"),
                        "end": resource.get("end"),
                        "schedule_id": sched_id,
                    })
    return slots


def create_appointment(
    patient_token: str,
    practitioner_fhir_id: str,
    slot_fhir_id: str,
    specialty: str,
) -> dict:
    """Create a FHIR Appointment resource."""
    payload = {
        "resourceType": "Appointment",
        "status": "booked",
        "serviceType": [{"text": specialty}],
        "participant": [
            {
                "actor": {"reference": f"Patient/{patient_token}"},
                "status": "accepted",
            },
            {
                "actor": {"reference": f"Practitioner/{practitioner_fhir_id}"},
                "status": "accepted",
            },
        ],
        "slot": [{"reference": f"Slot/{slot_fhir_id}"}],
    }
    with httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{settings.fhir_base_url}/Appointment",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def _extract_specialty(role: dict) -> str:
    specialties = role.get("specialty", [])
    if specialties:
        codings = specialties[0].get("coding", [])
        if codings:
            return codings[0].get("display", "")
    return ""
