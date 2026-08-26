"""The `retrieve` LangGraph node: fetches corpus context ahead of
`generate_node`, reached only via `decide_node`'s "no tool needed" branch
(DEC-013's decide-then-retrieve reordering) -- no longer the graph's
unconditional entry point.

Contract: reads `state["input_query"]`/`state["user_id"]`; calls
`agent/retrieval_client.py::retrieve` with `config.RETRIEVAL_TOP_K`;
returns `retrieved_docs` (a list of dicts) and `retrieval_unavailable`.
Fails closed to an empty result with `retrieval_unavailable: True` rather
than raising, so an unreadable corpus/manifest degrades the run instead
of crashing the graph.
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
