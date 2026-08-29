# Architecture Decision Records

Load-bearing design choices for this blueprint. Each ADR states the
decision and its consequences — the debugging story behind it lives in
the sibling `agent-roadmap` repository's `DECISIONS.md`, cited by each
ADR's own `Journal:` line.

| ADR | Title |
|---|---|
| [ADR-001](ADR-001-single-approval-gated-write-path.md) | Single approval-gated write path |
| [ADR-002](ADR-002-route-assertion-via-call-list.md) | Route assertion via call list |
| [ADR-003](ADR-003-model-swap-five-category-acceptance-gate.md) | Model-swap five-category acceptance gate |
| [ADR-004](ADR-004-prompt-and-model-params-as-measurement-instrument.md) | Prompt and model params as measurement instrument |
| [ADR-005](ADR-005-decide-generate-prompt-split.md) | Decide/generate prompt split |
| [ADR-006](ADR-006-otel-read-only-and-independently-sourced.md) | OTel read-only and independently sourced |
| [ADR-007](ADR-007-eval-gate-exception-allowlist-convention.md) | Eval-gate exception allowlist convention |
| [ADR-008](ADR-008-identity-config-contract-enforcement.md) | Identity/config contract enforcement |
| [ADR-009](ADR-009-single-pin-single-active-cluster.md) | Single-pin, single-active-cluster |
| [ADR-010](ADR-010-explicit-kubeconfig-context-required.md) | Explicit kubeconfig context required |
| [ADR-011](ADR-011-three-image-split.md) | Three-image split |
| [ADR-012](ADR-012-platform-foundation-shared-approval-service.md) | Platform Foundation shared approval service |
| [ADR-013](ADR-013-gitea-as-in-repo-git-provider.md) | Gitea as in-repo Git provider |
| [ADR-014](ADR-014-eval-only-fault-injection-fixture.md) | Eval-only fault-injection fixture |
| [ADR-015](ADR-015-techdocs-pinning-and-local-builder.md) | TechDocs pinning and local builder mode |
| [ADR-016](ADR-016-route-over-ingress-for-owner-facing-entry-points.md) | Route over Ingress for owner-facing entry points |
| [ADR-017](ADR-017-keycloak-deployment-and-secret-rotation.md) | Keycloak deployment and secret rotation |
| [ADR-018](ADR-018-ci-pipeline-ephemeral-architecture.md) | CI pipeline ephemeral architecture |
| [ADR-019](ADR-019-build-and-ci-discipline-tooling.md) | Build and CI discipline tooling |
| [ADR-020](ADR-020-otel-collector-deployment.md) | OTel Collector deployment |
| [ADR-021](ADR-021-scaffolding-and-gitea-publish.md) | Scaffolding and Gitea publish |
| [ADR-022](ADR-022-skeleton-design.md) | Skeleton design |
| [ADR-023](ADR-023-platform-catalog-entity-model.md) | Platform catalog entity model |
| [ADR-024](ADR-024-static-html-approver-ui.md) | Static HTML approver UI |
| [ADR-025](ADR-025-approval-service-rest-contracts.md) | Approval service REST contracts |

## Not here — process decisions, stay in the journal

Two candidates turned out to be process decisions rather than product
architecture, and stay in `agent-roadmap/DECISIONS.md` only:

- `DEC-099` — how this project's own parallel build streams were
  organized; nothing about the shipped artifact depends on it. Process
  decisions like this are recorded in the roadmap repository, not here.
- `DEC-087` — an owner decision bundling seven unrelated sub-items; the
  four with lasting design content were distributed into the ADRs above
  (Ingress/Route into ADR-016, Keycloak auth wiring into ADR-017,
  publish scope into ADR-021, templating engine into ADR-022); the
  remaining three (an `OI-04` trigger threshold — moot, `OI-04` is
  closed; a namespace name; a catalog-absence fallback found moot the
  same session) have no lasting design content to distill.
