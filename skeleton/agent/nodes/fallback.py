"""Deterministic fallback — the proposal's required "deterministic fallback
when the agent cannot proceed safely." Reached on step-limit, tool error, or
a rejected/withheld approval decision.
"""


def fallback_node(state):
    reason = state.get("fallback_reason")
    if not reason:
        last_call = state.get("tool_calls", [])[-1] if state.get("tool_calls") else None
        if last_call and last_call.get("error"):
            reason = f"tool_error:{last_call['error']}"
        else:
            reason = "max_reasoning_steps_exceeded"

    message = (
        "This request could not be completed safely right now "
        f"(escalation reason: {reason}). A human should review this session."
    )
    return {"final_output": message, "fallback_reason": reason}
