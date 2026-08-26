# Direct chat walkthrough — talk to the running agent over HTTP

## What this is

A copy-pasteable walkthrough for actually chatting with the running
agent and exercising a full write → approve/reject round trip — the path
`make eval`/`make test` never touch, since the eval harness calls
`agent.graph.build_graph()` **in-process** and never starts a server
(`eval/executor.py`, `eval/domain_executor.py`). Use this whenever you
need to confirm the agent behaves correctly against a real HTTP request,
a real model, and a real approval decision — not just a scripted eval
case. See `docs/testing-perspectives-guide.md` §1 for how this fits
alongside the other five testing perspectives, and
`reports/direct-chat-http-verification.md` for the evidence from the run
this walkthrough is based on.

Three ways to converse with the agent, all covered below: `curl` against
`agent/api.py` directly, the browser form at `GET /ui`, or `python -m
agent.cli` (single-shot, no server).

## 0. Prerequisites

```sh
cd golden-path-agent-template
cp .env.example .env   # skip if you already have one
```

For a live-model run, `.env` needs real `MODEL_API_BASE_URL` /
`MODEL_NAME` / `MODEL_API_KEY` values (see `docs/local-dev.md`'s "Running
for real" section). Everything below also works with `make up-offline`
(fake model, fully deterministic) if you just want to exercise the
mechanics without spending a real model call — the write/approve/reject
plumbing is identical either way; only the read-query answer differs
(scripted vs. real).

`jq` is used below for readability; plain `python3 -m json.tool` or
just eyeballing the raw JSON works too.

## 1. Start the stack

```sh
make up
```

This starts **four** containers on a shared network: `agent` (`:18080`),
`mcp` (`:18081`, the mock ITSM tool server), `approval` (`:18082`), and
an OTel collector (`:4318`). All four are required — without `approval`,
any write-classified query fails immediately with `fallback_reason:
approval_service_failure:ConnectError`.

In a second terminal, confirm both HTTP roles are up:

```sh
curl -sf http://localhost:18080/healthz && echo agent-ok
curl -sf http://localhost:18082/healthz && echo approval-ok
```

`Ctrl-C` in the first terminal stops and removes all four containers and
the network when you're done; `make down` does the same without starting
anything.

## 2. Observability — watch it happen

Every `/invoke` and `/resume` call is wrapped in a span
(`agent/telemetry.py::record_invocation_span`, called from
`agent/api.py`), so you don't have to take the JSON response's word for
what happened. In a third terminal, tail the local collector before
running the steps below:

```sh
podman logs -f golden-path-otel-collector-dev
```

Each call produces one `agent.invoke` or `agent.resume` span carrying:

- `session.id`, `request.id`, `proposal.id` — correlation keys. There is
  no single OTel trace ID spanning both the agent and approval-service
  processes (DEC-071) — they're joined by matching `proposal.id`/
  `session.id` attribute values across each service's own independent
  span tree, not by trace-context propagation.
- `model.route` / `model.route_reason_code`, plus one `model_call` event
  per model call this turn (`decide`/`generate` can each call once) with
  `route`, `reason_code`, token counts, and `response_model` — this is
  the authoritative way to confirm a turn actually hit the live model
  (`response_model: granite-3-2-8b-instruct`) rather than a fallback.
- One `tool_call` event per tool invocation, with `tool_name`,
  `classification` (`read`/`write`), and `error`.
- `approval.decision`, `fallback_reason`, and `final_output.length` /
  `final_output.preview` (first 200 chars only — spans aren't the place
  for a full response body).

The standalone `approval` role has its own tracer
(`approval_service/telemetry.py::record_transition_span`) emitting a span
on every proposal submission and decision, with the same `proposal.id`/
`session.id` attributes — so filtering the collector's log output by a
`session.id` you used gives you the whole story: submit → decide →
resume, across both services.

**Local vs. cluster, worth knowing:** the local collector
(`deploy/otel/otel-collector-config.yaml`) uses a `debug` exporter that
only writes verbose text to its own stdout — there's no UI or query
endpoint locally. `tools/query_traces.py` (a nicer, filterable JSON view)
is built against the *cluster*-tier collector's `file` exporter, which
serves a `traces.jsonl` endpoint that doesn't exist locally — it won't
work against this stack's `podman logs` output as-is; use it only
against a real cluster (`docs/environments.md`).

## 3. A read-only question

```sh
curl -sS -X POST http://localhost:18080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"query": "What is the current status of incident INC-10255?", "write": false}' | jq .
```

Expect `pending_approval: false`, a `tool_calls` entry with
`classification: "read"`, and a `final_output` that actually answers the
question, grounded in the mock ITSM's seed data (`INC-10255` is one of
the pre-seeded records — see `mcp_server/itsm_store.py` for the full
seed list if you want to ask about a different one). Watch the span from
step 2 (or check `.model_calls[0].response_model` via the CLI in step 7)
to confirm this actually hit the live model, not a fallback.

## 4. A write query — it pauses

```sh
curl -sS -X POST http://localhost:18080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"query": "Draft an access request for the staging namespace.", "write": true, "session_id": "walkthrough-1"}' | jq .
```

Expect `pending_approval: true`, `final_output: null`, and a `tool_calls`
entry with `classification: "write"` and `result: null` — drafted, not
executed. Note the `session_id` you passed (or, if you omit it, the one
the response generates) — you need it for the next step.

## 5. Decide, then resume — two calls, not one

