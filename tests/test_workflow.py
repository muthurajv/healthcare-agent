"""Integration-level tests for the LangGraph workflow graph structure."""
import pytest
from unittest.mock import patch, MagicMock


class TestWorkflowGraph:
    def test_graph_compiles(self):
        """Verify the graph compiles without errors."""
        from agents.workflow import build_graph
        from langgraph.checkpoint.memory import MemorySaver
        graph = build_graph(checkpointer=MemorySaver())
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        from agents.workflow import build_graph
        from langgraph.checkpoint.memory import MemorySaver
        graph = build_graph(checkpointer=MemorySaver())
        node_names = set(graph.nodes.keys())
        expected = {
            "input_phi_scan", "consent_check", "parse_request",
            "search_providers", "validate_network", "find_availability",
            "confirm_with_user", "schedule_appointment", "send_notification",
            "audit_event", "response_redaction",
        }
        assert expected.issubset(node_names)

    def test_consent_denied_skips_to_redaction(self):
        """When consent is denied the workflow should not call parse_request."""
        from agents.workflow import _route_after_consent
        state = {"consent_valid": False, "status": "consent_denied"}
        assert _route_after_consent(state) == "response_redaction"

    def test_consent_granted_routes_to_parse(self):
        from agents.workflow import _route_after_consent
        state = {"consent_valid": True, "status": "consent_validated"}
        assert _route_after_consent(state) == "parse_request"

    def test_no_providers_routes_to_audit(self):
        from agents.workflow import _route_after_providers
        assert _route_after_providers({"providers": []}) == "audit_event"
        assert _route_after_providers({"providers": [{}]}) == "validate_network"

    def test_no_network_routes_to_audit(self):
        from agents.workflow import _route_after_network
        assert _route_after_network({"in_network_providers": []}) == "audit_event"
        assert _route_after_network({"in_network_providers": [{}]}) == "find_availability"

    def test_no_slots_routes_to_audit(self):
        from agents.workflow import _route_after_availability
        assert _route_after_availability({"available_slots": []}) == "audit_event"
        assert _route_after_availability({"available_slots": [{}]}) == "confirm_with_user"


class TestSpanHelpers:
    def test_safe_zip3(self):
        from observability.span_helpers import safe_zip3
        assert safe_zip3("75034") == "750"
        assert safe_zip3("") == ""
        assert safe_zip3("90") == "90"  # short ZIP — return as-is (no crash)
