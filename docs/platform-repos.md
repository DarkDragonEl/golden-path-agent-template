# Platform repo topology

This blueprint, once bootstrapped, spans **three repo tiers**, not one.
`<adopter>` is a placeholder throughout — the same one-level-up
generalization of `docs/naming-conventions.md`'s
`golden-path-agent-<purpose>` namespace pattern — this page never names a
real organization.

## 1. The three tiers

| Tier | Identifier | Owner | Mutability |
|---|---|---|---|
| Blueprint | `golden-path-agent-template` | Blueprint maintainer | Read-only upstream for every adopter |
| Platform GitOps | `<adopter>-platform-gitops` | Each adopter, one per cluster | Adopter-owned; mutated only via a reviewed `open-promotion-pr` PR merge |
| Agent pair | `<name>` / `<name>-gitops` | Each scaffolded agent project | Adopter-owned; see `docs/adr/ADR-021-scaffolding-and-gitea-publish.md` |

The blueprint is **read-only upstream, unconditionally** — no cluster,
including this project's own showcase/demo-prod, syncs its live GitOps
state from this repo. That is what "read-only" means here: source of the
*recipe*, never the source ArgoCD reconciles against.

## 2. What stays in the blueprint

Everything not listed in §3 or §4 stays here, untouched by the split:
`agent/`, `mcp_server/`, `approval_service/`, `policy/`, `Containerfile.*`,
`pipelines/*.yaml` (Tekton Task/Pipeline *definitions*, applied by
bootstrap — never content the platform-gitops repo itself carries),
`skeleton/`, `skeleton-tools/`, `srs/`, `docs/`, `tools/`,
`scripts/bootstrap.sh`, `template.yaml` and `template-schema*.json`,
`eval/`, `tests/`, and `platform/bootstrap/` (Gitea/Keycloak/OTel install
manifests — cluster-bootstrap tooling, not GitOps-synced state).

## 3. What moves to `<adopter>-platform-gitops`

Extracted from this blueprint's current `deploy/` directory, unchanged in
content:

- `argocd/application-root.yaml`
- `argocd/apps/{demo-prod,rhdh,approval}.yaml`
- `argocd/application-{staging,pilot-prod,ephemeral-test}.yaml`
- `argocd/project.yaml`
- `kustomize/base/*` — including the three components' digest pins
  (`kustomization.yaml`'s `images:` block). Post-split, this is where the
  pins live — not in the blueprint.
- `kustomize/overlays/{approval-platform,demo-prod,ephemeral-test,pilot-prod,rhdh,staging}/*`
- `otel/otel-collector-config.yaml`

Two callouts, so extraction doesn't conflate them:

- `deploy/argocd/apps/demo-prod.yaml`'s own header comment travels
  unchanged with the file.
- `deploy/argocd/application-pilot-prod.yaml`'s deliberate
  `automated: null` is the **manual promotion gate** — a completely
  different `null` from the now-retired frozen-root `null` this same
  split retires (see `docs/adr/ADR-009-single-pin-single-active-cluster.md`,
  superseded). Only the frozen-root mechanism is retired; the pilot-prod
  manual gate is untouched.

## 4. Agent pairs (`<name>` / `<name>-gitops`)

Unchanged by this split — see
`docs/adr/ADR-021-scaffolding-and-gitea-publish.md` for the full design.
This page doesn't restate it: the platform-tier split described here
generalizes the same two-repo, Gitea-aware `open-promotion-pr` shape
already proved at the agent-pair tier, one level up, to the platform
itself.

## 5. The Git-provider contract

Three injected env vars, validated by `scripts/bootstrap.sh` at step 0
alongside the existing `MODEL_*` keys:

| Variable | Meaning | Default |
|---|---|---|
| `GIT_PROVIDER_URL` | Base URL of the Git host | Unset → the in-cluster Gitea this blueprint installs by default (`platform/bootstrap/gitea-cr.yaml`, pinned `v2.3.2`) |
| `GIT_PLATFORM_REPO` | The adopter's platform-gitops repo identifier (`<owner>/<adopter>-platform-gitops`) | — |
| `GIT_PROVIDER_TOKEN` | Promoter credential | Only used when `GIT_PROVIDER_URL` is external — bootstrap self-mints a minimum-scoped Gitea machine-account token when the default provider is in use |

Gitea is a platform dependency of three consumers under this contract:
ArgoCD's root source, `open-promotion-pr`, and RHDH's catalog/template
reads.

## 6. Naming convention

`<adopter>` is a placeholder throughout this document. An adopter names
their own platform-gitops repo `<their-chosen-name>-platform-gitops`,
following the same pattern `docs/naming-conventions.md` already documents
for this project's own `golden-path-agent-<purpose>` namespace, generalized
one level from "this project's own resources" to "an adopter's own
platform instance." This document never names a real organization.

## 7. Upstream-update path

Once an adopter's `<adopter>-platform-gitops` repo is seeded, it is
rendered once and then independently promoted — not a fork that tracks the
blueprint automatically. Pulling a newer blueprint's seed changes into an
already-diverged platform-gitops repo is a documented, manual procedure,
not automated tooling. Not yet written — tracked as future work alongside
the rest of this topology's build-out.
