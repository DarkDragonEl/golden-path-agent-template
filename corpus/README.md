# Corpus

Populated at Phase B3.5 with this blueprint's own synthetic demo corpus
(20 documents, `corpus/seed/*.md`) — the ITSM scenario per Annex A OI-02,
identities fixed in `eval/corpus-manifest.yaml`. A second adopting team
replaces this content with its own domain's documents; the mechanism
(`corpus/ingest.py`, `agent/retrieval_client.py`) stays the same.

Each document added here must carry:

- **Owner** — who is accountable for this content
- **Classification** — sensitivity/access level
- **Version / effective date**
- **Access policy** — who/what may retrieve it
- **Source** — where it came from
- **Refresh process** — how staleness gets caught

`seed/` is where locally-seeded documents live for local dev (bind-mounted
into the agent container at `AGENT_CORPUS_DIR`). `ingest.py` joins each
`eval/corpus-manifest.yaml` entry with its `seed/<doc_id>.md` body text
and gates retrievability on governance-metadata completeness
(`SRS-RET-F-01`) — no chunk/embed/vector-store pipeline; retrieval
(`agent/retrieval_client.py`) is lexical keyword-overlap, sufficient for
20 documents (Phase B3.5 scope decision — escalate to a real vector store
only if that stops being true).
