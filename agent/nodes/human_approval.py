"""The human-approval (HITL) gate. Functional control flow — not a TODO.

The graph is compiled with interrupt_before=["human_approval"], so execution
actually pauses before this node runs whenever tool_invoke sets
pending_approval=True. Resuming requires an external caller to set
approval_decision via graph.update_state(...) and then call
graph.invoke(None, thread_config) — see agent/api.py's
POST /approvals/{session_id}/resume.

Phase B2 restructure: this node is now the sole invoker of a
write-classified tool call, and only on an "approve" decision (SRS-AGT-F-04,
SRS-MIT-SEC-01 — tool_invoke_node never calls a write-classified tool
itself, it only drafts). On approve, the tool is invoked with exactly the
arguments persisted in `approval_action` at draft time — read back from the
graph's own checkpointed state, never from a node-scope variable or
re-derived from anything else (DECISIONS.md DEC-008). This is the Phase B
interim realization of what a standalone approval service's terminal-state
query (Phase D, SRS-APR-IF-05) will source the arguments from instead; the
invariant — execute exactly the approved arguments, from the persisted
record, not a cached copy — is identical in both phases.
"""

from .. import config
from ..tool_result_format import format_tool_result
from mcp_server.client import call_tool


def human_approval_node(state):
    decision = state.get("approval_decision")

    if decision is None and config.AUTO_APPROVE_IN_DEV:
        # Dev-only convenience so `--offline` runs don't require a second
        # call. Never set true in staging/pilot-prod overlay configmaps.
        decision = "approve"

    if decision == "approve":
        approval_action = state.get("approval_action") or {}
        tool_name = approval_action.get("tool_name")
        arguments = approval_action.get("arguments", {})

        try:
            result = call_tool(tool_name, arguments, timeout=config.TOOL_TIMEOUT_SECONDS)
            error = None
        except Exception as exc:  # noqa: BLE001 - tool failures route to fallback, not a crash
            result = None
            error = str(exc)

        tool_calls = state.get("tool_calls", []) + [
            {"tool_name": tool_name, "arguments": arguments, "result": result, "error": error}
        ]
        if error:
            return {
                "tool_calls": tool_calls,
                "pending_approval": False,
                "fallback_reason": f"tool_error:{error}",
            }

        final_output = format_tool_result(tool_name, result)
        return {"tool_calls": tool_calls, "final_output": final_output, "pending_approval": False}

    return {
        "pending_approval": False,
        "fallback_reason": f"approval_not_granted:{decision!r}",
    }
