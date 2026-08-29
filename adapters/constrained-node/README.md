# `--constrained-node` adapter

**This is an adapter, not part of the golden path.** The blueprint's
own design assumes a clean cluster with normal scheduling headroom for
its own footprint. This adapter exists only for the case where the
target cluster is shared, multi-tenant, and busy enough that scheduling
is gated by committed `requests`, not actual usage — it was built to
exercise this project's own bootstrap sequence against one specific
borrowed cluster (the owner's SNO, `DEC-135`), not because the blueprint
itself ever needs it. See `agent-roadmap`'s `DECISIONS.md` "Borrowed-
cluster adaptations" section for the full classification record.

No blueprint doc, runbook, or scaffolding template treats this as a
normal option. If you're not bootstrapping onto a shared, resource-
constrained cluster, ignore this directory entirely.

## What it patches

Lowers `resources.requests` only, to roughly 10–50m CPU / 32–256Mi
memory depending on the component. `resources.limits` are left at the
golden path's own committed values (Burstable QoS — a small guaranteed
floor with generous burst headroom on top, not Guaranteed or
BestEffort). The golden path's own manifests (`deploy/kustomize/base/`,
`deploy/kustomize/overlays/demo-prod/`, `.../approval-platform/`,
`.../rhdh/`, `platform/bootstrap/`) are never edited by this adapter —
every file here is either a kustomize overlay that composes the real
overlay as its own base (`resources: [../../../../deploy/kustomize/
overlays/<real-overlay>]`) or a standalone patch file applied live via
`oc patch --patch-file=` after the real manifest's own normal apply.

- `deploy-overlays/constrained-node/` — `demo-prod`'s two Deployments
  (`golden-path-agent`, `golden-path-agent-mcp`).
- `deploy-overlays/approval-platform-constrained-node/` — the shared
  approval-service singleton's Deployment (`ADR-012`).
- `deploy-overlays/rhdh-constrained-node/` — the `Backstage` CR's own
  `spec.deployment.patch` (RHDH's real mechanism for this, not
  `spec.application.resources` — verified live against the CRD, not
  assumed).
- `bootstrap-patches/{keycloak-postgres,keycloak-cr,otel-collector}.yaml`
  — `platform/bootstrap/`'s own directly-applied (not kustomize-based)
  manifests. Applied via `oc patch` right after their normal `oc apply
  -f`, not composed with kustomize — `platform/bootstrap/` is a flat
  tree with no `base/` a nested overlay could reference without
  breaking kustomize's own load-restriction boundary (hit live,
  `DEC-135`; standalone patch files were the fix).

`scripts/bootstrap.sh --constrained-node` applies all of the above; the
flag is documented there as an adapter, and a plain `scripts/bootstrap.sh`
run (no flag) never touches this directory at all.

## Why `golden-path-agent-root` must stay `OutOfSync` while this is in use

Step 8b of `scripts/bootstrap.sh` doesn't apply these overlays via
Git — it live-patches each affected child `Application`'s own
`spec.source.path` (e.g. `golden-path-agent-demo-prod`'s `source.path`
from `deploy/kustomize/overlays/demo-prod` to `adapters/constrained-node/
deploy-overlays/constrained-node`), because there is no committed,
per-cluster way to tell one cluster's `Application` to use a different
path than another's. This is a **live-only, deliberate divergence from
what's committed in Git**, and it only sticks because
`golden-path-agent-root`'s own auto-sync is already frozen (a
single-active-cluster deprotection, `DEC-083`) — if root's `selfHeal`
were active, it would notice this drift on its next reconcile and
revert every patched child's `source.path` straight back to the
committed value, undoing the adapter silently.

**This means root reporting `OutOfSync` while this adapter is active on
a cluster is the expected, correct state, not a failure** — root's own
diff against Git will always show the patched children as drifted for
as long as the adapter is in use. `scripts/bootstrap.sh`'s own step 9
verification table checks for exactly this (`OutOfSync` expected when
`--constrained-node` was passed, `Synced` otherwise) — don't "fix" root
back to `Synced` on a cluster using this adapter; that re-enables
`selfHeal`'s revert path and undoes the resource-request lowering on
the next sync.

## How to remove it

1. Stop passing `--constrained-node` to `scripts/bootstrap.sh` on any
   future run against that cluster.
2. Revert each affected child `Application`'s live `spec.source.path`
   back to its committed value (`oc patch applications.argoproj.io
   golden-path-agent-demo-prod -n openshift-gitops --type merge -p
   '{"spec":{"source":{"path":"deploy/kustomize/overlays/demo-prod"}}}'`,
   same pattern for `golden-path-agent-approval` →
   `deploy/kustomize/overlays/approval-platform` and
   `golden-path-agent-rhdh` → `deploy/kustomize/overlays/rhdh` if
   present) — or simply let a future `--reenable-sync` bootstrap run
   (which re-applies `application-root.yaml` and restores
   `automated: {prune: true, selfHeal: true}`) reconcile it back on its
   own once root's freeze is lifted.
3. Revert the three live `oc patch`es under `platform/bootstrap/` by
   re-applying `platform/bootstrap/{keycloak-postgres,keycloak-cr,
   otel-collector}.yaml` directly (their own committed, un-patched
   values) — `scripts/bootstrap.sh` run without `--constrained-node`
   does exactly this on every normal pass.

Nothing under `deploy/kustomize/base/`, the golden-path overlays
themselves, or `platform/bootstrap/`'s own committed manifests ever
needs to change to remove this adapter — it was never edited to begin
with.

## Field notes, verified directly against each CRD's own schema, not
assumed from documentation

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
  constraint, not a CR field. Not part of this adapter today.
- Tekton step defaults: no `TektonConfig`/`Task` in `pipelines/tasks/`
  declares its own `computeResources` — pipeline steps already schedule
  with no explicit request at all. Nothing to constrain further there;
  build/eval steps keep their current, unbounded limits since they're
  expected to burst.

## Verified total requests, static estimate (same method
`tools/cluster_precheck.sh` uses — parse committed/rendered manifests,
sum `resources.requests`, not a live measurement)

| Component | Before (golden-path profile) | After (this adapter) |
|---|---|---|
| `demo-prod` (agent + mcp) | 150m CPU / 384Mi | 30m CPU / 96Mi |
| `approval-platform` | 100m CPU / 256Mi | 20m CPU / 64Mi |
| `rhdh` (Postgres + Backstage) | 100m CPU / 256Mi | 150m CPU / 512Mi |
| `platform/bootstrap` (Keycloak DB + OTel Collector + Keycloak CR) | 175m CPU / 448Mi | 55m CPU / 240Mi |
| **Total** | **525m CPU / 1344Mi** | **255m CPU / 912Mi** |

`rhdh`'s own row rises, not falls: the committed `Backstage` CR had
**no declared request at all** before this adapter (BestEffort
scheduling, no accounting) — giving it an honest 50m/256Mi floor for a
real Node.js app is a deliberate correctness improvement, not a
regression, even though it makes that one row's static total larger.
Every other component's total falls. Treat this adapter as headroom
margin and QoS discipline for a busy shared node, not as a fix for an
acute capacity shortage — run `tools/cluster_precheck.sh` against the
actual target cluster to know whether this blueprint's own footprint is
even the binding constraint there before assuming this adapter is
needed.
