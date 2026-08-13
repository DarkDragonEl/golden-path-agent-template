"""The human-approval (HITL) gate. Functional control flow — not a TODO.

The graph is compiled with interrupt_before=["human_approval"], so execution
actually pauses before this node runs whenever tool_invoke sets
pending_approval=True. Resuming requires an external caller to set
approval_decision via graph.update_state(...) and then call
graph.invoke(None, thread_config) — see agent/api.py's
POST /approvals/{session_id}/resume.
"""

from .. import config


def human_approval_node(state):
    decision = state.get("approval_decision")

    if decision is None and config.AUTO_APPROVE_IN_DEV:
        # Dev-only convenience so `--offline` runs don't require a second
        # call. Never set true in staging/pilot-prod overlay configmaps.
        decision = "approve"

    if decision == "approve":
        last_call = state.get("tool_calls", [])[-1] if state.get("tool_calls") else None
        result = last_call.get("result") if last_call else None
        final_output = result.get("result", "") if isinstance(result, dict) else str(result)
        return {"final_output": final_output, "pending_approval": False}

    return {
        "pending_approval": False,
        "fallback_reason": f"approval_not_granted:{decision!r}",
    }
