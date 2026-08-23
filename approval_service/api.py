"""Approval service -- SRS-APR's standalone realization (Phase D, DEC-008).

Contracts-STOP artifact (DEC-045): endpoint signatures + schemas only.
Route bodies are deliberately NotImplementedError stubs -- business logic
(storage, expiry scanner, auth dependency) is D1's implementation step,
which comes after this contract is reviewed, per the owner's own staged
sequence.

Never issues the literal tool-contract call itself (SRS-APR-F-04) -- the
agent is the sole invoker (DECISIONS.md DEC-008). This service's job is
exactly: intake, decide, expose.
"""

from fastapi import FastAPI, HTTPException, Request

from .schemas import (
    ProposalCreate,
    ProposalCreated,
    ProposalDecision,
    ProposalDecided,
    ProposalSummary,
    ProposalTerminal,
)

app = FastAPI(title="golden-path-approval-service")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/proposals", response_model=ProposalCreated, status_code=201)
def create_proposal(body: ProposalCreate) -> ProposalCreated:
    """SRS-APR-IF-01/F-01. Caller: agent workload identity only (SEC-03).
    A replayed idempotency_key for the same originating_session_id
    returns the existing proposal's current state instead of creating a
    duplicate (SRS-APR-F-07)."""
    raise NotImplementedError("D1 implementation step")


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
    raise NotImplementedError("D1 implementation step")


@app.get("/proposals", response_model=list[ProposalSummary])
def list_pending_proposals(
    originating_session_id: str | None = None, originating_request_id: str | None = None
) -> list[ProposalSummary]:
    """SRS-APR-IF-04/F-06. Lists proposals currently `pending`, filterable
    by session/request id; full decision-context fields per F-05."""
    raise NotImplementedError("D1 implementation step")


@app.get("/proposals/{proposal_id}", response_model=ProposalTerminal)
def get_proposal(proposal_id: str) -> ProposalTerminal:
    """SRS-APR-IF-05. Current state; once terminal, the full record
    including the *unmodified* `action_arguments` accepted at intake --
    this is what agent/approval_client.py's terminal-state query calls
    from the /resume handler, and the exact arguments DEC-008 requires
    the agent to execute (never a locally cached copy)."""
    raise NotImplementedError("D1 implementation step")
