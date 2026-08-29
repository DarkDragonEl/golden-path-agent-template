"""agent/cli.py's --decision round-trip through the approval service.

Regression test: agent/cli.py's --decision path must round-trip through
approval_client.decide_proposal + resolve_and_resume, the same sequence
agent/api.py's /resume endpoint uses -- human_approval_node only
authorizes execution once approved_action is set, and only
resolve_and_resume ever sets it, so a CLI --decision approve that instead
mutated local graph state directly would have the exact same effect as
--decision reject. This asserts decide_proposal and resolve_and_resume
are actually called, not just that the CLI runs to completion.

The Agent Template no longer bundles mcp_server's server implementation
(only client.py), so the tool-execution boundary (mcp_server.client.call_tool,
imported into agent/nodes/human_approval.py) is mocked directly rather
than relying on a real in-process MCP server, matching
tests/test_write_gating.py's own MCP_MODE=live convention.
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "live")

from agent import cli  # noqa: E402

_QUERY = "submit a write request"
_PROPOSAL_ID = "prop-cli-test"


def _run_cli(capsys, monkeypatch, session_id, decision, terminal_proposal):
    monkeypatch.setattr(
        "sys.argv",
        ["agent.cli", _QUERY, "--write", "--session-id", session_id, "--decision", decision],
    )
    with (
        patch("agent.nodes.tool_invoke.approval_client.submit_proposal") as mock_submit,
        patch("agent.cli.approval_client.decide_proposal") as mock_decide,
        patch("agent.approval_client.get_proposal") as mock_get,
        patch("agent.nodes.human_approval.call_tool") as mock_call_tool,
    ):
        mock_submit.return_value = {"proposal_id": _PROPOSAL_ID, "state": "pending"}
        mock_get.return_value = terminal_proposal
        mock_call_tool.return_value = {"record_id": "REQ-99010", "status": "submitted", "source": "mock-itsm"}
        cli.main()

    result = json.loads(capsys.readouterr().out)
    return result, mock_decide, mock_call_tool


def test_decision_approve_calls_decide_proposal_and_resolve_and_resume(capsys, monkeypatch):
    result, mock_decide, mock_call_tool = _run_cli(
        capsys,
        monkeypatch,
        "cli-test-approve",
        "approve",
        {
            "state": "approved",
            "action_arguments": {"query": _QUERY},
            "decided_by": "test-approver",
            "decided_at": "2026-01-01T00:00:00Z",
        },
    )

    # Primary check: cli.py actually round-trips through the real
    # approval-service client, not local state mutation.
    mock_decide.assert_called_once_with(_PROPOSAL_ID, "approve")
    assert result["pending_approval"] is False
    assert result.get("fallback_reason") is None
    # resolve_and_resume's own effect: the tool-execution boundary was
    # reached, using resolve_and_resume's injected approved_action, not
    # a value cli.py computed itself.
    mock_call_tool.assert_called_once()


def test_decision_reject_never_reaches_the_tool_execution_boundary(capsys, monkeypatch):
    result, mock_decide, mock_call_tool = _run_cli(
        capsys,
        monkeypatch,
        "cli-test-reject",
        "reject",
        {
            "state": "rejected",
            "action_arguments": None,
            "decided_by": "test-approver",
            "decided_at": "2026-01-01T00:00:00Z",
        },
    )

    mock_decide.assert_called_once_with(_PROPOSAL_ID, "reject")
    assert result["pending_approval"] is False
    assert result["fallback_reason"] == "approval_not_granted:'rejected'"
    # No tool was ever invoked -- the regression this test guards
    # against is exactly a reject silently behaving like an approve.
    mock_call_tool.assert_not_called()
