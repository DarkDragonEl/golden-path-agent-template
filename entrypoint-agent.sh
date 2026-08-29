#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the agent, nothing else.
# Retires the three-way positional-arg dispatch now that G2
# gives each component its own image.
set -e
exec uvicorn agent.api:app --host 0.0.0.0 --port "${AGENT_PORT:-8080}"
