"""Retrieval API/library contract.

TODO(domain): this whole module is a placeholder. See TODO_DOMAIN.md.
"""

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    doc_id: str
    title: str
    snippet: str
    source_uri: str
    classification: str
    version: str


def retrieve(query: str, top_k: int = 5, filters: dict | None = None) -> list[RetrievedChunk]:
    """TODO(domain): connect to the real retrieval API / vector store.

    The contract is frozen: callers only depend on RetrievedChunk's fields
    (doc_id, title, snippet, source_uri, classification, version), so
    downstream policy/citation logic doesn't have to change when this is
    implemented.
    """
    raise NotImplementedError(
        "TODO(domain): implement retrieval against the real corpus/vector store."
    )
