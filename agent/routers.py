"""Conditional-edge predicates for `agent/graph.py`'s `StateGraph`.

Contract: each function takes the current `agent/state.py::AgentState`
and returns the name of the next node to run (a string matching one of
the branch keys `graph.add_conditional_edges` registers for that source
node in `agent/graph.py::build_graph`) -- never a state mutation. All
five together implement the golden path's routing: total model failure
or an exceeded `MAX_REASONING_STEPS` (`agent/policy.py::check_step_limit`)
routes to `fallback` from `decide`/`generate`; a failed tool call or a
pending write-approval routes from `tool_invoke`; every other case
routes to `respond` (graph `END`).
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
