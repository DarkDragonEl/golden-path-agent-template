"""Phase B3: tool_invoke_node's dispatch is fully driven by
state["selected_tool"] (set by decide_node) -- no hardcoded tool name
anywhere in this node. These tests cover the shapes selected_tool can
take on this node's actual precondition (never None -- see DEC-013
candidate: decide-then-retrieve reordering, agent/routers.py's
decide_after_decide routes the None case to retrieve/generate instead),
independent of tests/test_write_gating.py's B2 write-gating focus.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


def test_selected_tool_read_classified_executes_eagerly():
    state = {
        "selected_tool": {"tool_name": "itsm_search_records", "arguments": {"record_type": "incident", "record_id": "INC-10255"}},
        "tool_calls": [],
    }
    result = tool_invoke_node(state)

    assert result["pending_approval"] is False
    assert result["approval_action"] is None
    assert "resolved" in result["final_output"]
    assert result["tool_calls"][-1]["tool_name"] == "itsm_search_records"
    assert result["tool_calls"][-1]["result"] is not None


def test_selected_tool_write_classified_drafts_without_executing():
    state = {
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
    result = tool_invoke_node(state)

    assert result["pending_approval"] is True
    assert result["approval_action"] == state["selected_tool"]
    # Drafted, not executed -- the tool_calls entry records no result yet.
    assert result["tool_calls"][-1]["result"] is None
    assert result["tool_calls"][-1]["error"] is None
