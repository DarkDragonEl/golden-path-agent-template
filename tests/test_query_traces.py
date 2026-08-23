"""Phase D4 -- tools/query_traces.py's own parsing/filtering logic, pure
function, no live collector needed."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.query_traces import find_matching_records  # noqa: E402


def _span(name, service, attributes, start_ns=1000, events=None):
    return json.dumps(
        {
            "resourceSpans": [
                {
                    "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": service}}]},
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "name": name,
                                    "startTimeUnixNano": str(start_ns),
                                    "attributes": [
                                        {"key": k, "value": {"stringValue": v}} for k, v in attributes.items()
                                    ],
                                    "events": events or [],
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    )


def test_filters_by_session_id():
    lines = [
        _span("agent.invoke", "golden-path-agent", {"session.id": "sess-1"}),
        _span("agent.invoke", "golden-path-agent", {"session.id": "sess-2"}),
    ]
    records = find_matching_records(lines, session_id="sess-1", proposal_id=None)
    assert len(records) == 1
    assert records[0]["name"] == "agent.invoke"


def test_filters_by_proposal_id():
    lines = [
        _span("approval.decide_proposal", "golden-path-agent-approval", {"proposal.id": "prop-1"}),
        _span("approval.decide_proposal", "golden-path-agent-approval", {"proposal.id": "prop-2"}),
    ]
    records = find_matching_records(lines, session_id=None, proposal_id="prop-1")
    assert len(records) == 1


def test_events_included_when_parent_span_matches():
    lines = [
        _span(
            "agent.invoke",
            "golden-path-agent",
            {"session.id": "sess-1"},
            events=[{"name": "model_call", "timeUnixNano": "1500", "attributes": [{"key": "model_call.route", "value": {"stringValue": "primary"}}]}],
        )
    ]
    records = find_matching_records(lines, session_id="sess-1", proposal_id=None)
    kinds = {r["kind"] for r in records}
    assert kinds == {"span", "event"}


def test_results_sorted_chronologically_across_multiple_lines():
    lines = [
        _span("approval.decide_proposal", "golden-path-agent-approval", {"session.id": "sess-1"}, start_ns=5000),
        _span("agent.invoke", "golden-path-agent", {"session.id": "sess-1"}, start_ns=1000),
    ]
    records = find_matching_records(lines, session_id="sess-1", proposal_id=None)
    assert [r["name"] for r in records] == ["agent.invoke", "approval.decide_proposal"]


def test_no_match_returns_empty_list():
    lines = [_span("agent.invoke", "golden-path-agent", {"session.id": "sess-1"})]
    assert find_matching_records(lines, session_id="not-there", proposal_id=None) == []
