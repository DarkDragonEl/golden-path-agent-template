#!/usr/bin/env sh
# One image, two runtime roles — this is what makes the built artifact
# "one immutable OCI application artifact" while still letting the MCP
# server run as its own Deployment/Service/NetworkPolicy boundary.
set -e

case "$1" in
  agent)
    exec uvicorn agent.api:app --host 0.0.0.0 --port "${AGENT_PORT:-8080}"
    ;;
  mcp)
    exec python -m mcp_server.server
    ;;
  *)
    echo "usage: entrypoint.sh {agent|mcp}" >&2
    exit 1
    ;;
esac
