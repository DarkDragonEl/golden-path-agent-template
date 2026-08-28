"""Phase D4 -- approval_service/telemetry.py::record_transition_span, the
attribute-correlation mechanism (ADR-006). Mirrors
tests/test_telemetry.py's own _FakeSpan pattern for agent/telemetry.py.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from approval_service.telemetry import record_transition_span  # noqa: E402


class _FakeSpan:
    def __init__(self):
        self.attributes = {}

    def set_attribute(self, key, value):
        self.attributes[key] = value


def _record(**overrides):
    record = {
        "proposal_id": "prop-1",
        "originating_session_id": "sess-1",
        "originating_request_id": "req-1",
        "state": "pending",
        "action_type": "itsm_create_request",
        "decided_by": None,
    }
    record.update(overrides)
    return record


def test_transition_span_sets_correlation_attributes():
    span = _FakeSpan()
    record_transition_span("proposal_intake", _record(), span=span)
    assert span.attributes["proposal.id"] == "prop-1"
    assert span.attributes["session.id"] == "sess-1"
    assert span.attributes["request.id"] == "req-1"
    assert span.attributes["approval.event"] == "proposal_intake"
    assert span.attributes["approval.state"] == "pending"
    assert span.attributes["approval.action_type"] == "itsm_create_request"
    assert span.attributes["approval.decided_by"] == ""


def test_transition_span_carries_decided_by_once_terminal():
    span = _FakeSpan()
    record_transition_span("proposal_decided", _record(state="approved", decided_by="fb790f55-..."), span=span)
    assert span.attributes["approval.state"] == "approved"
    assert span.attributes["approval.decided_by"] == "fb790f55-..."
