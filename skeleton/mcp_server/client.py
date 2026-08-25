"""Thin client the agent's tool_invoke node calls. Stays unchanged once the
real tool lands — only the schema/body in server.py changes, because the
contract is what's frozen, not the implementation.
"""

import os

import httpx

MCP_TOOL_ENDPOINT = os.environ.get("MCP_TOOL_ENDPOINT", "http://localhost:8081")


def call_tool(tool_name: str, arguments: dict, timeout: float = 10.0) -> dict:
    mcp_mode = os.environ.get("MCP_MODE", "mock")

    if mcp_mode == "mock":
        # In-process call in mock mode: local/eval runs don't need a second
        # process or a network hop to exercise the contract end-to-end.
        from . import server

        dispatch = {
            "placeholder_lookup": server.placeholder_lookup,
            "placeholder_write_action": server.placeholder_write_action,
            "itsm_search_records": server.itsm_search_records,
            "itsm_create_request": server.itsm_create_request,
        }
        fn = dispatch.get(tool_name)
        if fn is None:
            raise ValueError(f"unknown tool: {tool_name}")
        return fn(**arguments)

    headers = {}
    if os.environ.get("AGENT_OIDC_MODE", "none") == "oidc":
        # Reusing AGENT_OIDC_MODE (not a third toggle) -- this IS the
        # agent's own outbound call, so its single OIDC on/off switch is
        # the right one. Deferred import, matching this file's own
        # existing local-import style for the mock branch above (`from .
        # import server`): pays the agent<->mcp_server coupling only when
        # this branch actually runs, which today is test-only.
        from agent.oidc_client import get_service_token

        token = get_service_token(
            os.environ.get("OIDC_ISSUER_URL"),
            os.environ.get("MCP_OIDC_CLIENT_ID"),
            os.environ.get("MCP_AUTH_TOKEN"),
        )
        headers["Authorization"] = f"Bearer {token}"

    response = httpx.post(f"{MCP_TOOL_ENDPOINT}/tools/{tool_name}", json=arguments, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()
