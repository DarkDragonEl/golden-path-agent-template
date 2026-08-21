"""Phase B3: tool_invoke_node's dispatch is now fully driven by
state["selected_tool"] (set by reason_node) -- no hardcoded tool name
anywhere in this node. These tests cover the three shapes selected_tool
can take, independent of tests/test_write_gating.py's B2 write-gating
focus.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent.nodes.tool_invoke import tool_invoke_node  # noqa: E402


def test_selected_tool_none_answers_directly_from_the_last_message():
    # SRS-AGT-F-03: a plain answer is a valid output type -- no tool call
    # needed this turn.
    state = {
        "selected_tool": None,
        "messages": [{"role": "assistant", "content": "An incident is an unplanned disruption."}],
        "tool_calls": [],
    }
    result = tool_invoke_node(state)

    assert result["pending_approval"] is False
    assert result["approval_action"] is None
    assert result["final_output"] == "An incident is an unplanned disruption."


def test_selected_tool_none_with_no_messages_yields_empty_final_output():
    result = tool_invoke_node({"selected_tool": None, "messages": [], "tool_calls": []})
    assert result["final_output"] == ""


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
