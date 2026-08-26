# `mcp_server/`

Source for the one MCP tool server in this golden path (`server.py`,
`schemas.py`, `client.py`, `auth.py`, `itsm_store.py`) — a FastMCP
streamable-HTTP server exposing the mock ITSM tool contract. Named
`mcp_server`, not `mcp`, deliberately: a directory literally named `mcp`
at the repo root would shadow the installed `mcp` SDK package
(`docs/architecture.md` explains the exact `ModuleNotFoundError` this
avoids).

**Consumed by**: `Containerfile.mcp` (builds its own independent image),
`deploy/kustomize/base/deployment-mcp.yaml` (deploys it), and the agent
(`agent/nodes/tool_invoke.py` via `mcp_server/client.py` — always over
real HTTP in local dev and on cluster, `docs/local-dev.md`).

See the [documentation hub](../docs/README.md),
[`docs/architecture.md`](../docs/architecture.md)'s contract-boundaries
table for the tool/MCP contract, [`docs/glossary.md`](../docs/glossary.md)
for what "mock ITSM" means here, and
[`agent/README.md`](../agent/README.md) for this server's one caller.
