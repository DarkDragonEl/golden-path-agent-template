import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import config
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
    decision: str  # "approve" | "reject"


def _initial_state(session_id: str, req: InvokeRequest) -> dict:
    return {
        "session_id": session_id,
        "user_id": req.user_id,
        "input_query": req.query,
        "write_requested": req.write,
        "messages": [],
        "reasoning_steps": 0,
        "tool_calls": [],
        "pending_approval": False,
    }


def _public_view(state: dict) -> dict:
    return {
        "final_output": state.get("final_output"),
        "pending_approval": state.get("pending_approval", False),
        "tool_calls": state.get("tool_calls", []),
        "fallback_reason": state.get("fallback_reason"),
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/invoke")
def invoke(req: InvokeRequest):
    session_id = req.session_id or str(uuid.uuid4())
    thread_config = {"configurable": {"thread_id": session_id}}
    with _tracer.start_as_current_span("agent.invoke"):
        result = _graph.invoke(_initial_state(session_id, req), thread_config)
        record_invocation_span(result)
    return {"session_id": session_id, **_public_view(result)}


@app.post("/approvals/{session_id}/resume")
def resume(session_id: str, req: ResumeRequest):
    thread_config = {"configurable": {"thread_id": session_id}}
    snapshot = _graph.get_state(thread_config)
    if snapshot is None or not snapshot.values.get("pending_approval"):
        raise HTTPException(status_code=404, detail="no pending approval for this session")

    with _tracer.start_as_current_span("agent.resume"):
        _graph.update_state(thread_config, {"approval_decision": req.decision})
        result = _graph.invoke(None, thread_config)
        record_invocation_span(result)
    return {"session_id": session_id, **_public_view(result)}
