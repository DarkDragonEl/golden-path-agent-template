import os
from unittest.mock import patch

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent import approval_client  # noqa: E402
from agent.graph import build_graph  # noqa: E402
from eval.fake_approval_client import FakeApprovalService  # noqa: E402


def _invoke(query, write=False, session_id="test-shell"):
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    return graph.invoke(
        {
            "session_id": session_id,
            "request_id": f"{session_id}-req",
            "user_id": "pytest",
            "input_query": query,
            "write_requested": write,
            "messages": [],
            "reasoning_steps": 0,
            "tool_calls": [],
            "pending_approval": False,
        },
        thread_config,
    )


def test_read_path_completes_without_approval():
    result = _invoke("what is the status", write=False, session_id="test-shell-read")
    assert result["pending_approval"] is False
    assert result["final_output"] is not None
    assert "PLACEHOLDER_TOOL_RESPONSE_MARKER" in result["final_output"]


def test_write_path_pauses_for_approval():
    # Phase D/DEC-049: tool_invoke_node's write branch submits a real
    # proposal over HTTP -- patched here, mirroring
    # eval/domain_executor.py's own always-active fake for the same
    # reason (no live approval_service in this unit test).
    fake = FakeApprovalService()
    with patch("agent.approval_client.submit_proposal", side_effect=fake.submit_proposal):
        result = _invoke("do the thing", write=True, session_id="test-shell-write")
    assert result["pending_approval"] is True
    assert result.get("final_output") is None


def test_resume_after_approval_completes():
    session_id = "test-shell-resume"
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    fake = FakeApprovalService()
    with patch("agent.approval_client.submit_proposal", side_effect=fake.submit_proposal):
        state = graph.invoke(
            {
                "session_id": session_id,
                "request_id": f"{session_id}-req",
                "user_id": "pytest",
                "input_query": "do the thing",
                "write_requested": True,
                "messages": [],
                "reasoning_steps": 0,
                "tool_calls": [],
                "pending_approval": False,
            },
            thread_config,
        )

    fake.decide(state["proposal_id"], "approved")
    with patch("agent.approval_client.get_proposal", side_effect=fake.get_proposal):
        result = approval_client.resolve_and_resume(graph, thread_config)
    assert result["pending_approval"] is False
    assert "PLACEHOLDER_TOOL_RESPONSE_MARKER" in result["final_output"]


def test_resume_after_rejection_falls_back():
    session_id = "test-shell-reject"
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    fake = FakeApprovalService()
    with patch("agent.approval_client.submit_proposal", side_effect=fake.submit_proposal):
        state = graph.invoke(
            {
                "session_id": session_id,
                "request_id": f"{session_id}-req",
                "user_id": "pytest",
                "input_query": "do the thing",
                "write_requested": True,
                "messages": [],
                "reasoning_steps": 0,
                "tool_calls": [],
                "pending_approval": False,
            },
            thread_config,
        )

    fake.decide(state["proposal_id"], "rejected")
    with patch("agent.approval_client.get_proposal", side_effect=fake.get_proposal):
        result = approval_client.resolve_and_resume(graph, thread_config)
    assert result["fallback_reason"] is not None
    assert "PLACEHOLDER_TOOL_RESPONSE_MARKER" not in (result.get("final_output") or "")
