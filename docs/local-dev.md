# Local development

Verified working end-to-end against a real running container on a machine
with Podman only (no `docker`, `docker-compose`, or `podman-compose`
installed) — see `docs/evaluation.md` for the eval harness results.

## Quickstart

```sh
cp .env.example .env
make up-offline
```

This runs `scripts/dev.sh up --offline`, which sets `AGENT_MODEL_MODE=fake`
and `MCP_MODE=mock`, builds the image once, and starts both roles as plain
containers (`podman run` / `docker run` — auto-detected, no compose
dependency of any kind) on a shared network so the agent can reach the mcp
container by name. No model endpoint, no network access, and no live MCP
process is actually required for the agent to answer — the mock tool call
happens in-process (see `mcp_server/client.py`); the separate mcp
container exists for architectural parity with the real deployment shape,
not because offline mode needs it running.

`Ctrl-C` stops and removes both containers and the network. `make down`
does the same without starting anything first.

### Why no docker-compose

Several dev machines only have Podman, and not every Podman install has a
compose backend (`podman compose` itself errors without one — confirmed
directly, not assumed). `scripts/dev.sh` orchestrates the two containers
itself instead of depending on any compose tool being present.

### Ports

Published on `18080` (agent) / `18081` (mcp) by default, **not** `8080`/`8081`
— confirmed by trial on a real dev box that already had other long-running
local infrastructure (a registry, an identity server) bound to exactly
those two ports, causing the container to fail to start with an opaque
`address already in use` error. Override with `AGENT_HOST_PORT`/
`MCP_HOST_PORT` env vars (or in `.env`) if `18080`/`18081` collide with
something else on your machine too. The in-container ports (what
`agent/config.py` and the Containerfile actually use) stay `8080`/`8081`
regardless — only the host-side publish mapping changed.

## Endpoints (agent role)

- `GET /healthz`
- `POST /invoke` — `{"query": "...", "write": false, "session_id": "...", "user_id": "..."}`. `session_id` is optional; a UUID is generated if omitted.
- `POST /approvals/{session_id}/resume` — `{"decision": "approve" | "reject"}`. 404s if there's no pending approval for that session.

Confirmed against a running container (not just in-process tests): the
read path completes immediately; the write path (`"write": true`) returns
`pending_approval: true` with no `final_output`; resuming with `approve`
completes it.

## CLI (no server needed)

```sh
python -m agent.cli "some query" [--write] [--session-id ID] [--decision approve|reject]
```

Runs the entire invoke → (pause) → approve/reject → resume sequence in one
process — it is **not** the same checkpointer as a running `agent/api.py`
server, so there's no cross-process resume here (a bug in an earlier
version of this file suggested curling a running server to resume a CLI
invocation; that never worked, since each CLI run has its own in-memory
state). If a `--write` call pauses, it prompts interactively for
approve/reject (or use `--decision` to skip the prompt; a non-interactive
run with no `--decision` defaults to reject rather than hanging). For the
real cross-request approval flow, run the actual server
(`scripts/dev.sh` / `make up`) and call
`POST /approvals/{session_id}/resume` against it, as in the section above.

## Running for real (live model)

Edit `.env` — `MODEL_API_BASE_URL`, `MODEL_NAME` — to point at an
OpenAI-compatible endpoint, then `make up` (no `--offline`). `MCP_MODE`
can stay `mock` even in live-model mode; it only controls whether tool
calls go through the real MCP server container or the in-process mock.

## Tests

```sh
make test    # pytest -q — 14 tests, all offline/deterministic
make eval    # python -m eval.cli run --all — 2 cases, both offline
```
