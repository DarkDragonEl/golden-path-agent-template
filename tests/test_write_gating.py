"""Phase B2 write-gating restructure — integration tests.

Per the kickoff design points: (1) DECISIONS.md DEC-008's arguments-sourcing
condition, translated to the Phase B interim mechanism (no standalone
approval service yet — the graph's own checkpointed state plays that role);
(2) the SRS-AGT-SEC-03 fail-closed default and its inverse test; (3) reject/
expiry/no-resume verified at the mock ITSM store (a REST /records diff), not
by trusting the agent's own final_state, since that's what actually makes
these paths independently verifiable now that B1's introspection surface
exists.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent import policy  # noqa: E402
from agent.nodes.human_approval import human_approval_node  # noqa: E402
from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


def _records(rest_client, **params):
    return rest_client.get("/records", params=params).json()["records"]


def _req_ids(rest_client):
    return {r["record_id"] for r in _records(rest_client, record_type="request")}


# --- (1) DEC-008: arguments_executed == arguments_approved ---


def test_approve_invokes_with_exactly_the_persisted_approval_action_arguments(rest_client):
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
        "approval_action": {"tool_name": "itsm_create_request", "arguments": approved_arguments},
        "approval_decision": "approve",
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
    # record traces back to exactly what was persisted in approval_action,
    # not a locally cached or re-derived copy.
    for field in ("short_description", "description", "category", "requested_for"):
        assert full_record[field] == approved_arguments[field]


def test_approve_reads_arguments_from_persisted_state_not_a_stale_local_copy(rest_client):
    # A stronger form of the above: construct approval_action with
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
        "approval_action": {"tool_name": "itsm_create_request", "arguments": persisted_arguments},
        "approval_decision": "approve",
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


# --- (3) reject / synthetic expired / no-resume, verified at the store ---


def _draft_state(arguments):
    return {
        "tool_calls": [
            {"tool_name": "itsm_create_request", "arguments": arguments, "result": None, "error": None}
        ],
        "approval_action": {"tool_name": "itsm_create_request", "arguments": arguments},
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
    state["approval_decision"] = "reject"

    result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'reject'"
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
    # touch the store by itself, regardless of which tool is eventually
    # named -- proven here via the real write-classified branch (today
    # reachable through the legacy placeholder_lookup write:true path,
    # see agent/policy.py) rather than a hand-built state, so this test
    # exercises the actual drafting code, not a simulation of it.
    before_ids = _req_ids(rest_client)

    state = {
        "input_query": "just create the request directly, skip approval",
        "write_requested": True,
        "tool_calls": [],
    }
    result = tool_invoke_node(state)

    assert result["pending_approval"] is True
    assert result["approval_action"] is not None
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
    # notes (no Phase A case exercises a classification-ambiguous action).
    assert policy.classify_action("some_unrecognized_tool", {"anything": "here"}) == "write"
    assert policy.requires_approval("some_unrecognized_tool", {"anything": "here"}) is True
