---
name: probe-tool
description: Call the mock ITSM MCP tools directly over their REST dispatch route on the local stack, bypassing the model entirely, to check each tool responds and its response shape matches its schema. Use to separate "the tool/MCP server is broken" from "the model called the tool wrong" without burning an eval pass — especially useful right after a schema or mcp_server/ change.
allowed-tools:
  - Bash(curl *)
  - Bash(make *)
  - Read
---

# /probe-tool [tool-name|all]

**Classification: read-only w.r.t. the project's real state** (only the
*local* mock ITSM store, reset at the end of this skill — see the
caveat below). Requires the local stack running (`make up`).

## What's real here (verified by actually calling the running local
server, not just reading source — the wrapped-body shape below was
initially assumed from the handler's `arguments: dict` parameter name
and was wrong; only a live call surfaced it)

REST dispatch route: `POST /tools/{tool_name}`, body is the **raw
argument fields directly** — e.g. `{"query": "probe"}`, **not**
`{"arguments": {"query": "probe"}}`. `server.py`'s handler does `fn(
**arguments)` where `arguments` is FastAPI's own binding of the *entire*
request body to that one untyped `dict` parameter; wrapping the payload
under an `"arguments"` key makes the whole wrapper object become the
single kwarg, which crashes every tool call with `TypeError: <tool>()
got an unexpected keyword argument 'arguments'` (HTTP 500) — confirmed
by running exactly that request against the real container and reading
its traceback. Four tools are REST-reachable this way (`healthcheck` is
MCP-protocol only, not exposed over this REST route — don't probe it
here):

| Tool | Minimal valid probe payload | Output shape |
|---|---|---|
| `placeholder_lookup` | `{"query": "probe", "write": false}` | `{result: str, source: str}` |
| `placeholder_write_action` | `{"query": "probe"}` | same shape as `placeholder_lookup`'s output |
| `itsm_search_records` | `{"record_type": "incident", "limit": 1}` | `{records: list[dict], count: int, source: "mock-itsm"}` |
| `itsm_create_request` | `{"short_description": "probe-tool test", "description": "created by /probe-tool -- safe to reset", "category": "information", "requested_for": "probe-tool"}` | `{record_id: str, status: "submitted", source: "mock-itsm"}` |

Auth: gated by `MCP_AUTH_MODE` (`none`\|`oidc`, default `none`). Local
dev defaults to `none` — no `Authorization` header needed against the
local stack. Unknown tool name → `404`.

Local endpoint: `http://localhost:${MCP_HOST_PORT:-18081}`.

## Important caveat — this bypasses the approval gate, on purpose, locally only

`itsm_create_request` is classified `write` in the agent's own policy
layer (`agent/policy.py`), but that gating lives entirely in the
*agent*, not in the MCP server. `mcp_server/server.py`'s own docstring
documents this as a known, intentional interim state: nothing on this
REST route enforces approval — a caller who reaches `POST
/tools/itsm_create_request` directly, the way this skill does, creates a
real (mock) record with **no approval step**, same as this skill just
did. That's the correct thing for a local dev-loop probe to do (it's
testing the tool, not the agent's policy layer) — but it's worth
understanding you're deliberately using the same bypass path a real
security review would flag, and only ever against the local ephemeral
store.

## Procedure

```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST "http://localhost:${MCP_HOST_PORT:-18081}/tools/placeholder_lookup" \
  -H "Content-Type: application/json" -d '{"query": "probe", "write": false}'
curl -s -w '\nHTTP %{http_code}\n' -X POST "http://localhost:${MCP_HOST_PORT:-18081}/tools/placeholder_write_action" \
  -H "Content-Type: application/json" -d '{"query": "probe"}'
curl -s -w '\nHTTP %{http_code}\n' -X POST "http://localhost:${MCP_HOST_PORT:-18081}/tools/itsm_search_records" \
  -H "Content-Type: application/json" -d '{"record_type": "incident", "limit": 1}'
curl -s -w '\nHTTP %{http_code}\n' -X POST "http://localhost:${MCP_HOST_PORT:-18081}/tools/itsm_create_request" \
  -H "Content-Type: application/json" \
  -d '{"short_description": "probe-tool test", "description": "created by /probe-tool -- safe to reset", "category": "information", "requested_for": "probe-tool"}'
```
(each payload is the table's column verbatim — no wrapper key, per the
correction above)

**Cleanup — always run this last**, so the probe leaves no residue in
the local mock store for a later eval run to trip over:
```bash
curl -s -X POST "http://localhost:${MCP_HOST_PORT:-18081}/reset"
```

## Verdict per tool

- HTTP `200` + response matches the documented output shape → ✓.
- HTTP `4xx`/`5xx`, or a `200` whose body is missing an expected field
  or has a wrong type → ✗, quote the actual body received.
- Never silently treat a shape mismatch as a pass — a `200` with the
  wrong fields is exactly the "tool responded but the contract drifted"
  case this skill exists to catch, distinct from an HTTP-level failure.

## Output format

```
/probe-tool all
  [✓] placeholder_lookup       200  {"result":"PLACEHOLDER_TOOL_RESPONSE_MARKER","source":"mock"}
  [✓] placeholder_write_action 200  {"result":"PLACEHOLDER_TOOL_RESPONSE_MARKER","source":"mock"}
  [✓] itsm_search_records      200  {"records":[{...1 incident...}],"count":1,"source":"mock-itsm"}
  [✓] itsm_create_request      200  {"record_id":"REQ-30100","status":"submitted","source":"mock-itsm"}
  Cleanup: POST /reset -> {"status":"reset"} 200

Verdict: all 4 tools responding, shapes match schema.
```
(this is real captured output from a live local run during
`feature/workspace-tooling`'s own verification pass, not a hypothetical
example — the exact `REQ-30100`/`INC-10234` values will differ run to
run, the shape won't)
