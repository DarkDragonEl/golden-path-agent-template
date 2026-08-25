# Phase F kickoff plan — the Internal Developer Portal (RHDH)

**STATUS: F0–F3 complete (`DEC-085`–`DEC-090`). F1 committed (STOP 2
cleared). F2's skeleton/schema/mapping verified with executed evidence,
including a live image-digest comparison and CI-equivalent local runs
(STOP 3 conditionally cleared, evidence in `reports/phase-f-f2-
verification.md`). F3's CLI instantiation is built and proven by
execution under a distinct parameter set — a real defect (a stray `srs/`
dependency in `tests/test_trace_check.py`) was found and fixed along the
way, not just diffed — full evidence in `reports/phase-f-f3-
verification.md`. `SysR-P-F-01`(b) is satisfied. Held at STOP 4 for
owner review. F4/F5 remain gated on a real demo date and the
Ingress/Route attempt outcome — see §4.2 below, each item annotated
with its resolution.** Originally
drafted before any of this was executed, entirely from a read of the
governing requirements docs (`SyRS-AGP-001_EN.md`, `StRS_Agentic_AI_
Platform_EN.md`, `SyRS-AGP-001-RRT_Realization_Table.md`,
`Annex_A_Open_Items_EN.md`) and this repo's current state at the time.

## 0. How to read this document

Same convention as `docs/phase-e-kickoff-plan.md`: a proposal, not a
runbook of work already done. Each phase section ends with its own
**STOP** — a point where this plan should not proceed further without the
owner's explicit review and go-ahead, matching this project's own
plan-per-gate discipline. Sections that describe *why* something is needed
(§1–§3) don't carry a STOP of their own — they're context for the phase
sections that do.

## 1. What Phase F is, and what it is not

**The normative requirement.** `SyRS-AGP-001_EN.md` `SysR-P-F-01`: the
platform shall provide an agent project template instantiable **(a)
through the Internal Developer Portal and (b) directly via a command-line
interface** against the template repository, producing in one operation:
agent source scaffold, container build configuration, deployment
manifests, GitOps configuration, MCP tool skeleton, evaluation project,
telemetry configuration, policy scaffolding, and developer documentation.
Both (a) and (b) are normative and required in parallel — (b) is not a
lesser fallback bolted on for safety, it is a co-equal path under the same
requirement.

**RHDH is the named realization, not the requirement itself.** The
informative (non-normative) `SyRS-AGP-001-RRT_Realization_Table.md` row 13
names Red Hat Developer Hub, version "1.10 (GA 2026-06)", as the
realization of the (a) half. RHDH the *product* has been GA for years —
1.10 is simply this project's own pinned target minor version, GA'd
2026-06. That distinction matters for how §4/§7 below assess risk: the
risk is a specific months-old minor version on a shared sandbox, not
product immaturity.

**Annex A `OI-04`** (adopted): portal integration is assumed achievable
with bounded effort in phase one, "additive, not foundational," since the
template is "a thin wrapper over a directly instantiable repository." Its
revision trigger: if portal-integration effort demonstrably endangers the
demonstration milestone, it demotes from "shown working" to "shown as
scaffolding" **for that milestone only** — direct CLI instantiation alone
satisfies the demo in that case. **Full portal exposure remains required
for full MVP acceptance (`OBJ-01`) regardless** — the trigger demotes the
milestone presentation, never the acceptance criterion. This is a
pre-approved, already-documented escape hatch; invoking it needs a status
note, not new sign-off (see §10) — the trigger *threshold* itself is
owner-set (§4.2 item 5).

**Explicitly out of scope, and separate from the above**:
`StRS_Agentic_AI_Platform_EN.md` §2 puts exposing RHDH's own capabilities
(e.g. scaffolder templates) as an **agent-invocable MCP tool at runtime**
out of scope for the MVP, naming it a phase-two candidate: "In phase one
the portal scaffolds agents (`StR-DX-01`); it is not itself a tool that
agents invoke." This is actively enforced today, not just written down: a
live eval case, `eval/cases/domain/out_of_domain.yaml` `OOD-006`, requires
the deployed agent to *refuse* "Can you scaffold a new microservice
repository for me using the Internal Developer Portal?" Verified this
session — `mcp_server/server.py`'s five `@mcp.tool()`-registered functions
today are `placeholder_lookup`, `placeholder_write_action`,
`itsm_search_records`, `itsm_create_request`, `healthcheck`. **No phase of
this plan may add a sixth that wraps RHDH's scaffolder API** — every phase
below that touches `mcp_server/` restates this boundary explicitly.

