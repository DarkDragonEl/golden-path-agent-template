# ADR-023: Platform Catalog Entity Model

## Context
The platform needs a Backstage catalog model for its own foundation
services — the approval service and the model-routing layer — so they are
discoverable and their contracts are declared, not just implemented in code.
The model must be sourced from the real contracts (the approval service's
actual REST interface, the agent's actual routed-model client and its closed
reason-code set) rather than invented, and must not leak a specific model
identifier, matching the no-hardcoded-model rule already applied to agent
source.

## Decision
The catalog model is: a `System` entity for the Platform Foundation; a
`Component` plus an OpenAPI `API` entity for the approval service, sourced
from its actual route contract; and a shared OpenAI-compatible `API` plus
two `Resource` entities (primary/fallback) for the model routes, sourced
from the agent's actual client and reason-code set. Neither model-route
`Resource` names a specific model — route identity (primary/fallback) is
stable catalog metadata, the model behind it is injected configuration.
Every new entity uses the repository's single existing owner rather than
inventing a platform-team/agent-team distinction that has no referent yet.

## Consequences
- Catalog entities are validated only at schema/shape level (required
  fields, dangling references, OpenAPI parse); live RHDH registration is a
  separate, deferred step, not to be assumed complete until it is done.
- Relations to other entities (`consumesApis`/`dependsOn`) are not yet
  wired; a consuming stream must confirm the assumed naming convention, not
  treat it as already verified.
- A future multi-team scenario needing distinct ownership must introduce
  that distinction deliberately — it does not exist in this model.
- Adopters keep model identifiers out of catalog entities, as out of agent
  source; the catalog encodes route identity, not a model name.

## Supersedes / Superseded-by
None.

## Journal
DEC-102
