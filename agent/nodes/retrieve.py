from ..retrieval_client import retrieve


def retrieve_node(state):
    try:
        docs = retrieve(state["input_query"], top_k=5)
        return {"retrieved_docs": [d.__dict__ for d in docs], "retrieval_unavailable": False}
    except NotImplementedError:
        # Catch-and-flag, not raise: keeps the graph runnable with zero
        # domain content instead of crashing. See TODO_DOMAIN.md.
        return {"retrieved_docs": [], "retrieval_unavailable": True}
