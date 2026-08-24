# Phase E kickoff plan — shared showcase cluster

**STATUS: DRAFT — awaiting owner authorization. Nothing in this document
has been executed. No environment has been requested. No cluster has been
touched to produce this plan.**

## 0. How to read this document

This is a proposal, not a runbook of work already done. Each major section
below ends with its own **STOP** — a point where this plan should not
proceed further without the owner's explicit review and go-ahead, matching
every prior phase's own gate discipline (`CLAUDE.md`'s "plan-per-gate,
owner STOPs" rule). Sections that describe *why* something is needed
(§1, §4) don't carry a STOP of their own — they're context for the
sections that do.

## 1. What Phase E is (recap, not new scope)

Per `E2E_DEMO_PLAN.md`'s own Phase E section and `docs/environments.md`'s
shared-cluster deviation note: Phase E is a continuous showcase *practice*
that starts as soon as Phase C produces a promotable digest and runs in
parallel with Phase D onward — not a discrete final phase that begins only
now. What's actually new at this point is the first real environment
request and the first from-scratch bootstrap attempt; the practice itself
(GitOps keeps it current, sharing moments per phase, a maintained
walkthrough script) has been implicitly running since Checkpoint C, just
without a dedicated showcase cluster to run it on yet.

## 2. E1 — showcase-cluster from-scratch bootstrap

### 2.1 Why this is the first real full-bootstrap test

`docs/environments.md` records this plainly: the shared SNO lab cluster
this milestone actually targeted already had the OpenShift Pipelines and
GitOps operators installed by prior, unrelated work before this project
ever touched it. This project's own namespaces/RBAC/`AppProject`/
pipeline/policy bundle all bootstrap from Git as designed — but operator
installation itself was never actually exercised from Git, because it was
never necessary on the shared cluster. **Phase E's dedicated showcase
cluster is the first and only place that leg of "instantiates from Git
alone" gets proven**, which raises the bar for what "exercised ≥2
refreshes" needs to mean here (§3) versus what Phase C already
demonstrated.

### 2.2 Reusable install mechanism

Keycloak: `DEC-056`'s OLM-free upstream kustomize path
(`pipelines/bootstrap/keycloak-operator-upstream/`, pinned tag `26.7.2`
per `PINS.md`), carried over as-is — no changes anticipated. It carries one
flagged cluster-scoped grant (a `ClusterRoleBinding` for read-only
`config.openshift.io/ingresses` access) that must be re-flagged, not
silently re-applied, on the showcase cluster too — the same disclosure
this plan is giving it here applies there.

Whether the showcase cluster's own OpenShift Pipelines/GitOps operators
need OLM (likely available cleanly, unlike this shared cluster's poisoned
catalog) or a similar workaround is unknown until the environment exists —
this plan does not assume either way; the first bootstrap attempt is
itself the test.

### 2.3 Full manual bootstrap sequence to replay

In order, matching what Phase C/D already established on the shared
cluster:
1. `pipelines/bootstrap/namespaces.yaml` — the six `golden-path-agent-*`
   namespaces.
2. `pipelines/bootstrap/rbac.yaml` — namespace-scoped pipeline
   ServiceAccount Role/RoleBinding.
3. Keycloak: `pipelines/bootstrap/keycloak-operator-upstream/` (operator),
   `keycloak-postgres.yaml`, `keycloak-cr.yaml`, `keycloak-realm-import.yaml`.
4. `pipelines/bootstrap/provision-identity-secrets.sh` — mints workload
   client secrets and demo user passwords into the right namespaces.
5. `deploy/argocd/project.yaml` (the `AppProject`) +
   `deploy/argocd/application-root.yaml` (the app-of-apps root) — applying
   this last one is what "instantiates every GitOps-managed environment
   from Git alone" actually means in practice.
6. PAT setup (`docs/phase-c-runbook.md` §3) — needed before
   `open-promotion-pr` can function on this new environment; see §8 below
   for the related pre-showcase rotation item on the *existing* PAT.

### 2.4 Open question: `make bootstrap`

`E2E_DEMO_PLAN.md` references `make bootstrap CLUSTER=<kubeconfig>` as the
eventual one-command version of §2.3's sequence. Confirmed: **no such
target exists in the current Makefile** (only `build up up-offline down
logs eval eval-fast eval-domain validate-eval-set trace test lint`).
Flagged, not silently assumed either way: is collapsing §2.3's sequence
into a real Makefile target in scope for Phase E itself, or is it a
separate, later work item? **Recommendation**: treat it as a named Phase E
work item (it directly serves the half-day refresh target in §3), but this
is the owner's call, not decided here.

