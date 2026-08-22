# Architecture

## Graph shape

```
decide -> tool_invoke -> human_approval -> respond
   |            |              |
   v            v              v
fallback     fallback       fallback

decide -> retrieve -> generate -> respond
   |                      |
   v                      v
(as above)             fallback
```

DEC-013 candidate (decide-then-retrieve reordering, replacing the earlier
single `reason` node): `decide` (`agent/nodes/decide.py`) is the sole
entry point and the sole tool-vs-no-tool decision point — it calls the
model client with `agent/prompts/decide_system_prompt.md` and the tool
schemas, and no retrieved context at all. Only when it selects no tool
does `retrieve` (`agent/nodes/retrieve.py`) run, followed by `generate`
(`agent/nodes/generate.py`), a second, separate model call with
`agent/prompts/generate_system_prompt.md` (citation instructions, no tool
schemas) and the retrieved context. This split exists because an
unconditional-retrieval, single-call design let citation instructions
compete with and beat tool-calling instructions whenever retrieval
returned any topically-plausible context, even for tool-oriented queries
(`DECISIONS.md` `DEC-012`) — see `DECISIONS.md` for the full diagnosis and
`DEC-013` for this redesign's re-baseline result.

- **retrieve** (`agent/nodes/retrieve.py`) calls `agent/retrieval_client.py`
  and catches a lookup failure into `retrieval_unavailable=True` instead of
  crashing — the graph keeps running with zero domain content.
- **decide**/**generate** (`agent/nodes/decide.py`, `agent/nodes/generate.py`)
  each call the model client (`agent/model_client.py`) once, per the split
  described above.
- **tool_invoke** (`agent/nodes/tool_invoke.py`) calls the one MCP tool
  (`mcp_server/`) via `mcp_server/client.py`. Every call carries a `write`
  flag; `agent/policy.py::classify_action()` uses it to decide whether the
  call needs human approval (`APPROVAL_MODE=required` by default — read
  actions complete immediately, write actions pause).
- **human_approval** (`agent/nodes/human_approval.py`) is where the graph
  actually pauses: the graph is compiled with
  `interrupt_before=["human_approval"]`, so a write-classified call stops
  execution *before* this node runs. Resuming requires an external caller
  to set `approval_decision` via `graph.update_state(...)` and then call
  `graph.invoke(None, thread_config)` — see `agent/api.py`'s
  `POST /approvals/{session_id}/resume`. Verified end-to-end against a
  running container, not just in tests.
- **fallback** (`agent/nodes/fallback.py`) is the deterministic escape
  hatch: step-limit exceeded, a tool error, or a rejected/withheld approval
  all land here instead of crashing or hanging.

## Contract boundaries

| Contract | File | Status |
|---|---|---|
| Model API | `agent/model_client.py` | OpenAI-compatible client + `FakeModelClient` for offline/eval runs. `AGENT_MODEL_MODE=fake\|live` switches between them. |
| Retrieval | `agent/retrieval_client.py` | Frozen dataclass contract (`RetrievedChunk`); body is TODO(domain). |
| Tool / MCP | `mcp_server/schemas.py`, `mcp_server/server.py`, `mcp_server/client.py` | FastMCP streamable-HTTP server with one placeholder tool. Contract (input/output schema) is meant to survive the domain tool's implementation; only the tool body changes. |
| Policy | `agent/policy.py`, `policy/*.yaml` | Step/timeout/retry guardrails + read-vs-write classification. `POLICY_BUNDLE_REF` points at a versioned YAML file that supplies defaults; env vars override per environment. |

## One image, two runtime roles

A single `Containerfile` builds one image; `entrypoint.sh` dispatches on
its first argument (`agent` vs `mcp`) to run either
`uvicorn agent.api:app` or `python -m mcp_server.server`. This is what
makes the artifact "one immutable OCI application artifact" while still
giving the MCP server its own Kubernetes Deployment/Service/NetworkPolicy
boundary (see `deploy/kustomize/base/`).

## Why the MCP package is named `mcp_server`, not `mcp`

A directory literally named `mcp` at the repo root would shadow the
installed `mcp` SDK package — `from mcp.server.fastmcp import FastMCP`
inside it would resolve to itself instead of the real library. This was
caught during implementation (an actual `ModuleNotFoundError`), not
theorized in advance.

## A version pin worth knowing about

`requirements.txt` pins `mcp>=1.0,<2.0`. The unpinned latest release at
scaffold-build time (`mcp==2.0.0`) removed `mcp.server.fastmcp.FastMCP`
entirely in favor of a differently-shaped `MCPServer` API, which breaks
this contract stub (and the donor pattern it's modeled on). If upgrading
past 2.0 later, expect to rewrite `mcp_server/server.py` against whatever
that version's high-level server API looks like — don't just bump the pin.
