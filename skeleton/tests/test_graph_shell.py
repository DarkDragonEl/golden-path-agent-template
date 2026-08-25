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


# --- Phase D2: approval_client's OIDC bearer-header attachment -------------


class _FakeHttpResponse:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_submit_and_get_proposal_send_no_auth_header_when_oidc_mode_none(monkeypatch):
    import httpx

    from agent import config

    monkeypatch.setattr(config, "AGENT_OIDC_MODE", "none")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["post_headers"] = headers
        return _FakeHttpResponse({"proposal_id": "prop-1", "state": "pending"})

    def fake_get(url, headers=None, timeout=None):
        captured["get_headers"] = headers
        return _FakeHttpResponse({"proposal_id": "prop-1", "state": "pending"})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    approval_client.submit_proposal(
        action_type="itsm_create_request",
        target_system_id="mock-itsm",
        action_arguments={},
        evidence_refs=[],
        initiating_user_id="pytest",
        agent_workload_id="${{ values.name }}",
        originating_session_id="sess-1",
        originating_request_id="req-1",
    )
    approval_client.get_proposal("prop-1")

    assert "Authorization" not in captured["post_headers"]
    assert "Authorization" not in captured["get_headers"]


def test_submit_and_get_proposal_attach_bearer_header_when_oidc_mode_oidc(monkeypatch):
    import httpx

    from agent import config, oidc_client

    monkeypatch.setattr(config, "AGENT_OIDC_MODE", "oidc")
    monkeypatch.setattr(config, "OIDC_ISSUER_URL", "https://idp.example.invalid/realms/demo")
    monkeypatch.setattr(config, "APPROVAL_OIDC_CLIENT_ID", "${{ values.name }}-approval-workload")
    monkeypatch.setattr(config, "APPROVAL_OIDC_CLIENT_SECRET", "the-client-secret")
    monkeypatch.setattr(oidc_client, "get_service_token", lambda *a, **kw: "fake-access-token")

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["post_headers"] = headers
        return _FakeHttpResponse({"proposal_id": "prop-1", "state": "pending"})

    def fake_get(url, headers=None, timeout=None):
        captured["get_headers"] = headers
        return _FakeHttpResponse({"proposal_id": "prop-1", "state": "pending"})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    approval_client.submit_proposal(
        action_type="itsm_create_request",
        target_system_id="mock-itsm",
        action_arguments={},
        evidence_refs=[],
        initiating_user_id="pytest",
        agent_workload_id="${{ values.name }}",
        originating_session_id="sess-1",
        originating_request_id="req-1",
    )
    approval_client.get_proposal("prop-1")

    assert captured["post_headers"]["Authorization"] == "Bearer fake-access-token"
    assert captured["get_headers"]["Authorization"] == "Bearer fake-access-token"
