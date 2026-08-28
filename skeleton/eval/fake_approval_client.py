"""In-process test double for agent.approval_client.

tool_invoke_node's write branch submits a real proposal to the
standalone approval service over HTTP.
Contexts that must not depend on a live approval_service -- the eval
harness (eval/domain_executor.py, driving the eval-gate-offline/
eval-gate-live CI stages) and plain pytest unit/integration tests --
patch agent.approval_client.submit_proposal/get_proposal with this
fake instead, mirroring eval/domain_executor.py's own _apply_fault
pattern for the mock ITSM store/model client.

Deliberately does NOT reimplement approval_service's own atomicity/
persistence logic (tests/test_approval_service.py already covers that
in isolation, against the real store) -- this only needs to support the
single-proposal-at-a-time sequential pattern an eval case or a graph-level
test actually exercises: submit, then (via .decide(), a test-only helper
not part of the real IF-02 contract) simulate an approver's decision, then
query the terminal state.
"""

import uuid
from datetime import datetime, timezone


class FakeApprovalService:
    def __init__(self):
        self._proposals: dict[str, dict] = {}

    def submit_proposal(self, *, action_arguments: dict, **_ignored) -> dict:
        proposal_id = str(uuid.uuid4())
        self._proposals[proposal_id] = {
            "proposal_id": proposal_id,
            "state": "pending",
            "action_arguments": action_arguments,
            "decided_by": None,
            "decided_at": None,
        }
        return {"proposal_id": proposal_id, "state": "pending"}

    def get_proposal(self, proposal_id: str, **_ignored) -> dict:
        return self._proposals[proposal_id]

    def decide(self, proposal_id: str, decision: str, approver_id: str = "eval-harness-approver") -> dict:
        """Test-only helper, not part of the real SRS-APR-IF-02 contract
        -- lets a case simulate an approver's decision (or a synthetic
        expiry) without a real HTTP call. `decision` is the approval
        service's own state vocabulary ("approved"/"rejected"/"expired"),
        matching schemas.py's ProposalState, not the caller's verb."""
        record = self._proposals[proposal_id]
        record["state"] = decision
        if decision == "approved":
            record["decided_by"] = approver_id
            record["decided_at"] = datetime.now(timezone.utc).isoformat()
        return record
