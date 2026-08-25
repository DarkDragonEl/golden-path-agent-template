#!/usr/bin/env sh
# Local dev loop, deterministic (--offline) vs live-model toggle.
#
# Deliberately does NOT depend on docker-compose or podman-compose — many
# dev machines have podman only, with neither compose backend installed
# (confirmed: `podman compose` itself fails without one). Orchestrates the
# two roles directly via plain `podman run`/`docker run` on a shared
# network instead.
set -e

ENGINE="${CONTAINER_ENGINE:-}"
if [ -z "$ENGINE" ]; then
  if command -v podman >/dev/null 2>&1; then
    ENGINE=podman
  elif command -v docker >/dev/null 2>&1; then
    ENGINE=docker
  else
    echo "[dev.sh] no container engine found (need podman or docker)" >&2
    exit 1
  fi
fi

NETWORK=${{ values.name }}-dev
IMAGE=${{ values.name }}:dev
AGENT_NAME=${{ values.name }}-dev
MCP_NAME=${{ values.name }}-mcp-dev
OTEL_NAME=golden-path-otel-collector-dev
# Pinned per PINS.md -- R4/DEC-020, plan-B6 closure. Core distribution
# (not -contrib): only the OTLP receiver + debug exporter are needed here.
OTEL_COLLECTOR_IMAGE=otel/opentelemetry-collector:0.159.0

# Host-published ports, not container-internal ports (those stay 8080/8081
# inside the network namespace regardless). Default to a less common range
# — 8080/8081 are common enough for local infra (registries, identity
# servers, ...) to already be taken on a dev box. Override with
# AGENT_HOST_PORT/MCP_HOST_PORT if 18080/18081 collide with something too.
AGENT_HOST_PORT="${AGENT_HOST_PORT:-18080}"
MCP_HOST_PORT="${MCP_HOST_PORT:-18081}"

ACTION="${1:-up}"
[ $# -gt 0 ] && shift

OFFLINE=false
for arg in "$@"; do
  case "$arg" in
    --offline) OFFLINE=true ;;
  esac
done

down() {
  "$ENGINE" rm -f "$AGENT_NAME" "$MCP_NAME" "$OTEL_NAME" >/dev/null 2>&1 || true
  "$ENGINE" network rm "$NETWORK" >/dev/null 2>&1 || true
}

up() {
  if [ "$OFFLINE" = "true" ]; then
    AGENT_MODEL_MODE=fake
    MCP_MODE=mock
    echo "[dev.sh] offline mode: fake model client, mock MCP tool, no network required"
  else
    echo "[dev.sh] live mode: reads MODEL_API_BASE_URL/MODEL_NAME from .env"
    [ -f .env ] && . ./.env
  fi

  "$ENGINE" build -t "$IMAGE" .
  down
  "$ENGINE" network create "$NETWORK" >/dev/null 2>&1 || true

  "$ENGINE" run -d --name "$MCP_NAME" --network "$NETWORK" -p "${MCP_HOST_PORT}:8081" \
    -e MCP_MODE="${MCP_MODE:-mock}" -e MCP_HOST=0.0.0.0 -e MCP_PORT=8081 \
    "$IMAGE" mcp >/dev/null

  # R4/DEC-020 (plan-B6 closure): a real local OTel Collector so telemetry
  # actually fires on every run instead of silently no-op'ing -- started
  # before the agent so OTEL_EXPORTER_OTLP_ENDPOINT below can point at it
  # by container name on the shared network. Spans land in this
  # container's stdout (`podman logs golden-path-otel-collector-dev`).
  "$ENGINE" run -d --name "$OTEL_NAME" --network "$NETWORK" -p "4318:4318" \
    -v "$(pwd)/deploy/otel/otel-collector-config.yaml:/etc/otelcol/config.yaml:Z" \
    "$OTEL_COLLECTOR_IMAGE" >/dev/null

  "$ENGINE" run -d --name "$AGENT_NAME" --network "$NETWORK" -p "${AGENT_HOST_PORT}:8080" \
    -e AGENT_MODEL_MODE="${AGENT_MODEL_MODE:-live}" \
    -e MCP_MODE="${MCP_MODE:-mock}" \
    -e MODEL_API_BASE_URL="${MODEL_API_BASE_URL:-http://localhost:11434/v1}" \
    -e MODEL_NAME="${MODEL_NAME:-placeholder-model}" \
    -e MODEL_API_KEY="${MODEL_API_KEY:-not-needed}" \
    -e MODEL_FALLBACK_API_BASE_URL="${MODEL_FALLBACK_API_BASE_URL:-}" \
    -e MODEL_FALLBACK_NAME="${MODEL_FALLBACK_NAME:-}" \
    -e MODEL_TEMPERATURE="${MODEL_TEMPERATURE:-0}" \
    -e MODEL_SEED="${MODEL_SEED:-42}" \
    -e MCP_TOOL_ENDPOINT="http://${MCP_NAME}:8081" \
    -e MAX_REASONING_STEPS="${MAX_REASONING_STEPS:-5}" \
    -e TOOL_TIMEOUT_SECONDS="${TOOL_TIMEOUT_SECONDS:-10}" \
    -e TOOL_RETRY_LIMIT="${TOOL_RETRY_LIMIT:-2}" \
    -e APPROVAL_MODE="${APPROVAL_MODE:-required}" \
    -e AUTO_APPROVE_IN_DEV="${AUTO_APPROVE_IN_DEV:-false}" \
    -e AGENT_WORKLOAD_ID="${AGENT_WORKLOAD_ID:-${{ values.name }}}" \
    -e AGENT_OIDC_MODE="${AGENT_OIDC_MODE:-none}" \
    -e MCP_AUTH_MODE="${MCP_AUTH_MODE:-none}" \
    -e OIDC_ISSUER_URL="${OIDC_ISSUER_URL:-http://${{ values.name }}-service.${{ values.name }}-keycloak.svc.cluster.local:8080/realms/${{ values.name }}}" \
    -e APPROVAL_OIDC_CLIENT_ID="${APPROVAL_OIDC_CLIENT_ID:-${{ values.name }}-approval-workload}" \
    -e MCP_OIDC_CLIENT_ID="${MCP_OIDC_CLIENT_ID:-${{ values.name }}-mcp-workload}" \
    -e APPROVAL_OIDC_CLIENT_SECRET="${APPROVAL_OIDC_CLIENT_SECRET:-not-needed}" \
    -e MCP_AUTH_TOKEN="${MCP_AUTH_TOKEN:-not-needed}" \
    -e OTEL_EXPORTER_OTLP_ENDPOINT="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://${OTEL_NAME}:4318}" \
    -v "$(pwd)/corpus/seed:/mnt/corpus:ro" \
    "$IMAGE" agent >/dev/null

  echo "[dev.sh] agent: http://localhost:${AGENT_HOST_PORT}  mcp: http://localhost:${MCP_HOST_PORT}  otel: podman logs -f ${OTEL_NAME}  (Ctrl-C to stop)"
  trap down INT TERM
  "$ENGINE" logs -f "$AGENT_NAME"
  down
}

case "$ACTION" in
  up)
    up
    ;;
  down)
    down
    ;;
  logs)
    "$ENGINE" logs -f "$AGENT_NAME"
    ;;
  *)
    echo "usage: dev.sh {up|down|logs} [--offline]" >&2
    exit 1
    ;;
esac
