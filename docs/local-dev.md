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
and `MCP_MODE=mock`, builds the image once, and starts all three roles as
plain containers (`podman run` / `docker run` — auto-detected, no compose
dependency of any kind) on a shared network so each can reach the others
by name. No model endpoint and no network access are required for the
agent to answer a read-only query — the mock tool call happens in-process
(see `mcp_server/client.py`); the separate mcp container exists for
architectural parity with the real deployment shape, not because offline
mode needs it running for reads. The approval container, unlike mcp, is
not optional even offline: any `--write`/`"write": true` request submits
a real proposal to it (`agent/approval_client.py::submit_proposal`), so
without it a write request fails immediately with
`fallback_reason: approval_service_failure:ConnectError`.

`Ctrl-C` stops and removes all three containers and the network. `make down`
does the same without starting anything first.

### Why no docker-compose

Several dev machines only have Podman, and not every Podman install has a
compose backend (`podman compose` itself errors without one — confirmed
directly, not assumed). `scripts/dev.sh` orchestrates the roles itself
instead of depending on any compose tool being present.

### Ports

Published on `18080` (agent) / `18081` (mcp) / `18082` (approval) by
default, **not** `8080`/`8081`/`8082` — confirmed by trial on a real dev
box that already had other long-running local infrastructure (a
registry, an identity server) bound to exactly those ports, causing the
container to fail to start with an opaque `address already in use`
error. Override with `AGENT_HOST_PORT`/`MCP_HOST_PORT`/`APPROVAL_HOST_PORT`
env vars (or in `.env`) if `18080`/`18081`/`18082` collide with something
else on your machine too. The in-container ports (what `agent/config.py`,
`approval_service/config.py`, and the Containerfile actually use) stay
`8080`/`8081`/`8082` regardless — only the host-side publish mapping
changed.

## Endpoints (agent role)

- `GET /healthz`
- `POST /invoke` — `{"query": "...", "write": false, "session_id": "...", "user_id": "..."}`. `session_id` is optional; a UUID is generated if omitted.
- `POST /approvals/{session_id}/resume` — empty body (`{}`), deliberately
  (DECISIONS.md DEC-045/DEC-049): it carries no decision, only a trigger
  to re-query the approval service and continue. 404s if there's no
  pending approval for that session.

The decision itself is made on the standalone **approval** role, not the
agent:

- `POST /proposals/{proposal_id}/decision` — `{"decision": "approve" | "reject"}`,
  against `http://localhost:${APPROVAL_HOST_PORT:-18082}`.

So resuming a paused write is two calls, not one: decide on the approval
service, then trigger resume on the agent. The read path completes
immediately; the write path (`"write": true`) returns
`pending_approval: true` with no `final_output`; deciding `approve` then
resuming completes it and actually invokes the tool; deciding `reject`
then resuming completes it with no tool call. See
`reports/direct-chat-http-verification.md` for a live run confirming this
end to end, including the before/after mock-ITSM record counts.

## CLI (single-shot, no agent server needed)

```sh
python -m agent.cli "some query" [--write] [--session-id ID] [--decision approve|reject]
```

Runs the whole invoke → (pause) → approve/reject → resume sequence in one
process, so no `agent/api.py` server is needed. It still needs the
approval service reachable for any `--write` call, exactly like the
server path above (`APPROVAL_SERVICE_ENDPOINT`) — `--decision` posts a
real decision to it (`agent/approval_client.py::decide_proposal`) and
then calls the same `resolve_and_resume` the server's own `/resume`
endpoint uses, so `approve` here genuinely invokes the tool rather than
being silently ignored (an earlier version of this CLI set graph state
directly instead and skipped the approval service entirely — the
DEC-049 authorization node never reads that state, so it had the same
effect as a rejection regardless of `--decision`; fixed, see
`reports/direct-chat-http-verification.md`).

The graph's own checkpointer is still per-process — there is no
cross-*process* resume of the graph itself, so a `--write` call's pause
can only be resumed by that same CLI invocation, not by a separate
`POST /approvals/{session_id}/resume` call against a running server —
but the approval decision itself is genuinely recorded on the shared
approval service either way. If a `--write` call pauses, it prompts
interactively for approve/reject (or use `--decision` to skip the
prompt; a non-interactive run with no `--decision` defaults to reject
rather than hanging).

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
