"""Field-for-field per srs/SRS-APR.md's Interfaces section (IF-01..05).
SRS-APR-IF-01 is the single authoritative schema for proposal submission
-- agent/approval_client.py and this module's ProposalCreate must stay in
sync with it in the same PR, per SRS-AGT-IF-05's own same-PR sync rule.

Contracts-STOP artifact (DEC-045): schemas only, no business logic here.
"""

from typing import Literal

from pydantic import BaseModel, Field

ProposalState = Literal["pending", "approved", "rejected", "expired"]
Decision = Literal["approve", "reject"]


class ProposalCreate(BaseModel):
    """SRS-APR-IF-01. Missing required field -> the endpoint returns 422
    and creates no record (SRS-APR-F-01)."""

    action_type: str
    target_system_id: str
    action_arguments: dict
    evidence_refs: list[str] = Field(default_factory=list)
    initiating_user_id: str
    agent_workload_id: str
    originating_session_id: str
    originating_request_id: str
    idempotency_key: str | None = None  # SRS-APR-F-07


class ProposalCreated(BaseModel):
    proposal_id: str
    state: ProposalState


class ProposalDecision(BaseModel):
    """SRS-APR-IF-02. Deliberately carries no approver identity field --
    SRS-APR-SEC-03: the approver identity is established from the
    validated bearer token, never a client-supplied claim."""

    decision: Decision


class ProposalDecided(BaseModel):
    proposal_id: str
    state: ProposalState
    decided_by: str
    decided_at: str  # ISO 8601
    decision: Decision


class ProposalRefused(BaseModel):
    """Returned (409) when a decision targets a non-pending proposal --
    SRS-APR-F-02's duplicate/late-decision refusal, audit-logged as a
    refused attempt, not silently ignored."""

    proposal_id: str
    state: ProposalState  # the proposal's actual current state


class ProposalSummary(BaseModel):
    """SRS-APR-IF-04/F-06 (pending list) and the pending-state shape of
    SRS-APR-IF-05 -- full decision-context fields, per SRS-APR-F-05."""

    proposal_id: str
    state: ProposalState
    action_type: str
    target_system_id: str
    action_arguments: dict
    evidence_refs: list[str]
    initiating_user_id: str
    agent_workload_id: str
    originating_session_id: str
    originating_request_id: str


class ProposalTerminal(ProposalSummary):
    """SRS-APR-IF-05, terminal-state shape. `action_arguments` (inherited
    from ProposalSummary) is the *unmodified* value accepted at intake --
    what agent/approval_client.py's terminal-state query returns to the
    /resume handler for an `approved` proposal (DECISIONS.md DEC-008)."""

    decided_by: str | None = None
    decided_at: str | None = None  # ISO 8601