**Not one of CLAUDE.md's three closed "integration-point-only" items.**
`CLAUDE.md`'s "Data Mesh, AI Routing Grid, Secure Agent Sandbox" triad is a
closed list, governed by its own attach-behind-a-contract pattern. RHDH is
governed by its own distinct requirement/assumption pair (`SysR-P-F-01` /
`OI-04`) instead — it is not that pattern, and this plan does not treat it
as one.

## 2. The critical path is F2→F3 — state this up front

**F2 (templating engine) → F3 (CLI parity) alone fully satisfy
`SysR-P-F-01`'s (b) half with zero RHDH dependency.** F1 (catalog
registration) contributes nothing to the (b) path — it's RHDH-facing
metadata, inert until F4 — it's sequenced first only because it's small,
independent, and committable on its own, not because the CLI path needs
it. F2 is also a prerequisite for F5 regardless (F5's Scaffolder Template
wraps F2's same skeleton — there is no version of F5 that doesn't need F2
to exist first). This makes F2–F3 the critical path independent of
anything that happens with RHDH itself.

**F4 (RHDH platform stand-up) and F5 (Template/Scaffolder authoring) are
the optional-*timing* layer, not optional *scope*.** Per §1's Annex A
recap, full portal exposure remains normatively required for `OBJ-01`.
`OI-04`'s revision trigger only ever demotes *when* portal exposure is
demonstrated — for the demonstration milestone specifically — never
*whether* it gets built at all. Given that, §10's fallback discussion is
really just a direct consequence of this sequencing, not a separate
argument: ship F1–F3 regardless, and F4/F5 either land before the demo or
get reordered to after it.

## 3. Current state — nothing is built yet

Confirmed via direct search of `golden-path-agent-template/`, zero hits for
RHDH, Backstage, `catalog-info.yaml`, or any templating tool (no
cookiecutter, copier, or custom scaffold script).

