# Corpus

Empty by design — this is a template, not a domain deployment.

Each document added here must carry:

- **Owner** — who is accountable for this content
- **Classification** — sensitivity/access level
- **Version / effective date**
- **Access policy** — who/what may retrieve it
- **Source** — where it came from
- **Refresh process** — how staleness gets caught

`seed/` is where locally-seeded documents live for local dev (bind-mounted
into the agent container at `AGENT_CORPUS_DIR`). `ingest.py` is a
TODO(domain) stub for the chunk/embed/load pipeline — see
[`../TODO_DOMAIN.md`](../TODO_DOMAIN.md).
