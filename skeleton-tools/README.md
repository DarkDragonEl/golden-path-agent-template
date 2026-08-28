# ${{ values.name }}

${{ values.description }}

Standalone MCP tool server, scaffolded from the Golden Path Agent
blueprint's Tools Template. This
repo produces one independently-built, independently-promoted artifact:
the tool server, nothing else. It has no agent and no approval-service
code -- an Agent Template instance consumes this server's contract
(`catalog-info.yaml`'s own `API` entity) over the network, never by
bundling this repo's source.

## Local development

```
make build   # build the container image
make up      # run it locally, port 18081 -> 8081
make test    # pytest, no cluster needed
make down    # stop the local container
```

Call a tool directly (bypassing the full MCP protocol session), the same
route CI's own operational test exercises:

```
curl -X POST http://localhost:18081/tools/healthcheck -d '{}'
```

## Deploying

`deploy/kustomize/base/` renders a Deployment, Service, ServiceAccount,
NetworkPolicy, PodDisruptionBudget, and ConfigMap. The NetworkPolicy
restricts ingress to one named consumer (`allowedConsumerName`, set at
scaffold time) -- see that file's own header comment for what this does
and does not cover (a single-consumer allow-list, not a real multi-tenant
ACL).

## What to fill in

See `TODO_DOMAIN.md` -- this scaffold ships with placeholder tools
(`placeholder_lookup`, `placeholder_write_action`) plus a worked example
domain (`itsm_search_records`, `itsm_create_request`, mock/seeded state)
to show the contract shape a real integration should follow.
