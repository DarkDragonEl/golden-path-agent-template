# API reference (local preview only)

This page is rendered by [mkdocstrings](https://mkdocstrings.github.io/)
from every module's own docstring — it does **not** render on the live
RHDH TechDocs page (`docs/techdocs-preview.md` explains why). Run
`mkdocs serve -f mkdocs.local.yml` to view it.

## `agent/`

::: agent.api
::: agent.approval_client
::: agent.cli
::: agent.config
::: agent.graph
::: agent.model_client
::: agent.oidc_client
::: agent.policy
::: agent.retrieval_client
::: agent.routers
::: agent.state
::: agent.telemetry
::: agent.tool_result_format
::: agent.tool_schemas

### `agent/nodes/`

::: agent.nodes.decide
::: agent.nodes.fallback
::: agent.nodes.generate
::: agent.nodes.human_approval
::: agent.nodes.retrieve
::: agent.nodes.tool_invoke

## `mcp_server/`

::: mcp_server.auth
::: mcp_server.client
::: mcp_server.itsm_store
::: mcp_server.schemas
::: mcp_server.server

## `approval_service/`

::: approval_service.api
::: approval_service.auth
::: approval_service.config
::: approval_service.schemas
::: approval_service.store
::: approval_service.telemetry

## `eval/`

::: eval.cli
::: eval.config
::: eval.domain_executor
::: eval.domain_loader
::: eval.domain_scorer
::: eval.executor
::: eval.fake_approval_client
::: eval.loader
::: eval.reporter
::: eval.runner
::: eval.scorer
::: eval.validate
