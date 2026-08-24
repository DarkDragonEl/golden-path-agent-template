# Session handoff

**This file was rewritten at Checkpoint D's formal closure**
(previously rewritten at Phase D's close, `DEC-073`; everything through
`DEC-077` had drifted out of it since). `DECISIONS.md` (currently
through `DEC-077`) is the authoritative, complete, chronological record
of every decision this project has made — this file is a *pickup*
summary, not a substitute for it. When in doubt, `DECISIONS.md` wins.

## Where this is

**Phase D is complete and Checkpoint D is formally closed.** D1
(approval service) → D2 (Keycloak/OIDC identity) → D3 (minimal approver
UI) → D4 (trace continuity) → Checkpoint D have all been executed,
live-verified against the real `golden-path-agent-demo-prod` deployment,
and — the last open piece — the owner personally completed the live
`GET /ui` browser click-through on 2026-08-23 (`DEC-077`): both the
`demo-approver` approve→ticket path and the `demo-user` read-only path
passed, `demo-prod` left clean. **No further Phase D work is open.**
Full evidence:

- `reports/phase-d-d1-verification.md` — D1's five named tests (approve/
  reject/expiry/pod-restart-survives-pending/live-concurrency-race).
- `reports/phase-d-d2-verification.md` — D2's five named tests (real
  approver login, forged/absent/wrong-role token handling, the agent's
  own workload token refused on the decision endpoint, MCP credential
  enforcement, the mechanical `AUTH_MODE=oidc` assertion demonstrated
  failing on a seeded regression).
- `reports/checkpoint-d-run.md` — the accepted plan's own Checkpoint D
  exit criterion, verbatim, all five parts: ask → cited answer, draft →
  approve → ticket exists, reject → nothing written, expiry → nothing
  written, and one full trace spanning the async approval gap
  (`tools/query_traces.py`), stitched by `session.id`/`proposal.id`.
- `reports/phase-d-owner-walkthrough-verification.md` — the
  owner-walkthrough closure prep: the `DEC-074` OIDC browser-discovery
  fix, the `DEC-075` port-forward bug found live and fixed, and the
  `DEC-076` real-browser (Playwright) drive of the approver UI that
  found and fixed a second real gap (no in-app logout) — all with full
  transcripts.
- `reports/browser-walkthrough-screenshots/` — 12 screenshots, one per
  step, from `DEC-076`'s real-browser run of the identical path the
  owner then also ran themselves.

**`DECISIONS.md` `DEC-053` through `DEC-077`** cover all of Phase D and
Checkpoint D's closure in full detail, including several real live
findings worth knowing before touching this cluster again:

- `DEC-055`/`DEC-056` — `rhbk-operator`'s OLM install is blocked
  cluster-wide by a *different tenant's* broken `CatalogSource`
  (`nousie-docling-catalog`) — not this project's bug, not fixed (not
  this project's resource). Keycloak is installed via the upstream
  project's own OLM-free kustomize path instead
  (`pipelines/bootstrap/keycloak-operator-upstream/`). `pipelines/bootstrap/keycloak-operator.yaml`
  (the original OLM `Subscription`) is kept committed as the migration
  target for whenever the shared catalog gets fixed by whoever
  administers it.
- `DEC-051`/`DEC-070` — two live cluster-networking/tooling quirks worth
  remembering together: `oc auth can-i --as=` gives a false negative
  specifically for `imagestreams/layers` (use `oc policy who-can`
  instead, it's authoritative); `oc get application` (no group) can
  silently resolve to the wrong CRD on this cluster (a generic
  `applications.app.k8s.io` also exists) — always use
  `oc get applications.argoproj.io` explicitly for ArgoCD.
- `DEC-065` — **`ConfigMap`-content-only changes do not roll already-
  running pods** in this project's `kustomize` setup (fixed-name
  `ConfigMap`s, `behavior: merge`, no hash-suffix generation) — a
  `Deployment` only restarts automatically on a *digest* change. Any
  manual `ConfigMap` edit against `demo-prod` (e.g. temporarily lowering
  `APPROVAL_TIMEOUT_SECONDS` for a live expiry test) needs an explicit
  `oc rollout restart` afterward — and do it fast: `demo-prod`'s own
  `selfHeal: true` will silently revert an out-of-band `ConfigMap` patch
  back to the committed value once ArgoCD's reconciliation catches up
  (confirmed live, twice, `DEC-073`). Named backlog item for Phase E: a
  `checksum/config`-annotation pattern would close this properly.
