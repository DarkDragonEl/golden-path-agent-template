# Cluster profile

What this blueprint's own bootstrap needs from a target cluster, and
what to check or adjust when a cluster differs from the one `PINS.md`'s
pins were originally verified against. Derived from `tools/
cluster_precheck.sh`'s own output and from real, live-verified
findings, not hand-written speculation. Each new target cluster is
expected to add rows here, not replace the existing ones, unless a row
is proven wrong.

## Model endpoint

**No GPU is required to run this blueprint.** The agent consumes an
OpenAI-compatible model endpoint over HTTP
(`MODEL_API_BASE_URL`/`MODEL_API_KEY`) — an external MaaS route, not a
model served from cluster GPU capacity. GPU provisioning is explicitly
out of this blueprint's own scope.

**What the cluster needs**: an OpenAI-compatible endpoint reachable
from the cluster's own pod network (or from wherever `scripts/dev.sh`
runs, for local dev). Nothing else — no in-cluster inference stack,
no GPU node, no model-serving operator.

**How the credential is provisioned** (`docs/phase-c-runbook.md` §2,
`DEC-138`, unchanged for a new cluster — same mechanism, different
target): filled once into `bootstrap.env` (gitignored, copied from the
committed `bootstrap.env.example`), validated at `scripts/bootstrap.sh`
step 0 before anything touches the cluster, then written into a
`golden-path-agent-secrets` Secret in both `golden-path-agent-ephemeral-test`
and `golden-path-agent-demo-prod` (step 5) — idempotent by regeneration
(`DEC-059`), never scripted into Git, never printed in a report. The
`demo-prod` copy additionally carries `MODEL_API_BASE_URL`/`MODEL_NAME`/
`MODEL_FALLBACK_API_BASE_URL`/`MODEL_FALLBACK_NAME` (`demo-prod`'s
`ConfigMap` is ArgoCD-managed with `selfHeal: true`, so only a Secret —
never Kustomize/ArgoCD-managed — can hold the real value without being
stomped back to the committed placeholder on the next sync). A separate,
still-manual `golden-path-agent-ci`-namespace copy remains needed for
`eval-gate-live` specifically — `docs/phase-c-runbook.md` §2b names this
as a known gap `DEC-138` did not close.

The owner decides which endpoint each new cluster targets; this
document and the bootstrap tooling never assume one.

## Shared/single-node profile (`--constrained-node`)

For a shared, multi-tenant cluster or a single node where scheduling
headroom is the actual constraint, not real usage — a cluster can run
at a small fraction of its allocatable CPU while still having no
schedulable headroom left, because the scheduler gates on committed
*requests*, not actual usage. `scripts/bootstrap.sh --constrained-node`
applies:

- `deploy/kustomize/overlays/constrained-node/` instead of `demo-prod`
  (agent, mcp Deployments).
- `deploy/kustomize/overlays/approval-platform-constrained-node/`
  instead of `approval-platform` (the shared approval-service
  singleton, `ADR-012`).
- `deploy/kustomize/overlays/rhdh-constrained-node/` instead of `rhdh`,
  when `--with-rhdh` is also passed.
- `platform/bootstrap/constrained-node-patches/{keycloak-postgres,
  keycloak-cr,otel-collector}.yaml`, applied via `oc patch` right
  after the normal `oc apply -f` of those three manifests (not a
  kustomize overlay — `platform/bootstrap/` is a flat, directly-
  applied tree with no `base/` subdirectory a nested overlay could
  reference without breaking kustomize's own load-restriction
  boundary).

**What changes**: `resources.requests` only, lowered to roughly
10–50m CPU / 16–256Mi memory depending on the component. `resources.
limits` are left at `base/`'s own committed values (Burstable QoS —
generous burst headroom on top of a small guaranteed floor). `base/`
itself, `demo-prod`, `approval-platform`, and `rhdh` are never edited
by this profile; it is a selectable environment variant, applied
either via a fresh kustomize `path` (deploy/-based components) or a
live-only `oc patch` (platform/bootstrap/'s directly-applied
manifests and, for the two GitOps-managed Applications, their own
`spec.source.path`).

