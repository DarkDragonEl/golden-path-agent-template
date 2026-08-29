# Architecture

One image, one runtime role: the MCP tool server (`mcp_server/`), nothing
else. This is a Tools Template
instance -- it is deliberately independent of any Agent Template
instance's own build/deploy/promote lifecycle. No agent code, no
approval-service code exists in this repo.

## Consumers

An Agent Template instance is this server's consumer, over the network
only (`MCP_TOOL_ENDPOINT`, configured on the agent's own side) -- it never
imports this repo's code. This repo's own `mcp_server/client.py`-shaped
calling surface does not exist here; that lives in the Agent Template,
which ships only the client half of the contract this server's
`catalog-info.yaml` `API` entity documents.

## Security boundary

`deploy/kustomize/base/networkpolicy.yaml` restricts ingress to one named
consumer (`allowedConsumerName`). `mcp_server/auth.py` adds a second,
application-level layer: per-request JWT audience validation when
`MCP_AUTH_MODE=oidc`. Neither is a real multi-tenant ACL yet -- see the
NetworkPolicy file's own header comment for what a genuinely shared,
multi-consumer instance would need (a G5/G6-era question, not solved
here).

## Testing

`pytest -q` (unit, no cluster) plus this repo's own CI pipeline
(`pipelines/pipeline.yaml`): build, unit-test, deploy to an ephemeral
namespace, then `mcp-operational-test.yaml` proves the NetworkPolicy
boundary and the real tool-dispatch route both work against the
freshly-deployed pod, using throwaway probe pods rather than a
co-deployed agent (this repo has none).
