from typing import Any, Literal, Optional, TypedDict


class ToolCallRecord(TypedDict):
    tool_name: str
    arguments: dict
    result: Optional[dict]
    error: Optional[str]


class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    input_query: str
    write_requested: bool
    messages: list
    retrieval_unavailable: bool
    retrieved_docs: list
    reasoning_steps: int
    tool_calls: list[ToolCallRecord]
    pending_approval: bool
    approval_action: Optional[dict]
    approval_decision: Optional[Literal["approve", "reject"]]
    final_output: Optional[str]
    fallback_reason: Optional[str]
