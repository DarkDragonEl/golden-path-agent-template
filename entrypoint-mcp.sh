#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the MCP tool server, nothing
# else. Retires the three-way positional-arg dispatch now that
# G2 gives each component its own image.
set -e
exec python -m mcp_server.server