`POST /approvals/{session_id}/resume` takes an **empty body** by design
(DECISIONS.md DEC-045/DEC-049 — it's a trigger, not a claim). The actual
decision is made on the standalone `approval` role first:

```sh
SID=walkthrough-1

# Find the proposal for this session
PID=$(curl -s "http://localhost:18082/proposals?originating_session_id=${SID}" | jq -r '.[0].proposal_id')
echo "proposal_id=$PID"

# Decide (a real approver would do this from the /ui approve/reject panel instead)
curl -sS -X POST "http://localhost:18082/proposals/${PID}/decision" \
  -H 'Content-Type: application/json' -d '{"decision": "approve"}' | jq .

# Trigger resume on the agent
curl -sS -X POST "http://localhost:18080/approvals/${SID}/resume" \
  -H 'Content-Type: application/json' -d '{}' | jq .
```

Expect the decision call to return `state: "approved"`, and the resume
call to return `pending_approval: false` with a real `final_output` like
`"Request REQ-xxxxx has been submitted (status: submitted)"`, plus a
second `tool_calls` entry whose `result` is now populated.

To try rejection instead, repeat steps 4–5 with a fresh `session_id` and
`{"decision": "reject"}` — expect `final_output` to describe an
escalation and `fallback_reason: "approval_not_granted:'rejected'"`, with
no second, populated `tool_calls` entry.

## 6. Confirm it against the store, not the response

This project's own convention (`tests/test_write_gating.py`) is to never
trust the agent's self-reported JSON alone for a write — check the mock
ITSM store directly.

**Caveat that will bite you if you skip it:** with `MCP_MODE=mock` (the
default `make up` sets), the agent calls the mock tool **in-process**,
inside its own container — a separate in-memory store from the standalone
`mcp` container's own REST store. Querying `:18081/records` in that mode
checks the *wrong* copy and will look like nothing happened even after a
real approve. To make the `mcp` container's store the actual source of
truth, run the agent with `MCP_MODE=live` instead (`-e MCP_MODE=live` if
you're constructing your own `podman run`/`docker run`, or export
`MCP_MODE=live` before `make up`) so tool calls genuinely cross the
network:

```sh
# record count before/after, against the real mcp container
curl -s "http://localhost:18081/records?record_type=request" | jq '.records | length'
# ... run steps 4-5 ...
curl -s "http://localhost:18081/records?record_type=request" | jq '.records | length'
# expect +1 after an approve, unchanged after a reject
```

## 7. Same thing, single-shot, no server (CLI)

```sh
python -m agent.cli "What is the current status of incident INC-10261?"
```

No pause, no server needed for a read-only query. Check
`.model_calls[0].response_model` in the output to confirm which model
actually answered (e.g. `granite-3-2-8b-instruct`) — proof this hit the
real model, not a scripted case.

```sh
python -m agent.cli "Submit an information request ticket about the standard offboarding checklist." \
  --write --session-id cli-walkthrough --decision approve
```

This one call submits the proposal, records the decision on the
approval service, and resumes — all in one process. It still needs
`APPROVAL_SERVICE_ENDPOINT` reachable (export it, or run from a shell
that's sourced `.env` with the right value, e.g.
`http://localhost:18082` if you're on the host talking to the containers
`make up` started). Expect `approved_action` populated with an
`approver_id`, and a real `final_output`. Swap `--decision reject` to see
the rejection path — expect `approved_action: null` and the same
`approval_not_granted` `fallback_reason` as the curl version.

If `--decision` is omitted on a write call, the CLI prompts interactively
(or defaults to reject if there's no TTY, e.g. in a script).

## 8. Or just use the browser

```
open http://localhost:18080/ui
```

`agent/static/approver_ui.html` has both a live query box (posts to
`/invoke`, same as step 3/4) and an approve/reject panel for whatever's
pending — not approver-only despite the filename. Useful for an
eyeballed walkthrough rather than scripted curl calls; functionally
identical to the steps above under the hood.

## 9. Clean up

```sh
curl -sS -X POST http://localhost:18081/reset   # wipe any records you created back to seed data
make down                                        # stop + remove all four containers and the network
```

Always run the reset before `make down` if you created any real records
(step 5/7's approve path) — a leaked `REQ-*` record can trip up a later
`make eval-domain` run, which pins to the exact seed-data record count.

## Troubleshooting

- **`fallback_reason: approval_service_failure:ConnectError`** on any
  write query — the `approval` container isn't reachable. Confirm
  `podman ps` shows `golden-path-agent-approval-dev` running and
  `curl :18082/healthz` succeeds.
- **A write "succeeded" but you can't find the record** — you're almost
  certainly checking the `mcp` container's store while the agent is
  running `MCP_MODE=mock` (in-process, separate store). See step 6.
- **`GET /proposals?originating_session_id=...` returns `[]`** — either
  the session never actually paused (check `pending_approval` on the
  `/invoke` response first) or you used the wrong `session_id`.
- **CLI `--decision approve` doesn't create anything** — confirm
  `APPROVAL_SERVICE_ENDPOINT` is set and reachable in the shell you're
  running the CLI from; it needs the same approval service the containers
  use, not a default that points nowhere.
- **No spans show up in `podman logs -f golden-path-otel-collector-dev`**
  — telemetry silently no-ops (not an error) if `OTEL_EXPORTER_OTLP_ENDPOINT`
  isn't set on the agent/approval containers (`agent/telemetry.py`'s own
  guard); `scripts/dev.sh` sets it by default, so this only bites if
  you're running a hand-rolled container invocation without it.
