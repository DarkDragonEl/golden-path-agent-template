import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import approval_client, config
from .graph import build_graph
from .telemetry import get_tracer, init_telemetry, record_invocation_span

app = FastAPI(title="golden-path-agent")
_graph = build_graph()

init_telemetry()
_tracer = get_tracer()


class InvokeRequest(BaseModel):
    query: str
    write: bool = False
    user_id: str = "anonymous"
    session_id: str | None = None


class ResumeRequest(BaseModel):
    """Phase D (DECISIONS.md DEC-045/DEC-049): deliberately empty. A
    resume call carries no claims, only a trigger -- the decision outcome
    and the arguments to execute come exclusively from the approval
    service's own IF-05 terminal-state query
    (agent/approval_client.py::resolve_and_resume), never from this
    request body. This is the Layer 1/Layer 2 split DEC-045's design
    settled on: who/what triggers a resume check (Layer 2, unconstrained)
    is a separate question from what the resume handler does when called
    (Layer 1, DEC-008-governed -- always re-fetch, never trust a caller-
    supplied decision)."""


def _initial_state(session_id: str, request_id: str, req: InvokeRequest) -> dict:
    return {
        "session_id": session_id,
        "request_id": request_id,
        "user_id": req.user_id,
        "input_query": req.query,
        "write_requested": req.write,
        "messages": [],
        "reasoning_steps": 0,
        "tool_calls": [],
        "model_calls": [],
        "pending_approval": False,
    }


def _public_view(state: dict) -> dict:
    return {
        "final_output": state.get("final_output"),
        "pending_approval": state.get("pending_approval", False),
        "tool_calls": state.get("tool_calls", []),
        "fallback_reason": state.get("fallback_reason"),
    }


def _auto_approve(thread_config: dict, result: dict) -> dict:
    """Dev-only convenience (config.AUTO_APPROVE_IN_DEV) so a caller of
    /invoke doesn't need a second HTTP round-trip to /resume for a
    write-classified request -- relocated here from the Phase B2 interim
    mechanism's own human_approval_node (DECISIONS.md DEC-049). Bypasses
    the real approval service entirely for this path -- no proposal this
    submitted is ever actually decided there. Never set true in
    staging/pilot-prod/demo-prod overlay configmaps.

    Still two internal graph.invoke() calls, not one -- interrupt_before
    is unconditional at the graph level (a real finding from this
    redesign, DEC-049), so there is no way to skip the pause itself; this
    only avoids the caller needing a second HTTP request to clear it.
    """
    drafted = result.get("drafted_action") or {}
    _graph.update_state(
        thread_config,
        {
            "approved_action": {
                "tool_name": drafted.get("tool_name"),
                "arguments": drafted.get("arguments", {}),
            },
            "approval_decision": "approved",
        },
    )
    return _graph.invoke(None, thread_config)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/invoke")
def invoke(req: InvokeRequest):
    session_id = req.session_id or str(uuid.uuid4())
    # R4/DEC-020: a fresh id per API call, distinct from session_id (which
    # can span multiple calls -- an /invoke followed by a later /resume) --
    # SRS-AGT-IF-08's "request and session identifiers" as two separate
    # correlation keys, not one doing double duty.
    request_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": session_id}}
    with _tracer.start_as_current_span("agent.invoke"):
        result = _graph.invoke(_initial_state(session_id, request_id, req), thread_config)
        if result.get("pending_approval") and config.AUTO_APPROVE_IN_DEV:
            result = _auto_approve(thread_config, result)
        record_invocation_span(result, request_id=request_id)
    return {"session_id": session_id, **_public_view(result)}


@app.post("/approvals/{session_id}/resume")
def resume(session_id: str, req: ResumeRequest):  # noqa: ARG001 - req is deliberately unused; see
    # ResumeRequest's own docstring for why an empty body is the point, not an oversight.
    request_id = str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": session_id}}
    snapshot = _graph.get_state(thread_config)
    if snapshot is None or not snapshot.values.get("pending_approval"):
        raise HTTPException(status_code=404, detail="no pending approval for this session")

    with _tracer.start_as_current_span("agent.resume"):
        result = approval_client.resolve_and_resume(_graph, thread_config)
        record_invocation_span(result, request_id=request_id)
    return {"session_id": session_id, **_public_view(result)}
