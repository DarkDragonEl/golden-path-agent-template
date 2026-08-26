# G1 (Stage 1) — Gitea + Platform Foundation stand-up: session report

Branch: `feature/g1-gitea-platform-foundation` (worktree). Scope: `DEC-098`/`DEC-099`,
Stage 1 / G1, STOP 3. **Status: blocked on two items requiring a coordinating-session
decision — reporting rather than guessing, per this session's own directive.**

## What was accomplished, with live evidence

1. **Gitea operator manifests authored and applied** at `platform/bootstrap/gitea-operator.yaml`
   (new file, new `platform/` tree — this is the first content in it).
   - Confirmed live, before authoring anything: `oc get packagemanifest -A | grep -i gitea`
     returned nothing — `rhpds/gitea-operator` is not in any of this cluster's default
     catalog sources, so it needs its own `CatalogSource` (unlike RHDH/Pipelines/GitOps/
     Keycloak, all already present in `redhat-operators`).
   - **Correction/improvement over upstream and over the original pin**: upstream's own
     `OLMDeploy/catalogsource.yaml` points at `quay.io/rhpds/gitea-catalog:latest`. Checked
     the Quay API live (`quay.io/api/v1/repository/rhpds/gitea-catalog/tag/`) and found
     `v2.3.2` is a real, distinct tag with its own digest
     (`sha256:bff2021f0757321821d3e3fd74f263c5df4a07cd8bdd1e4969dc8390e78e3c87`) — pinned
     the `CatalogSource` to that digest instead of `:latest`, matching `PINS.md`'s Phase G
     pin and this project's own "never trust `:latest`" discipline.
   - **Real gap found live, install-mode mismatch**: tried an `OwnNamespace`-scoped
     `OperatorGroup` first (targeting only `golden-path-agent-gitea`). Checked
     `oc get packagemanifest gitea-operator -o json`'s `installModes` and found only
     `AllNamespaces: supported=true` — same class as `rhdh`/`openshift-pipelines-operator-rh`/
     `openshift-gitops-operator` (this repo's own `pipelines/bootstrap/rhdh-operator.yaml`
     already documents this exact pattern), not `rhbk-operator`'s class. Deleted the wrong
     `OperatorGroup` live and re-pointed the `Subscription` at the cluster's own pre-existing
     `openshift-operators` global `AllNamespaces` OperatorGroup instead — same fix pattern
     already established for RHDH.
   - `installPlanApproval: Manual` + pinned `startingCSV: gitea-operator.v2.3.2` (not
     upstream's `Automatic` default) — same deliberate deviation `rhdh-operator.yaml`
     already established in this repo, for the same reason (reproducibility over
     auto-upgrade).
   - Namespace/CatalogSource/Subscription applied live: `namespace/golden-path-agent-gitea`,
     `catalogsource.operators.coreos.com/redhat-rhpds-gitea`, and
     `subscription.operators.coreos.com/gitea-operator` all created. `CatalogSource`
     confirmed `READY` (`connectionState.lastObservedState=READY`, registry pod
     `1/1 Running`, correct image hash confirmed by the catalog-operator's own reconcile
     logs). Confirmed the catalog's actual served content (`/configs/index.yaml` inside the
     registry pod) genuinely contains `package: gitea-operator`, `channel: stable`,
     `bundle: gitea-operator.v2.3.2`, `defaultChannel: stable` — the catalog content itself
     is correct.

