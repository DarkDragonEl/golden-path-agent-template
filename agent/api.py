"""FastAPI HTTP surface for the golden-path agent — the process boundary
between an external caller and the LangGraph graph built by agent/graph.py.

Routes and their contracts:
- POST /invoke — body: InvokeRequest {query, write, user_id, session_id?};
  starts (or continues) a graph run on a per-session thread and returns
  {session_id, final_output, pending_approval, tool_calls, fallback_reason}
  (see _public_view). If config.AUTO_APPROVE_IN_DEV is set and the run
  paused for approval, _auto_approve clears it in-process before
  responding — a dev-only bypass of the real approval service, never
  enabled in staging/pilot-prod/demo-prod overlay configmaps.
- POST /approvals/{session_id}/resume — body: ResumeRequest (deliberately
  empty; see its own docstring). Never trusts caller-supplied decision
  data — it only triggers agent/approval_client.py::resolve_and_resume to
  re-fetch the approval service's own terminal-state (SRS-APR-IF-05)
  before resuming the paused graph (DECISIONS.md DEC-008/DEC-045/DEC-049's
  Layer 1/Layer 2 split).
- GET /healthz — liveness probe.
- GET /ui / GET /ui/config — serves the static approver UI page and the
  one piece of real environment config it needs at load time
  (OIDC_ISSUER_URL).

Reads config.AUTO_APPROVE_IN_DEV and config.OIDC_ISSUER_URL via
agent/config.py; no environment variables are read directly here.
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import approval_client, config
from .graph import build_graph
from .telemetry import get_tracer, init_telemetry, record_invocation_span

app = FastAPI(title="golden-path-agent")
_graph = build_graph()

init_telemetry()
_tracer = get_tracer()

# Phase D3: read once at import time, not per-request -- this is static
# content that never changes at runtime (no templating, see GET /ui/config
# below for the one piece of real environment config the page needs),
# so a repeated disk read on every GET /ui would be pure waste.
_APPROVER_UI_HTML = (Path(__file__).resolve().parent / "static" / "approver_ui.html").read_text()


class InvokeRequest(BaseModel):
    query: str
    write: bool = False
    user_id: str = "anonymous"
    session_id: str | None = None


class ResumeRequest(BaseModel):
    """Deliberately empty (DEC-045's Layer 1/Layer 2 split): the decision
    and arguments to execute come only from the approval service's own
    IF-05 terminal-state query (approval_client.py::resolve_and_resume),
    never from this request body (DEC-008)."""


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
    """Dev-only convenience (config.AUTO_APPROVE_IN_DEV, DEC-049): bypasses
    the real approval service entirely for this path. **Never set true in
    staging/pilot-prod/demo-prod overlay configmaps.** Still two internal
    graph.invoke() calls, not one -- interrupt_before is unconditional at
    the graph level, so there is no way to skip the pause itself."""
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


@app.get("/ui", response_class=HTMLResponse)
def approver_ui():
    return _APPROVER_UI_HTML


@app.get("/ui/config")
def approver_ui_config():
    """The one piece of real environment config agent/static/approver_ui.html
    needs (the OIDC issuer URL) -- fetched at page-load time instead of
    templated into the static file, so GET /ui above can stay a plain,
    byte-for-byte-static file read (see its own comment) rather than
    growing a server-side templating step. Not secret: the same value is
    already the committed default of config.OIDC_ISSUER_URL and is visible
    to any browser completing the OIDC redirect anyway."""
    return {"oidc_issuer_url": config.OIDC_ISSUER_URL}


@app.post("/invoke")
def invoke(req: InvokeRequest):
    session_id = req.session_id or str(uuid.uuid4())
    # DEC-020: fresh per call, distinct from session_id (SRS-AGT-IF-08's
    # two separate correlation keys).
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
