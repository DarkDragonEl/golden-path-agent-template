"""Conditional-edge routing functions for the graph built in
agent/graph.py — each takes the current `state` dict and returns the next
node's name (the StateGraph.add_conditional_edges destination key); none of
these mutate state.

decide_after_decide routes to "fallback" on total model failure or a
reasoning-step-limit breach (agent/policy.py::check_step_limit), to
"tool_invoke" when decide_node selected a tool, otherwise "retrieve".
decide_after_retrieve currently always routes to "generate" (TODO(domain):
route retrieval_unavailable to "fallback" once a domain requires it).
decide_after_generate mirrors decide_after_decide's fallback/step-limit
checks before "respond". decide_after_tool routes a failed tool call to
"fallback", a write-classified pending approval to "human_approval",
otherwise "respond". decide_after_approval routes to "fallback" only on a
fallback_reason set by human_approval_node, otherwise "respond".
"""

from . import policy


def decide_after_decide(state):
    if state.get("fallback_reason"):
        # decide_node sets this on total model failure (both routes
        # exhausted, or none configured) -- SysR-A-F-05/SysR-P-F-12.
        return "fallback"
    try:
        policy.check_step_limit(state)
    except policy.StepLimitExceeded:
        return "fallback"
    if state.get("selected_tool") is not None:
        return "tool_invoke"
    return "retrieve"


def decide_after_retrieve(state):
    # TODO(domain): if this agent's role requires retrieval to answer
    # safely, route retrieval_unavailable to "fallback" instead. Until
    # domain scope is defined, unavailability alone does not block
    # generation -- the "fallback" branch below exists for that future case.
    return "generate"


def decide_after_generate(state):
    if state.get("fallback_reason"):
        return "fallback"
    try:
        policy.check_step_limit(state)
    except policy.StepLimitExceeded:
        return "fallback"
    return "respond"


def decide_after_tool(state):
    last_call = state.get("tool_calls", [])[-1] if state.get("tool_calls") else None
    if last_call and last_call.get("error"):
        return "fallback"
    if state.get("pending_approval"):
        return "human_approval"
    return "respond"


def decide_after_approval(state):
    if state.get("fallback_reason"):
        return "fallback"
    return "respond"
