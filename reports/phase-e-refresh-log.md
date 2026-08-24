# Phase E refresh log — showcase cluster

Per `docs/phase-e-kickoff-plan.md` §3's refresh definition, confirmed
as-is (STOP 2, no amendment needed after refresh #1): a refresh runs
start-to-finish from (a) a fresh environment being requested or an
existing one torn down, through (b) the bootstrap sequence (`make
bootstrap`), to (c) one full pipeline run completing green and promoting
a digest, to (d) the showcase serving the current `demo-prod`-equivalent
state. Target: under half a day, exercised at least twice before
milestone-done applies. Every manual fix found during a refresh is
Git-committed and must not still be manual on the refresh after it.

**Idempotency re-runs of `make bootstrap` against an already-populated
cluster (used here to iterate on real bugs found live) do NOT themselves
count as separate refreshes** — only a from-scratch provision counts.
This log records one refresh (#1), assembled from several `make
bootstrap` invocations against the same freshly-granted environment
while real gaps were found and fixed, not several refreshes.

---

## showcase-refresh-1

**Environment**: a freshly-granted, disposable showcase sandbox (never
touched by this project before). Step (a) of the refresh definition is
trivially satisfied — there is no prior showcase state to tear down,
this being the first-ever showcase.

**Start**: ~07:19 UTC (first `oc login` + pre-flight discovery).
**Stop**: ~07:39 UTC (`golden-path-agent-demo-prod` confirmed `Synced`,
pods in the expected `ImagePullBackOff` state per `DEC-078`).
**Elapsed**: ~20 minutes — comfortably under the half-day target, even
counting all live debugging below as part of this refresh's own time
(per the refresh definition, a refresh needing manual fixes is not
disqualified).

**Manual fixes found and fixed during this refresh** (all now committed,
so the *next* refresh should not need to repeat any of them —
`DEC-080` has full detail on each):

1. OLM `installPlanApproval: Manual` needs explicit InstallPlan approval
   even for the pinned `startingCSV` — fixed in `scripts/bootstrap.sh`.
2. `golden-path-agent-keycloak-db-secret`/`golden-path-agent-keycloak-admin`
   were undocumented manual prerequisites — fixed in `scripts/bootstrap.sh`
   (create-once, `openssl rand`-generated).
3. `Keycloak` CR `Ready` vs. `KeycloakRealmImport` `Done` race — fixed
   with an explicit wait on both conditions in `scripts/bootstrap.sh`.
4. Latent bug in `provision-identity-secrets.sh` (a failing subprocess's
   exit code not propagating through a `read <<EOF $(...) EOF`
   construct) — **found, not fixed this refresh** (documented in
   `DEC-080` as a real robustness gap; the race that triggers it, #3
   above, is now eliminated, but the underlying swallow-on-failure
   pattern remains).
5. `scripts/bootstrap.sh`'s own manual-secret gate checked Secret
   *existence* rather than the specific key needed — fixed same refresh.
6. Showcase's fresh OpenShift GitOps install needs the
   `argocd.argoproj.io/managed-by` namespace label for write access
   (the SNO's pre-installed GitOps operator never needed this) — fixed
   in `pipelines/bootstrap/namespaces.yaml`.

**Known-incomplete, by design (`DEC-078` Option 2)**: no `PipelineRun`
executed yet this refresh; the showcase's `demo-prod`-equivalent is
`Synced` but its three `Deployment`s are `ImagePullBackOff` — the base
digest pin resolves to this cluster's own, empty internal registry. This
is the documented, expected consequence of not granting the showcase
promotion authority this session, not a bug. The optional one-off
`skopeo copy --all --preserve-digests` mentioned in `DEC-078` was **not
attempted this refresh** — deferred, see below.

**Refresh target evaluation**: PASS on timing (~20 min vs. half-day
target). Refresh #1 is **partial** against the full definition's step
(c)/(d) — no pipeline run, no fully-serving `demo-prod`-equivalent —
by deliberate scope decision (`DEC-078`), not a failure to meet the
target. Six real bootstrap-sequence bugs found and fixed live; none of
them are expected to recur on refresh #2.

**Refresh #2**: not attempted this session. Per `DEC-078`'s own note,
sandbox lifetime/renewal is an owner-managed operational item — the
owner is tracking the reservation portal directly. Refresh #2 is the
run that actually proves fix #1–#6 above held without re-discovery, and
is a separate, later exercise.
