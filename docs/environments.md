# Environments

**On the SNO target being a shared, multi-tenant lab cluster, not a
dedicated one (`DECISIONS.md` `DEC-024`):** the accepted delivery plan
assumed Phase C would bootstrap a dedicated SNO from Git alone, operators
included. The real target is a shared lab cluster where the OpenShift
Pipelines and GitOps operators were already installed by prior, unrelated
work, before this project ever touched it. Consequence, stated plainly
rather than left for a colleague to notice: this project's own
namespaces/RBAC/`AppProject`/pipeline/policy bundle all do bootstrap from
Git as designed, but **operator installation does not** — installing or
reinstalling cluster-wide operators on a shared, busy cluster is outside
this project's authority and would itself be a blast-radius risk. Phase
E's shared showcase cluster is therefore the first and only full
from-scratch bootstrap test (operators included) — that raises the bar for
what "exercised ≥2 refreshes" needs to mean at that milestone, since Phase
C alone cannot prove the operator-install leg of the story.

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

`deploy/kustomize/overlays/ephemeral-test/namespace.yaml` declares the
`Namespace` object (the other two overlays only set `namespace:` on
existing resources — they assume the namespace already exists), but on the
real SNO target this object is created once, out of band
(`pipelines/bootstrap/namespaces.yaml`, applied manually — see the Phase C
runbook), not per `PipelineRun` and not TTL-garbage-collected.

**This is a deliberate deviation from the original design** (`DECISIONS.md`
`DEC-024`), driven by RBAC, not convenience: creating/deleting a `Namespace`
is a cluster-scoped action that a namespace-scoped `Role`/`RoleBinding`
cannot grant (Kubernetes RBAC's `create` verb has no `resourceNames`
restriction, since the target doesn't exist yet at authorization-check
time), and the Phase C pipeline's own `ServiceAccount` is deliberately
granted zero cluster-scoped permissions — no `ClusterRoleBinding`, no
cluster-admin — regardless of what a human operator's own session could do
(`pipelines/bootstrap/rbac.yaml`'s header). **"Ephemeral" now means
ephemeral resources inside a stable namespace**: `deploy-ephemeral`/
`destroy-ephemeral` cycle the `Deployment`/`Service`/`ConfigMap` objects on
every `PipelineRun`; the `Namespace` itself persists across runs, and
nothing deletes it on a TTL. `deploy/kustomize/overlays/ephemeral-test/namespace.yaml`
carries no `lifecycle/*` annotation for exactly this reason: it is
re-applied every run (`kubectl apply -k`, not a one-time action), so a
static timestamp there would be overwritten back to itself on every
apply rather than ever reflecting the real, one-time bootstrap event.

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
