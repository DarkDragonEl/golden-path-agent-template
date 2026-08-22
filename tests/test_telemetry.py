"""R4/DEC-020: agent/telemetry.py::record_invocation_span. Central concern
mirrors eval/domain_scorer.py's own DEC-009 fix -- state["model_calls"]
(a list, not the last-write-wins model_route/model_route_reason_code
scalars) must be the source of truth for per-call route telemetry, so a
routing failure on `decide` isn't silently hidden once `generate` writes
over the scalar fields.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent.telemetry import record_invocation_span  # noqa: E402


class _FakeSpan:
    """Records set_attribute/add_event calls without a real OTel SDK span."""

    def __init__(self):
        self.attributes = {}
        self.events = []

    def set_attribute(self, key, value):
        self.attributes[key] = value

    def add_event(self, name, attributes=None):
        self.events.append((name, attributes or {}))


def _state(**overrides):
    state = {
        "session_id": "sess-1",
        "user_id": "alice",
        "retrieved_docs": [{"doc_id": "PLAT-001"}, {"doc_id": "PLAT-002"}],
        "tool_calls": [],
        "model_calls": [],
        "approval_decision": None,
        "final_output": None,
    }
    state.update(overrides)
    return state


def test_every_model_call_gets_its_own_event_not_just_the_last():
    # The literal regression guard: a decide-then-generate turn makes two
    # model calls; both must be independently visible, not just generate's
    # (which would overwrite decide's route in the old scalar-only design).
    state = _state(
        model_calls=[
            {"node": "decide", "route": "fallback", "reason_code": "primary_5xx",
             "prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            {"node": "generate", "route": "primary", "reason_code": "none",
             "prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        ]
    )
    span = _FakeSpan()
    record_invocation_span(state, span=span)

    model_call_events = [e for e in span.events if e[0] == "model_call"]
    assert len(model_call_events) == 2
    assert model_call_events[0][1]["model_call.node"] == "decide"
    assert model_call_events[0][1]["model_call.route"] == "fallback"
    assert model_call_events[1][1]["model_call.node"] == "generate"
    assert model_call_events[1][1]["model_call.route"] == "primary"
    # decide's fallback route must still be recoverable from the events even
    # though the scalar attribute below reflects only the last call.
    assert span.attributes["model.route"] == "primary"


def test_every_tool_call_gets_its_own_event_with_classification():
    state = _state(
        tool_calls=[
            {"tool_name": "itsm_search_records", "arguments": {}, "result": {}, "error": None, "classification": "read"},
            {"tool_name": "itsm_create_request", "arguments": {}, "result": None, "error": None, "classification": "write"},
        ]
    )
    span = _FakeSpan()
    record_invocation_span(state, span=span)

    tool_call_events = [e for e in span.events if e[0] == "tool_call"]
    assert len(tool_call_events) == 2
    assert tool_call_events[0][1]["tool_call.classification"] == "read"
    assert tool_call_events[1][1]["tool_call.classification"] == "write"
    assert span.attributes["tool_calls.count"] == 2


def test_request_id_and_workload_id_and_prompt_versions_set():
    span = _FakeSpan()
    record_invocation_span(_state(), request_id="req-42", span=span)

    assert span.attributes["request.id"] == "req-42"
    assert span.attributes["session.id"] == "sess-1"
    assert span.attributes["workload.id"]
    assert span.attributes["prompt.decide_version"] != "unknown"
    assert span.attributes["prompt.generate_version"] != "unknown"


def test_final_output_reference_captured_without_full_body_assumption():
    span = _FakeSpan()
    record_invocation_span(_state(final_output="A" * 500), span=span)

    assert span.attributes["final_output.length"] == 500
    assert len(span.attributes["final_output.preview"]) == 200


def test_no_model_calls_falls_back_to_scalar_fields():
    # A run that never made it past a very early failure (or a legacy
    # caller) still gets something sensible on the scalar attributes.
    span = _FakeSpan()
    record_invocation_span(_state(model_route="none", model_route_reason_code="model_failure:X"), span=span)

    assert span.attributes["model.route"] == "none"
    assert span.attributes["model.route_reason_code"] == "model_failure:X"
    assert [e for e in span.events if e[0] == "model_call"] == []
