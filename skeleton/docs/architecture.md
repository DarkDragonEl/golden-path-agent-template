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
- **tool_invoke** (`agent/nodes/tool_invoke.py`) calls the MCP tool server
  via `mcp_server/client.py` (the calling surface only -- this repo does
  not bundle the server implementation, see "Independent Tools Template"
  below). Every call carries a `write` flag; `agent/policy.py::classify_action()`
  uses it to decide whether the call needs human approval
  (`APPROVAL_MODE=required` by default — read actions complete
  immediately, write actions pause).
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
| Tool / MCP | `mcp_server/client.py` (this repo, calling surface only) | The server implementation (`mcp_server/schemas.py`/`server.py`/`auth.py`/`itsm_store.py`) lives in a separately-scaffolded Tools Template instance, not here (Phase G, Stage 2 -- DEC-098/DEC-099, amended `SysR-P-F-01`). Reached over the network at `MCP_TOOL_ENDPOINT` (`mcpEndpoint` scaffold parameter); `MCP_MODE` is fixed to `live` at build time, never configurable to `mock` (there is no local server to fall back to). |
| Approval | `agent/approval_client.py` (this repo, calling surface only) | The approval service is a shared Platform Foundation singleton (DEC-098), not bundled per project. Reached at `APPROVAL_SERVICE_ENDPOINT` (`approvalServiceEndpoint` scaffold parameter), per its published contract (`SRS-APR-IF-01..05`). |
| Policy | `agent/policy.py`, `policy/*.yaml` | Step/timeout/retry guardrails + read-vs-write classification. `POLICY_BUNDLE_REF` points at a versioned YAML file that supplies defaults; env vars override per environment. |

## One image, one runtime role

A single `Containerfile` builds one image; `entrypoint.sh` runs
`uvicorn agent.api:app`, nothing else. Phase G, Stage 2 (DEC-098/DEC-099)
retired the old three-way positional-arg dispatch (`DEC-047`) that used to
also run the MCP server and the approval service as roles of this same
image -- both are now independent artifacts (a separate Tools Template
instance; a shared Platform Foundation component), each with their own
build/deploy/promote lifecycle.

## Independent Tools Template

This repo's own `mcp_server/` contains only `client.py` -- the calling
surface `agent/nodes/tool_invoke.py`/`agent/nodes/human_approval.py`
import. The actual MCP server (FastMCP streamable-HTTP transport, the
domain tools, the mock/real backend) is a different project entirely,
scaffolded from the Tools Template (`template-tools.yaml` in the
blueprint repo) and consumed purely over the network. This repo cannot
run a working tool call without `mcpEndpoint` pointing at a real,
reachable instance -- there is no in-process fallback.
