"""Write-gating integration tests, against the standalone-approval-service
model of ADR-001:
human_approval_node now reads approved_action/approval_decision, both of
which are only ever populated by agent/approval_client.py::resolve_and_resume
from the approval service's own IF-05 response -- these unit tests
construct that already-resolved state directly (simulating what
resolve_and_resume would have injected), exercising the node's own
execution behavior in isolation.

Per the kickoff design points: (1) ADR-001's arguments-sourcing
condition -- the agent executes exactly the arguments the approval
service's terminal-state query returned, never a locally cached draft;
(2) the SRS-AGT-SEC-03 fail-closed default and its inverse test; (3) reject/
expiry/no-resume verified at the mock ITSM store (a REST /records diff), not
by trusting the agent's own final_state, since that's what actually makes
these paths independently verifiable now that B1's introspection surface
exists.
"""

import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent import policy  # noqa: E402
from agent.nodes.human_approval import human_approval_node  # noqa: E402
from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


def _records(rest_client, **params):
    return rest_client.get("/records", params=params).json()["records"]


def _req_ids(rest_client):
    return {r["record_id"] for r in _records(rest_client, record_type="request")}


# --- (1) ADR-001: arguments_executed == arguments_approved ---


def test_approve_invokes_with_exactly_the_persisted_approved_action_arguments(rest_client):
    before_ids = _req_ids(rest_client)

    approved_arguments = {
        "short_description": "VPN access for new hire",
        "description": "New hire on the platform team needs VPN access.",
        "category": "access",
        "requested_for": "frank",
    }
    state = {
        "tool_calls": [
            {
                "tool_name": "itsm_create_request",
                "arguments": approved_arguments,
                "result": None,
                "error": None,
            }
        ],
        "approved_action": {"tool_name": "itsm_create_request", "arguments": approved_arguments},
        "approval_decision": "approved",
    }

    result = human_approval_node(state)

    # Agent-side state is corroborating evidence, checked first but not
    # the primary check (design point 3).
    assert result["pending_approval"] is False
    assert result.get("fallback_reason") is None

    # Primary check: the store's own state, via REST -- the same surface
    # T-04..T-08 use.
    after_ids = _req_ids(rest_client)
    new_ids = after_ids - before_ids
    assert len(new_ids) == 1
    created_id = new_ids.pop()

    full_record = rest_client.get(f"/records/{created_id}").json()
    # arguments_executed == arguments_approved: every field on the created
    # record traces back to exactly what was persisted in approved_action,
    # not a locally cached or re-derived copy.
    for field in ("short_description", "description", "category", "requested_for"):
        assert full_record[field] == approved_arguments[field]


def test_approve_reads_arguments_from_persisted_state_not_a_stale_local_copy(rest_client):
    # A stronger form of the above: construct approved_action with
    # arguments that differ from what a naively-recomputed draft would
    # produce, proving human_approval_node genuinely reads the persisted
    # record rather than recomputing anything.
    persisted_arguments = {
        "short_description": "Persisted description, not recomputed",
        "description": "This exact text must appear on the created record.",
        "category": "information",
        "requested_for": "grace",
    }
    state = {
        "tool_calls": [],
        "approved_action": {"tool_name": "itsm_create_request", "arguments": persisted_arguments},
        "approval_decision": "approved",
    }

    result = human_approval_node(state)
    assert result["pending_approval"] is False

    matches = [
        r
        for r in _records(rest_client, record_type="request")
        if r["short_description"] == "Persisted description, not recomputed"
    ]
    assert len(matches) == 1
    full_record = rest_client.get(f"/records/{matches[0]['record_id']}").json()
    assert full_record["description"] == persisted_arguments["description"]
    assert full_record["requested_for"] == "grace"


