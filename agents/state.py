from typing import Any, Optional
from typing_extensions import TypedDict


class ProviderSlot(TypedDict):
    provider_id: str
    date: str
    time: str
    location: str


class Provider(TypedDict):
    id: str
    name: str
    specialty: str
    location: str
    accepting_new_patients: bool
    npi: Optional[str]
    fhir_id: Optional[str]


class AppointmentState(TypedDict, total=False):
    # Raw and sanitized input
    user_request: str
    safe_request: str          # PHI-redacted version sent to LLM

    # Guardrail flags
    pii_detected: bool
    phi_detected: bool
    consent_valid: bool

    # Parsed intent (LLM output — no PHI)
    specialty: Optional[str]
    location: Optional[str]
    insurance_plan: Optional[str]
    preferred_date: Optional[str]
    gender_preference: Optional[str]
    language_preference: Optional[str]

    # Secure references (tokens, not raw PHI)
    member_id_token: Optional[str]   # opaque token for eligibility API calls
    user_id: Optional[str]

    # Agent results
    providers: list[Provider]
    in_network_providers: list[Provider]
    available_slots: list[ProviderSlot]
    selected_slot: Optional[ProviderSlot]

    # Booking
    appointment_id: Optional[str]

    # LLM usage metadata (for observability — no PHI)
    llm_usage: dict[str, Any]

    # Response to user
    response: Optional[str]

    # Audit
    audit_id: Optional[str]

    # Current workflow status
    status: str
