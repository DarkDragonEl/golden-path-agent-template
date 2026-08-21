from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from . import routers
from .nodes.decide import decide_node
from .nodes.fallback import fallback_node
from .nodes.generate import generate_node
from .nodes.human_approval import human_approval_node
from .nodes.retrieve import retrieve_node
from .nodes.tool_invoke import tool_invoke_node
from .state import AgentState


def build_graph():
    """decide -> (tool_invoke -> (human_approval -> respond|fallback) | respond) |
                  (retrieve -> generate -> respond|fallback) | fallback

    DEC-013 candidate (decide-then-retrieve reordering): `decide` sees only
    the user query + both tool schemas + tool-selection/refusal/injection
    instructions -- no corpus context, no citation instructions -- so
    citation guidance can no longer compete with and beat tool-calling
    instructions for the model's attention (DEC-012's diagnosed root
    cause). Only the "no tool needed" branch retrieves; the retrieved
    context and citation instructions are `generate`'s job alone, in a
    second, separate model call made with no tool schemas at all.

    Compiled with interrupt_before=["human_approval"] so a consequential
    (write-classified) tool call actually pauses the graph rather than
    just recording that it should have.
    """
    graph = StateGraph(AgentState)
    graph.add_node("decide", decide_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("tool_invoke", tool_invoke_node)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("decide")
    graph.add_conditional_edges(
        "decide",
        routers.decide_after_decide,
        {"tool_invoke": "tool_invoke", "retrieve": "retrieve", "fallback": "fallback"},
    )
    graph.add_conditional_edges(
        "retrieve", routers.decide_after_retrieve, {"generate": "generate", "fallback": "fallback"}
    )
    graph.add_conditional_edges(
        "generate", routers.decide_after_generate, {"respond": END, "fallback": "fallback"}
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
