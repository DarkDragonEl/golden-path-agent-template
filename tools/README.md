# `tools/`

One-off and standalone operator tooling that isn't part of the running
agent, the eval harness, or `tests/`: live-verification scripts
(`verify_owner_walkthrough.py`, `browser_verify_owner_walkthrough.py`,
`verify_skeleton.py`), diagnostics written during specific incident
investigations (`diagnose_*.py`), the Scaffolder-adjacent publishing/
instantiation helpers (`gitea_publish.py`, `instantiate_agent_project.py`,
`skeleton_renderer.py`), `query_traces.py` (OTel trace inspection), and
`trace-check/` (the SyRS→StRS→SRS traceability validator, see
`srs/README.md`).

**Consumed by**: a human operator or developer, invoked directly
(`python tools/<script>.py`) — nothing here is imported by `agent/`,
`mcp_server/`, or `approval_service/` at runtime.

See the [documentation hub](../docs/README.md),
[`docs/access-and-credentials.md`](../docs/access-and-credentials.md)
for the two credential-management scripts that belong here conceptually
but are not yet tracked in this repository (flagged there, not linked),
and [`srs/README.md`](../srs/README.md) for what `trace-check/` validates.
