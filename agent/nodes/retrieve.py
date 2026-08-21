from .. import config
from ..retrieval_client import retrieve


def retrieve_node(state):
    try:
        docs = retrieve(state["input_query"], top_k=config.RETRIEVAL_TOP_K, user_id=state.get("user_id"))
        return {"retrieved_docs": [d.__dict__ for d in docs], "retrieval_unavailable": False}
    except Exception:  # noqa: BLE001 - catch-and-flag, not raise: keeps the graph
        # runnable even if the corpus/manifest is unreadable, instead of crashing.
        return {"retrieved_docs": [], "retrieval_unavailable": True}
