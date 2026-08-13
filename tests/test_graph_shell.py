import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from agent.graph import build_graph  # noqa: E402


def _invoke(query, write=False, session_id="test-shell"):
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    return graph.invoke(
        {
            "session_id": session_id,
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
    result = _invoke("do the thing", write=True, session_id="test-shell-write")
    assert result["pending_approval"] is True
    assert result.get("final_output") is None


def test_resume_after_approval_completes():
    session_id = "test-shell-resume"
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    graph.invoke(
        {
            "session_id": session_id,
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
    graph.update_state(thread_config, {"approval_decision": "approve"})
    result = graph.invoke(None, thread_config)
    assert result["pending_approval"] is False
    assert "PLACEHOLDER_TOOL_RESPONSE_MARKER" in result["final_output"]


def test_resume_after_rejection_falls_back():
    session_id = "test-shell-reject"
    graph = build_graph()
    thread_config = {"configurable": {"thread_id": session_id}}
    graph.invoke(
        {
            "session_id": session_id,
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
    graph.update_state(thread_config, {"approval_decision": "reject"})
    result = graph.invoke(None, thread_config)
    assert result["fallback_reason"] is not None
    assert "PLACEHOLDER_TOOL_RESPONSE_MARKER" not in (result.get("final_output") or "")