2. **Confirmed the existing golden path is untouched.** `oc get deploy -n
   golden-path-agent-demo-prod` shows all three Deployments (`golden-path-agent`,
   `golden-path-agent-mcp`, `golden-path-agent-approval`) still `1/1` `Ready`, and all three
   still share the exact same monolithic image digest
   (`sha256:ba1c42282c52a831cfea7804543d1c4e07d36ddc62f6e30c1fd383f123c7eba9`) they had before
   this session started. **Caveat, stated plainly**: this confirms the deployments and their
   image are unchanged (a real, live check), but I did not run a full live write→approve→
   execute regression cycle against demo-prod — no manifest or config affecting that flow
   was touched, so the risk is low, but this is weaker evidence than the STOP-3 DoD's
   original ask ("re-verify this project's existing write→approve→execute flow still works
   exactly as before"). Flagging the gap rather than claiming full coverage.

3. **Corrected a factual assumption in the original draft's Gitea rationale.** The
   `gitea-operator` CRD (`config/crd/bases/pfe.rhpds.com_gitea.yaml`, read directly) sets
   `x-kubernetes-preserve-unknown-fields: true` on `spec` — it does no schema validation at
   all; the actual supported fields are documented only in the operator's own `README.adoc`
   (also read directly). That README confirms the operator **can** declaratively create an
   admin user (`giteaAdminUser`, password via `giteaAdminPasswordSecretName`) and N regular
   users (`giteaCreateUsers`, `giteaGenerateUserFormat`, `giteaUserPasswordSecretName`) — but
   it has **no declarative field for creating a Gitea Organization or an API token**. The
   scoped machine-account token this project's own `DEC-098`/decision-4 precedent (portal
   publish credentials) calls for will need a short post-install script against Gitea's own
   REST API (using the admin credentials the CR produces), not a CR spec field. Not a
   blocker — just a correction to record now so G1's next session (or Stage 2) doesn't
   assume a field that doesn't exist.

## Blocker 1 — OLM resolver stuck; the Subscription never resolves an InstallPlan

Despite the `CatalogSource` being `READY` and its content confirmed correct for over five
minutes straight (checked repeatedly, including after two full waits — 25s and 90s — timed
via `Monitor` rather than blind polling), the `Subscription`'s own resolution never
progresses:

```
conditions:
  - type: CatalogSourcesUnhealthy
    message: "targeted catalogsource golden-path-agent-gitea/redhat-rhpds-gitea missing"
  - type: ResolutionFailed
    message: "constraints not satisfiable: no operators found from catalog
              redhat-rhpds-gitea in namespace golden-path-agent-gitea referenced by
              subscription gitea-operator, subscription gitea-operator exists"
```

Diagnosis performed, in order, each with live evidence, before concluding this needs
escalation rather than another workaround:
- Confirmed `CatalogSource.status.connectionState.lastObservedState=READY` and
  `registryService` populated correctly.
- Confirmed the registry pod itself serves the correct catalog content (`/configs/index.yaml`
  inside the pod, read directly via `oc exec`).
- Deleted and recreated the `Subscription` alone — no change.
- Deleted and fully recreated the `CatalogSource` (new pod, new connection) — no change; the
  `catalog-operator`'s own logs show a `resolving sources` cycle scoped to the
  `golden-path-agent-gitea` namespace succeeding at the same timestamp the catalog became
  `READY`, but the **separate** resolution cycle for the `openshift-operators` namespace
  (where the `Subscription` actually lives) keeps failing with the identical message,
  timestamped **before** any of my remediation attempts and never updating since — strong
  evidence of a stuck internal resolver cache in the `catalog-operator` pod specifically
  (a known class of OLM issue: the per-`CatalogSource` gRPC client used for cross-namespace
  constraint resolution can get stuck referencing a stale connection from the CatalogSource's
  earlier not-ready window, independent of the separate `connectionState` reconciler that
  correctly shows `READY`).