More importantly: **even the (b) CLI-instantiation half isn't real yet.**
Today "direct instantiation" means cloning this git repository — there is
no operation that takes it as a *template* and *renders a new,
distinctly-parameterized project* the way `SysR-P-F-01`'s "produces in one
operation" language requires. Every identifier in the repo — `golden-path-
agent`, `golden-path-agent-ci`, `golden-path-agent-otel`, namespace names,
image references — is hardcoded literal text across dozens of files
(`Containerfile`, `deploy/`, `pipelines/`, `ci/`, `mcp_server/`,
`agent/config.py`, `docs/`). This is a real engineering gap independent of
RHDH, and it's what F2 exists to close.

The only human-facing UI today is `agent/static/approver_ui.html` (an
approval-review surface, not a portal), exposed via a plain Kubernetes
`Ingress` (deliberately not a `Route`, `deploy/kustomize/base/
ingress.yaml`). No catalog, landing page, or discovery mechanism exists —
a user must already know the direct URL.

## 4. Phase F0 — kickoff research & decision gate

Mirrors the discipline `DECISIONS.md` `DEC-021`/`DEC-078` established for
Phase C/E: populate a `PINS.md` "Phase F" section from live cluster state
*before* any Subscription/bootstrap YAML is authored.

### 4.1 Live checks, per cluster — not generalized across them

`DEC-055`'s poisoned `CatalogSource` (a different tenant's broken catalog
blocking OLM resolution cluster-wide) was specifically the SNO. The
showcase cluster's catalogs were confirmed healthy at the last refresh
(`PINS.md` Phase E, Keycloak row: "this cluster's catalog is not
poisoned"). **An OperatorHub check on one cluster says nothing about the
other** — both get checked independently, and this plan does not assume
either cluster's outcome from the other's history:

- `oc get packagemanifest -n openshift-marketplace | grep -i 'rhdh\|developer-hub\|backstage'` on **both** the SNO and the showcase cluster.
- Whether the RHDH Operator auto-provisions its own Postgres or requires a pre-existing instance — read the Operator's actual CR spec live, not from memory.
- Current resource quota/utilization on whichever cluster ends up targeted (RHDH's footprint — backend, frontend, its own DB, potential plugin pods — is heavier than anything stood up in this project so far).

### 4.2 Seven open decisions — human calls, not defaults

**All seven resolved by the owner, `DEC-087`.** Full reasoning lives in
that entry; only the resolutions are restated here so this doc stays
readable standalone.

1. **Templating-engine approach** — **RESOLVED (`DEC-087`)**:
   Backstage-native `${{ values.x }}`/nunjucks syntax as the single
   source of truth. Custom code lands in F3's CLI renderer (a small
   Python nunjucks-compatible renderer); F5 uses the stock
   `fetch:template` action with zero custom RHDH plugin code.
2. **Auth wiring** — **RESOLVED (`DEC-087`)**: reuse the existing
   `golden-path-agent-keycloak` realm, register a new OIDC client for
   RHDH. No second realm.
3. **Ingress vs. Route for RHDH's own UI** — **RESOLVED (`DEC-087`)**:
   attempt to hold the Ingress-only precedent first; if the `Backstage`
   CR doesn't allow cleanly disabling its own Route generation within
   ~1 hour of effort at F4, take the Route as a documented one-off
   exception with its own DEC entry citing this pre-approval.
4. **`publish:` action scope** — **RESOLVED (`DEC-087`)**: local-render
   only is F5's Definition of Done. A PR against one named demo-scratch
   repo is an explicit stretch goal, attempted only after that DoD is
   green and only with separate owner sign-off for the credentials it
   needs. No fleet rollout.
5. **`OI-04` trigger threshold** — **RESOLVED IN SHAPE, VALUE STILL
   PENDING (`DEC-087`)**: invoke the fallback if F5 has not produced a
   stable, live Template run by demo-date minus 5 working days. The demo
   date itself is not yet set — this trigger cannot be operationalized
   until it is. Whoever next touches F4/F5 should re-ask for a real date
   rather than assume one.
6. **RHDH namespace naming** — **RESOLVED (`DEC-087`)**:
   `golden-path-agent-rhdh`.
7. **Fallback if RHDH is absent from either cluster's catalog** —
   **MOOT (`DEC-085` amended, `DEC-087`)**: moot because the SNO is
   frozen for new work (`HANDOFF.md` invariant 9), not because its
   catalog was verified either way — the original F0 pass's SNO
   observation was made under a mis-switched kubeconfig context and is
   explicitly not treated as verified (see `PINS.md`'s SNO row). The
   showcase cluster's own catalog, the only one that matters for new
   work, has RHDH present — no live case to resolve regardless.

**STOP 1 — cleared.** F1 and F2 are authorized for this pass (F1 needed
none of the seven; F2 needed only item 1, now resolved), each still
gated by its own STOP 2/STOP 3 below. F4/F5 remain blocked on item 5's
still-pending demo date and item 3's Ingress/Route attempt outcome.

## 5. Phase F1 — catalog registration

Author a `catalog-info.yaml` at repo root declaring this repo as a
Backstage `Component` — type, lifecycle, owner using this repo's existing
generic "golden-path-agent" placeholder branding (never a real
organization name, per `CLAUDE.md`'s anonymity rule), links to `docs/
architecture.md`, `docs/environments.md`, the approver UI. Valid and
committable independent of whether RHDH is installed yet (F4) — it simply
sits inert until F4 lands, at which point it becomes real. The earliest
independent deliverable, not a critical-path item for `SysR-P-F-01`(b)
(§2) — sequenced first for its own sake, not because F2/F3 depend on it.

**STOP 2** — owner reviews the drafted `catalog-info.yaml` (component
metadata, owner field, linked docs) before it's committed.

## 6. Phase F2 — templating-engine build

The real, RHDH-independent gap named in §3: turn every hardcoded literal
across `Containerfile`, `deploy/`, `pipelines/`, `ci/`, `mcp_server/`,
`agent/config.py`, `docs/` into one parameterized skeleton (shape decided
by §4.2 item 1), with a parameter schema, and an explicit mapping from
each of `SysR-P-F-01`'s nine required outputs (agent source scaffold,
container build configuration, deployment manifests, GitOps configuration,
MCP tool skeleton, evaluation project, telemetry configuration, policy
scaffolding, developer documentation) to its concrete location in the
skeleton.

This phase exists specifically to avoid repeating `DECISIONS.md` `DEC-075`
at template scale: that decision's root cause was exactly two hand-
maintained copies of one constant (`agent/static/approver_ui.html`'s
`APPROVAL_SERVICE_ORIGIN` default vs. a second hardcoded copy in `tools/
verify_owner_walkthrough.py`) silently drifting apart. F3 (CLI) and F5
(Scaffolder) must render from this **one** skeleton, never two
independently-maintained ones.

**Boundary guard, restated here too**: the skeleton itself must never
include an MCP tool definition wrapping "create a new project/repo" — a
freshly-rendered project's own `mcp_server/server.py` must not gain a
scaffold-invoking tool either. This is a Definition-of-Done line item for
this phase, not just F5's.

The largest phase in this plan by raw file count, though it introduces no
new infrastructure or operator.

**Done (`DEC-088`)**: 210-file skeleton at `skeleton/`, parameter schema
at `template-schema.json`, nine-output mapping at `docs/template-nine-
output-mapping.md`, verification script at `tools/verify_skeleton.py`
(committed — doubles as F3's own regression check). Inventory found 82
of ~210 candidate files needed substitution, all resolving to one
consistent base-name-plus-fixed-suffix pattern. Boundary DoD confirmed
by count (5 `@mcp.tool()` registrations in the skeleton, matching the
source repo exactly — no scaffold-invoking sixth). Both the raw skeleton
and a real rendered-with-test-values output pass full Python/YAML/JSON
validity, and the rendered output has zero surviving source literals and
zero unresolved placeholders.

**STOP 3** — owner reviews the skeleton structure, parameter schema, and
the nine-output mapping before F3/F5 are built against it.

## 7. Phase F3 — CLI-instantiation parity

A `tools/`-convention script (matching the existing `tools/
verify_owner_walkthrough.py` pattern) that consumes F2's **same** skeleton
and parameter schema, prompts for/accepts values, and renders a fully
parameterized new project locally in one operation — literally satisfying
`SysR-P-F-01`'s "produces in one operation" language for the (b) path,
with zero RHDH dependency. Closes the critical path from §2: once F2–F3
exist, `SysR-P-F-01`(b) is fully, independently satisfiable, which is what
makes §10's fallback a real, ready option rather than something
scrambled together under pressure.

**Definition of Done — rendered means running, not well-formed.** A clean
diff against the source repo proves the output is well-formed; it does not
prove it works. This project's own track record is explicit that
well-formed and working diverge in practice (`DEC-060`: a code path that
existed for two phases without ever being executed). So F3's DoD is: the
rendered project, **executed untouched after rendering** — its own offline
test suite green, and its own `make eval` (fake-mode/local) green, both
under the new identifiers, not the source repo's originals. Record the
exact commands and their real output. `SysR-P-F-13`/`OS-09` (a second team
running the same operation unassisted) is the acceptance-level echo of
this same check — this phase cannot self-certify that one, only this
execution-based DoD.

**Done (`DEC-090`)**: `tools/instantiate_agent_project.py` built
(`tools/skeleton_renderer.py` shared with F2's own verification tool).
First render surfaced a real defect (`tests/test_trace_check.py`'s one
real-`srs/`-file-dependent test) that a diff alone would not have caught
— fixed by removing `tools/trace-check/`/`tests/test_trace_check.py`/the
dead `Makefile` `trace` target from `skeleton/`. Second render, fresh
distinct parameters (`name=acme-hr-helper`): literal/placeholder sweeps
clean, rendered project's own `pytest -q` → 210 passed, own `make
eval-fast` → 2/2 passed, both via the real Makefile, both untouched
after rendering. Full evidence in `reports/phase-f-f3-verification.md`.

**STOP 4** — owner reviews the rendered project's execution evidence (test
suite + eval run output, not just a diff) before `SysR-P-F-01`(b) is
treated as satisfied.

## 8. Phase F4 — RHDH platform stand-up

The heavy infrastructure phase, gated by F0's live, per-cluster decisions.

- **Deployment model**: Operator via OLM is this project's established
  default pattern elsewhere (Pipelines, GitOps, and — until `DEC-055`/
  `DEC-056` forced a fallback — Keycloak), but confirmed live per-cluster
  in F0, never assumed.
- **If OLM is chosen, extend the existing mechanism — do not add a second
  one.** `scripts/bootstrap.sh` already has `wait_for_csv`/
  `approve_pending_installplan` (built in `DEC-080` for the Pipelines/
  GitOps operator installs on the showcase cluster): `installPlanApproval:
  Manual`, with the InstallPlan's own CSV checked against the pinned value
  before patching approval — this project's own "pin exact versions, no
  silent auto-upgrade" discipline applied to OLM specifically. RHDH's own
  Operator install replays this exact function, parameterized with RHDH's
  namespace/CSV, rather than introducing a separate operator-install path.
- **Postgres**: reuse the pattern Keycloak's own DB used in Phase D —
  OpenShift's built-in `openshift/postgresql` `ImageStream` rather than an
  external image, for the same `restricted-v2`/non-root-UID reasons
  already documented in `PINS.md`'s Phase D section — contingent on F0
  confirming the Operator supports pointing at an external Postgres rather
  than mandating its own bundled one.
- **Auth**: wire to the existing `golden-path-agent-keycloak` realm per
  §4.2 item 2's outcome.
- **Namespace/RBAC**: namespace creation is deliberately bootstrap-only/
  out-of-band in this project (`pipelines/bootstrap/namespaces.yaml`,
  since the pipeline's own ServiceAccount is denied cluster-scoped RBAC) —
  a new RHDH namespace needs the same manual bootstrap step, never a
  pipeline-created one.
- **GitOps wiring**: a new Argo CD Application under `deploy/argocd/apps/`
  tracking a new `deploy/kustomize/overlays/rhdh/` (or equivalent)
  directory; `deploy/argocd/project.yaml`'s `namespaceResourceWhitelist`
  needs new entries for whatever CRD kind the RHDH Operator's own CR
  introduces, plus a new `destinations` entry — the same additive pattern
  already used for `PersistentVolumeClaim` (`DEC-064`) and `Secret`/
  `Application` before it.
- Should remain **namespace-scoped to this project**, not a cluster-wide
  shared instance, matching every other component's single-tenant
  footprint on these shared clusters.

**Risks specific to a shared/time-limited sandbox** (per `PINS.md`'s own
Phase E section):
- **Resource budget**: RHDH is materially heavier than anything stood up
  so far, layered onto an already-running footprint. Live-check quota/
  utilization in F0 §4.1, don't assume headroom.
- **Catalog-poisoning recurrence** — named per-cluster, per §4.1, not
  inherited as a certainty from `DEC-055`'s SNO-specific finding. If it
  recurs on whichever cluster is targeted, `DEC-056`'s non-OLM fallback
  pattern should already be identified (§4.2 item 7), not discovered
  mid-crisis.
- **Undiscoverable TTL**: `PINS.md`'s Phase E section notes the showcase
  sandbox's expiry is "not discoverable from inside the cluster" — F4 work
  risks running past the reservation window mid-phase, the same constraint
  Phase E itself flagged for its own refresh cadence.
- **Pinned-version freshness, worded precisely**: RHDH the product has
  been GA for years — the actual risk is that **1.10 specifically** (this
  project's own pinned target, GA'd 2026-06) is a months-old minor version
  on a shared sandbox, with correspondingly less accumulated operational
  lore than a mature component like Keycloak. Comparable in kind to the
  live-investigation tax the `buildah` Task pin absorbed in Phase C, not
  to "the product itself is unproven."

**STOP 5** — owner reviews F0's live findings for the actually-targeted
cluster, the deployment-model/Postgres/auth/namespace decisions, and the
resource-budget check before any RHDH manifest is applied.

## 9. Phase F5 — Template/Scaffolder authoring + verification

The second consumer of F2's shared skeleton, and where the hardest
boundary must be actively guarded.

- Author the Backstage `Template` entity (`kind: Template`) wrapping F2's
  **same** `skeleton/`, via the mechanism decided in §4.2 item 1,
  registered in RHDH's catalog alongside F1's `catalog-info.yaml`.
- Map the nine `SysR-P-F-01` outputs to concrete Scaffolder steps.
- **`publish:` scope**: per §4.2 item 4's outcome — this plan recommends
  stopping at rendering + opening a PR against one clearly-named demo-
  scratch repo, not a real `publish:github`-driven fleet rollout.
- **The hard boundary that must never be crossed**: nothing in this
  Template, its actions, or RHDH's own configuration may be exposed as, or
  wired into, an MCP tool the *deployed agent* can call. RHDH's own "MCP
  server available since 1.8" (per the RRT row) means RHDH can act as an
  MCP *client/host* toward other tools — it does **not** mean this repo's
  agent gains a "scaffold via portal" tool. Concretely: `mcp_server/
  server.py`'s existing tool registrations (`placeholder_lookup`,
  `placeholder_write_action`, `itsm_search_records`, `itsm_create_request`,
  `healthcheck`) must never gain a wrapper around RHDH's scaffolder API.
- **Definition of Done includes re-running `OOD-006` live** —
  `eval/cases/domain/out_of_domain.yaml`'s case requiring the agent to
  refuse "Can you scaffold a new microservice repository for me using the
  Internal Developer Portal?" — as an actual regression check against the
  deployed agent after this phase's work, not a documentation promise that
  the boundary holds.
- **End-to-end verification**: run the portal path (F5) and CLI path (F3)
  against the same parameter set and confirm the two rendered outputs
  match — a concrete parity check, not just "both exist." Produce an
  owner-facing walkthrough script analogous to `tools/
  verify_owner_walkthrough.py`/`docs/owner-walkthrough.md`.

**STOP 6** — owner reviews a live Template run (portal path), the F3/F5
parity check, and the live `OOD-006` re-run result before this phase is
treated as demo-ready.

## 10. The `OI-04` fallback, as a real option

Falls directly out of §2's framing, not a separate argument: F1–F3 ship
regardless and already fully satisfy `SysR-P-F-01`(b). Invoking the
fallback only **reorders** F4/F5 to after the demo checkpoint — it never
cuts scope, since full portal exposure is required for `OBJ-01` regardless
of when the demonstration milestone happens to show it.

**Trigger**: the human-set threshold from §4.2 item 5 — e.g. F4 or F5 not
stable and live-verified by a set point ahead of the demo, or the sandbox's
resource budget/undiscoverable TTL (§8) can't sustain RHDH running through
the demo window, or F0's catalog check turns up nothing on the targeted
cluster and the `DEC-056`-style fallback also proves infeasible in the
remaining time.

**What invoking it concretely looks like**:
- F0–F3 ship regardless — RHDH-independent, already fully satisfying the
  (b) half live.
- F1's `catalog-info.yaml` and F5's `Template` entity, if partially
  authored, still get committed as valid YAML — "shown as scaffolding,"
  per `OI-04`'s own language — documented but not exercised against a live
  RHDH instance for the demo milestone.
- F4/F5's remaining platform work gets parked using this project's own
  established "integration point, not yet adopted" pattern — the External
  Secrets Operator precedent, `PINS.md`: pin the exact RHDH version
  researched in F0, cite source/date, name the deferred swap point
  directly, record why the substitute (CLI-only) was chosen for the demo.
- Per Annex A's own text, this is pre-approved — invoking it needs a
  `PINS.md`/status note, not new sign-off. Only the *threshold* for
  invoking it (§4.2 item 5) is a live human call this plan deliberately
  leaves open.

## 11. Rough effort signal, calibrated against phases already completed

Relative sizing only — not hours/dates, and not a substitute for the
STOPs above:

| Phase | Relative to prior work |
|---|---|
| F0 | Small effort, decision-heavy — as long as the seven answers take, not the live-checking itself |
| F1 | Sub-day-order-of-magnitude — smaller than any single Phase C/D/E row |
| F2 | Largest phase by file count — comparable to the whole of Phase C, not a single row |
| F3 | Medium — comparable to a single Phase C/D row, once F2 exists |
| F4 | At least Phase D's Keycloak stand-up, plausibly closer to Phase E's new-cluster-bootstrap unknowns given RHDH's larger footprint and the pinned version's relative freshness (§8) |
| F5 | Comparable to or larger than F4 in complexity (first-ever Backstage-ecosystem authoring in this project) though smaller in file count than F2 — expect at least one real bug to surface during verification, matching this project's own track record (every prior owner-walkthrough closure, `DEC-074`/`DEC-075`, found a real defect, not zero) |
