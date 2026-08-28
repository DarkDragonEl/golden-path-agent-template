"""The human-approval (HITL) gate. Functional control flow — not a TODO.

The graph is compiled with interrupt_before=["human_approval"], pausing
before this node whenever tool_invoke sets pending_approval=True.
approval_client.py::resolve_and_resume injects approved_action/
approval_decision from the approval service's own terminal-state query
before resuming -- this node never sees a client-supplied decision
(ADR-001).

Sole invoker of a write-classified tool call (SRS-AGT-F-04,
SRS-MIT-SEC-01), only when approved_action is set -- exactly the
arguments from resolve_and_resume's own IF-05 response, never
drafted_action (kept only for audit display).
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
