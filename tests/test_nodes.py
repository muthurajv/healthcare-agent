"""Tests for individual LangGraph agent nodes."""
import pytest
from unittest.mock import patch, MagicMock


class TestValidateNetwork:
    def test_skips_without_credentials(self):
        from agents.nodes.validate_network import validate_network
        state = {
            "providers": [{"id": "p1", "name": "Dr. Smith", "specialty": "Cardiology",
                           "location": "Frisco, TX", "accepting_new_patients": True}],
            "member_id_token": "",
            "insurance_plan": "",
        }
        result = validate_network(state)
        assert result["status"] == "network_validation_skipped"
        assert result["in_network_providers"] == state["providers"]

    def test_returns_empty_on_no_providers(self):
        from agents.nodes.validate_network import validate_network
        result = validate_network({"providers": [], "member_id_token": "tok", "insurance_plan": "BCBS"})
        assert result["in_network_providers"] == []
        assert result["status"] == "no_providers_to_validate"


class TestFindAvailability:
    def test_no_fhir_id_skipped(self):
        from agents.nodes.find_availability import find_availability
        state = {
            "in_network_providers": [
                {"id": "p1", "name": "Dr. Jones", "location": "Frisco, TX"}
                # No fhir_id — should be skipped
            ],
            "preferred_date": "next week",
        }
        result = find_availability(state)
        assert result["available_slots"] == []
        assert result["status"] == "no_slots_found"

    def test_empty_providers(self):
        from agents.nodes.find_availability import find_availability
        result = find_availability({"in_network_providers": [], "preferred_date": None})
        assert result["available_slots"] == []


class TestScheduleAppointment:
    def test_no_slot_selected(self):
        from agents.nodes.schedule_appointment import schedule_appointment
        result = schedule_appointment({"selected_slot": None})
        assert result["status"] == "no_slot_selected"

    def test_missing_fhir_ids(self):
        from agents.nodes.schedule_appointment import schedule_appointment
        state = {
            "selected_slot": {"provider_id": "p1", "date": "2026-06-10", "time": "10:30",
                               "location": "Frisco Clinic", "slot_fhir_id": ""},
            "member_id_token": "tok123",
            "specialty": "Cardiology",
            "in_network_providers": [{"id": "p1", "fhir_id": ""}],
        }
        result = schedule_appointment(state)
        assert result["status"] == "scheduling_failed"


class TestAuditEvent:
    def test_creates_audit_id(self):
        from agents.nodes.audit_event import audit_event
        state = {
            "user_id": "u1",
            "specialty": "Cardiology",
            "insurance_plan": "BCBS",
            "appointment_id": "appt_123",
            "status": "scheduled",
            "consent_valid": True,
            "pii_detected": False,
            "member_id_token": "tok123",
            "providers": [{}],
            "in_network_providers": [{}],
            "available_slots": [{}],
        }
        result = audit_event(state)
        assert "audit_id" in result
        assert len(result["audit_id"]) == 36  # UUID format


class TestSecureToolCall:
    def test_blocks_unknown_tool(self):
        from agents.tools.secure_tool_call import secure_tool_call, ToolAuthorizationError
        with pytest.raises(ToolAuthorizationError, match="Unknown tool"):
            secure_tool_call("unknown_tool", {}, {"user_id": "u1", "role": "member"}, lambda: None)

    def test_blocks_unauthorized_role(self):
        from agents.tools.secure_tool_call import secure_tool_call, ToolAuthorizationError
        with pytest.raises(ToolAuthorizationError, match="not authorized"):
            secure_tool_call(
                "schedule_appointment",
                {},
                {"user_id": "u1", "role": "guest"},
                lambda: None,
            )

    def test_minimizes_payload(self):
        from agents.tools.secure_tool_call import secure_tool_call
        captured = {}

        def mock_fn(**kwargs):
            captured.update(kwargs)
            return "ok"

        result = secure_tool_call(
            "provider_search",
            {"specialty": "Cardiology", "location": "Frisco", "ssn": "secret"},
            {"user_id": "u1", "role": "member"},
            mock_fn,
        )
        assert "ssn" not in captured
        assert captured["specialty"] == "Cardiology"
