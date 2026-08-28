# ADR-025: Approval Service REST Contracts

## Context
Every agent-proposed write requires human approval before it executes. That
approval flow needs a standalone service with a fixed contract the agent's
own resume logic depends on, plus a state, deployment, and RBAC shape
distinct from the agent's own, decided and validated before business logic
is written against it.

## Decision
The approval service is a separate FastAPI package (`approval_service/`)
exposing five endpoints — `POST /proposals`, `POST /proposals/{id}/decision`,
`GET /proposals`, `GET /proposals/{id}`, `GET /healthz` — backed by schemas
that carry no identity field on the decision itself. It persists to
SQLite-on-PVC, runs under Keycloak-issued auth with an `AUTH_MODE=none|oidc`
switch, and deploys via its own manifest set mirroring the agent's existing
shape. Approval resolution is client/UI-triggered polling against the
running service, not a push mechanism.

## Consequences
- `AUTH_MODE=none` must be structurally unable to reach the production
  environment, and an agent-issued token must not be able to decide its own
  proposal — both are required negative tests, not optional hardening.
- Approval expiry must survive a service restart; expiry state belongs to
  the persisted record, not in-memory process state.
- The agent-side resume mechanics that read/write approval state must land
  atomically together with this service's decision endpoint — splitting
  them has already been shown to silently drop state under the agent
  graph's typed-state channel behavior.
- The service's manifests exist in the deploy tree but stay out of the live
  Kustomize resource list until business logic is complete; adding them
  prematurely would deploy a non-functional service to a running,
  auto-syncing environment.

## Supersedes / Superseded-by
None.

## Journal
DEC-045