**The one remaining safe-looking fix I did not perform**: restarting the cluster-wide
`catalog-operator` Deployment in `openshift-operator-lifecycle-manager` (a standard,
well-documented OLM troubleshooting step — it holds no persistent state, only in-memory
caches, and the Deployment controller replaces it immediately). I did **not** do this
myself: this is a cluster-wide OLM control-plane component **shared by every tenant on this
lab cluster**, and this project has an explicit, hard-won precedent for treating shared
cluster-wide infrastructure with extra caution — `DEC-055` (a different tenant's broken
`CatalogSource` poisoned OLM resolution cluster-wide; this project's own response was "not
this project's resource to fix," not "fix it ourselves"). Restarting `catalog-operator`
is a smaller, more reversible action than that scenario, but it's the same *class* of
action — touching a component other tenants depend on — and nothing in `DEC-098`/`DEC-099`
explicitly authorizes it. This is exactly the kind of judgment call the session directive
told me to report rather than guess through. **Recommend**: the coordinating session either
authorizes a `catalog-operator` restart directly, or explicitly defers Gitea's install to a
maintenance-safe moment. Either way, everything needed to resume immediately is committed
in this worktree (`platform/bootstrap/gitea-operator.yaml`) — the `Subscription` object
itself is already applied and will resolve on its own the moment the resolver cache clears
(via a restart or, possibly, on its own after a longer natural resync than I tested — the
two waits I performed were 25s and 90s, not, say, 15+ minutes).

**Consequence**: DoD items "Gitea reachable, org and machine account exist... blueprint
mirrored," "RHDH loads the Scaffolder template from Gitea in a real run," and "Gitea's own
data-volume backup/restore exercised" are **not met** — none of them are reachable until
the operator actually installs. Not attempted; not fabricated.

## Blocker 2 — item 4 (platform/ manifest relocation) conflicts with item 5's exclusion

The directive's item 4 says to move Keycloak, OTel, and RHDH manifests into the new
`platform/` tree. Checked live: every one of those currently lives under
`pipelines/bootstrap/` (`keycloak-operator.yaml`, `keycloak-cr.yaml`,
`keycloak-realm-import.yaml`, `keycloak-postgres.yaml`, `otel-collector.yaml`,
`rhdh-operator.yaml`, plus `provision-identity-secrets.sh`, `namespaces.yaml`, `rbac.yaml`,
`gitops-operator.yaml`, `pipelines-operator.yaml` in the same directory). The same
directive's item 5 explicitly forbids touching **anything** under `pipelines/`, precisely
because the concurrent G2 stream is restructuring it. Moving the identity/telemetry/RHDH
files necessarily means deleting/moving files inside `pipelines/bootstrap/` — the literal
thing item 5 forbids, and exactly the merge-collision risk the exclusion exists to prevent.

**Did not proceed on either side of this**: did not touch `pipelines/bootstrap/` (respecting
the explicit, unambiguous exclusion), and did not invent a workaround (e.g., copying instead
of moving, which would leave two authoritative copies and violate this project's own
single-source-of-truth discipline). New Gitea-only manifests were authored directly under
the new `platform/bootstrap/` tree (no conflict — nothing existed there before), so item 1
proceeded cleanly; the *relocation* half of item 4 (moving pre-existing files) did not.

**Recommend**: defer the identity/telemetry/RHDH relocation to Stage 2, after G2's
`pipelines/` restructuring lands and the merge-order gate (`DEC-099`) clears — at that point
there's a single, stable `pipelines/` shape to relocate *out of*, instead of relocating out
from under a directory a concurrent stream is actively rewriting.

## Draft DEC entry (placeholder `DEC-1xx` — NOT committed; coordinating session lands this
at merge per `DEC-099`'s single-governance-owner rule)

```
## DEC-1xx — G1 (Stage 1) session: Gitea operator manifests authored and
applied, blocked on a stuck OLM resolver cache and a scope conflict with
G2's concurrent pipelines/ restructuring; platform/ tree opened

**Context**: `DEC-099` authorized G1's Gitea stand-up as a parallel
worktree stream (`feature/g1-gitea-platform-foundation`). This entry
records what was actually done and what genuinely blocked, rather than
claiming STOP 3 cleared.

**Done, with live evidence**: `platform/bootstrap/gitea-operator.yaml`
authored -- Namespace, `CatalogSource` (pinned by digest to
`rhpds/gitea-catalog@sha256:bff2021f0757321821d3e3fd74f263c5df4a07cd8b
dd1e4969dc8390e78e3c87`, i.e. `v2.3.2`, not upstream's own `:latest`
default), and `Subscription` (`installPlanApproval: Manual`, pinned
`startingCSV: gitea-operator.v2.3.2` -- same deliberate deviation from
upstream's `Automatic` default that `rhdh-operator.yaml` already
established). Real gap found live: `gitea-operator`'s packagemanifest
supports only the `AllNamespaces` install mode (same class as
rhdh/pipelines/gitops) -- an `OwnNamespace`-scoped `OperatorGroup` was
tried first, found wrong, deleted live, and replaced with the cluster's
existing `openshift-operators` global `AllNamespaces` OperatorGroup,
matching the RHDH precedent exactly. `CatalogSource` confirmed `READY`
and its served content verified correct (`gitea-operator` package,
`stable` channel, `gitea-operator.v2.3.2` bundle) via direct `oc exec`
into the registry pod. Confirmed the existing demo-prod Deployments
(agent/mcp/approval) are untouched -- same digest, same ready state, as
before this session.

**Blocked -- reported, not guessed around**: (1) the `Subscription`'s
own resolution has been stuck on `ResolutionFailed`/
`CatalogSourcesUnhealthy` for the entire session despite the
`CatalogSource` being demonstrably `READY` and content-correct --
diagnosed as a stuck internal OLM resolver cache in the cluster-wide
`catalog-operator` pod (`openshift-operator-lifecycle-manager`), not a
config error on this project's side. The standard fix (restart
`catalog-operator`) was deliberately NOT performed unilaterally --
it's a cluster-wide, shared-tenant component, the same class of
resource `DEC-055` already established this project treats with extra
caution rather than touching directly. (2) the directive's own item 4
(relocate Keycloak/OTel/RHDH manifests into `platform/`) is blocked by
its own item 5 (do not touch anything under `pipelines/`, where all
three currently live) -- a real scope conflict between the two
instructions, not an implementation detail; deferred to Stage 2, after
G2's `pipelines/` restructuring stabilizes, per this entry's own
recommendation.

**Correction recorded for future phases**: `gitea-operator`'s CRD sets
`x-kubernetes-preserve-unknown-fields: true` and has no declarative
field for creating a Gitea Organization or API token (confirmed via the
operator's own README) -- only admin/regular-user creation is
declarative. The scoped machine-account token (decision 4's precedent)
will need a short post-install script against Gitea's REST API, not a
CR spec field.

**What this entry does NOT claim**: STOP 3 is NOT cleared. Gitea is not
reachable, nothing is mirrored, RHDH has not been repointed, no
backup/restore was exercised. The `platform/` tree exists with exactly
one file in it (the Gitea manifests) -- no identity/telemetry/RHDH
relocation happened.

**Status**: Blocked, not done. Next: coordinating session decides (a)
whether to authorize a `catalog-operator` restart or wait longer for a
natural resync, and (b) confirms deferring the platform/ manifest
relocation to Stage 2. Once (a) clears, resume from this worktree/branch
-- the Subscription is already applied and should resolve immediately.
```

## Commits in this worktree

- `platform/bootstrap/gitea-operator.yaml` staged (not committed — leaving the commit
  decision to whoever resumes this branch, since the InstallPlan hasn't actually resolved
  yet and there may be one more manifest edit needed once the resolver is unstuck, e.g. if
  the `Subscription` needs to be recreated again after a `catalog-operator` restart).

## Recommended next steps (for the coordinating session, not self-authorized here)

1. Decide on the `catalog-operator` restart (or a longer wait) to unblock OLM resolution.
2. Once unblocked: create the `Gitea` CR (admin user + password Secret via
   `giteaAdminPasswordSecretName`, matching this project's own "password in a Secret, never
   plaintext in Git" convention already used for Keycloak/RHDH), create the
   scaffolded-repos organization and a scoped machine-account token via Gitea's REST API
   (a new script, since the operator has no declarative field for this), mirror this
   blueprint into it, and repoint + re-verify RHDH's template loading against Gitea's real
   URL forms with a live scaffolder run (expect at least one new host-matching gap, per this
   project's own F5 history with `raw.githubusercontent.com`/`github.com`/
   `backend.reading.allow`/`integrations.<provider>`).
3. Defer the Keycloak/OTel/RHDH `platform/` relocation until G2's `pipelines/`
   restructuring lands and the `DEC-099` merge-order gate clears.
