from typing import Any, Literal, Optional, TypedDict


class ToolCallRecord(TypedDict):
    tool_name: str
    arguments: dict
    result: Optional[dict]
    error: Optional[str]
    classification: str  # "read" | "write" -- agent/policy.py::classify_action's result
    # (R4/DEC-020: SRS-AGT-IF-08 "every policy decision" -- surfaced in telemetry per call,
    # not just the final approve/reject outcome).


class ModelCallRecord(TypedDict):
    node: str  # "decide" | "generate"
    route: str  # "primary" | "fallback" | "none" (total failure)
    reason_code: str  # SysR-P-F-12 reason code, or "model_failure:<ExcType>" on total failure
    prompt_tokens: Optional[int]  # R4/DEC-020: SRS-AGT-IF-08 "token consumption" -- None when
    completion_tokens: Optional[int]  # the backend doesn't report usage (e.g. FakeModelClient,
    total_tokens: Optional[int]  # or a route that failed before any response was returned).


class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    input_query: str
    write_requested: bool
    messages: list
    retrieval_unavailable: bool
    retrieved_docs: list
    reasoning_steps: int
    selected_tool: Optional[dict]  # {tool_name, arguments} or None -- set by decide_node
    model_calls: list[ModelCallRecord]  # DEC-009 compensating control's source of truth -- one
    # entry per model call this turn (decide, and generate when reached); see
    # eval/domain_scorer.py::check_dec009_route_assertion. AgentState has no reducer
    # annotations, so model_route/model_route_reason_code below are last-write-wins scalars
    # and would silently hide an earlier call's route once a turn makes more than one --
    # this list is what makes both calls' routing independently verifiable.
    model_route: Optional[str]  # "primary" | "fallback" | "none" -- last call only, convenience
    model_route_reason_code: Optional[str]  # ditto, last call only
    tool_calls: list[ToolCallRecord]
    pending_approval: bool
    approval_action: Optional[dict]
    approval_decision: Optional[Literal["approve", "reject"]]
    final_output: Optional[str]
    fallback_reason: Optional[str]
