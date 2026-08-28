"""Tests mcp_server/client.py's MCP_MODE=live path: bearer-token
attachment gated by AGENT_OIDC_MODE (the agent's own single OIDC on/off
switch, reused here rather than inventing a third toggle). Also covers
the new POST /tools/{tool_name} REST route this live path now actually
reaches (previously a 404 -- see mcp_server/server.py's rest_call_tool).
"""

import httpx
import pytest

import agent.oidc_client as oidc_client
from mcp_server import client as mcp_client


@pytest.fixture(autouse=True)
def _live_mode(monkeypatch):
    monkeypatch.setenv("MCP_MODE", "live")
    monkeypatch.setenv("MCP_TOOL_ENDPOINT", "http://mcp.example.invalid")


class _FakeResponse:
    def __init__(self):
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"result": "ok"}


def test_no_oidc_mode_sends_no_authorization_header(monkeypatch):
    monkeypatch.setenv("AGENT_OIDC_MODE", "none")
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeResponse()

    monkeypatch.setattr(httpx, "post", fake_post)

    mcp_client.call_tool("placeholder_lookup", {"query": "x"})

    assert "Authorization" not in captured["headers"]


def test_oidc_mode_attaches_bearer_token_from_oidc_client(monkeypatch):
    monkeypatch.setenv("AGENT_OIDC_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://idp.example.invalid/realms/demo")
    monkeypatch.setenv("MCP_OIDC_CLIENT_ID", "golden-path-agent-mcp-workload")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "the-client-secret")

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["headers"] = headers
        return _FakeResponse()

    def fake_get_service_token(issuer_url, client_id, client_secret, **kwargs):
        captured["token_call"] = (issuer_url, client_id, client_secret)
        return "fake-access-token"

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(oidc_client, "get_service_token", fake_get_service_token)

    mcp_client.call_tool("placeholder_lookup", {"query": "x"})

    assert captured["headers"]["Authorization"] == "Bearer fake-access-token"
    assert captured["token_call"] == (
        "https://idp.example.invalid/realms/demo",
        "golden-path-agent-mcp-workload",
        "the-client-secret",
    )
