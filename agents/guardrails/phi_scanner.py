"""
PHI/PII detection and redaction using Microsoft Presidio.
Call detect_phi_pii() to find entities, redact_for_llm() to anonymize before LLM calls.
"""
from __future__ import annotations

from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

_PHI_ENTITIES = [
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "US_DRIVER_LICENSE",
    # LOCATION and DATE_TIME are intentionally excluded:
    # city names and date preferences are needed for provider search and scheduling.
    # Actual member address and DOB are never in the user's natural-language request.
    "MEDICAL_LICENSE",
    "IP_ADDRESS",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_BANK_NUMBER",
    "US_PASSPORT",
]


@lru_cache(maxsize=1)
def _get_analyzer() -> AnalyzerEngine:
    return AnalyzerEngine()


@lru_cache(maxsize=1)
def _get_anonymizer() -> AnonymizerEngine:
    return AnonymizerEngine()


def detect_phi_pii(text: str) -> list[RecognizerResult]:
    """Return Presidio recognition results for all PHI/PII entities found in text."""
    return _get_analyzer().analyze(
        text=text,
        language="en",
        entities=_PHI_ENTITIES,
    )


def redact_for_llm(text: str) -> tuple[str, bool]:
    """
    Redact PHI/PII from text before sending to the LLM.

    Returns:
        (redacted_text, phi_was_detected)
    """
    results = detect_phi_pii(text)
    if not results:
        return text, False

    anonymized = _get_anonymizer().anonymize(text=text, analyzer_results=results)
    return anonymized.text, True


def has_phi(text: str) -> bool:
    return bool(detect_phi_pii(text))
