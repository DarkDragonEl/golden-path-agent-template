# Session handoff

**Rewritten again, this time closing out a later session** (OTel
collector fix + Phase F0–F3) on top of the Phase E kickoff session this
file previously summarized. `DECISIONS.md` (currently through `DEC-091`)
is the authoritative, complete, chronological record of every decision
this project has made — this file is a *pickup* summary, not a
substitute for it. When in doubt, `DECISIONS.md` wins. The Phase E
content below (bootstrap proof, showcase promotion, sharing-moment
artifacts) is unchanged since that earlier rewrite and remains current —
nothing in this session's work touched it.

## Where this is — most recent session first

**OTel collector fix** (no DEC entry — drafted in-conversation per
`/close-step`'s draft-only governance, never committed; full detail in
`reports/phase-e-otel-collector-fix.md`): the cluster-tier OTel
collector's `traces-http` sidecar was stuck in `ImagePullBackOff` for
17h+ (its pinned image digest, borrowed from this project's own CI
ImageStream, had been pruned), which starved the collector Service of
ready endpoints and silently broke every OTLP export from
agent/approval/mcp. Repinned to `registry.access.redhat.com/ubi9/
python-312-minimal` (independently maintained, decoupled from this
project's own CI/promotion lifecycle), verified live end-to-end with a
real write→approve→resume flow and a correlated trace query across both
services. Also split `mcp`'s `OTEL_SERVICE_NAME` from the shared
ConfigMap value it previously collided with the agent's own. Commits
`a6e1625`/`22d3bc3`.

**Phase F0–F3 complete** (`DECISIONS.md` `DEC-085`–`DEC-091`;
`docs/phase-f-kickoff-plan.md` is the governing plan, kept current in
place as each STOP cleared):

- **Scoping** (`DEC-085`–`DEC-087`): "what would it take to add RHDH"
  turned out to already be normative (`SysR-P-F-01`, Annex A `OI-04`),
  not scope creep — but the underlying template-scaffolding mechanism
  didn't exist at all, independent of RHDH. Live research found RHDH
  present in OperatorHub on the showcase cluster (`rhdh-operator.
  v1.10.3`, `AllNamespaces`-only install mode, external Postgres
  genuinely supported). A same-day correction: an incidental SNO catalog
  observation, made under a mis-switched ambient kubeconfig context, was
  reworded to explicitly disclaim it as unverified rather than stand as
  a finding (`DEC-085`'s own amendment) — `DEC-086` adopted an
  explicit-`--context`-only rule for the rest of Phase F as a direct
  result. `DEC-087` records the owner's answers to all seven open
  decisions (templating engine, auth, Ingress/Route, `publish:` scope,
  `OI-04` threshold shape, namespace name, catalog-fallback — now moot).
- **F1** (catalog registration): `catalog-info.yaml` committed,
  registering this repo as a Backstage/RHDH Component. Inert until F4.
- **F2** (templating engine, `DEC-088`/`DEC-089`): `skeleton/` — a
  207-file parameterized copy of the template-eligible parts of this
  repo — plus `template-schema.json` (the one parameter-schema source of
  truth) and `docs/template-nine-output-mapping.md`. Verified two ways:
  `tools/verify_skeleton.py` (zero surviving literals, zero unresolved
  placeholders) and, after owner review demanded evidence over assertion,
  a live image-digest comparison (byte-identical before/after) plus
  CI-equivalent local runs (pytest/lint/eval-gate all green, confirmed
  scoped away from `skeleton/`) — full commands in `reports/phase-f-f2-
  verification.md`.
- **F3** (CLI instantiation, `DEC-090`/`DEC-091`): `tools/
  instantiate_agent_project.py` (sharing `tools/skeleton_renderer.py`
  with F2's own verification tool). **A real defect was found and fixed
  by execution, not caught by diff**: the first render's own test suite
  failed on one test depending on real `srs/` files, which the skeleton
  had already (correctly) excluded — the whole `tools/trace-check/`
  directory and `tests/test_trace_check.py` were removed from the
  skeleton as a conscious product decision (`DEC-090`'s addendum), not
  merely a bugfix. Second render, fresh parameters, passed clean: own
  test suite (210 passed) and own `make eval-fast` (2/2), both via the
  real Makefile, untouched after rendering. Full commands in
  `reports/phase-f-f3-verification.md`. **`SysR-P-F-01`(b) is now
  satisfied and live-verified** (`DEC-091`) — the Annex A `OI-04`
  fallback is a real, ready option, not a contingency to scramble
  together under pressure. F4/F5 can now only ever put at risk *when*
  portal exposure is demonstrated, never *whether* the milestone
  succeeds.

**What Phase F leaves genuinely open** (`DEC-091`, named explicitly so
"milestone satisfied" isn't mistaken for full closure): (1) full portal
exposure — `SysR-P-F-01`(a), F4/F5 — still required for `OBJ-01`, just
no longer time-pressured; (2) `SysR-P-F-13`/`OS-09` (a second team
running the instantiation unassisted) — this project cannot self-certify
that, `DEC-090`/`DEC-091` only prove one session's own execution
succeeded once.

**Phase E** (unchanged since the prior rewrite — see that session's own
detail below): Checkpoint D closed, showcase cluster from-scratch
bootstrap proven (`DEC-080`/`DEC-081`), one full green `PipelineRun`,
single-active-cluster model adopted and executed (`DEC-083`/`DEC-084`),
STOP 3/4 sharing artifacts drafted and their blocking condition resolved.

---

## Phase E detail (from the prior session's rewrite, still current)

- **The showcase cluster's from-scratch bootstrap is proven.** A real,
  dedicated OpenShift cluster (never touched by this project before) was
  bootstrapped entirely from Git — including, for the first time in this
  project's history, the cluster-scoped operator installs (OpenShift
  Pipelines, OpenShift GitOps) that the SNO always had pre-installed by
  other work. `make bootstrap CLUSTER=<kubeconfig>` (`scripts/bootstrap.sh`)
  is the scripted replay. Nine real, previously-undocumented gaps were
  found and fixed live — see `DECISIONS.md` `DEC-080`/`DEC-081` for the
  full list (OLM Manual-approval InstallPlans, two undocumented Keycloak
  bootstrap secrets, a Keycloak-Ready-vs-RealmImport-Done race, a
  storage-class-specific `git clone` failure, a missing `ConfigMap`, an
  ArgoCD RBAC namespace-label requirement, and the never-documented step
  of applying the `Pipeline`/`Task` definitions themselves).
- **One full `PipelineRun` went green on the showcase cluster** —
  `unit-tests` through `operational-tests`, all passing, `eval-gate-live`
  scoring 60/62 (the same standing baseline reported since Phase B, now
  independently reproduced on a different cluster and image build from
  the same commit). `open-promotion-pr` failed cleanly on a missing
  credential — blocked by construction, not just by discipline.
- **A real, previously-unflagged architecture gap was found, named, and
  then resolved by owner decision — not by the structural fix originally
  scoped**: `DECISIONS.md` `DEC-078` found that the single shared
  `images:` digest pin in `deploy/kustomize/base/kustomization.yaml`
  isn't portable across clusters, and that a second cluster's pipeline
  merging its own promotion PR would silently break the SNO's live
  `demo-prod`. `DEC-078`'s own three-part structural fix (hosted
  registry → per-cluster overlays → parametrized promotion) is now
  superseded, not implemented — `DEC-083` adopted a single-active-cluster
  model instead: the showcase owns the shared pin and promotes normally;
  the SNO's `demo-prod` is deprotected (its own root app-of-apps'
  auto-sync disabled live, never committed) and frozen at its last
  digest. `DEC-084` records this actually executed: both SNO patches
  applied and confirmed durable, and — first time in this project's
  history — a second cluster's pipeline opened and got a real promotion
  PR (#6) merged, with the showcase's own `demo-prod` synced, `Healthy`,
  and functionally confirmed live (`GET /healthz` → `200`).
- **A real anonymity-rule violation was caught pre-push and fixed by
  local history rewrite** (`DECISIONS.md` `DEC-082`) — a live MaaS
  hostname had been committed twice (via the concurrent
  `feature/workspace-tooling` merge, not this session's own work) in
  violation of this repo's "every committed model endpoint is a
  placeholder" rule. Fixed before anything left the machine; the pushed
  history has zero occurrences, verified commit-by-commit.
- **The STOP 3/STOP 4 artifacts the Phase E kickoff plan named are
  drafted, and their blocking condition is resolved**: `reports/phase-d-
  sharing-run.md` (the after-D sharing moment), `docs/showcase-
  access.md` (the sharing-schedule template, structure only — no real
  names/emails), `SHOWCASE_NOTES.md` (E4's feedback-log skeleton),
  `docs/showcase-walkthrough-script.md` (the ~20-minute script). These
  were drafted while the showcase's `demo-prod` had nothing running
  (`DEC-078`'s original state) — it now does (`DEC-084`), so the first
  real sharing moment is genuinely unblocked. Still pending — see "Next
  session's mission" below.

A few real live findings worth knowing before touching either cluster
again (Phase E):

- `DEC-080` — OLM `installPlanApproval: Manual` requires explicit
  InstallPlan approval even for the pinned `startingCSV` on a first
  install, not just on upgrades. `scripts/bootstrap.sh`'s `wait_for_csv`
  now approves the InstallPlan on every poll, matched against the exact
  pinned CSV only — **this is also the mechanism `DEC-090`'s F4 (not yet
  started) is directed to reuse for RHDH's own Operator install**, since
  RHDH's install mode is also `AllNamespaces`-only.
- `DEC-080` — `golden-path-agent-keycloak-db-secret`/`-admin` and
  (`DEC-081`) `golden-path-agent-ci-config` were all real, previously
  undocumented manual prerequisites. All three are now documented
  (`docs/phase-c-runbook.md` §2b for the `ConfigMap`; `scripts/bootstrap.sh`
  creates the two Keycloak secrets itself, create-once) and checked by
  `scripts/bootstrap.sh`'s own gates.
- `DEC-080` — a **latent, unfixed** bug found in
  `pipelines/bootstrap/provision-identity-secrets.sh`: its
  `read <<EOF $(...) EOF` pattern doesn't propagate a failing
  subprocess's exit code through `set -e`. Worth fixing properly next
  time that script is touched.
- `DEC-081` — `fetch-source`'s `git clone ... .` fails on a storage
  class that formats fresh PVs ext4 (always creates a visible
  `lost+found`); fixed via `git init`/`fetch`/`checkout` instead.
- `DEC-082` — the pre-push anonymity sweep is not a formality; it caught
  a real violation on first serious contact this session. Run it fresh
  before every future push that includes anyone else's commits, and
  remember it needs to check the full `origin/main..main` *range*, not
  just working-tree content at HEAD.
- `DEC-083`/`DEC-084` — `deploy/argocd/apps/demo-prod.yaml` and
  `deploy/argocd/application-root.yaml` are single files **every**
  cluster bootstraps identically from the same Git history — a
  cluster-local decision (like deprotecting one cluster's `demo-prod`)
  can only ever be a live-only patch, never a commit to those files.
  `scripts/bootstrap.sh` guards the one real silent-failure mode this
  creates (a routine re-run silently re-enabling a deliberately-frozen
  cluster's auto-sync) — read its `--reenable-sync` usage text before
  re-running it against the SNO for any reason.
- `DEC-084` — reused the SNO's existing `golden-path-agent-github-token`
  PAT for the showcase's own promotion path rather than provisioning a
  second credential. `§8`'s PAT rotation (still deferred) now needs to
  rotate this value in **both** clusters' `golden-path-agent-ci`
  namespaces whenever it happens.

## Next session's mission

**Two independent threads are open — neither blocks the other:**

1. **Phase F: awaiting the owner.** F4 (RHDH platform stand-up) and F5
   (Scaffolder authoring) are gated per `DEC-087` on (a) a real demo date
   from the owner, which arms the `OI-04` trigger threshold (kickoff
   doc §4.2 item 5 — do not invent a date), and (b) explicit
   authorization to begin cluster work. **When that comes, the first
   task is the Ingress-vs-Route attempt with its ~1-hour timebox**
   (`DEC-087` item 3), using the `DEC-086` kubeconfig-hygiene rule
   (explicit `--context` or a dedicated `KUBECONFIG`, never the ambient
   shared one) throughout every `oc` invocation.
2. **Phase E: the first real sharing moment and refresh #2 remain
   pending**, unchanged since the prior session and not addressed by
   this one:
   - **First real sharing moment.** `docs/showcase-access.md` has the
     schedule template and anonymity-sweep procedure; the owner still
     needs to fill in the actual access list. Run the sweep (`DEC-082`),
     then share. `reports/phase-d-sharing-run.md` and `docs/showcase-
     walkthrough-script.md` are ready but were written before the
     promotion — re-verify content (digest, pod state) still matches the
     live showcase before presenting.
   - **Refresh #2.** A second from-scratch provision of the showcase —
     the run that proves the nine `DEC-080`/`DEC-081` bootstrap fixes
     held without re-discovery, and should re-run through a real
     promotion (`DEC-084`'s path is now normal, not a special case). The
     sandbox's TTL/renewal is an owner-managed operational item, not
     discoverable from inside the cluster — check the reservation portal
     before planning this.

**Also pending, lower priority, explicitly not blocking either thread
above**:

- **§8 PAT rotation** — still explicitly deferred by the owner. Touches
  **both** clusters' `golden-path-agent-ci` namespaces whenever it happens.
- **A real in-app logout control** (`DEC-076`) — named Phase E hardening
  candidate, touches the image, needs its own authorization.
- **The `DEC-065` `ConfigMap`-rollout `checksum/config`-annotation fix**
  — named, not yet implemented.
- **The per-cluster-overlays / hosted-registry evolution path** — fully
  documented (`DEC-078`, kept for reference by `DEC-083`), not scheduled.
- **`SysR-P-F-13`/`OS-09` independent verification** (Phase F) — a second
  team running `tools/instantiate_agent_project.py` unassisted. Not
  scheduled; named in `DEC-091` as a real, still-open acceptance item.

## Invariants that must survive any future session

These are load-bearing design decisions, not implementation details —
do not silently drift from them while doing other work. (Numbering kept
stable from earlier phases; corrections noted inline where later work
changed something.)

1. **DEC-008 arguments-sourcing — updated shape as of `DEC-049`.**
   `human_approval_node` is the sole invoker of a write-classified tool,
   and only once a real, terminal `approved` decision exists — it reads
   the arguments back from `state["approved_action"]`, populated *only*
   by `agent/approval_client.py::resolve_and_resume` from the approval
   service's own `IF-05` terminal-state query response, never a cached
   or re-derived copy. No other code path may call a write-classified
   tool.
2. **DEC-009 route assertion (list-based).** Every domain-eval-run model
   call must assert `route=primary, reason_code=none`, except cases
   specifically designed to exercise the fallback path — enforced via
   `state["model_calls"]` (a list, one entry per call), never the
   last-write-wins scalar fields.
3. **The 5-category rule for model swaps (`DEC-011`).** Any future
   primary-model change must pass the full 5-category acceptance test
   before adoption.
4. **The prompt-is-instrument rule (`DEC-012`), extended at `DEC-049`.**
   `decide_system_prompt.md`, `generate_system_prompt.md`, model choice,
   retrieval code, graph topology, `MODEL_TEMPERATURE`/`MODEL_SEED`
   (frozen at `temperature=0`/`seed=42`, `DEC-015`) are all part of the
   measurement instrument — any change requires a fresh, frozen-state,
   multi-pass re-baseline before its results are compared against
   anything measured before the change.
5. **`decide` never sees retrieved context, `generate` never sees tool
   schemas.** Regression-guarded by
   `tests/test_decide_node.py::test_context_never_reaches_decide_prompt`
   and `tests/test_generate_node.py::test_called_without_tools_kwarg`.
6. **OTel instrumentation stays read-only with respect to model inputs**
   (`DEC-020`, extended to `approval_service` at `DEC-071`).
   `OTLPSpanExporter(endpoint=...)` does **not** auto-append `/v1/traces`
   when `endpoint` is passed explicitly — both `agent/telemetry.py` and
   `approval_service/telemetry.py` already append it themselves. **Also
   now covers infra, not just code**: any image pinned for a supporting
   sidecar (e.g. the otel-collector's `traces-http` container) must be
   sourced from somewhere with no relationship to this project's own
   CI/promotion lifecycle — this project's own CI ImageStream prunes old
   build digests by design, which is exactly what broke the original
   pin (fixed, no DEC entry — see `reports/phase-e-otel-collector-fix.md`).
7. **`KNOWN_GAP_TOLERANCES` (`eval/cli.py`) is the only sanctioned way to
   exclude a case from the domain gate's failure count.** The four
   entries (`INJ-006`, `UAW-003`, `ITR-004`, `TSEL-004`) are final — do
   not add a fifth without new direction.
8. **The identity/config discipline (Phase D).** (a) Any new no-default
   env key in `agent/config.py` *or* `approval_service/config.py` must
   be declared on every deployment surface
   (`tools/check_config_contract.py` catches this automatically). (b)
   `demo-prod`'s three security-downgrade switches (`AUTH_MODE`,
   `AGENT_OIDC_MODE`, `MCP_AUTH_MODE`) are mechanically asserted `oidc`,
   never `none`, by that same script. (c) `demo-prod` `ConfigMap` changes
   need an explicit `oc rollout restart` to actually reach already-
   running pods (`DEC-065`).
9. **The single-pin, single-active-cluster model (Phase E, `DEC-083`/
   `DEC-084`).** `deploy/kustomize/base/kustomization.yaml`'s `images:`
   block is a *single, shared* pin; only one cluster's `demo-prod` is
   ever active. The **showcase** is that cluster now; its pipeline
   promotes normally. The **SNO's** `demo-prod` is deliberately
   deprotected and must **stay** that way unless the owner explicitly
   decides otherwise. Never run `scripts/bootstrap.sh ... --reenable-sync`
   against the SNO without that explicit direction.
10. **New at Phase F — kubeconfig hygiene (`DEC-086`).** Every `oc`
    invocation for the remainder of Phase F must pin an explicit
    `--context=<name>` or use a dedicated `KUBECONFIG` scoped to the
    showcase cluster — never the ambient shared current-context. Found
    live: the shared kubeconfig's current-context silently switched
    mid-session to an unrelated project on the SNO (another concurrent
    process's own `oc login`). Survivable during F0's read-only checks;
    would risk mutating the wrong cluster during F4's writes.

## Pointers

- `DECISIONS.md` — the complete, authoritative decision history,
  `DEC-001` through `DEC-091`. Always read the tail before starting new
  work in a fresh session.
- `PINS.md` — every pinned component version, with the live-verification
  date and source. Has a "Phase E — Shared showcase cluster" section and
  a "Phase F — Internal Developer Portal (RHDH)" section, both verified
  live.
- `docs/phase-f-kickoff-plan.md` — **the governing Phase F plan**, kept
  current in place as each STOP clears (unlike the Phase E kickoff plan
  below, which is a static record of a session already fully executed).
  Read this first for any Phase F work — its own STATUS banner states
  exactly what's done and what's gated.
- `reports/phase-f-f2-verification.md`, `reports/phase-f-f3-
  verification.md` — F2/F3's execution evidence (image-digest
  comparison, CI-equivalent local runs, the real defect found and fixed,
  the passing second render).
- `skeleton/`, `template-schema.json`, `docs/template-nine-output-
  mapping.md` — F2's deliverables. `tools/skeleton_renderer.py`,
  `tools/verify_skeleton.py`, `tools/instantiate_agent_project.py` —
  F2/F3's tooling, deliberately sharing one rendering engine.
- `catalog-info.yaml` — F1's deliverable, inert until F4.
- `reports/phase-e-otel-collector-fix.md` — the OTel collector fix, this
  session's other piece of work. No DEC entry (drafted, never committed,
  per `/close-step`'s governance) — this report is the only record.
- `docs/phase-e-kickoff-plan.md` — the Phase E session's own plan,
  already fully executed (all four STOPs authorized and acted on); a
  static historical record now, not a living document the way the Phase
  F kickoff plan is.
- `scripts/bootstrap.sh` / `make bootstrap CLUSTER=<kubeconfig>` — the
  scripted from-scratch bootstrap. Re-runnable; idempotent except
  `provision-identity-secrets.sh`'s own credential regeneration.
- `docs/phase-c-runbook.md` §2b — the `golden-path-agent-ci-config`
  `ConfigMap` prerequisite.
- `reports/phase-e-refresh-log.md` — refresh #1's full timing and the
  nine gaps found and fixed.
- `reports/phase-d-sharing-run.md`, `docs/showcase-access.md`,
  `SHOWCASE_NOTES.md`, `docs/showcase-walkthrough-script.md` — the Phase
  E STOP 3/STOP 4 artifacts. Blocking condition resolved (`DEC-084`);
  the owner filling in the access list is what's actually still pending.
- `reports/phase-c-sharing-run.md`, `reports/phase-b-sharing-run.md` —
  earlier sharing artifacts these follow the same shape as.
- `reports/phase-d-d1-verification.md`, `reports/phase-d-d2-verification.md`,
  `reports/checkpoint-d-run.md`, `reports/phase-d-owner-walkthrough-verification.md`,
  `reports/browser-walkthrough-screenshots/` — Phase D's own closure
  evidence.
- `docs/owner-walkthrough.md` — the closed-out owner click-through
  script (Checkpoint D), distinct from `docs/showcase-walkthrough-script.md`.
- `tools/query_traces.py`, `tools/verify_owner_walkthrough.py`,
  `tools/browser_verify_owner_walkthrough.py` — Phase D's own
  verification tooling, unchanged.
