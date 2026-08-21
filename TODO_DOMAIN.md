# Domain TODOs

This scaffold is deliberately use-case-independent. Everything below is a
placeholder that a future implementer (or a different client engagement
reusing this template) must fill in before this agent does anything
domain-specific.

Two TODO conventions are used throughout the codebase — know the difference
before touching either:

- **`raise NotImplementedError("TODO(domain): ...")`** — an interface that
  is unsafe to silently fake. Calling it without implementing it is a bug,
  not a degraded mode.
- **catch-and-flag** — a graph node that calls one of the above, catches the
  `NotImplementedError`, and sets a state flag (e.g. `retrieval_unavailable`)
  so the graph keeps running and routes to the deterministic fallback
  instead of crashing. This is what lets `eval run --all` pass today with
  zero domain content.

| Location | What to fill in |
|---|---|
| `corpus/` (entire directory) | The curated RAG corpus: real documents, `ingest.py`'s chunking/embedding logic, and per-document metadata (owner, classification, version/effective date, access policy, source, refresh process) |
| `agent/retrieval_client.py::retrieve()` | Connection to the real retrieval API / vector store. Contract (`RetrievedChunk`) is frozen — implement the body, don't change the shape |
| `agent/prompts/decide_system_prompt.md` / `agent/prompts/generate_system_prompt.md` | The agent's one business role, one knowledge domain, tone, and refusal/escalation instructions — split across the tool-decision call and the citation-bearing answer call (DEC-013 candidate, DECISIONS.md DEC-012) |
| `mcp_server/schemas.py::PlaceholderLookupInput` / `PlaceholderLookupOutput` | The real tool's actual input/output fields, once the 1-2 domain tools are selected |
| `mcp_server/server.py::placeholder_lookup()` (the `raise NotImplementedError` branch) | The real call to the enterprise tool this agent integrates with (auth, error handling, argument mapping) |
| `agent/nodes/tool_invoke.py` (argument construction) | Map agent state to the real tool's input schema once it exists |
| `agent/policy.py::classify_action()` | The real consequential-action taxonomy for this agent's tool(s) — today it only distinguishes on an explicit `write` flag |
| `eval/cases/` | Real domain golden-set cases: answer correctness, retrieval relevance, citation quality, tool-argument correctness, refusal/escalation behavior, prompt-injection resistance |
| `deploy/kustomize/base/configmap.yaml` + `deploy/kustomize/overlays/*/kustomization.yaml` | Real `DATA_SOURCE_BINDING` and `MODEL_API_BASE_URL` values per environment |