**Field notes, verified directly against each CRD's own schema, not
assumed from documentation**:
- `Backstage`'s CRD has no `spec.application.resources` field. The
  real mechanism is `spec.deployment.patch` ("a valid fragment of
  Deployment to be merged with default/raw configuration"), and the
  main container's name — `backstage-backend` — comes from the
  operator's own default deployment template
  (`redhat-developer/rhdh-operator`, `config/profile/rhdh/
  default-config/deployment.yaml`, read directly at the pinned
  `rhdh-operator.v1.10.3` release, not guessed).
- `Keycloak`'s CRD does expose `spec.resources.{requests,limits}`
  directly, confirmed via `oc explain keycloak.spec.resources`.
- Gitea's operator CRD (`pfe.rhpds.com/v1`, `rhpds/gitea-operator`)
  has **no resources field of any kind** — confirmed by reading its
  CRD schema directly at the pinned commit. There is no CR-level knob
  to constrain Gitea's own pod; the operator's underlying Deployment
  would need a direct post-creation patch if this ever becomes a real
  constraint, not a CR field. Not yet needed — Gitea's own footprint
  was never part of the static request total to begin with (the
  operator was never installed on this cluster before this
  bootstrap), so there is nothing to compare a "before" against.
  Revisit once a real instance exists to inspect.
- Tekton step defaults: this cluster's own `TektonConfig` sets no
  `default-container-resource-requirements`, and no `Task` in
  `pipelines/tasks/` declares its own `computeResources` — pipeline
  steps already schedule with no explicit request at all (confirmed
  no `LimitRange` in `golden-path-agent-ci` imposes an implicit
  default either). Nothing to constrain further; already the smallest
  possible footprint. Build/eval steps keep their current, unbounded
  limits — they are expected to burst.

**Verified total requests, static estimate** (same method
`tools/cluster_precheck.sh` uses — parse committed/rendered manifests,
sum `resources.requests`, not a live cluster measurement):

| Component | Before (realistic profile) | After (`--constrained-node`) |
|---|---|---|
| `demo-prod` (agent + mcp) | 150m CPU / 384Mi | 30m CPU / 96Mi |
| `approval-platform` | 100m CPU / 256Mi | 20m CPU / 64Mi |
| `rhdh` (Postgres + Backstage) | 100m CPU / 256Mi | 150m CPU / 512Mi |
| `platform/bootstrap` (Keycloak DB + OTel Collector + Keycloak CR) | 175m CPU / 448Mi | 55m CPU / 240Mi |
| **Total** | **525m CPU / 1344Mi** | **255m CPU / 912Mi** |

`rhdh`'s own row rises, not falls: the committed `Backstage` CR had
**no declared request at all** before this profile (BestEffort
scheduling, no accounting) — giving it an honest 50m/256Mi floor for
a real Node.js app is a deliberate correctness improvement, not a
regression, even though it makes that one row's static total larger.
Every other component's total falls. Treat this profile as headroom
margin and QoS discipline for a busy shared node, not as a fix for an
acute capacity shortage — run `tools/cluster_precheck.sh` against the
actual target cluster to know whether this blueprint's own footprint
is even the binding constraint there before assuming this profile is
required.

## Operator channel/version drift between clusters

Every operator this blueprint subscribes to should be re-verified
against the *target* cluster's own live catalog before bootstrapping —
`tools/cluster_precheck.sh` automates exactly this check. Do not
assume a pin verified on one cluster (or a now-gone cluster) still
resolves on a different one; record what actually differed here, not
just what was expected.

**Pin discipline: channel + minimum version, not an exact CSV.** For
each cluster-scoped operator this blueprint uses (OpenShift Pipelines,
OpenShift GitOps, the Keycloak operator, RHDH), `PINS.md` and this
blueprint's tooling require a *channel* and a *minimum version* on that
channel, not one exact historical CSV name. An exact-CSV pin is
brittle across clusters: catalogs prune old entries and roll forward on
their own schedule, and a shared cluster may already have the operator
installed — by the adopter, or by a prior bootstrap run — at a CSV
newer than whatever this blueprint last verified. `scripts/bootstrap.sh`
treats a pre-existing `Subscription` for one of these packages as
adopter-provided: if it already exists on the expected channel, the
script verifies the installed CSV meets the minimum version (approving
any in-progress, `installPlanApproval: Manual` upgrade within that
channel if it doesn't yet) and never reapplies its own Subscription
manifest over it. It installs fresh, using its own committed
`startingCSV`, only when no such Subscription exists at all. A
`Subscription` that exists but targets a *different* channel than
expected is left untouched and flagged for a human to resolve — see
"Leftover-state checks" below.

**A single unhealthy `CatalogSource` can block dependency resolution
for every `Subscription` on the cluster, not just ones targeting the
broken catalog** — a known OLM behavior, not specific to this
blueprint. If an operator install this blueprint's own bootstrap
attempts sits unresolved (no `InstallPlan`, no CSV appearing) even
though the package/channel/CSV are confirmed present in the catalog,
check `oc get catalogsource -A` for any source that isn't `READY`
before assuming the failure is this blueprint's own bug. This is not
this blueprint's resource to fix if the broken catalog belongs to
something else already on the cluster; either wait for it to be
resolved by whoever owns it, or work around it the same way this
blueprint already does for Keycloak — an OLM-free upstream install as
a documented fallback for that one operator specifically.

## Leftover-state checks before a clean-slate re-bootstrap

A cluster this blueprint didn't provision from scratch — or is being
re-bootstrapped onto after an earlier, superseded run of this same
project — can carry state a clean-slate step needs to account for
before it runs:

- **An operator Subscription for a package this blueprint also
  subscribes to, already installed on a different channel than this
  blueprint's own pin.** Not necessarily a conflict to work around —
  if it is this same project's own abandoned prior instance, delete it
  outright (its CR, namespace, Subscription, and CSV) so this
  blueprint's own bootstrap creates and owns a fresh one on its own
  pinned channel, rather than colliding with or silently adopting an
  unrelated install.
- **Shared Gateway API infrastructure.** A `GatewayClass`/`Gateway`
  serving real, unrelated workloads may share underlying
  infrastructure with a stack this blueprint has no use for. Before
  proposing removal of anything attached to shared gateway
  infrastructure, confirm via each policy/CR's own `targetRef` (not
  naming conventions) exactly which `Gateway` it targets, and confirm
  the `GatewayClass`'s own `controllerName` and owning labels — do not
  assume shared infrastructure is safe to remove just because part of
  it looks unused.
- **A shared, multi-tenant cluster's own unrelated workloads.** Prefer
  fitting this blueprint's own footprint (the shared/single-node
  profile above) over reducing another workload's resources or
  deleting anything this blueprint doesn't own. Only propose changes
  to unrelated workloads as a last resort, listed for explicit
  approval before any of it is touched.
- **A pre-existing Subscription for the same package under a
  *different object name* than this blueprint's own manifest uses —
  not only a different channel.** Confirmed live once: matching by
  this blueprint's own fixed Subscription name alone missed an
  adopter's differently-named Subscription for the identical package,
  and this blueprint's own bootstrap created a second, conflicting one
  (OLM does not support two Subscriptions to one package in one
  namespace). `scripts/bootstrap.sh`'s `ensure_operator` matches by
  package (`spec.name`), not by object name, for exactly this reason.
  For a package this blueprint is meant to be the *sole* owner of on a
  given cluster (an owner decision made once, not this blueprint's own
  default assumption — RHDH's `--with-rhdh` flag on one real cluster is
  the one case so far), any pre-existing Subscription found for it is
  treated as drift to resolve manually, never silently adopted or
  duplicated.
