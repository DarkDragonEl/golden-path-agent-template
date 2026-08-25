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

| Stage | Purpose | Deployed this milestone? | What's here |
|---|---|---|---|
| Local laptop | Fast dev loop, deterministic testing | yes | `scripts/dev.sh --offline` (plain `podman run`/`docker run`, no compose dependency), `.env.example` |
| PR CI | Basic correctness + the eval promotion gate | yes (as the real Tekton `Pipeline`, `pipelines/`, Step C1) | `ci/pr-checks.yaml`'s shape, realized: `unit-tests` → `eval-gate-offline`/`eval-gate-live` → `container-build` → `sbom-generate` |
| Ephemeral test | Validate integrated behavior in a real (short-lived) namespace, pre-promotion | yes | `deploy/kustomize/overlays/ephemeral-test/`, `deploy/argocd/application-ephemeral-test.yaml`; deployed directly by the pipeline's own `deploy-ephemeral` Task, not by ArgoCD sync — see the ownership model below for why |
| Demo production | The demo milestone's own promoted, always-on environment (`DECISIONS.md` `DEC-021`) | **yes — new at Step C4** | `deploy/kustomize/overlays/demo-prod/`, `deploy/argocd/apps/demo-prod.yaml`; ArgoCD-synced (`automated`, `selfHeal: true`) from the digest the promotion PR merge lands on `main` |
| Staging | Validate against approved staging data / real identity | **no — explicitly out of scope this milestone** | `deploy/kustomize/overlays/staging/`, `deploy/argocd/application-staging.yaml` (stub, un-synced, not part of the app-of-apps root) |
| Pilot production | Controlled, human-approval-gated value delivery | **no — explicitly out of scope this milestone** | `deploy/kustomize/overlays/pilot-prod/`, `deploy/argocd/application-pilot-prod.yaml` (stub, un-synced, not part of the app-of-apps root) |

**Ownership model (`DECISIONS.md` `DEC-040`, resolved at the Step C3/C4
STOP): `demo-prod` is GitOps-managed (ArgoCD auto-sync); `ephemeral-test`
is pipeline-managed (direct `oc apply`, a specific unpromoted digest,
per `PipelineRun`).** `deploy-ephemeral` (the pipeline `Task`) applies a
digest that is deliberately not yet on `main` — the whole point of the
ephemeral-test step. If ArgoCD also synced that same namespace —
automatically (`selfHeal` reverting the pipeline's own apply back to
whatever `main` last promoted) or even just via a stray manual sync — it
would fight that mechanism mid-run. `ephemeral-test`'s `Application`
manifest (`deploy/argocd/application-ephemeral-test.yaml`) exists as a
real, dry-run-validated scaffold for a *future* GitOps-synced path (one
that would need its own digest-injection story compatible with ArgoCD
sync, which doesn't exist yet) — deliberately kept outside
`deploy/argocd/apps/`, so the app-of-apps root never syncs it.

## Promotion model

One image, one digest, promoted unchanged. `deploy/kustomize/base/kustomization.yaml`
pins the image by digest (`images:` block); CI updates only that digest.
Each overlay's `kustomization.yaml` never touches the image — only
environment-specific config (`configMapGenerator` with `behavior: merge`),
namespace, and replica count differ per environment. This was verified by
rendering all three overlays with `kubectl kustomize` and confirming the
digest, image name, and namespace come out identically shaped, only the
`ConfigMap` data and namespace differing.

GitOps promotion at this MVP's scale is small `Application` manifests
pointed at overlay paths — not an `ApplicationSet` generator matrix.
Since Step C4 (`DECISIONS.md` `DEC-021`/`DEC-040`), `deploy/argocd/apps/`
holds exactly the `Application`s the app-of-apps root
(`deploy/argocd/application-root.yaml`) actually syncs — currently just
`demo-prod` (see the ownership model above for why `ephemeral-test`
deliberately isn't there too). Applying the one root object is enough to
instantiate every GitOps-managed environment from Git alone; nothing
needs applying per-environment by hand. `demo-prod` syncs automatically
(`prune: true, selfHeal: true`) — the digest-promotion PR *merge* is its
actual human gate (`SysR-P-F-06`), not the sync itself. Staging/pilot-prod's
stub `Application`s stay outside `deploy/argocd/apps/` too, un-synced;
**pilot-prod's `syncPolicy.automated` is `null`**
regardless, preserving a manual-sync gate for whenever it is activated.

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
`MODEL_API_BASE_URL`, `MODEL_NAME`, `MODEL_FALLBACK_API_BASE_URL`,
`MODEL_FALLBACK_NAME` (`DECISIONS.md` `DEC-035`), `DATA_SOURCE_BINDING`,
`APPROVAL_MODE`, `MCP_MODE`, plus replica count via the `replicas:`
transformer. None of it requires a rebuild — this is the literal
implementation of "environment differences expressed through
configuration."

**Two different mechanisms deliver the real (non-placeholder) model
endpoint values, per how each environment is deployed** (`DECISIONS.md`
`DEC-039`): `ephemeral-test` gets them injected transiently, at
apply-time, by the pipeline's own `deploy-ephemeral` Task (a one-shot
`oc apply`, never reconciled again — safe to override a Kustomize-managed
`ConfigMap` key this way). `demo-prod` is ArgoCD-synced with
`selfHeal: true`, which would continuously stomp any such override back
to the committed placeholder — so its real values instead come from a
third copy of the `${{ values.name }}-secrets` `Secret` (never
Kustomize/ArgoCD-managed), shadowing the `ConfigMap`'s placeholder at the
container level via `envFrom` ordering (`deployment-agent.yaml` lists
`secretRef` after `configMapRef`). Documented in full in
`deploy/kustomize/overlays/demo-prod/kustomization.yaml`'s own comment
and `docs/phase-c-runbook.md`'s demo-prod bootstrap section.

## What's still a placeholder

Every model endpoint *committed to this repo* is an `example.com`
placeholder (RFC 2606 reserved domain, chosen deliberately so it's
obviously fake rather than a real internal hostname) — true for every
overlay, including `demo-prod`'s (inherited unmodified from `base`, per
the mechanism above). `deploy/argocd/*.yaml`'s `REPLACE_WITH_GIT_REPO_URL`/
`REPLACE_WITH_GITOPS_NAMESPACE` placeholders were filled in at Step C1a
(`DECISIONS.md` `DEC-024`) with this repo's real, public HTTPS URL and
the shared cluster's `openshift-gitops` namespace — no longer a
placeholder as of this milestone.
