"""Unit tests for eval/domain_scorer.py::check_dec009_route_assertion,
ADR-002's compensating control, rewritten under the ADR-005
candidate (decide-then-retrieve reordering) to read state["model_calls"]
(a list, one entry per model call this turn) instead of the single-call
scalar fields model_route/model_route_reason_code -- previously only
exercised indirectly through full domain-case runs.
"""

from types import SimpleNamespace

from eval.domain_scorer import check_dec009_route_assertion


def _case(category="knowledge_qa", **input_fields):
    return SimpleNamespace(category=category, input=input_fields)


def test_passes_when_all_calls_primary_none():
    state = {
        "model_calls": [
            {"node": "decide", "route": "primary", "reason_code": "none"},
            {"node": "generate", "route": "primary", "reason_code": "none"},
        ]
    }
    ok, detail = check_dec009_route_assertion(state, _case())
    assert ok is True
    assert "2 model call" in detail


def test_fails_when_any_call_is_fallback():
    state = {
        "model_calls": [
            {"node": "decide", "route": "fallback", "reason_code": "primary_5xx"},
            {"node": "generate", "route": "primary", "reason_code": "none"},
        ]
    }
    ok, detail = check_dec009_route_assertion(state, _case())
    assert ok is False
    assert "decide" in detail
    assert "fallback" in detail


def test_fails_when_model_calls_missing_entirely():
    ok, detail = check_dec009_route_assertion({}, _case())
    assert ok is False
    assert "instrumentation gap" in detail


def test_operational_model_failure_case_is_exempt():
    state = {"model_calls": []}
    ok, detail = check_dec009_route_assertion(state, _case(category="operational", fault="model_failure"))
    assert ok is True
    assert "exempt" in detail
