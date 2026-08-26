"""Retrieval node — runs only on decide_node's "no tool needed" branch
(DEC-013 candidate: decide-then-retrieve reordering), no longer the
graph's unconditional entry point.

Node contract: reads state["input_query"] and state.get("user_id"); returns
{"retrieved_docs": [...], "retrieval_unavailable": bool}. Calls
agent/retrieval_client.py::retrieve with config.RETRIEVAL_TOP_K as top_k;
any exception is caught and flagged via retrieval_unavailable rather than
raised, keeping the graph runnable if the corpus/manifest is unreadable.
"""

from .. import config
from ..retrieval_client import retrieve


def retrieve_node(state):
    """Runs only on decide_node's "no tool needed" branch (DEC-013
    candidate: decide-then-retrieve reordering) -- no longer the graph's
    unconditional entry point."""
    try:
        docs = retrieve(state["input_query"], top_k=config.RETRIEVAL_TOP_K, user_id=state.get("user_id"))
        return {"retrieved_docs": [d.__dict__ for d in docs], "retrieval_unavailable": False}
    except Exception:  # noqa: BLE001 - catch-and-flag, not raise: keeps the graph
        # runnable even if the corpus/manifest is unreadable, instead of crashing.
        return {"retrieved_docs": [], "retrieval_unavailable": True}
