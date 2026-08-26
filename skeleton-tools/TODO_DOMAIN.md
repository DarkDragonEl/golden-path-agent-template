# Domain TODOs

This scaffold is deliberately use-case-independent. Everything below is a
placeholder that a future implementer must fill in before this tool
server does anything domain-specific. This is the Tools Template's own
TODO list -- narrower than the Agent Template's, since this repo only
ever contains the tool server, not the agent's own retrieval/prompt/eval
concerns (see the Agent Template's own TODO_DOMAIN.md for those).

Two TODO conventions are used throughout the codebase -- know the
difference before touching either:

- **`raise NotImplementedError("TODO(domain): ...")`** -- an interface
  that is unsafe to silently fake. Calling it without implementing it is
  a bug, not a degraded mode.
- **catch-and-flag** -- the calling side (in the Agent Template's own
  repo) catches this and routes to a deterministic fallback instead of
  crashing.

| Location | What to fill in |
|---|---|
| `mcp_server/schemas.py::PlaceholderLookupInput` / `PlaceholderLookupOutput` | The real tool's actual input/output fields, once the 1-2 domain tools are selected |
| `mcp_server/server.py::placeholder_lookup()` / `placeholder_write_action()` (the `raise NotImplementedError` branches) | The real call to the enterprise tool this server integrates with (auth, error handling, argument mapping) |
| `mcp_server/itsm_store.py` | Replace with a real client/adapter for the actual backend this tool integrates with, or delete if the domain tools don't need seeded synthetic state |
| `catalog-info.yaml`'s `API` definition | Update the tool contract description once the real tools replace the placeholders |
| `deploy/kustomize/base/networkpolicy.yaml`'s `allowedConsumerName` | The real Agent Template instance(s) authorized to call this server -- see that file's own header comment for the single-consumer limitation |
