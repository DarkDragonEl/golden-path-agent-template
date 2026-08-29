"""Shared state schema for the LangGraph graph assembled in agent/graph.py.

AgentState is a TypedDict with total=False: every node function in
agent/nodes/*.py receives the accumulated state dict and returns only the
subset of keys it updates, which LangGraph merges into the run's
checkpointed state rather than requiring each node to return the full
state. ToolCallRecord and ModelCallRecord are the per-call telemetry
shapes appended to state["tool_calls"] / state["model_calls"] (ADR-006:
per-call, not just a final summary). See each field's own inline comment for
the specific node that sets it and the ADR it traces to — notably
ADR-001/ADR-002 governing approved_action/drafted_action/
model_calls.
"""

from typing import Any, Literal, Optional, TypedDict


class ToolCallRecord(TypedDict):
    tool_name: str
    arguments: dict
    result: Optional[dict]
    error: Optional[str]
    classification: str  # "read" | "write" -- agent/policy.py::classify_action's result
    # ADR-006: surfaced per call, not just the final approve/reject outcome.


class ModelCallRecord(TypedDict):
    node: str  # "decide" | "generate"
    route: str  # "primary" | "fallback" | "none" (total failure)
    reason_code: str  # SysR-P-F-12 reason code, or "model_failure:<ExcType>" on total failure
    prompt_tokens: Optional[int]  # R4/ADR-006: SRS-AGT-IF-08 "token consumption" -- None when
    completion_tokens: Optional[int]  # the backend doesn't report usage (e.g. FakeModelClient,
    total_tokens: Optional[int]  # or a route that failed before any response was returned).
    response_model: Optional[str]  # Post-Checkpoint-C backlog item 1: the model identity the
    # backend's own response reported for this specific call -- None for FakeModelClient or a
    # route that failed before any response was returned. Read-only telemetry (see
    # agent/model_client.py's own comment); never used to alter a request.


class AgentState(TypedDict, total=False):
    session_id: str
    request_id: str  # ADR-001: threaded into state (previously api.py-local
    # only) so tool_invoke_node can supply SRS-APR-IF-01's originating_request_id.
    user_id: str
    input_query: str
    write_requested: bool
    messages: list
    retrieval_unavailable: bool
    retrieved_docs: list
    reasoning_steps: int
    selected_tool: Optional[dict]  # {tool_name, arguments} or None -- set by decide_node
    model_calls: list[ModelCallRecord]  # ADR-002/ADR-006 compensating control -- one
    # entry per model call this turn; model_route/reason_code below are last-write-wins
    # scalars that would hide an earlier call's route otherwise. See
    # eval/domain_scorer.py::check_dec009_route_assertion.
    model_route: Optional[str]  # "primary" | "fallback" | "none" -- last call only, convenience
    model_route_reason_code: Optional[str]  # ditto, last call only
    tool_calls: list[ToolCallRecord]
    pending_approval: bool
    proposal_id: Optional[str]  # ADR-001: the approval service's own identifier for the
    # submitted proposal (SRS-APR-IF-01), set by tool_invoke_node at submission time -- what
    # agent/approval_client.py::resolve_and_resume's IF-05 query is correlated by.
    drafted_action: Optional[dict]  # {tool_name, arguments} -- set by tool_invoke_node at draft/
    # submission time. Kept ONLY for audit/evidence display (what was proposed); never read by the
    # execution path (human_approval_node) again after submission -- see approved_action below.
    approved_action: Optional[dict]  # {tool_name, arguments, proposal_id, approver_id, decided_at}
    # -- set ONLY by resolve_and_resume from the approval service's IF-05 response. Structural
    # enforcement of ADR-001: never drafted_action, never a locally cached copy.
    approval_decision: Optional[Literal["approved", "rejected", "expired"]]  # the approval
    # service's own state vocabulary (schemas.py's ProposalState), not the caller's verb -- this
    # is a recorded OUTCOME, sourced from resolve_and_resume, never a client-supplied command.
    final_output: Optional[str]
    fallback_reason: Optional[str]
