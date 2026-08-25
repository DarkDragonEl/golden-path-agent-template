#!/usr/bin/env sh
# One image, three runtime roles — this is what makes the built artifact
# "one immutable OCI application artifact" while still letting the MCP
# server and the approval service each run as their own Deployment/
# Service/NetworkPolicy boundary. Phase D, Step D1 (DEC-047): approval is
# the third role, same pattern as mcp before it.
set -e

case "$1" in
  agent)
    exec uvicorn agent.api:app --host 0.0.0.0 --port "${AGENT_PORT:-8080}"
    ;;
  mcp)
    exec python -m mcp_server.server
    ;;
  approval)
    exec uvicorn approval_service.api:app --host 0.0.0.0 --port "${APPROVAL_PORT:-8082}"
    ;;
  *)
    echo "usage: entrypoint.sh {agent|mcp|approval}" >&2
    exit 1
    ;;
esac
