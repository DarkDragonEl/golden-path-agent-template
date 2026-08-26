"""agent/cli.py's --decision round-trip through the approval service.

Regression test for the fix that replaced a direct
`graph.update_state(thread_config, {"approval_decision": decision})` call
with a real `approval_client.decide_proposal` + `resolve_and_resume`
sequence -- the same one `agent/api.py`'s `/resume` endpoint uses. The
old code was silently ignored by `agent/nodes/human_approval.py` (DEC-049:
a tool call is only ever authorized when `approved_action` is set, and
that field is set only by `resolve_and_resume`), so a CLI `--decision
approve` had the exact same effect as `--decision reject`.
"""

import json
import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

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
    ):
        mock_submit.return_value = {"proposal_id": _PROPOSAL_ID, "state": "pending"}
        mock_get.return_value = terminal_proposal
        cli.main()

    result = json.loads(capsys.readouterr().out)
    return result, mock_decide


def test_decision_approve_actually_invokes_the_tool(capsys, monkeypatch):
    result, mock_decide = _run_cli(
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

    mock_decide.assert_called_once_with(_PROPOSAL_ID, "approve")
    assert result["pending_approval"] is False
    assert result.get("fallback_reason") is None
    assert result["final_output"] is not None


def test_decision_reject_never_invokes_the_tool(capsys, monkeypatch):
    result, mock_decide = _run_cli(
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
    # No tool was ever invoked: the write-classified tool_calls entry
    # drafted by tool_invoke_node still shows no result.
    write_calls = [c for c in result["tool_calls"] if c["tool_name"] == "placeholder_write_action"]
    assert len(write_calls) == 1
    assert write_calls[0]["result"] is None
