#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the MCP tool server, nothing
# else. The Tools Template is a standalone
# artifact from the start, never a role of a shared multi-purpose image.
set -e
exec python -m mcp_server.server
