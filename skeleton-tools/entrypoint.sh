#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the MCP tool server, nothing
# else. Phase G (DEC-098/DEC-099): the Tools Template is a standalone
# artifact from the start, never a role of a shared multi-purpose image.
set -e
exec python -m mcp_server.server
