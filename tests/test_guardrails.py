"""Tests for PHI/PII guardrail nodes."""
import pytest
from unittest.mock import patch, MagicMock

from agents.guardrails.phi_scanner import redact_for_llm, has_phi
from agents.guardrails.response_redaction import response_redaction


class TestPhiScanner:
    def test_redact_person_name(self):
        text = "Find a cardiologist for John Smith near Frisco."
        redacted, detected = redact_for_llm(text)
        assert detected is True
        assert "John Smith" not in redacted

    def test_redact_phone_number(self):
        # Use phone number which Presidio reliably detects
        text = "Call me at 214-555-1234 to confirm."
        redacted, detected = redact_for_llm(text)
        assert detected is True
        assert "214-555-1234" not in redacted

    def test_no_phi_passthrough(self):
        # Location (city) and specialty are intentionally NOT in our PHI entity list
        # so they pass through unredacted for use in provider search
        text = "Find a cardiologist near Frisco who accepts new patients."
        redacted, detected = redact_for_llm(text)
        assert "cardiologist" in redacted
        assert "Frisco" in redacted
        assert detected is False

    def test_has_phi_true(self):
        assert has_phi("My name is John Doe, call me at 214-555-0001") is True

    def test_has_phi_false(self):
        # City and specialty are not flagged as PHI in our configuration
        assert has_phi("Find a cardiologist in Frisco.") is False


class TestResponseRedaction:
    def test_redacts_phi_in_response(self):
        state = {
            "response": "Appointment booked for John Smith on Monday.",
            "status": "scheduled",
        }
        result = response_redaction(state)
        assert "John Smith" not in result["response"]

    def test_empty_response_skipped(self):
        state = {"response": None, "status": "scheduled"}
        result = response_redaction(state)
        assert result["status"] == "redaction_skipped"

    def test_clean_response_unchanged_status(self):
        state = {
            "response": "Your appointment is confirmed at Frisco Clinic.",
            "status": "scheduled",
        }
        result = response_redaction(state)
        assert "Frisco Clinic" in result["response"]
