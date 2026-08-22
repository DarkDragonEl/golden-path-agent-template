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
            "itsm_search_records": server.itsm_search_records,
            "itsm_create_request": server.itsm_create_request,
        }
        fn = dispatch.get(tool_name)
        if fn is None:
            raise ValueError(f"unknown tool: {tool_name}")
        return fn(**arguments)

    response = httpx.post(f"{MCP_TOOL_ENDPOINT}/tools/{tool_name}", json=arguments, timeout=timeout)
    response.raise_for_status()
    return response.json()
