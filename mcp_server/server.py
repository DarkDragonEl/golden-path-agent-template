"""MCP tool server: mock ITSM (SRS-MIT) plus the pre-existing placeholder.

NOTE: this package is named `mcp_server`, not `mcp` — a directory literally
named `mcp` at the repo root would shadow the installed `mcp` SDK package
(the `from mcp.server.fastmcp import FastMCP` import below would resolve to
itself instead of the real library). Keep this name.

REST/MCP coexistence: confirmed via a minimal probe (Phase B kickoff, Task
1 prerequisite) that the pinned `mcp` SDK (1.x) supports mounting
`FastMCP.streamable_http_app()` as an ASGI sub-app under a parent FastAPI
app on one port, provided the parent's lifespan explicitly enters the
sub-app's own lifespan context (its session manager otherwise never
starts). No second port needed. `docs/architecture.md` already records a
breaking-change scare with this package's API — this shape was verified
empirically against the actually-installed version, not assumed from
memory.

`placeholder_lookup` is left in place, unchanged, alongside the two new
ITSM tools below — it is still load-bearing for
`eval/cases/EXAMPLE-001.yaml` (the harness-mechanics smoke fixture,
explicitly never treated as domain content per SRS-EVH-F-03) and for
`agent/nodes/tool_invoke.py`'s current hardcoded tool call. Retiring it
from the agent's active path is Phase B2 work (the write-gating
restructure), not this one.
"""

import os
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, HTTPException
from mcp.server.fastmcp import FastMCP

from .itsm_store import store
from .schemas import (
    ItsmCreateRequestInput,
    ItsmCreateRequestOutput,
    ItsmSearchRecordsInput,
    ItsmSearchRecordsOutput,
    PlaceholderLookupInput,
    PlaceholderLookupOutput,
)

HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8081"))

mcp = FastMCP("golden-path-tools", host=HOST, port=PORT)


@mcp.tool()
def placeholder_lookup(query: str, write: bool = False) -> dict:
    """CONTRACT-FROZEN placeholder for the future 1-2 domain tool(s).

    Interface (PlaceholderLookupInput/Output) is stable; do not change
    lightly. Superseded, for the ITSM domain, by itsm_search_records /
    itsm_create_request below — kept only for eval/cases/EXAMPLE-001.yaml
    and the agent's not-yet-updated tool_invoke node (Phase B2).
    """
    validated = PlaceholderLookupInput(query=query, write=write)
    mcp_mode = os.environ.get("MCP_MODE", "mock")

    if mcp_mode == "mock":
        output = PlaceholderLookupOutput(result="PLACEHOLDER_TOOL_RESPONSE_MARKER", source="mock")
        return output.model_dump()

    raise NotImplementedError("TODO(domain): implement the live enterprise-tool call.")


@mcp.tool(meta={"semver": "1.0.0", "certification_status": "blueprint-demo"})
def itsm_search_records(
    record_type: str,
    query: str | None = None,
    record_id: str | None = None,
    status: str | None = None,
    limit: int = 10,
) -> dict:
    """Search or look up mock ITSM records. Read-only (SRS-MIT-IF-02) —
    never creates, modifies, or deletes state."""
    validated = ItsmSearchRecordsInput(
        record_type=record_type, query=query, record_id=record_id, status=status, limit=limit
    )
    result = store.search(
        record_type=validated.record_type,
        query=validated.query,
        record_id=validated.record_id,
        status=validated.status,
        limit=validated.limit,
    )
    return ItsmSearchRecordsOutput(**result).model_dump()


@mcp.tool(meta={"semver": "1.0.0", "certification_status": "blueprint-demo"})
def itsm_create_request(
    short_description: str,
    description: str,
    category: str,
    requested_for: str,
    related_record_id: str | None = None,
) -> dict:
    """Draft a new ITSM service request. Write (SRS-MIT-IF-03).

    Interim Phase B1 state, deliberately not yet gated here: this tool is
    reachable and directly callable with no approval check in front of it.
    That is expected and correct for B1 — SRS-MIT-SEC-01's no-bypass
    guarantee is enforced by the agent's policy layer plus the approval
    flow (Phase B2's write-gating restructure), never by this MCP tool
    interface itself. Do not read this ungated window as the intended end
    state; it closes in B2.
    """
    validated = ItsmCreateRequestInput(
        short_description=short_description,
        description=description,
        category=category,
        requested_for=requested_for,
        related_record_id=related_record_id,
    )
    result = store.create_request(
        short_description=validated.short_description,
        description=validated.description,
        category=validated.category,
        requested_for=validated.requested_for,
        related_record_id=validated.related_record_id,
    )
    return ItsmCreateRequestOutput(**result).model_dump()


@mcp.tool()
def healthcheck() -> dict:
    return {"status": "ok"}


# --- REST introspection surface (SRS-MIT-IF-04, demo/test-support only) ---
# Never called by the agent, never part of its tool contract. Mounted
# alongside, not instead of, the MCP contract above.

rest_app = FastAPI(title="mock-itsm-introspection")


@rest_app.get("/records")
def rest_list_records(record_type: str | None = None, status: str | None = None):
    return {"records": store.list_records(record_type=record_type, status=status)}


@rest_app.get("/records/{record_id}")
def rest_get_record(record_id: str):
    record = store.get_record(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no such record: {record_id}")
    return record


@rest_app.post("/reset")
def rest_reset():
    store.reset()
    return {"status": "reset"}


def build_app() -> FastAPI:
    """Combine the REST introspection app with the MCP streamable-http
    ASGI app on one port, per the confirmed mounting mechanism above.

    Call this exactly once per process (as main() below does). `mcp`'s
    streamable_http_app() lazily creates and caches a
    StreamableHTTPSessionManager on the FastMCP instance itself; that
    session manager's .run() (entered via this app's lifespan) can only be
    called once per instance's lifetime — a real constraint found while
    writing tests against this function, not assumed from memory. A test
    suite exercising this app must reuse one built app/client across
    tests, not call build_app() fresh per test."""
    mcp_asgi_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(mcp_asgi_app.router.lifespan_context(mcp_asgi_app))
            yield

    rest_app.router.lifespan_context = lifespan
    rest_app.mount("/", mcp_asgi_app)
    return rest_app


def main():
    import uvicorn

    uvicorn.run(build_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
