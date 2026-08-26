#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the MCP tool server, nothing
# else. Retires the three-way positional-arg dispatch (DEC-047) now that
# G2 (DECISIONS.md DEC-098/DEC-099) gives each component its own image.
set -e
exec python -m mcp_server.server
