"""MCP tool server contract stub.

NOTE: this package is named `mcp_server`, not `mcp` — a directory literally
named `mcp` at the repo root would shadow the installed `mcp` SDK package
(the `from mcp.server.fastmcp import FastMCP` import below would resolve to
itself instead of the real library). Keep this name.
"""

import os

from mcp.server.fastmcp import FastMCP

from .schemas import PlaceholderLookupInput, PlaceholderLookupOutput

HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8081"))

mcp = FastMCP("golden-path-tools", host=HOST, port=PORT)


@mcp.tool()
def placeholder_lookup(query: str, write: bool = False) -> dict:
    """CONTRACT-FROZEN placeholder for the future 1-2 domain tool(s).

    Interface (PlaceholderLookupInput/Output) is stable; do not change
    lightly. TODO(domain): replace the mock branch below with the real call
    to the enterprise tool this agent integrates with (auth, error
    handling, argument mapping from PlaceholderLookupInput to the real API).
    """
    validated = PlaceholderLookupInput(query=query, write=write)
    mcp_mode = os.environ.get("MCP_MODE", "mock")

    if mcp_mode == "mock":
        output = PlaceholderLookupOutput(result="PLACEHOLDER_TOOL_RESPONSE_MARKER", source="mock")
        return output.model_dump()

    raise NotImplementedError("TODO(domain): implement the live enterprise-tool call.")


@mcp.tool()
def healthcheck() -> dict:
    return {"status": "ok"}


def main():
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
