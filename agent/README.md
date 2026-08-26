# `agent/`

Source for the one LangGraph agent in this golden path: the graph
(`graph.py`, `nodes/`), the model/retrieval/tool/approval clients
(`model_client.py`, `retrieval_client.py`, `approval_client.py`,
`oidc_client.py`), the HTTP surface (`api.py`, `routers.py`), the
single-shot CLI (`cli.py`), policy/state (`policy.py`, `state.py`,
`config.py`), telemetry (`telemetry.py`), prompts (`prompts/`), and the
approver UI's static assets (`static/`).

**Consumed by**: `Containerfile.agent` (builds the image),
`deploy/kustomize/base/deployment-agent.yaml` (deploys it),
`scripts/dev.sh`/`make up` (runs it locally), `tests/` and `eval/`
(exercise it without a server), and a human operator via `agent/cli.py`
or `POST /invoke` directly.

See the [documentation hub](../docs/README.md) for the full picture,
[`docs/architecture.md`](../docs/architecture.md) for the graph shape and
contract boundaries, and [`mcp_server/README.md`](../mcp_server/README.md) /
[`approval_service/README.md`](../approval_service/README.md) for the two
services this component calls.
