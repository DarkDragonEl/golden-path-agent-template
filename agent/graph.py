from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from . import routers
from .nodes.fallback import fallback_node
from .nodes.human_approval import human_approval_node
from .nodes.reason import reason_node
from .nodes.retrieve import retrieve_node
from .nodes.tool_invoke import tool_invoke_node
from .state import AgentState


def build_graph():
    """retrieve -> reason -> (tool_invoke -> (human_approval -> respond|fallback) | respond) | fallback

    Compiled with interrupt_before=["human_approval"] so a consequential
    (write-classified) tool call actually pauses the graph rather than
    just recording that it should have.
    """
    graph = StateGraph(AgentState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason_node)
    graph.add_node("tool_invoke", tool_invoke_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("retrieve")
    graph.add_conditional_edges(
        "retrieve", routers.decide_after_retrieve, {"reason": "reason", "fallback": "fallback"}
    )
    graph.add_conditional_edges(
        "reason", routers.decide_after_reason, {"tool_invoke": "tool_invoke", "fallback": "fallback"}
    )
    graph.add_conditional_edges(
        "tool_invoke",
        routers.decide_after_tool,
        {"human_approval": "human_approval", "respond": END, "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "human_approval", routers.decide_after_approval, {"respond": END, "fallback": "fallback"}
    )
    graph.add_edge("fallback", END)

    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["human_approval"])
