# `tools/`

One-off and standalone operator tooling that isn't part of the running
agent, the eval harness, or `tests/`: live-verification scripts
(`verify_owner_walkthrough.py`, `browser_verify_owner_walkthrough.py`,
`verify_skeleton.py`), diagnostics written during specific incident
investigations (`diagnose_*.py`), the Scaffolder-adjacent publishing/
instantiation helpers (`gitea_publish.py`, `instantiate_agent_project.py`,
`skeleton_renderer.py`), `query_traces.py` (OTel trace inspection),
`provision-demo-credentials.sh`/`get-test-user-credential.sh` (demo/test
credential provisioning and self-service reset — see
`docs/access-and-credentials.md`), and `trace-check/` (the
SyRS→StRS→SRS traceability validator, see `srs/README.md`).

**Consumed by**: a human operator or developer, invoked directly
(`python tools/<script>.py` / `./tools/<script>.sh`) — nothing here is
imported by `agent/`, `mcp_server/`, or `approval_service/` at runtime.

See the [documentation hub](../docs/README.md),
[`docs/access-and-credentials.md`](../docs/access-and-credentials.md)
for the credential-management scripts' full model (both mutate the live
cluster — read that page before running either), and
[`srs/README.md`](../srs/README.md) for what `trace-check/` validates.
