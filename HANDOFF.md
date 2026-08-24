# Session handoff

**This file was rewritten at the close of Phase E's kickoff session**
(previously rewritten at Checkpoint D's formal closure; `DEC-078`
through `DEC-082` had drifted out of it since). `DECISIONS.md`
(currently through `DEC-082`) is the authoritative, complete,
chronological record of every decision this project has made — this
file is a *pickup* summary, not a substitute for it. When in doubt,
`DECISIONS.md` wins.

## Where this is

**Checkpoint D is closed (unchanged since the last rewrite). Phase E's
kickoff plan is now owner-authorized and its first execution pass is
done**, with real results, not just a plan:

- **The showcase cluster's from-scratch bootstrap is proven.** A real,
  dedicated OpenShift cluster (never touched by this project before) was
  bootstrapped entirely from Git — including, for the first time in this
  project's history, the cluster-scoped operator installs (OpenShift
  Pipelines, OpenShift GitOps) that the SNO always had pre-installed by
  other work. `make bootstrap CLUSTER=<kubeconfig>` (`scripts/bootstrap.sh`,
  new this session) is the scripted replay. Nine real, previously-
  undocumented gaps were found and fixed live — see `DECISIONS.md`
  `DEC-080`/`DEC-081` for the full list (OLM Manual-approval InstallPlans,
  two undocumented Keycloak bootstrap secrets, a Keycloak-Ready-vs-
  RealmImport-Done race, a storage-class-specific `git clone` failure,
  a missing `ConfigMap`, an ArgoCD RBAC namespace-label requirement, and
  the never-documented step of applying the `Pipeline`/`Task` definitions
  themselves).
- **One full `PipelineRun` went green on the showcase cluster** —
  `unit-tests` through `operational-tests`, all passing, `eval-gate-live`
  scoring 60/62 (the same standing baseline reported since Phase B, now
  independently reproduced on a different cluster and image build from
  the same commit). `open-promotion-pr` failed cleanly on a missing
  credential — blocked by construction, not just by discipline.
