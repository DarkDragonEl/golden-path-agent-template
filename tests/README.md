# `tests/`

Pytest suite covering `agent/`, `approval_service/`, and `mcp_server/`
in-process — graph topology and node behavior, the approval service's
API and telemetry, MCP auth/contract/client-OIDC, policy limits and
write-gating, model/retrieval clients, and `tools/trace-check` itself
(`test_trace_check.py`). Fully offline and deterministic: no live model,
no cluster, no network access required.

**Consumed by**: `make test` (`pytest -q`, a human developer's inner
loop) and `pipelines/tasks/unit-tests.yaml` (the same command as a CI
gate, before any image is built).

See the [documentation hub](../docs/README.md) and
[`docs/testing-perspectives-guide.md`](../docs/testing-perspectives-guide.md)
for how this suite fits alongside the other five verification mechanisms
(offline eval, live eval, direct HTTP chat, operational tests,
trace-check).
