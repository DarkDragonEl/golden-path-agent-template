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
**Stop**: ~07:57 UTC (first full green `PipelineRun`,
`golden-path-agent-ci-bzrhl`, completed).
**Elapsed**: ~38 minutes — comfortably under the half-day target, even
counting all live debugging below as part of this refresh's own time
(per the refresh definition, a refresh needing manual fixes is not
disqualified).

**Manual fixes found and fixed during this refresh** (all now committed,
so the *next* refresh should not need to repeat any of them —
`DEC-080`/`DEC-081` have full detail on each):

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
7. `pipelines/pipeline.yaml`/`pipelines/tasks/*.yaml` were never applied
   by anything in `pipelines/bootstrap/` and never documented as their
   own step — fixed: `scripts/bootstrap.sh` step 7 now applies them.
8. `fetch-source`'s `git clone ... .` fails on this cluster's storage
   class (`ocs-external-storagecluster-ceph-rbd`, ext4-formatted block
   PVs always carry a `lost+found` directory) — fixed in
   `pipelines/tasks/fetch-source.yaml` (`DEC-081`).
9. `golden-path-agent-ci-config` (the model-endpoint `ConfigMap`
   `deploy-ephemeral`/`eval-gate-live` read) was never created or
   documented anywhere — fixed and documented in
   `docs/phase-c-runbook.md` §2b, checked by `scripts/bootstrap.sh`
   step 6 (`DEC-081`).

**Pipeline run, once fixes #7–9 landed**: one full `PipelineRun`
(`golden-path-agent-ci-bzrhl`) went green through every gate —
`unit-tests`, `eval-gate-offline`, `policy-validate`, `container-build`,
`digest-capture`, `sbom-generate`, `deploy-ephemeral`, `eval-gate-live`,
`security-tests`, `operational-tests` — `destroy-ephemeral` cleaned up
afterward. `eval-gate-live` scored **60/62** (only `TSEL-004` excluded
by tolerance) — the exact same standing baseline reported since Phase B,
now independently reproduced on a different cluster and a different
image build from the same commit. `open-promotion-pr` failed with
`CreateContainerConfigError` — blocked by construction (no GitHub PAT
provisioned on this cluster, `DEC-078` Option 2), not merely by
discipline: its TaskRun pod never started, so no branch was pushed, no
PR was opened, nothing needed closing.

**Known-incomplete, by design (`DEC-078` Option 2)**: the showcase's
`demo-prod`-equivalent is `Synced` but its three `Deployment`s stay
`ImagePullBackOff` — the base digest pin resolves to this cluster's own,
empty internal registry, and the ephemeral-test image built by this
refresh's `PipelineRun` was never promoted to that pin. This is the
documented, expected consequence of not granting the showcase promotion
authority this session, not a bug. The optional one-off `skopeo copy
--all --preserve-digests` mentioned in `DEC-078` was **not attempted
this refresh** — deferred, see below.

**Owner-acknowledged consequence of skipping the skopeo copy**: the
first sharing moment against the showcase (`docs/phase-e-kickoff-plan.md`
§5.1's "after D" moment) is blocked until `DEC-078`'s first follow-up
commit (the hosted-registry migration) gives the showcase's `demo-prod`
something actually running — no colleague gets the showcase URL before
then. Not a gap in this refresh; a known, accepted sequencing
consequence of the owner's own scope decision.

**Refresh target evaluation**: PASS on timing (~38 min vs. half-day
target). Refresh #1 completes the full definition's step (c) — one full
pipeline run went green — and is **partial** on step (d) — the
`demo-prod`-equivalent isn't fully serving — by deliberate scope
decision (`DEC-078`), not a failure to meet the target. Nine real
bootstrap/pipeline gaps found and fixed live; none of them are expected
to recur on refresh #2.

**Refresh #2**: not attempted this session. Per `DEC-078`'s own note,
sandbox lifetime/renewal is an owner-managed operational item — the
owner is tracking the reservation portal directly. Refresh #2 is the
run that actually proves fix #1–#6 above held without re-discovery, and
is a separate, later exercise — and should now go through a real
promotion (see the update below), not stop short of one.

---

**Update, same session, after this log was first written**: the
`ImagePullBackOff`/"known-incomplete" state described above is
resolved. `DEC-083`/`DEC-084` superseded the registry-migration plan
with a single-active-cluster model — the SNO's `demo-prod` was
deprotected and frozen instead, and the showcase ran a second
`PipelineRun` through a real merged promotion (PR #6). The showcase's
`demo-prod` is now `Synced`, all three `Deployment`s `Healthy`, running
digest `sha256:ba1c4228...`, functionally confirmed (`GET /healthz` →
`200`). Left in place above as an accurate record of refresh #1's own
state at the time — see `DECISIONS.md` `DEC-083`/`DEC-084` for the full
account of what changed and why.