def test_execution_uses_approved_action_not_drafted_action_when_they_diverge(rest_client):
    # ADR-025's own mutated-draft regression test: drafted_action (what
    # tool_invoke_node originally proposed) and approved_action (what
    # resolve_and_resume's IF-05 query actually returned) deliberately
    # differ here -- a stronger proof than equality alone, since two
    # identical values would trivially match even if execution read the
    # wrong field. Only approved_action's arguments may ever reach the
    # store.
    before_ids = _req_ids(rest_client)
    drafted_arguments = {
        "short_description": "DRAFTED -- must never reach the store",
        "description": "If this text appears on a created record, execution read the wrong field.",
        "category": "access",
        "requested_for": "mallory",
    }
    approved_arguments = {
        "short_description": "APPROVED -- the only value execution may use",
        "description": "This is the IF-05-sourced value.",
        "category": "access",
        "requested_for": "mallory",
    }
    state = {
        "tool_calls": [],
        "drafted_action": {"tool_name": "itsm_create_request", "arguments": drafted_arguments},
        "approved_action": {"tool_name": "itsm_create_request", "arguments": approved_arguments},
        "approval_decision": "approved",
    }

    result = human_approval_node(state)
    assert result["pending_approval"] is False

    after_ids = _req_ids(rest_client)
    new_ids = after_ids - before_ids
    assert len(new_ids) == 1
    full_record = rest_client.get(f"/records/{new_ids.pop()}").json()
    assert full_record["short_description"] == approved_arguments["short_description"]
    assert full_record["short_description"] != drafted_arguments["short_description"]


# --- (3) reject / synthetic expired / no-resume, verified at the store ---


def _draft_state(arguments):
    return {
        "tool_calls": [
            {"tool_name": "itsm_create_request", "arguments": arguments, "result": None, "error": None}
        ],
        "drafted_action": {"tool_name": "itsm_create_request", "arguments": arguments},
    }


def test_reject_creates_no_new_request_record(rest_client):
    before_ids = _req_ids(rest_client)
    state = _draft_state(
        {
            "short_description": "Should never be created",
            "description": "Rejected before execution.",
            "category": "access",
            "requested_for": "henry",
        }
    )
    state["approval_decision"] = "rejected"

    result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'rejected'"
    # Primary check: the store, not the agent's own report of what happened.
    assert _req_ids(rest_client) == before_ids


def test_synthetic_expired_creates_no_new_request_record(rest_client):
    before_ids = _req_ids(rest_client)
    state = _draft_state(
        {
            "short_description": "Should never be created (expired)",
            "description": "Expired before a decision was rendered.",
            "category": "access",
            "requested_for": "iris",
        }
    )
    state["approval_decision"] = "expired"

    result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'expired'"
    assert _req_ids(rest_client) == before_ids


def test_no_resume_bypass_attempt_creates_no_new_request_record(rest_client):
    # UAW-003/UAW-004/UAW-006 (bypass_attempt / not_requested): the policy
    # forces the approval path despite the caller's request to skip it, and
    # no decision is ever rendered -- human_approval_node is never even
    # invoked. tool_invoke_node's write branch (the draft step) must not
    # touch the store by itself. tool_invoke_node's
    # hardcoded dispatch was retired -- it now reads state["selected_tool"], set by
    # reason_node (real tool_calls in live mode, a legacy simulation in
    # fake mode) -- so this test drives the real write-classified branch
    # directly against the real itsm_create_request tool, exercising the
    # actual drafting code, not a simulation of it.
    before_ids = _req_ids(rest_client)

    state = {
        "session_id": "sess-bypass",
        "request_id": "req-bypass",
        "user_id": "jules",
        "selected_tool": {
            "tool_name": "itsm_create_request",
            "arguments": {
                "short_description": "Should never be created (bypass attempt)",
                "description": "Policy forced the approval path; no decision is ever rendered.",
                "category": "access",
                "requested_for": "jules",
            },
        },
        "tool_calls": [],
    }
    with patch("agent.nodes.tool_invoke.approval_client.submit_proposal") as mock_submit:
        mock_submit.return_value = {"proposal_id": "prop-bypass", "state": "pending"}
        result = tool_invoke_node(state)

    assert result["pending_approval"] is True
    assert result["drafted_action"] is not None
    # No resume call follows -- this is the whole point of the scenario.
    assert _req_ids(rest_client) == before_ids


# --- (2) SRS-AGT-SEC-03 fail-closed default: inverse test ---


def test_unrecognized_tool_classifies_as_write_and_would_pause():
    # This is the exact predicate tool_invoke_node's read/write branch
    # depends on (`policy.classify_action(...) != "write"` => execute
    # eagerly; otherwise => draft and pause). An unrecognized tool name
    # fails closed to "write", so a hypothetical call to it would take the
    # draft-and-pause branch, never the eager-execution one -- this is the
    # eval-set gap srs/SRS-AGT.md's own Verification table for SEC-03
    # notes (no eval case exercises a classification-ambiguous action).
    assert policy.classify_action("some_unrecognized_tool", {"anything": "here"}) == "write"
    assert policy.requires_approval("some_unrecognized_tool", {"anything": "here"}) is True