**STOP 1** — owner authorizes requesting the first showcase environment,
and confirms the `make bootstrap` question's disposition (in scope now, or
deferred).

## 3. The ≥2-refresh / half-day-restore target

`E2E_DEMO_PLAN.md` §E1's explicit target: re-provisioning + bootstrap +
one pipeline run must restore the full showcase from Git, hands-off,
**in under half a day**, and this must be exercised **at least twice**
before "milestone-done" (`E2E_DEMO_PLAN.md` §5) applies.

Proposed definition of "a refresh," for the owner to confirm or amend: (a)
the environment is torn down or a fresh one requested, (b) §2.3's sequence
(or its `make bootstrap` equivalent) is run against it with no manual
intervention beyond what's documented, (c) one full pipeline run completes
green and promotes a digest, (d) the showcase serves the current
`demo-prod`-equivalent state. The half-day clock starts at (a) and stops
at (d); each refresh's start/stop times and any manual fix required go
into a short log (candidate location: a section of `SHOWCASE_NOTES.md`,
see §6, or its own `reports/phase-e-refresh-log.md` — owner's preference).
Every manual fix discovered during a refresh is itself Git-committed and
re-verified on the *next* refresh, per `E2E_DEMO_PLAN.md`'s own "every
refresh is a free reproducibility test" framing — a refresh that needed a
manual step is not disqualified, but that step must not still be manual on
the refresh after it.

**STOP 2** — owner reviews this refresh definition and the logging
location before the first refresh is attempted.

## 4. E2 — GitOps keeps it current

No new work needed here. Whatever digest `demo-prod`'s ArgoCD sync last
promoted appears on the showcase automatically, since the showcase tracks
the same GitOps repo — this is already true today by construction, not
something Phase E has to build.

## 5. E3 — sharing moments + anonymity sweep

### 5.1 Schedule

Four moments, per `E2E_DEMO_PLAN.md` §E3: after A/B0 (repo walkthrough, no
cluster — `reports/phase-b-sharing-run.md`'s own predecessor content
covers this), after B (`reports/phase-b-sharing-run.md`, already exists),
after C (`reports/phase-c-sharing-run.md`, already exists, explicitly
caveated as captured on the shared SNO, not yet a dedicated showcase), and
after D (full clickable flow: ask→answer→draft→approve/reject/expiry→
ticket→trace).

**Open question, flagged not silently answered**: the after-D sharing
report doesn't exist yet — `phase-c-sharing-run.md` itself calls it out as
still pending. Is producing `reports/phase-d-sharing-run.md` in scope for
Phase E's own E3 work, or a separate item that should happen closer to
when Checkpoint D actually closes (i.e., after the owner's own
`docs/owner-walkthrough.md` click-through)? **Recommendation**: produce it
as part of Phase E's E3 work, once Checkpoint D is formally closed, using
the same "What this is NOT yet" structure `phase-b-sharing-run.md`/
`phase-c-sharing-run.md` already established — but sequencing this after
Checkpoint D's closure, not before, since it should describe a completed
Checkpoint D, not an in-progress one.

### 5.2 Anonymity sweep procedure

Run before **every** sharing moment, not just once — the established
`DEC-021`/`DEC-024` pattern: confirm no `*client*`/`*research-notes*`
files exist in what's being shared; confirm `.env` was never tracked;
grep all tracked files (and, before any *first* push of new history, the
full git history via pickaxe search) for real hostnames, org names,
emails, IP literals; confirm corpus/eval data stays synthetic-only. This
is a repeat, not a one-time gate — each new sharing moment can introduce
new content that needs its own sweep.

**STOP 3** — owner reviews the sharing schedule, the after-D report
sequencing decision, and the access list (who receives the showcase
URL/viewer account, and when) before any sharing moment after Checkpoint D
closes.

## 6. E4 — feedback loop

`SHOWCASE_NOTES.md` (does not exist yet — confirmed via a repo-wide
search): a log of colleague feedback captured at each sharing moment,
triaged into one of three buckets — a tracked issue, an Annex A open-item
observation, or explicit phase-two parking. Created once the first sharing
moment against the showcase actually happens; not needed before then.

## 7. E5 — the ~20-minute owner-facing walkthrough script

### 7.1 Structure

Per `E2E_DEMO_PLAN.md` §E5: template instantiation → inner loop → gate
failure + recovery → immutable-digest promotion → approval trilogy →
trace → "what this is NOT yet" as the deliberate phase-two hook. A
recorded happy-path run is kept current as a backup for whenever a live
demo isn't possible.

### 7.2 "What this is NOT yet" — full list for this script

Stated plainly, on a slide, not glossed over:

- **Steps 4–6** (`StRS_Agentic_AI_Platform_EN.md` §18.2/§19: staging
  integration, controlled pilot, the production architecture decision) —
  explicitly phase-two; this milestone covers Steps 1–3 only.
- **No external HTTP routing this milestone** — no working `Ingress`
  exists yet for any of this project's services; every live interaction
  (including this plan's own `DEC-074` mechanism) goes through
  `oc port-forward`.
- **Attestation / per-agent sandbox profiles** — `Annex_A_Open_Items_EN.md`
  OI-03's "explicitly deferred" tier (cryptographic workload attestation,
  fleet-wide policy governance). Say so on a slide; don't fake it.
- **ESO/Vault secrets integration** — deferred phase-two, per
  `docs/security-identity.md` and `PINS.md`.
  `pipelines/bootstrap/provision-identity-secrets.sh`'s own header comment
  calls itself "the demo-scale realization" of what a real ESO/Vault
  integration would do continuously — that framing is walkthrough
  material, not a caveat to hide.
- **The `DEC-065` ConfigMap-rollout gap** — `ConfigMap`-only changes to a
  GitOps-synced overlay don't roll already-running pods; the
  `checksum/config`-annotation pattern is named, explicitly, as this
  gap's Phase E hardening candidate. Whether to actually implement it
  during Phase E or keep naming it as a backlog item is the owner's call —
  not decided by this plan.
- **The four named known-gaps** (`INJ-006`, `UAW-003`, `ITR-004`,
  `TSEL-004`) — declared final per `HANDOFF.md` invariant #7 ("do not add
  a fifth without new direction"). Referenced here, not re-litigated:
  `INJ-006` (jailbreak framing can still get a write action drafted, but
  the human-approval gate held 100% across every measurement —
  defense-in-depth demonstrated, not a weakness hidden), `UAW-003`
  (measurement-tolerance, one irreproducible non-deterministic flip, not a
  stable behavior), `ITR-004` (a narrow scorer string-comparison artifact,
  the functional half already fixed), `TSEL-004` (a query-phrasing
  classification tendency, no unsafe behavior results).

**STOP 4** — owner reviews the script draft and this "what this is NOT
yet" list before it's treated as demo-ready for an actual showcase
audience.

## 8. Pre-showcase housekeeping: PAT rotation

Parked since Phase C (`docs/phase-c-runbook.md`'s "Post-Checkpoint-C
backlog" item 4, `DEC-036`/`DEC-039`) — named explicitly here as a
pre-showcase item to finally execute, not a someday item. Mechanism
already fully specified in `docs/phase-c-runbook.md` §3: regenerate a
fine-grained GitHub PAT (repository access scoped to only
`DarkDragonEl/golden-path-agent-template`, permissions `Contents: Read and
write` + `Pull requests: Read and write` only, short expiry), then:
```sh
oc create secret generic golden-path-agent-github-token \
  -n golden-path-agent-ci \
  --from-literal=token="<the fine-grained PAT>"
```
(replacing the existing Secret in place — `docs/phase-c-runbook.md` §2
covers the exact rotation mechanics). Do this before the showcase
cluster's own PAT is first provisioned, so the showcase never inherits the
same broader-exposure history the current one has (supplied directly in
conversation twice, per `DEC-036`/`DEC-039`).

## 9. Scope guard (`CLAUDE.md`, applies with full force)

This demo remains one agent, one knowledge domain, one tool, one model
route + one fallback, human approval for every write. Anything in this
plan or discovered during Phase E execution that looks like a second tool,
semantic routing, memory tiers, or multi-agent orchestration must be named
as scope creep and flagged to the owner before proceeding — not folded in
because it seemed convenient. Phase-two capabilities (Data Mesh, AI
Routing Grid, Secure Agent Sandbox) get clean integration points only,
never implementations, exactly as they have throughout this project.

## 10. Definition of milestone-done (recap, `E2E_DEMO_PLAN.md` §5)

So this document is self-contained: milestone-done means Checkpoints
A2/B0-b/B2/C/D are all closed, the blueprint instantiates on a fresh
showcase cluster from Git alone (exercised at least twice via refreshes,
§3), and the ~20-minute walkthrough script (§7) is maintained and current.
This is the demonstration milestone per `StRS_Agentic_AI_Platform_EN.md`
§19 — not MVP acceptance, which additionally requires Steps 4–5 and the
Step 6 decision (§7.2's "what this is NOT yet" list).

## 11. This session's execution boundary

Restated explicitly: nothing in this document has been executed. No
showcase environment has been requested. No cluster was touched to produce
this plan (all research behind it was read-only exploration of the
existing repo and its own documentation). This markdown file is the entire
deliverable of this session's Task 2. Execution of any section above
requires the owner's explicit go-ahead at that section's own STOP.
