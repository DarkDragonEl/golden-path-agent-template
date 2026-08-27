# Session handoff

**Rewritten again, this time closing out Phase F in full** (F0 through
F5, on top of the OTel fix + F0–F3 the prior rewrite already covered).
`DECISIONS.md` (currently through `DEC-123`; `DEC-096` belongs to a
concurrent parallel-workspace thread, `feature/phase-e-live-chat-
verification`, not this one) is the authoritative, complete,
chronological record of every decision this project has made — this
file is a *pickup* summary, not a substitute for it. When in doubt,
`DECISIONS.md` wins. The Phase E content further below (bootstrap proof,
showcase promotion, sharing-moment artifacts) is unchanged since the
earlier rewrite and remains current — nothing in this session's work
touched it.

## Where this is — most recent session first

**Phase H (Documentation & DX hardening) complete** (`DECISIONS.md`
`DEC-114` through `DEC-128`), run concurrently with G6 below — file
ownership stayed partitioned throughout, confirmed no real conflict.
Two coordinating sessions independently ran H1/H2/H3a at one point
(`DEC-115`/`116`/`117` document which one's content actually landed);
reconciled without redoing completed work. Summary of what shipped:
`README.md` full rewrite, `docs/` reorganized into a Diátaxis hub (16 →
20+ pages, 14 new per-directory `README.md`s), 13 Python modules gained
docstrings, 37 code-comment findings migrated into `DECISIONS.md`
(`DEC-040` reconstructed, `DEC-119` corrected a real misattributed
incident), live TechDocs wired into RHDH and owner-verified in a real
browser (`DEC-124`; one real bug — a `raw.githubusercontent.com`/
`github.com` reader host-mismatch — caught only by that browser check,
`DEC-122`, with a repo-wide sweep finding and pre-emptively fixing three
more dormant instances), and every category-(b)/(c) comment across all
7 census directories slimmed to a `DEC-NNN` pointer (`DEC-126`–`128`).
`docs/code-comment-policy.md` documents the policy for future sessions.
Full ledger: `DECISIONS.md` `DEC-114`–`DEC-128`. This paragraph is added
without altering anything below it — the G6 narrative that follows is
that coordinating session's own and is left as-is.

**Phase F4–F5 complete** (`DECISIONS.md` `DEC-092`–`DEC-095`,
amended by `DEC-097`;
`reports/phase-f-f4-verification.md` and `reports/phase-f-f5-
verification.md` carry the full command-level evidence): RHDH is live
on the showcase cluster, synced via ArgoCD, with a real Scaffolder
Template wired to F2/F3's own `skeleton/`.

- **F4** (RHDH platform stand-up, `DEC-092`–`DEC-094`): operator
  (`rhdh-operator.v1.10.3`), external Postgres, and a new OIDC client in
  the existing `golden-path-agent-keycloak` realm are all live. STOP 5's
  bar ("the owner could open the portal URL and log in") took **three
  rounds of claiming it was met and then finding a real gap only a
  literal browser navigation surfaced** — the single sharpest recurring
  lesson of this phase: a scripted backend API call and a real browser
  navigation are not interchangeable evidence. In order: (1) `scope` →
  `additionalScopes`, missing `baseUrl`/`session.secret` — found by the
  backend crash-looping; (2) `backend.reading.allow` for the catalog's
  own `UrlReader` guard, unrelated to network reachability — found by
  F1's `catalog-info.yaml` 404ing despite everything else checking out;
  (3), *after* the first "STOP 5 cleared" claim (`DEC-093`), opening the
  actual URL in Chrome surfaced two more: an HTTP-only Ingress that
  modern browsers' HTTPS-first default can't reach at all (fixed by
  switching to a native `Route` inheriting the cluster's own trusted
  wildcard cert, since OpenShift's Ingress-to-Route translation — unlike
  a native Route — requires an explicit Secret and won't fall back to
  the router default), and a sign-in page silently defaulting to RHDH's
  bundled example GitHub provider because `signInPage` was nested under
  `auth:` instead of being a top-level key (`DEC-094`). Every fix
  landed in the committed manifest before taking effect, after the very
  first one was live-patched and silently reverted by ArgoCD's own
  `selfHeal: true` within about a minute — documented in `PINS.md` as
  the phase's other standing lesson.
- **F5** (Template/Scaffolder authoring, `DEC-095`): `template.yaml`
  wraps `skeleton/` via the stock `fetch:template` action — zero custom
  plugin code, per `DEC-087` item 1, no `publish:*` step (this
  instance's own live action list has none registered at all, enforcing
  the local-render-only scope at the platform level). Three more real
  gaps, all found only by actually running the Template (schema-valid
  YAML and a clean `--dry-run` caught none of them): `fs:readdir`'s real
  input key is `paths` (array), not `path`; `fetch:template`'s relative
  URL resolution needs `integrations.github`, distinct from
  `backend.reading.allow`; and `GithubUrlReader`'s host match is a
  literal string equality (confirmed by reading Backstage's own source),
  never matching `raw.githubusercontent.com` against `host: github.com`
  — fixed by registering the Template via the `github.com/blob/main/...`
  URL form instead (F1's own `catalog-info.yaml` location is unaffected).
  STOP 6's four DoD items are all met with execution evidence: a
  completed live Template run (241 files), F3/F5 file-set parity
  (241/241 identical, with an honestly-stated limit — this platform has
  no way to pull rendered file *content* back out of a completed task,
  so this is file-set parity, not byte-level content parity), a live
  `OOD-006` re-run against the real deployed agent (still `tool_calls:
  []`, still refuses), and the MCP boundary confirmed unchanged at
  exactly 5 tool registrations on both source and the live pod.
- **`DEC-097` (amendment to `DEC-093`/`DEC-095`): the owner's own real
  external browser found a deeper login gap immediately after STOP 6 was
  first declared cleared.** Every login test in F4/F5 up to that point,
  including the ones cited as proof, ran via `oc exec` *inside* the
  cluster — structurally blind to whether a real external browser can
  even reach the redirect target. It couldn't: RHDH's OIDC popup
  redirected to Keycloak's internal-cluster-only Service DNS,
  `ERR_CONNECTION_REFUSED`. Two more bugs chained off fixing that
  (Keycloak reporting `http://` endpoints behind an edge-terminated
  Route until `spec.proxy.headers: xforwarded` was set; then RHDH's own
  stale discovery-document cache needing one more restart) — full chain
  in `DEC-097`/`PINS.md`. Fix: a native `Route` exposing Keycloak
  externally (same pattern as RHDH's own Route, `DEC-094`) — a
  deliberate departure from this project's existing hosts-file +
  port-forward workaround for this exact class of problem
  (approver-ui's own `DEC-074`), since RHDH is the first genuinely
  owner-facing entry point here, not an internal testing tool. Once
  fixed, the owner completed a real login and then drove the
  Create-page wizard's actual click-through themselves (project-identity
  form fields only, never a credential) — **closing the wizard
  click-through gap the initial STOP 6 report had honestly left open**.
- **What's genuinely still open, named rather than assumed closed**:
  (1) `OBJ-01`'s full portal exposure (this stand-up proves the platform
  is live and reachable; broader owner/team-facing rollout is a separate
  later decision) — same item `DEC-091` already named; (2) `SysR-P-F-13`
  /`OS-09`'s second-team acceptance — this project still cannot
  self-certify that.
- **`DEC-098` (Phase G, step G0 — decision record + requirement amendment,
  documentation only, nothing built).** The agent-project template is
  decomposed into three named components — a Platform Foundation (shared
  identity, telemetry, approval service, Git hosting, model routes, GitOps
  machinery, RHDH itself), a Tools Template (independent MCP-server
  artifact), and a slimmed Agent Template — owner-confirmed this session:
  three images (agent/MCP/approval, not one), two repositories per
  scaffolded project (source+pipeline, and a separate GitOps repo,
  matching the verified `redhat-ai-dev/ai-lab-template` pattern), and
  in-cluster Gitea (`rhpds/gitea-operator`, pinned `v2.3.2`) as Git
  provider. `SysR-P-F-01` amended (`SyRS-AGP-001_EN.md` v0.2) to add a
  separate tools-template output and a no-bundling clause for both the
  tool server and the approval service; new `SRS-APR-QUAL-02` requirement
  (`srs/SRS-APR.md` v0.3) extends fail-closed behavior to the shared
  approval service's now-remote consumers. RRT rows 24/25 pin Gitea and
  `redhat-ai-dev/ai-rhdh-installer`. The `OI-04` fallback trigger stays
  unarmed — still no demo date, reconfirmed this session, per `DEC-092`.
  Next: G1 (stand up Gitea, extract the Platform Foundation) — a separate
  phase, its own STOP, not started here.
- **`DEC-099` (Phase G restructured into four stages; Stage 1 — G1's
  Gitea stand-up + G2's three-image split — authorized as two parallel
  worktree streams).** G1-G7 collapse into four dependency-driven stages
  (see `DEC-099`'s stage table) without waiving any phase's own DoD or
  STOP. Worktree isolation for the two Stage-1 streams; this coordinating
  session remains the sole owner of `DECISIONS.md`/`HANDOFF.md`/`PINS.md`
  throughout — each stream drafts its own DEC entry in its report, landed
  here at merge. G1's ArgoCD-repoint/approval-extraction tail is held
  until G2's STOP clears and the bad-change gate re-passes; G2's DoD
  keeps the `DEC-096`-inherited `MCP_MODE=live` validation requirement.
  Stage 2 (G1's held tail + G3/G4/G5) is pre-authorized to start the
  moment Stage 1's dependency chain clears — no separate go needed.
- **`DEC-100` (G1/Stage-1, substantially complete).** Gitea stood up via
  `rhpds/gitea-operator`'s own `config/default` kustomize path (its OLM
  `Subscription` never resolved — a stuck cluster-wide resolver cache,
  `DEC-055`/`DEC-056`-class, not fixed unilaterally); org, non-admin
  machine account, and scoped token proven live to actual destruction;
  blueprint mirrored; backup/restore proven against real data; identity/
  telemetry/RHDH manifests relocated to `platform/bootstrap/`. One item
  open at merge time: RHDH loading the Scaffolder template from Gitea,
  blocked by ArgoCD `selfHeal` reverting live-patch attempts faster than
  a manual test cycle could outrun — resolved after this entry landed (a
  real, first-class Backstage `GiteaIntegration` exists in core, not the
  GitHub-mimicking workaround first tried); see the merge/push history
  around `858e961` for the actual fix, folded into G1's live-verification
  work rather than its own separate DEC entry. **Superseded by `DEC-103`**
  — see below; G1's Gitea-load blocker and held tail both fully closed
  since this entry landed.
- **`DEC-101` (G2/Stage-1, STOP 4 closed).** Monolithic image split into
  three independently-built, independently-promoted artifacts (agent/
  mcp/approval); four real live-only bugs found and fixed (a digest-
  bootstrap chicken-and-egg, two rounds of a NetworkPolicy label bug, an
  approval-Deployment RWO-PVC/`RollingUpdate` deadlock); demo-prod
  redeployed and verified on the three fresh digests; the seeded
  bad-change gate re-verified twice, empirically. **Also records a
  governance incident**: the G2 worktree opened and merged three PRs
  directly to `main` without authorization before the coordinating
  session caught and reconciled it (no conflicts, nothing lost) and
  drew a firm boundary for the remainder of Stage 1 — see `DEC-101` for
  the full account, disclosed there in full rather than edited out. Per
  `DEC-099`'s merge-order rule, G1's held tail is now unblocked —
  Stage 2 begins next.
- **`DEC-102` (G5/Stage-2, catalog model designed locally).** Three new
  files under `platform/catalog/`: a `System` for the Platform
  Foundation; the approval service as a `Component`+`API` sourced from
  the real `SRS-APR` contract and cross-checked against
  `approval_service/api.py`'s actual routes; model routes as a shared
  `API` plus primary/fallback `Resource`s sourced from
  `agent/model_client.py`'s real reason-code set (which differs from
  `SRS-AGT-IF-02`'s own illustrative example list — noted). Deliberately
  not yet registered live in RHDH — deferred to a coordinated edit once
  G1's tail and G3+G4 both report their own catalog-relevant output, to
  avoid three Stage-2 streams racing the same shared config file.
- **`DEC-103` (G1/Stage-1, fully complete, supersedes `DEC-100`).** Both
  of `DEC-100`'s open items closed with real, live, end-to-end evidence:
  (1) RHDH genuinely reads content from Gitea via Backstage's real core
  `GiteaIntegration` (not the earlier GitHub-mimicking guess) — proven at
  the catalog level, with an honestly-scoped limitation that
  task-level `fetch:template` still resolves against GitHub due to
  Backstage's own entity-merging behavior when both sources are
  byte-identical (named as a future item, not a remaining defect); (2)
  the approval service is fully extracted to its own Platform Foundation
  namespace and **actually cut over** — old `demo-prod` approval
  resources genuinely pruned, a real write query through the live agent
  reached the new shared service, was approved by a real `demo-approver`
  identity, and executed (`REQ-30100`), nothing simulated or isolated.
  Stage 1 is now fully done; Stage 2 (G3/G4/G5) is already running in
  parallel per pre-authorization.
- **`DEC-104`/`DEC-105`/`DEC-108`/`DEC-109` (G3+G4/Stage-2, Tools
  Template + slimmed Agent Template, complete).** A new Tools Template
  (`skeleton-tools/`) produces a standalone MCP server; the existing
  Agent Template (`skeleton/`) is re-cut to remove `mcp_server`'s server
  implementation and `approval_service` entirely, consuming both over
  the network only (six real bugs found and fixed live; both templates
  render, test, build, and run as real containers). This surfaced a real
  architectural gap — domain eval's fault-injection monkey-patched
  `mcp_server.itsm_store` in-process, incompatible with a genuinely
  separate MCP server — escalated to the owner per `CLAUDE.md`'s "STOP
  and ask" rule rather than decided unilaterally. Owner's ruling
  (`DEC-105`): decouple domain eval into an in-process, eval-only
  fixture (never adding a fault-injection surface to the real,
  templated MCP server, since that would ship in every future scaffolded
  project guarded only by an env flag — incoherent for a
  structurally-gated-writes platform); network-fault fidelity becomes the
  integration suite's job instead. Implemented and verified live
  (`DEC-108`): 95/95 rendered tests, `eval-domain` 60/62 matching G2's
  pre-split baseline exactly. The required network-fault complement
  (`kill-mcp-connectivity-check`) verified via a real agent `PipelineRun`
  (`DEC-109`) — a genuine DNS-resolution failure, graceful escalation in
  3.7s, correct `fallback_reason` attribution.
- **`DEC-102`/`DEC-106`/`DEC-107` (G5/Stage-2, catalog model, complete).**
  G5's three locally-designed catalog files registered live in RHDH
  (three new `catalog.locations` entries) and confirmed fully resolved
  against the live catalog database — all six entities present, 18
  relation rows, zero dangling references. Deliberately did not register
  `skeleton/catalog-info.yaml`/`skeleton-tools/catalog-info.yaml`
  (template output, unresolved placeholders) — that's G6's job once a
  real instance is scaffolded.

**Stage 2 (G3/G4/G5) is now fully complete.** Per `DEC-099`'s stage
table, G6 (publish + automatic onboarding) is next.

**G6 (publish + automatic onboarding) is now complete on both required
paths** (`DECISIONS.md` `DEC-110`–`DEC-113`, `DEC-118`, `DEC-123`).
A feasibility check found the original draft's assumption — that Gitea
Scaffolder support was a stock RHDH dynamic plugin — was false for this
RHDH version; two paths were pursued in parallel:
- **Path B (CLI-first, `SysR-P-F-01`(b))**: `tools/gitea_publish.py`
  publishes two real repos (source+pipeline, and a separate `-gitops`
  repo) to the Platform Foundation's Gitea instance, live-verified for
  both templates, including a full pass making the rendered GitOps/
  promotion-PR content genuinely Gitea-aware (`DEC-111`/`DEC-112`) —
  it had been silently hardcoded to GitHub since before Gitea existed.
- **Path A (portal wizard, `SysR-P-F-01`(a))**: a real Gitea Scaffolder
  dynamic plugin was built from upstream Backstage core using RHDH's own
  first-party `rhdh-dynamic-plugin-factory` tool (the same mechanism
  RHDH's own maintainers used for the bundled GitHub/GitLab modules),
  wired into the live `Backstage` CR, and proven end-to-end — a real
  Scaffolder task, through RHDH's actual authenticated API, creates two
  real Gitea repos with real content and registers a real catalog entry
  (`DEC-118` spiked it live-patched; `DEC-123` committed the same wiring
  to Git and re-verified against the committed state, resolving one more
  real bug along the way — `catalog:register`'s `catalogInfoPath` must
  not carry a leading slash against a bare Gitea URL). **`STOP 8`** (the
  original design's own "owner runs the real browser wizard" moment) is
  restored — CLI-first is not superseded, both paths are normatively
  required in parallel per `SysR-P-F-01`.
- Landing this touched the same `deploy/kustomize/overlays/rhdh/`
  files a concurrent Phase H (TechDocs) stream was also touching —
  reconciled cleanly via a real three-way merge (one list-append
  conflict in `kustomization.yaml`, resolved by keeping both entries;
  verified via a full render, not just the absence of conflict markers).
- Per `DEC-099`'s stage table, G7 (multi-team demonstration) is next.

**Open items, deferred (owner-reviewed, low priority, no dedicated work
until named):**
- Branch protection on `main` — deferred to G7's scope, where "platform
  ready for a second team" makes it part of that phase's own deliverable.
- `PINS.md`/RRT row 24 describe Gitea's OLM install path; it actually
  landed via non-OLM `config/default` kustomize (`DEC-100`) — correction
  folded into the end-of-phase docs-reconciliation batch, not dedicated
  work.

**OTel collector fix + Phase F0–F3** (prior session, still current —
detail below unchanged):

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

- `reports/docs-audit.md`, `reports/docs-terms-sheet.md` — Phase H0's
  audit and binding glossary for the documentation-hardening workstream
  (`DEC-114` onward). Read these before touching `README.md`, `docs/`,
  or adding Python docstrings.
- `DECISIONS.md` — the complete, authoritative decision history,
  `DEC-001` through `DEC-123`. Always read the tail before starting new
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
