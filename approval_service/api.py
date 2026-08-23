"""Approval service -- SRS-APR's standalone realization (Phase D, DEC-008).

Contracts-STOP artifact (DEC-045): endpoint signatures + schemas only.
Route bodies are deliberately NotImplementedError stubs -- business logic
(storage, expiry scanner, auth dependency) is D1's implementation step,
which comes after this contract is reviewed, per the owner's own staged
sequence.

Never issues the literal tool-contract call itself (SRS-APR-F-04) -- the
agent is the sole invoker (DECISIONS.md DEC-008). This service's job is
exactly: intake, decide, expose.

D1 implementation note (DEC-046 closed this STOP): route bodies below are
now real. Telemetry (SRS-APR-IF-03) is realized via structured `logging`,
not an OTel span/TracerProvider -- this service's frozen config.py
contract carries no OTEL_EXPORTER_OTLP_ENDPOINT/OTEL_SERVICE_NAME fields
(unlike agent/config.py), so standing up a second OTel exporter here would
mean extending a contract file this implementation step is not authorized
to change. A structured, correlated log line is the minimal faithful
realization at this scope; wiring a real OTel exporter is a natural
follow-up once this service's own config contract grows those fields.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request

from . import config
from .auth import get_current_approver
from .schemas import (
    ProposalCreate,
    ProposalCreated,
    ProposalDecision,
    ProposalDecided,
    ProposalRefused,
    ProposalSummary,
    ProposalTerminal,
)
from .store import ApprovalStore, ExpiryScanner
from .store import store as _default_store

_telemetry_logger = logging.getLogger("approval_service.telemetry")
_audit_logger = logging.getLogger("approval_service.audit")

# Module-level, reassignable so tests can point the whole API at an
# isolated, fresh SQLite file per test -- ApprovalStore intentionally has
# no reset/delete method (SEC-04), so isolation happens by swapping the
# instance, never by clearing one shared instance's rows.
_store: ApprovalStore = _default_store
_expiry_scanner = ExpiryScanner(_store, config.APPROVAL_TIMEOUT_SECONDS)


def _use_store(store: ApprovalStore) -> None:
    """Test-only hook, not part of the SRS-APR contract. Repoints both
    this module's store reference and the background scanner's, so a
    test's fresh per-file store is what every route AND the expiry sweep
    operate against."""
    global _store
    _store = store
    _expiry_scanner.rebind_store(store)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _expiry_scanner.start()
    try:
        yield
    finally:
        await _expiry_scanner.stop()


app = FastAPI(title="golden-path-approval-service", lifespan=_lifespan)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _emit_transition_event(event: str, record: dict) -> None:
    """SRS-APR-IF-03: every state transition emits a telemetry event
    correlated to the originating session/request ID."""
    _telemetry_logger.info(
        "approval_transition event=%s proposal_id=%s state=%s session_id=%s request_id=%s",
        event,
        record.get("proposal_id"),
        record.get("state"),
        record.get("originating_session_id"),
        record.get("originating_request_id"),
    )


def _to_summary(record: dict) -> ProposalSummary:
    return ProposalSummary(
        proposal_id=record["proposal_id"],
        state=record["state"],
        action_type=record["action_type"],
        target_system_id=record["target_system_id"],
        action_arguments=record["action_arguments"],
        evidence_refs=record["evidence_refs"],
        initiating_user_id=record["initiating_user_id"],
        agent_workload_id=record["agent_workload_id"],
        originating_session_id=record["originating_session_id"],
        originating_request_id=record["originating_request_id"],
    )


def _to_terminal(record: dict) -> ProposalTerminal:
    return ProposalTerminal(
        **_to_summary(record).model_dump(),
        decided_by=record.get("decided_by"),
        decided_at=record.get("decided_at"),
    )


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/proposals", response_model=ProposalCreated, status_code=201)
def create_proposal(body: ProposalCreate) -> ProposalCreated:
    """SRS-APR-IF-01/F-01. Caller: agent workload identity only (SEC-03).
    A replayed idempotency_key for the same originating_session_id
    returns the existing proposal's current state instead of creating a
    duplicate (SRS-APR-F-07)."""
    record = _store.create_proposal(
        action_type=body.action_type,
        target_system_id=body.target_system_id,
        action_arguments=body.action_arguments,
        evidence_refs=body.evidence_refs,
        initiating_user_id=body.initiating_user_id,
        agent_workload_id=body.agent_workload_id,
        originating_session_id=body.originating_session_id,
        originating_request_id=body.originating_request_id,
        idempotency_key=body.idempotency_key,
    )
    _emit_transition_event("proposal_intake", record)
    return ProposalCreated(proposal_id=record["proposal_id"], state=record["state"])


@app.post("/proposals/{proposal_id}/decision", response_model=ProposalDecided)
def decide_proposal(proposal_id: str, body: ProposalDecision, request: Request) -> ProposalDecided:
    """SRS-APR-IF-02/F-02. Approver identity comes from the validated
    bearer token (SEC-03), never `body` -- `body` deliberately carries no
    identity field. 409 + the proposal's actual state if not pending
    (audit-logged refusal, SRS-APR-F-02). 403, audit-logged, if the
    token's role claim doesn't include the approver role (SEC-02) --
    including, explicitly, the agent's own workload token: SRS-APR-SEC-02's
    own known-limitation note accepts one human being both initiator and
    approver, but the agent submitting *and* deciding its own proposal
    (no human in the loop at all) is a strictly worse case this endpoint
    must close via role assignment (D2), not application logic alone."""
    approver = get_current_approver(request)

    target_state = "approved" if body.decision == "approve" else "rejected"
    decided_at = _now_iso()
    updated = _store.transition_to_terminal(
        proposal_id, decision=target_state, decided_by=approver, decided_at=decided_at
    )
    if updated is None:
        current = _store.get_proposal(proposal_id)
        if current is None:
            _audit_logger.warning(
                "refused decision attempt: proposal_id=%s approver=%s reason=not_found",
                proposal_id,
                approver,
            )
            raise HTTPException(status_code=404, detail=f"no such proposal: {proposal_id}")
        _audit_logger.warning(
            "refused decision attempt: proposal_id=%s approver=%s reason=not_pending actual_state=%s",
            proposal_id,
            approver,
            current["state"],
        )
        raise HTTPException(
            status_code=409,
            detail=ProposalRefused(proposal_id=proposal_id, state=current["state"]).model_dump(),
        )

    _emit_transition_event("proposal_decided", updated)
    return ProposalDecided(
        proposal_id=updated["proposal_id"],
        state=updated["state"],
        decided_by=updated["decided_by"],
        decided_at=updated["decided_at"],
        decision=body.decision,
    )


@app.get("/proposals", response_model=list[ProposalSummary])
def list_pending_proposals(
    originating_session_id: str | None = None, originating_request_id: str | None = None
) -> list[ProposalSummary]:
    """SRS-APR-IF-04/F-06. Lists proposals currently `pending`, filterable
    by session/request id; full decision-context fields per F-05."""
    records = _store.list_pending(
        originating_session_id=originating_session_id, originating_request_id=originating_request_id
    )
    return [_to_summary(r) for r in records]


@app.get("/proposals/{proposal_id}", response_model=ProposalTerminal)
def get_proposal(proposal_id: str) -> ProposalTerminal:
    """SRS-APR-IF-05. Current state; once terminal, the full record
    including the *unmodified* `action_arguments` accepted at intake --
    this is what agent/approval_client.py's terminal-state query calls
    from the /resume handler, and the exact arguments DEC-008 requires
    the agent to execute (never a locally cached copy)."""
    record = _store.get_proposal(proposal_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"no such proposal: {proposal_id}")
    return _to_terminal(record)