- **A real, previously-unflagged architecture gap was found and named,
  not silently patched around**: `DECISIONS.md` `DEC-078` — the single
  shared `images:` digest pin in `deploy/kustomize/base/kustomization.yaml`
  is not portable across clusters (it resolves to whichever cluster's
  own internal registry happens to be running it), and if a second
  cluster's pipeline ever merged its own promotion PR against that one
  shared pin, it would silently break the SNO's already-live `demo-prod`.
  This session's showcase bootstrap deliberately does **not** grant the
  showcase promotion authority (`DEC-078`'s "Option 2"). The real fix —
  three coupled, separately-reviewed commits ending in the showcase
  getting real promotion authority over its own digest — is scoped but
  **not implemented**. See "Next session's mission" below.
- **A real anonymity-rule violation was caught pre-push and fixed by
  local history rewrite** (`DECISIONS.md` `DEC-082`) — a live MaaS
  hostname had been committed twice (via the concurrent
  `feature/workspace-tooling` merge, not this session's own work) in
  violation of this repo's "every committed model endpoint is a
  placeholder" rule. Fixed before anything left the machine; the pushed
  history has zero occurrences, verified commit-by-commit.
- **The STOP 3/STOP 4 artifacts the kickoff plan named are drafted**:
  `reports/phase-d-sharing-run.md` (the after-D sharing moment),
  `docs/showcase-access.md` (the sharing-schedule template, structure
  only — no real names/emails), `SHOWCASE_NOTES.md` (E4's feedback-log
  skeleton), `docs/showcase-walkthrough-script.md` (the ~20-minute
  script). None of these have been *used* yet (no real sharing moment
  has happened) — they're ready for when one can.

**`DECISIONS.md` `DEC-078` through `DEC-082`** cover all of this in full
detail. A few real live findings worth knowing before touching either
cluster again:

- `DEC-080` — OLM `installPlanApproval: Manual` requires explicit
  InstallPlan approval even for the pinned `startingCSV` on a first
  install, not just on upgrades — never exercised before this session
  (Keycloak's OLM path was always blocked earlier by `DEC-055` on the
  SNO). `scripts/bootstrap.sh`'s `wait_for_csv` now approves the
  InstallPlan on every poll, matched against the exact pinned CSV only.
- `DEC-080` — `golden-path-agent-keycloak-db-secret`/`-admin` and
  (`DEC-081`) `golden-path-agent-ci-config` were all real, previously
  undocumented manual prerequisites. All three are now documented
  (`docs/phase-c-runbook.md` §2b for the `ConfigMap`; `scripts/bootstrap.sh`
  creates the two Keycloak secrets itself, create-once) and checked by
  `scripts/bootstrap.sh`'s own gates.
- `DEC-080` — a **latent, unfixed** bug found in
  `pipelines/bootstrap/provision-identity-secrets.sh`: its
  `read <<EOF $(...) EOF` pattern doesn't propagate a failing
  subprocess's exit code through `set -e`. The race that triggered it
  live (Keycloak `Ready` vs. `KeycloakRealmImport` `Done`) is now
  eliminated by an explicit wait in `scripts/bootstrap.sh`, but the
  underlying swallow-on-failure pattern in that script is still there —
  worth fixing properly next time that script is touched.
- `DEC-081` — `fetch-source`'s `git clone ... .` fails on a storage
  class that formats fresh PVs ext4 (always creates a visible
  `lost+found`); fixed via `git init`/`fetch`/`checkout` instead. Worth
  remembering if a *third* cluster's storage class surfaces a different
  quirk in the same task.
- `DEC-082` — the pre-push anonymity sweep is not a formality; it caught
  a real violation on first serious contact this session. Run it fresh
  before every future push that includes anyone else's commits, not just
  your own, and remember it needs to check the full `origin/main..main`
  *range*, not just working-tree content at HEAD (a per-commit diff
  check catches things a HEAD-only grep would miss if a later commit
  happened to also touch the same line).

## Next session's mission

**`DECISIONS.md` `DEC-078`'s three-part follow-up, starting with part 1
(the hosted-registry migration).** This is the real fix for the
registry-portability gap — not optional polish, load-bearing for the
showcase ever being a genuine second live environment:

1. **Hosted-registry migration** — `deploy/kustomize/base/kustomization.yaml`'s
   `newName` to an externally-reachable registry (e.g. `ghcr.io` under
   the same GitHub account already used for the promotion-PR credential);
   `pipelines/pipeline.yaml`'s `image-repo` default;
   `pipelines/tasks/digest-capture.yaml` rewritten off `oc get
   imagestreamtag` onto buildah's own digest result; a new registry
   push/pull `Secret` + `imagePullSecrets`; RRT row 16's Notes column +
   a new `PINS.md` row. **Verify against the SNO's live `demo-prod`
   first** — this changes what an already-working system pulls from.
2. **Per-cluster digest pins via overlays** — move the `images:` block
   out of `deploy/kustomize/base/` into per-cluster `demo-prod` overlays
   (`overlays/demo-prod-sno/`, `overlays/demo-prod-showcase/`). Makes
   the shared-pin breakage path structurally impossible, not just
   discipline-avoided.
3. **Promotion-PR parametrized by target overlay** — `open-promotion-pr`
   takes the overlay as a parameter. **After this lands, grant the
   showcase promotion authority over its own overlay** — that grant is
   this follow-up's own closure.

One repo throughout — no second repo, no branch-per-cluster; flag it if
anything drifts that way.

**Also pending, lower priority, explicitly not blocking the above**:

- **Refresh #2** — needs a second from-scratch provision of the showcase
  (or the same sandbox torn down and re-requested within its reservation
  window). The showcase sandbox's TTL/renewal is an owner-managed
  operational item (`DEC-078`), not something discoverable from inside
  the cluster — check the reservation portal directly before planning
  this.
- **§8 PAT rotation** — still explicitly deferred by the owner (`DEC-036`/
  `DEC-039`/`docs/phase-c-runbook.md`'s own backlog item 4). Unrelated to
  the registry work above; do it separately whenever convenient.
- **A real in-app logout control** (`DEC-076`) — named Phase E hardening
  candidate, touches the image, needs its own authorization.
- **The `DEC-065` `ConfigMap`-rollout `checksum/config`-annotation fix**
  — named, not yet implemented.
- **Real sharing moments** — blocked on (a) the registry follow-up
  giving the showcase's `demo-prod` something to actually show, and
  (b) the owner filling in `docs/showcase-access.md`'s access list.

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
   or re-derived copy. (`state["approval_action"]`, this invariant's
   original field name, was retired at `DEC-049` — the field is now
   split into `drafted_action`, audit-only, and `approved_action`, the
   only one `human_approval_node` ever reads — structural, not
   comment-only, enforcement of this same invariant.) No other code path
   may call a write-classified tool.
2. **DEC-009 route assertion (list-based).** Every domain-eval-run model
   call must assert `route=primary, reason_code=none`, except cases
   specifically designed to exercise the fallback path — enforced via
   `state["model_calls"]` (a list, one entry per call), never the
   last-write-wins scalar fields. Any new node making a model call must
   append to `model_calls`.
3. **The 5-category rule for model swaps (`DEC-011`).** Any future
   primary-model change must pass the full 5-category acceptance test
   before adoption.
4. **The prompt-is-instrument rule (`DEC-012`), extended at `DEC-049`.**
   `decide_system_prompt.md`, `generate_system_prompt.md`, model choice,
   retrieval code, graph topology, `MODEL_TEMPERATURE`/`MODEL_SEED`
   (frozen at `temperature=0`/`seed=42`, `DEC-015`) are all part of the
   measurement instrument — any change requires a fresh, frozen-state,
   multi-pass re-baseline before its results are compared against
   anything measured before the change. Any future graph-code-only
   change should state explicitly why it's instrument-safe, then prove
   it with one pass, not assume it (`DEC-049`'s own precedent).
5. **`decide` never sees retrieved context, `generate` never sees tool
   schemas.** Regression-guarded by
   `tests/test_decide_node.py::test_context_never_reaches_decide_prompt`
   and `tests/test_generate_node.py::test_called_without_tools_kwarg`.
6. **OTel instrumentation stays read-only with respect to model inputs**
   (`DEC-020`, extended to `approval_service` at `DEC-071`). Any future
   telemetry change must be verified by diffing the actual model-call
   construction, not assumed safe. `OTLPSpanExporter(endpoint=...)` does
   **not** auto-append `/v1/traces` when `endpoint` is passed explicitly
   — both `agent/telemetry.py` and `approval_service/telemetry.py`
   already append it themselves; any new OTLP endpoint construction must
   do the same or spans silently 404 with nothing to notice.
7. **`KNOWN_GAP_TOLERANCES` (`eval/cli.py`) is the only sanctioned way to
   exclude a case from the domain gate's failure count.** The four
   entries (`INJ-006`, `UAW-003`, `ITR-004`, `TSEL-004`) are final per
   the owner's standing "no further iteration" instruction — do not add
   a fifth without new direction.
8. **The identity/config discipline (Phase D).** (a) Any new no-default
   env key in `agent/config.py` *or* `approval_service/config.py` must
   be declared on every deployment surface
   (`tools/check_config_contract.py` catches this automatically — run it
   after adding one, don't wait for CI). (b) `demo-prod`'s three
   security-downgrade switches (`AUTH_MODE`, `AGENT_OIDC_MODE`,
   `MCP_AUTH_MODE`) are mechanically asserted `oidc`, never `none`, by
   that same script — if a fourth one is ever added, add it to
   `DEMO_PROD_REQUIRED_VALUES` too. (c) `demo-prod` `ConfigMap` changes
   need an explicit `oc rollout restart` to actually reach already-
   running pods (`DEC-065`) — a `Deployment` spec/digest change rolls
   automatically, a `ConfigMap`-only change does not.
9. **New at Phase E — the single-registry-pin constraint (`DEC-078`).**
   `deploy/kustomize/base/kustomization.yaml`'s `images:` block is a
   *single, shared* pin — it is not yet safe for a second cluster's
   pipeline to have promotion authority over it (that pipeline would
   overwrite the SNO's own live pin). Do not grant a second cluster's
   `open-promotion-pr` a working GitHub PAT until `DEC-078`'s three-part
   follow-up (hosted registry → per-cluster overlay pins → parametrized
   promotion) has actually landed and been verified. This invariant
   retires itself once that follow-up closes.

## Pointers

- `DECISIONS.md` — the complete, authoritative decision history,
  `DEC-001` through `DEC-082`. Always read the tail before starting new
  work in a fresh session.
- `PINS.md` — every pinned component version, with the live-verification
  date and source. Phase E added a "Phase E — Shared showcase cluster"
  section (operator channels/CSVs, storage class, registry state, all
  verified live against the actual showcase cluster).
- `docs/phase-e-kickoff-plan.md` — the plan this session executed
  against. All four of its STOPs are now authorized and acted on; its
  own §2.4 `make bootstrap` open question is resolved (built, this
  session, `scripts/bootstrap.sh`).
- `scripts/bootstrap.sh` / `make bootstrap CLUSTER=<kubeconfig>` — the
  scripted from-scratch bootstrap, new this session. Re-runnable;
  idempotent except `provision-identity-secrets.sh`'s own credential
  regeneration.
- `pipelines/bootstrap/pipelines-operator.yaml` /
  `gitops-operator.yaml` — new this session, the first OLM Subscriptions
  this project has ever had to author for these two operators (the SNO
  always had them pre-installed).
- `docs/phase-c-runbook.md` §2b — the newly-documented
  `golden-path-agent-ci-config` `ConfigMap` prerequisite (found live
  this session, previously undocumented anywhere).
- `reports/phase-e-refresh-log.md` — refresh #1's full timing, the nine
  gaps found and fixed, the eval-parity result, and the known-incomplete
  markers.
- `reports/phase-d-sharing-run.md`, `docs/showcase-access.md`,
  `SHOWCASE_NOTES.md`, `docs/showcase-walkthrough-script.md` — the
  STOP 3/STOP 4 artifacts, drafted, not yet used for a real sharing
  moment.
- `reports/phase-c-sharing-run.md`, `reports/phase-b-sharing-run.md` —
  the earlier sharing artifacts these new ones follow the same shape as.
- `reports/phase-d-d1-verification.md`, `reports/phase-d-d2-verification.md`,
  `reports/checkpoint-d-run.md`, `reports/phase-d-owner-walkthrough-verification.md`,
  `reports/browser-walkthrough-screenshots/` — Phase D's own closure
  evidence, still the source material `reports/phase-d-sharing-run.md`
  draws from.
- `docs/owner-walkthrough.md` — the closed-out owner click-through
  script (Checkpoint D closure), distinct from
  `docs/showcase-walkthrough-script.md` (the new, broader ~20-minute
  narrative script for any colleague session).
- `tools/query_traces.py`, `tools/verify_owner_walkthrough.py`,
  `tools/browser_verify_owner_walkthrough.py` — Phase D's own
  verification tooling, unchanged this session.
- `~/.claude/plans/i-wanna-continue-with-eager-turtle.md` — this
  session's own plan document (registry-gap analysis, the nine-step
  bootstrap design, the STOP 3/4 artifact scope).
