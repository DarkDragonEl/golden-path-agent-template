"""TODO(domain): implement the chunk/embed/load ingestion pipeline that
populates the vector store agent/retrieval_client.py connects to.

Each ingested document must carry the metadata described in
corpus/README.md (owner, classification, version, access policy, source,
refresh process) — that is not optional per the proposal's curated-RAG-
corpus requirement.
"""


def ingest(source_dir: str) -> None:
    raise NotImplementedError("TODO(domain): implement corpus ingestion.")


if __name__ == "__main__":
    import sys

    ingest(sys.argv[1] if len(sys.argv) > 1 else "./seed")
