"""tool_invoke_node's dispatch is fully driven by
state["selected_tool"] (set by decide_node) -- no hardcoded tool name
anywhere in this node. These tests cover the shapes selected_tool can
take on this node's actual precondition (never None -- under the
decide-then-retrieve reordering, agent/routers.py's decide_after_decide
routes the None case to retrieve/generate instead), independent of
tests/test_write_gating.py's write-gating focus.
"""

import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "live")

from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


def test_selected_tool_read_classified_executes_eagerly():
    state = {
        "selected_tool": {"tool_name": "itsm_search_records", "arguments": {"record_type": "incident", "record_id": "INC-10255"}},
        "tool_calls": [],
    }
    # This repo never bundles
    # mcp_server/server.py -- patched at the tool-execution boundary,
    # matching test_write_gating.py's own fix. Return value mirrors the
    # real seeded INC-10255 record (mcp_server/itsm_store.py) exactly,
    # since this test asserts on its real "resolved" status field.
    mock_response = {
        "records": [
            {
                "record_id": "INC-10255",
                "record_type": "incident",
                "status": "resolved",
                "short_description": "Ingress certificate auto-renewal failure on staging cluster",
                "owner_team": "platform-networking",
            }
        ],
        "count": 1,
        "source": "mock-itsm",
    }
    with patch("agent.nodes.tool_invoke.call_tool", return_value=mock_response):
        result = tool_invoke_node(state)

    assert result["pending_approval"] is False
    assert result["drafted_action"] is None
    assert result["approved_action"] is None
    assert "resolved" in result["final_output"]
    assert result["tool_calls"][-1]["tool_name"] == "itsm_search_records"
    assert result["tool_calls"][-1]["result"] is not None


def test_selected_tool_write_classified_drafts_without_executing():
    state = {
        "session_id": "sess-1",
        "request_id": "req-1",
        "user_id": "kim",
        "selected_tool": {
            "tool_name": "itsm_create_request",
            "arguments": {
                "short_description": "x",
                "description": "x",
                "category": "access",
                "requested_for": "kim",
            },
        },
        "tool_calls": [],
    }
    # tool_invoke_node's write branch submits a real
    # proposal to the approval service -- patched here (no running service
    # in this unit test), mirroring eval/domain_executor.py's own
    # _FakeApprovalService pattern for the same reason.
    with patch("agent.nodes.tool_invoke.approval_client.submit_proposal") as mock_submit:
        mock_submit.return_value = {"proposal_id": "prop-1", "state": "pending"}
        result = tool_invoke_node(state)

    assert result["pending_approval"] is True
    assert result["proposal_id"] == "prop-1"
    assert result["drafted_action"] == state["selected_tool"]
    mock_submit.assert_called_once()
    assert mock_submit.call_args.kwargs["action_arguments"] == state["selected_tool"]["arguments"]
    # Drafted, not executed -- the tool_calls entry records no result yet.
    assert result["tool_calls"][-1]["result"] is None
    assert result["tool_calls"][-1]["error"] is None