- `DEC-068` — the upstream `otel/opentelemetry-collector` image is fully
  distroless (no shell, no `tar` — `oc exec`/`oc cp` can't read anything
  out of it); a sidecar (this project's own image, `python3 -m
  http.server`) serves the trace file over HTTP instead. That sidecar's
  own `http.server` would not bind port `8888` on this cluster
  specifically (`Address already in use`, immediately, every time,
  `SO_REUSEADDR` made no difference) — routed around with an unrelated
  high port (`19999`, Service still exposes `8888` externally). Not
  root-caused further.
- `DEC-069` — a real, significant security gap: three approval-service
  endpoints (`create_proposal`, `list_pending_proposals`, `get_proposal`)
  had **no auth check at all** under `AUTH_MODE=oidc` until this was
  found and fixed — found while planning D3, not by any earlier
  verification pass. Worth remembering as a reminder to test the
  *absence* of a check on every route when a new `AUTH_MODE` gate goes
  in, not just the routes that were the original design's obvious focus.
- `DEC-074` — the browser-facing OIDC issuer is an internal cluster
  Service DNS name; a browser outside the cluster needs a third
  `oc port-forward` (Keycloak) **plus** a local hosts-file entry mapping
  that exact DNS name to `127.0.0.1` — documented in
  `docs/owner-walkthrough.md`, zero app/config changes.
  Redirect-URI on `golden-path-agent-approver-ui` is `["*"]` live,
  confirmed via the Admin API, not just the committed YAML.
- `DEC-075` — a real live bug the owner's own first attempt hit:
  `docs/phase-d-runbook.md` instructed forwarding approval-service to
  local port `18082`; `agent/static/approver_ui.html`'s own hardcoded
  default only looks at `localhost:8082`. The poll loop's own error
  handling treats a connection failure the same as a transient hiccup,
  so it hung silently forever with zero visible error. Fixed in the
  port-forward instructions (not the page). If touching this UI's
  port-forward docs again, keep the local port at `8082` unless
  `window.APPROVAL_SERVICE_ORIGIN` is also set to match.
- `DEC-076` — `approver_ui.html` has **no logout control**, and
  Keycloak's SSO session cookie means a second "Log in" click in the
  same browser silently re-authenticates as whoever's already signed in
  — the login form never renders. `docs/owner-walkthrough.md` now
  instructs a private/incognito window for the `demo-user` pass, not
  "log out." A real logout control is a named, not-yet-implemented
  Phase E hardening candidate (touches the image).
- `DEC-077` — Checkpoint D formally closed on the owner's own live
  browser click-through, 2026-08-23. See "Where this is" above.

## Next session's mission

**Owner review of `docs/phase-e-kickoff-plan.md` — plan-approved-then-
execute.** The plan is written, drafted for review, and holds its own
internal STOPs (owner authorizes the first showcase environment request,
reviews the refresh cadence, reviews the sharing schedule, reviews the
20-minute walkthrough script) — nothing in it has been executed, no
environment has been requested, no cluster has been touched. **Do not
begin any Phase E work — infrastructure, environment requests, or
otherwise — without the owner's own explicit authorization of that
plan first**, matching every prior phase's gate discipline. If the
owner's review changes the plan, update `docs/phase-e-kickoff-plan.md`
and get re-confirmation before executing anything in it.

## Invariants that must survive any future session

These are load-bearing design decisions, not implementation details —
do not silently drift from them while doing other work. (Numbering kept
stable from earlier phases; corrections noted inline where Phase D
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
   anything measured before the change. `DEC-049`'s own agent-side
   redesign (the `approval_action` split, the resume mechanism) touched
   graph *code* but deliberately no model-visible input — verified via
   one deterministic domain pass confirming the gate result was
   genuinely unmoved (`60/62`, same two tolerated cases), not a full
   re-baseline, per the owner's own approved instrument-rule statement
   for that specific case. Any future graph-code-only change should
   follow that same pattern: state explicitly why it's instrument-safe,
   then prove it with one pass, not assume it.
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
8. **New at Phase D — the identity/config discipline.** (a) Any new
   no-default env key in `agent/config.py` *or* `approval_service/config.py`
   must be declared on every deployment surface
   (`tools/check_config_contract.py` catches this automatically — run it
   after adding one, don't wait for CI). (b) `demo-prod`'s three security-
   downgrade switches (`AUTH_MODE`, `AGENT_OIDC_MODE`, `MCP_AUTH_MODE`)
   are mechanically asserted `oidc`, never `none`, by that same script —
   if a fourth one is ever added, add it to
   `DEMO_PROD_REQUIRED_VALUES` too. (c) `demo-prod` `ConfigMap` changes
   need an explicit `oc rollout restart` to actually reach already-
   running pods (invariant list item above, `DEC-065`) — a `Deployment`
   spec/digest change rolls automatically, a `ConfigMap`-only change does
   not.

## Pointers

- `DECISIONS.md` — the complete, authoritative decision history,
  `DEC-001` through `DEC-077`. Always read the tail before starting new
  work in a fresh session.
- `PINS.md` — every pinned component version, with the live-verification
  date and source. Phase D added the Keycloak/Postgres/OTel-Collector
  rows.
- `docs/phase-d-runbook.md` — the manual bootstrap steps for D2/D3
  (Keycloak operator/Postgres/Keycloak CR, port-forward procedure for
  `/ui` — corrected port at `DEC-075`).
- `docs/owner-walkthrough.md` — the closed-out owner click-through
  script: pre-flight verification summary, credential retrieval, the
  three port-forwards + hosts-file mapping (`DEC-074`), both parts
  (approver/read-only), now the reference doc for re-running this
  walkthrough in any future session, not just a one-time closure
  artifact.
- `docs/phase-e-kickoff-plan.md` — the next gate. Owner-review-only;
  nothing in it executes without explicit authorization.
- `pipelines/bootstrap/provision-identity-secrets.sh` — the committed,
  idempotent script that materializes all Keycloak-issued
  credentials (workload client secrets, demo user passwords) into K8s
  `Secret`s — re-run it any time those need rotating, or for a fresh
  environment.
- `tools/query_traces.py` — the scripted trace-query view (D4).
- `tools/verify_owner_walkthrough.py` — protocol-level (no browser)
  Authorization Code + PKCE verification of the approval flow.
- `tools/browser_verify_owner_walkthrough.py` — real headless-Chromium
  (Playwright) drive of the actual `/ui` page; re-run this first if the
  page, the Keycloak client, or the port-forward convention ever change
  — it would have caught both `DEC-075` and `DEC-076` immediately.
- `reports/phase-c-c1c-run.md`, `reports/phase-c-sharing-run.md` — Phase
  C's own evidence (pipeline gates, promotion, negative proofs).
- `reports/phase-d-d1-verification.md`, `reports/phase-d-d2-verification.md`,
  `reports/checkpoint-d-run.md` — Phase D's live evidence, described
  above.
- `reports/phase-d-owner-walkthrough-verification.md` — Checkpoint D
  closure prep, all three addenda (`DEC-074`/`DEC-075`/`DEC-076`).
- `reports/browser-walkthrough-screenshots/` — the 12 screenshots
  backing `DEC-076`'s real-browser run.
- `~/.claude/plans/read-claude-md-handoff-md-decisions-md-vast-hare.md` —
  the living Phase D design/plan document (D1–D4 architecture, updated
  at each major decision point through the whole phase).
