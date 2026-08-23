"""The human-approval (HITL) gate. Functional control flow — not a TODO.

The graph is compiled with interrupt_before=["human_approval"], so execution
actually pauses before this node runs whenever tool_invoke sets
pending_approval=True. Resuming is agent/approval_client.py::resolve_and_resume's
job (called from agent/api.py's POST /approvals/{session_id}/resume) — it
queries the approval service's own terminal-state (SRS-APR-IF-05), and
only if that query reports a terminal state does it inject
approved_action/approval_decision into checkpointed state and call
graph.invoke(None, thread_config). This node never sees a client-supplied
decision (DECISIONS.md DEC-008/DEC-049) — it only ever reads what
resolve_and_resume already validated against the service.

Phase D graduation from Phase B2's interim mechanism: this node is still
the sole invoker of a write-classified tool call, and only when
approved_action is set (SRS-AGT-F-04, SRS-MIT-SEC-01 — tool_invoke_node
never calls a write-classified tool itself, it only drafts and submits).
On approval, the tool is invoked with exactly the arguments in
approved_action — set by resolve_and_resume from the approval service's
own IF-05 response, never from drafted_action (the node's own earlier
draft, kept only for audit display) or any other cached copy.
"""

from .. import config
from ..tool_result_format import format_tool_result
from mcp_server.client import call_tool


def human_approval_node(state):
    approved_action = state.get("approved_action")

    if approved_action is not None:
        tool_name = approved_action.get("tool_name")
        arguments = approved_action.get("arguments", {})

        try:
            result = call_tool(tool_name, arguments, timeout=config.TOOL_TIMEOUT_SECONDS)
            error = None
        except Exception as exc:  # noqa: BLE001 - tool failures route to fallback, not a crash
            result = None
            error = str(exc)

        tool_calls = state.get("tool_calls", []) + [
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
                "error": error,
                "classification": "write",
            }
        ]
        if error:
            return {
                "tool_calls": tool_calls,
                "pending_approval": False,
                "fallback_reason": f"tool_error:{error}",
            }

        final_output = format_tool_result(tool_name, result)
        return {"tool_calls": tool_calls, "final_output": final_output, "pending_approval": False}

    # rejected, expired, or (AUTO_APPROVE_IN_DEV aside) any other non-approved
    # outcome resolve_and_resume recorded -- SRS-APR-F-03: expired must be
    # indistinguishable from rejected w.r.t. execution side effects, and
    # both land here identically (no tool call either way).
    decision = state.get("approval_decision")
    return {
        "pending_approval": False,
        "fallback_reason": f"approval_not_granted:{decision!r}",
    }
