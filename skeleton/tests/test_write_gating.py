"""Write-gating integration tests. human_approval_node reads
approved_action/approval_decision, both of which are only ever populated
by agent/approval_client.py::resolve_and_resume from the approval
service's own IF-05 response -- these unit tests construct that
already-resolved state directly (simulating what resolve_and_resume would
have injected), exercising the node's own execution behavior in
isolation.

Per the kickoff design points: (1) the arguments-sourcing condition --
the agent executes exactly the arguments the approval service's
terminal-state query returned, never a locally cached draft; (2) the
SRS-AGT-SEC-03 fail-closed default and its inverse test; (3) reject/
expiry/no-resume verified by asserting the tool-execution boundary
(mcp_server.client.call_tool) is never invoked, not by trusting the
agent's own final_state.

Rewritten from a live-store-round-trip shape (an in-process
TestClient(build_app()) + REST /records introspection) to a mocked
call_tool boundary. The Agent Template no longer bundles mcp_server's
server implementation at all (only client.py -- the amended SysR-P-F-01
forbids bundling tool-server source), so an in-process FastAPI+MCP app is
no longer something this repo's own test suite can construct. This is not
a downgrade: the actual invariant under test is "the agent calls the tool
with exactly the approved arguments," which asserting directly on
call_tool's own call arguments proves more precisely than a store
round-trip ever did (the store's own create-request response never echoed
the input fields back at all -- the original test's field-by-field
comparison depended on a *second*, separate GET, an indirect proxy for
the same fact this file now asserts directly).
"""

import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "live")

from agent import policy  # noqa: E402
from agent.nodes.human_approval import human_approval_node  # noqa: E402
from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


# --- (1) arguments_executed == arguments_approved ---


def test_approve_invokes_with_exactly_the_persisted_approved_action_arguments():
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

    with patch("agent.nodes.human_approval.call_tool") as mock_call_tool:
        mock_call_tool.return_value = {"record_id": "REQ-99001", "status": "submitted", "source": "mock-itsm"}
        result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result.get("fallback_reason") is None

    # Primary check: exactly one call, with exactly the approved arguments --
    # not a re-derived or locally cached copy.
    mock_call_tool.assert_called_once()
    called_tool_name, called_arguments = mock_call_tool.call_args.args[:2]
    assert called_tool_name == "itsm_create_request"
    assert called_arguments == approved_arguments


def test_approve_reads_arguments_from_persisted_state_not_a_stale_local_copy():
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

    with patch("agent.nodes.human_approval.call_tool") as mock_call_tool:
        mock_call_tool.return_value = {"record_id": "REQ-99002", "status": "submitted", "source": "mock-itsm"}
        result = human_approval_node(state)

    assert result["pending_approval"] is False
    called_arguments = mock_call_tool.call_args.args[1]
    assert called_arguments["description"] == persisted_arguments["description"]
    assert called_arguments["requested_for"] == "grace"


def test_execution_uses_approved_action_not_drafted_action_when_they_diverge():
    # Mutated-draft regression test: drafted_action (what
    # tool_invoke_node originally proposed) and approved_action (what
    # resolve_and_resume's IF-05 query actually returned) deliberately
    # differ here -- a stronger proof than equality alone, since two
    # identical values would trivially match even if execution read the
    # wrong field. Only approved_action's arguments may ever reach
    # call_tool.
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

    with patch("agent.nodes.human_approval.call_tool") as mock_call_tool:
        mock_call_tool.return_value = {"record_id": "REQ-99003", "status": "submitted", "source": "mock-itsm"}
        result = human_approval_node(state)

    assert result["pending_approval"] is False
    called_arguments = mock_call_tool.call_args.args[1]
    assert called_arguments["short_description"] == approved_arguments["short_description"]
    assert called_arguments["short_description"] != drafted_arguments["short_description"]


# --- (3) reject / synthetic expired / no-resume, verified at the call_tool boundary ---


def _draft_state(arguments):
    return {
        "tool_calls": [
            {"tool_name": "itsm_create_request", "arguments": arguments, "result": None, "error": None}
        ],
        "drafted_action": {"tool_name": "itsm_create_request", "arguments": arguments},
    }


def test_reject_creates_no_new_request_record():
    state = _draft_state(
        {
            "short_description": "Should never be created",
            "description": "Rejected before execution.",
            "category": "access",
            "requested_for": "henry",
        }
    )
    state["approval_decision"] = "rejected"

    with patch("agent.nodes.human_approval.call_tool") as mock_call_tool:
        result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'rejected'"
    # Primary check: the tool-execution boundary itself, not the agent's
    # own report of what happened.
    mock_call_tool.assert_not_called()


def test_synthetic_expired_creates_no_new_request_record():
    state = _draft_state(
        {
            "short_description": "Should never be created (expired)",
            "description": "Expired before a decision was rendered.",
            "category": "access",
            "requested_for": "iris",
        }
    )
    state["approval_decision"] = "expired"

    with patch("agent.nodes.human_approval.call_tool") as mock_call_tool:
        result = human_approval_node(state)

    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'expired'"
    mock_call_tool.assert_not_called()


def test_no_resume_bypass_attempt_creates_no_new_request_record():
    # UAW-003/UAW-004/UAW-006 (bypass_attempt / not_requested): the policy
    # forces the approval path despite the caller's request to skip it, and
    # no decision is ever rendered -- human_approval_node is never even
    # invoked. tool_invoke_node's write branch (the draft step) must not
    # call the tool-execution boundary by itself. tool_invoke_node's
    # hardcoded dispatch was retired -- it now reads
    # state["selected_tool"], set by reason_node (real tool_calls in live
    # mode, a legacy simulation in fake mode) -- so this test drives the
    # real write-classified branch directly against the real
    # itsm_create_request tool, exercising the actual drafting code, not a
    # simulation of it.
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
    with (
        patch("agent.nodes.tool_invoke.approval_client.submit_proposal") as mock_submit,
        patch("agent.nodes.tool_invoke.call_tool") as mock_call_tool,
    ):
        mock_submit.return_value = {"proposal_id": "prop-bypass", "state": "pending"}
        result = tool_invoke_node(state)

    assert result["pending_approval"] is True
    assert result["drafted_action"] is not None
    # No execution call follows -- this is the whole point of the scenario.
    mock_call_tool.assert_not_called()


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
