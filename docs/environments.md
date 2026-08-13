# Environments

| Stage | Purpose | What's here |
|---|---|---|
| Local laptop | Fast dev loop, deterministic testing | `scripts/dev.sh --offline` (plain `podman run`/`docker run`, no compose dependency), `.env.example` |
| PR CI | Basic correctness + the eval promotion gate | `ci/pr-checks.yaml`: `pytest` → `eval run --all` → container build → SBOM |
| Ephemeral test | Validate integrated behavior in a real (short-lived) namespace | `deploy/kustomize/overlays/ephemeral-test/`, `deploy/argocd/application-ephemeral-test.yaml` |
| Staging | Validate against approved staging data / real identity | `deploy/kustomize/overlays/staging/`, `deploy/argocd/application-staging.yaml` |
| Pilot production | Controlled, human-approval-gated value delivery | `deploy/kustomize/overlays/pilot-prod/`, `deploy/argocd/application-pilot-prod.yaml` |

## Promotion model

One image, one digest, promoted unchanged. `deploy/kustomize/base/kustomization.yaml`
pins the image by digest (`images:` block); CI updates only that digest.
Each overlay's `kustomization.yaml` never touches the image — only
environment-specific config (`configMapGenerator` with `behavior: merge`),
namespace, and replica count differ per environment. This was verified by
rendering all three overlays with `kubectl kustomize` and confirming the
digest, image name, and namespace come out identically shaped, only the
`ConfigMap` data and namespace differing.

GitOps promotion at this MVP's scale is three small `Application`
manifests pointed at three overlay paths — not an `ApplicationSet`
generator matrix. Ephemeral-test and staging sync automatically
(`prune: true, selfHeal: true`); **pilot-prod's `syncPolicy.automated` is
`null`** — a manual sync is the actual promotion gate into pilot
production.

## Ephemeral-test namespace lifecycle

`deploy/kustomize/overlays/ephemeral-test/namespace.yaml` creates the
`Namespace` object itself (the other two overlays only set `namespace:` on
existing resources — they assume the namespace already exists). It carries
`lifecycle/created-at` and `lifecycle/ttl` annotations that a
platform-level TTL garbage-collector (not part of this repo) is expected to
consume to delete stale ephemeral namespaces. `lifecycle/created-at` is a
placeholder the deploying pipeline must set to the real timestamp.

## Config that changes per environment

All of it lives in `deploy/kustomize/base/configmap.yaml` (defaults) and
each overlay's `configMapGenerator` literals (overrides):
`MODEL_API_BASE_URL`, `DATA_SOURCE_BINDING`, `APPROVAL_MODE`, `MCP_MODE`,
plus replica count via the `replicas:` transformer. None of it requires a
rebuild — this is the literal implementation of "environment differences
expressed through configuration."

## What's still a placeholder

Every model endpoint in the overlays is an `example.com` placeholder
(RFC 2606 reserved domain, chosen deliberately so it's obviously fake
rather than a real internal hostname). `REPLACE_WITH_GIT_REPO_URL` and
`REPLACE_WITH_GITOPS_NAMESPACE` in `deploy/argocd/*.yaml` need real values
once this scaffold has an actual repo and target cluster.
