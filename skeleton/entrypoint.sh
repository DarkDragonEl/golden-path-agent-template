#!/usr/bin/env sh
# Single-purpose entrypoint: this image runs the agent, nothing else.
# Retires entrypoint.sh's old three-way positional-arg dispatch -- the
# Agent Template is a standalone artifact from the start, never a role of
# a shared multi-purpose image.
set -e
exec uvicorn agent.api:app --host 0.0.0.0 --port "${AGENT_PORT:-8080}"
