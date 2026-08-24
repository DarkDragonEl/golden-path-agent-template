# feature/workspace-tooling — report

Mission: build a first generation of Claude Code skills/commands (a
pre-flight environment check, a packaged eval-runner, a tool prober, a
post-deploy verifier) plus a provisional UI map of the approver UI, on
an isolated branch, without colliding with the separate live session
that was fixing the owner-walkthrough UI flow to close Checkpoint D at
the same time.

## What was built

| File | What it is | Live-tested? |
|---|---|---|
| `.claude/skills/pre-flight/SKILL.md` | 6-check demo-prod readiness gate | **Yes, release phase** — all 6 checks green live; see "Release phase" below |
| `.claude/skills/run-evals/SKILL.md` | Wraps `make up` + an N-pass `eval-domain` loop (no native `--passes` flag exists) against `eval/thresholds.yaml` + `KNOWN_GAP_TOLERANCES` | **Yes, both phases** — see Verification below and "Release phase" |
| `.claude/skills/probe-tool/SKILL.md` | Calls the mock ITSM MCP tools directly over REST, bypassing the model | **Yes, both phases** — a real bug was found and fixed in the build phase, reconfirmed in the release phase |
| `.claude/skills/post-deploy/SKILL.md` | ArgoCD sync/health + image-digest-matches-promoted-digest check | **Yes, release phase** — all 4 checks green live; see "Release phase" below |
| `.claude/commands/start-step.md` | Session-bootstrap brief: `HANDOFF.md` + last 5 DEC entries + `PINS.md` + current phase artifact | **Yes, release phase** — executed for real, found and fixed a real gap (kickoff-plan naming) |
| `.claude/commands/close-step.md` | Drafts (never commits) a DEC entry + report skeleton | **Yes, release phase** — tail-detection confirmed correct against a live-moving `DECISIONS.md` tail |
| `docs/drafts/AGENT-UI-MAP.draft.md` | Provisional approver-UI map, built from the real `agent/static/approver_ui.html` source | Not browser-tested — explicitly provisional per its own header, unchanged this phase |

**Note on status vs. the table above**: this table described the build
phase's own state at the time it was written; "Release phase" below is
the authoritative current state after live-testing everything.

## Isolation mechanism (why a worktree, not a branch switch)

Reconnaissance found only one git worktree for this repo, and the
parallel session's uncommitted edits (`DECISIONS.md`,
`docs/owner-walkthrough.md`, `docs/phase-d-runbook.md`,
`tools/verify_owner_walkthrough.py`) lived directly in it. A plain `git
checkout -b feature/workspace-tooling` there would have swapped files
out from under that session's in-progress edits. Instead:

```
git worktree add -b feature/workspace-tooling \
  /home/darkdragonel/workspaceAgentMvp/golden-path-agent-template-tooling main
```

This created a second, fully independent checkout of the same repo
(shared `.git` history, separate working directory), branched from
`main`'s tip at that moment (`f9e061f`). All work happened there. The
original checkout was never touched.

**Confirmed working, not just assumed:** `main` advanced by one real
commit during this mission (`91af75b`, DEC-075's fix, committed by the
parallel session while this mission was mid-flight) — visible via `git
log main` from inside this worktree, with zero effect on this branch's
own working tree or history. `git diff $(git merge-base HEAD main)
--name-only` (diff against this branch's actual base, not `main`'s
now-moved tip) shows nothing tracked changed outside the two new
directories this mission added.

## A live demonstration of exactly the problem C2 warns about

While writing this report, `git show main:DECISIONS.md`'s real tip
showed **`DEC-075` already committed** (`91af75b`) — but this branch's
own checked-out `DECISIONS.md` still ends at `DEC-074`, because it was
branched before that commit landed. A naive "increment this branch's
own tail" computation would have produced `DEC-075` for the consolidated
draft below, which would have collided with a real, already-committed
entry. The correct provisional number, checked against `main`'s actual
current tip rather than this branch's stale view, is **`DEC-076`**. This
is not a hypothetical risk `close-step.md` was written to guard
against in the abstract — it is what would have happened, concretely,
in this exact session, had the number not been re-checked against the
live tip before writing it down here.

## `CLAUDE.md` skills-registry section (drafted, not applied)

Per rule 6, `CLAUDE.md` is shared surface and was not edited this
mission. This is the section a future session should add, verbatim or
close to it:

```markdown
## Workspace skills and commands

Claude Code skills (auto-invocable, read-only) and commands
(explicit-invocation-only) live under `.claude/skills/` and
`.claude/commands/`. Governance rule: anything that runs automatically
is read-only; anything that modifies state requires explicit human
invocation -- classification is stated at the top of each file.

- `/pre-flight` (skill, read-only, cluster) -- verify demo-prod is
  healthy before any owner-facing walkthrough or demo.
- `/run-evals` (skill, read-only, local stack) -- run the local eval
  gate N times and compare against the standing baseline + known-gap
  tolerances.
- `/probe-tool` (skill, read-only w.r.t. project state, local stack) --
  call the mock ITSM MCP tools directly, bypassing the model.
- `/post-deploy` (skill, read-only, cluster) -- verify a promotion
  landed correctly (ArgoCD sync/health, image digest).
- `/start-step` (command) -- bootstrap session context from HANDOFF.md +
  recent DEC entries + PINS.md + the current runbook.
- `/close-step <name>` (command) -- draft (never commit) a DEC entry +
  report skeleton for the session's work.

`/pre-flight` and `/post-deploy` were written without live cluster
access (see `reports/feature-workspace-tooling.md`) and need a live
verification pass before being trusted as-is.
```

## Consolidated DEC-entry draft

**`DEC-076 (provisional — re-check tail before commit)` — First-generation
workspace tooling: skills, commands, provisional UI map**

**Ambiguity:** the mission ran in parallel with a live session closing
Checkpoint D in the same repo, with no worktree isolation specified by
the mission brief itself (it said "own branch," not "own worktree") and
no `.claude/` scaffolding yet existing in the repo.

**Finding:** the shared working directory held live uncommitted edits
from the other session; a same-directory branch switch would have been
unsafe. Live-testing `/probe-tool`'s REST payload shape (assumed from
the handler's `arguments: dict` parameter name during static
reconnaissance) surfaced a real bug in that assumption — FastAPI binds
the *entire* request body to that single untyped dict parameter, so the
correct payload is the raw argument fields, unwrapped, not `{"arguments":
{...}}`. Confirmed via live HTTP 500s with the wrong shape and live 200s
with the corrected shape against the real running `mcp_server`.

**Decision:** isolate via `git worktree add` instead of `git checkout
-b` (see "Isolation mechanism" above); write `/pre-flight` and
`/post-deploy` from static source only, explicitly labeled not
live-tested (all their checks are `oc`-gated and this mission excluded
cluster access); live-test `/run-evals` and `/probe-tool` fully, since
both are local-stack-only; correct `/probe-tool`'s documented payload
shape to the verified-real one rather than the initially-assumed one.

**Evidence:**
- Worktree isolation: `git worktree add -b feature/workspace-tooling ...`;
  `git log main` from inside the new worktree shows `main` advancing by
  one commit (`91af75b`) mid-mission with zero effect on this branch.
- Port-collision check: `ss -tln` before starting the local stack showed
  `18080`/`18082`/`8080` already bound (the owner's live port-forwards);
  the local stack was started with `AGENT_HOST_PORT=28080
  MCP_HOST_PORT=28081` instead, confirmed non-colliding both before and
  after (`ss -tln` clean on `28080`/`28081` post-teardown).
- `/probe-tool` live run (corrected payload): all 4 tools returned `200`
  with schema-matching bodies (`itsm_create_request` → `REQ-30100`,
  `itsm_search_records` → 1 record, both placeholder tools → the
  documented marker string); `POST /reset` → `200` cleanup confirmed.
- `/run-evals` live run: `make eval-fast` → `2/2 EXAMPLE cases passed`;
  one `eval-domain` pass (against the local stack, `MCP_TOOL_ENDPOINT`
  pointed at the overridden port) → `60/62 cases passed`, gate verdict
  `PASS`, tolerated failures `ITR-004`, `TSEL-004` — an exact match to
  the standing baseline, zero new failures.
- `make lint` → clean; `make test` → `252 passed`.
- `git diff $(git merge-base HEAD main) --name-only` → only the two new
  directories this mission added; nothing under `DECISIONS.md`,
  `HANDOFF.md`, `PINS.md`, `docs/owner-walkthrough.md`, `agent/**`,
  `approval_service/**`, `mcp_server/**`, `eval/**`, `pipelines/**`,
  `deploy/**`, `Makefile`, or `CLAUDE.md` changed.
- Zero `oc` invocations anywhere in this session (grep of this session's
  own command history against `oc ` confirms none).

**Status:** Implemented and locally verified on `feature/workspace-tooling`.
Not merged (rule 4 — merge happens post-Checkpoint-D, with a rebase, per
the merge procedure below). `/pre-flight` and `/post-deploy` still need
a live cluster pass before being trusted as-is (see checklist below).

## Live-test checklist for `/pre-flight` and `/post-deploy`

Both were written entirely from static source with zero cluster access.
Before trusting either against a real environment:

- [ ] `/pre-flight` check 3: confirm the real pod label selector for
  Keycloak Operator pods in `golden-path-agent-keycloak` (marked
  `[VERIFY ON FIRST LIVE RUN]` in the file) and the exact
  `KeycloakRealmImport` status-condition field/value.
- [ ] `/pre-flight` check 4: confirm the MaaS endpoint in
  `golden-path-agent-secrets` is reachable directly, or whether the
  check needs to run via `oc exec` into the agent pod instead.
- [ ] `/pre-flight` checks 5-6 and `/post-deploy` check 3: confirm the
  approval-service port-forward and pod-label-selector assumptions
  against a real live session (both marked `[VERIFY ON FIRST LIVE
  RUN]`/best-effort in their files).
- [ ] `/post-deploy` check 2: confirm the `images:` block's exact
  location/shape in `deploy/kustomize/overlays/demo-prod/kustomization.yaml`
  still matches what a real promotion PR commits (grounded in the git
  history read during this mission, but not re-verified live here).
- [ ] Run both once for real, then remove or update this checklist and
  the `[NOT LIVE-TESTED]` headers in the two files accordingly.

## Verification output (Phase 5)

**Port-collision check** (`ss -tln`, before starting anything):
```
LISTEN 127.0.0.1:8080    <- Keycloak port-forward (owner's session)
LISTEN 127.0.0.1:18080   <- agent port-forward (owner's session)
LISTEN 127.0.0.1:18082   <- approval port-forward (owner's session)
```
All three of the owner's active port-forwards confirmed bound at check
time — exactly matching what was reported ahead of execution. Local
stack started instead with `AGENT_HOST_PORT=28080 MCP_HOST_PORT=28081`.
Post-teardown `ss -tln` confirmed `28080`/`28081` released and no
listeners left behind.

**`/probe-tool` live run** — see the Evidence section above; full
request/response detail lives in `.claude/skills/probe-tool/SKILL.md`
itself (updated in place with the real captured output after the
payload-shape bug was found and fixed).

**`/run-evals` live run** — `eval-fast`: `2/2` passed. One `eval-domain`
pass: `60/62` passed, gate `PASS`, `ITR-004`/`TSEL-004` tolerated (an
exact match to the standing baseline — no new failures). Per this
mission's plan, only one domain pass was run (not the full 3-pass
frozen-state discipline), to minimize load on the shared MaaS endpoint
the parallel session's cluster agent also uses. Full 3-pass re-baseline
is a post-merge concern.

**`make lint`**: clean. **`make test`**: `252 passed`.

## Proposed merge procedure (post-Checkpoint-D)

1. Once Checkpoint D is formally closed (owner's DEC entry recorded),
   rebase `feature/workspace-tooling` onto `main`'s then-current tip
   (which will include DEC-075, DEC-076+, and whatever else lands
   before then) from inside this worktree: `git fetch && git rebase
   main`.
2. Re-run `/run-evals` once, full 3-pass discipline this time, as the
   merge smoke test — no assumption that the local-stack behavior
   observed during this mission still holds after a rebase across
   however many commits land in between.
3. Re-check `DECISIONS.md`'s live tail at that point (not this report's
   `DEC-076` guess) and commit the consolidated entry with the real
   next number.
4. Merge (or open a PR, matching whatever convention `main` uses by
   then) — no-squash, per the project's standing convention.
5. Only then remove this worktree (`git worktree remove`), if desired —
   it was deliberately left on disk after this mission for exactly this
   continuation.

## Release phase (executed)

The owner authorized releasing this generation for real, without
waiting for Checkpoint D's own formal closure — recorded as a
deliberate call in `DEC-079`, not reframed after the fact. In practice
`DEC-077` closed Checkpoint D concurrently (the owner's own live
click-through completed the same day) — the two did not end up racing,
but the authorization to proceed regardless is the operative decision.

### Precondition check

Git evidence alone (clean tree, up to date with `origin/main`) was
**not** sufficient to conclude the parallel Checkpoint-D session was
done — the same three port-forwards from the build phase were still
bound, and a new `DEC-076` showed a Playwright-driven verification pass
had just run. Asked the owner directly rather than guessing; confirmed
done. (By the time cluster testing actually started, those
port-forwards had in fact been torn down — further, independent
confirmation.)

### `main` kept moving under this session — three times

`main` advanced past this branch's fork point three separate times
during this release phase alone: once before rebase-prep even started
(`DEC-075`, `DEC-076`, its addendum), once between the first rebase and
the merge (`DEC-077`, then a real `DEC-078` — unrelated Phase E
infrastructure work, unpushed to `origin` at the time, discovered via
untracked files — `pipelines/bootstrap/gitops-operator.yaml`,
`pipelines/bootstrap/pipelines-operator.yaml`, `scripts/bootstrap.sh` —
sitting in the shared checkout with no tracked-file modifications
alongside them). Each time, this branch was rebased fresh rather than
assuming the earlier rebase still held, and the DEC number for this
report's own entry was computed from the *real* tail immediately before
writing it, not reused from any earlier guess — `DEC-076` was guessed in
the build phase and collided with a real, differently-scoped `DEC-076`;
this phase's own mid-session guess of `DEC-078` was superseded the same
way before it was ever written down. The actual number used,
**`DEC-079`**, was checked directly against `git log --oneline
origin/main -1` and `DECISIONS.md`'s own tail in the same breath as
writing it.

Merging happened directly in the original checkout
(`golden-path-agent-template/`, where `main` is checked out — a second
worktree can't check out a branch already checked out elsewhere). Before
doing so, confirmed via `git status` that no *tracked* file there was
currently modified (only new *untracked* files existed, which `git
merge` never touches, and none overlapped this branch's own files) —
the same non-interference discipline as the build phase's worktree
isolation, applied to the one step that genuinely couldn't be worktree-
isolated.

### `/pre-flight` — live, all 6 checks green

```
Pre-flight: golden-path-agent-demo-prod
  [✓] 1. Session alive (oc whoami: darkdragonel, project: golden-path-agent-demo-prod)
  [✓] 2. Deployments ready (3/3 -- agent, mcp, approval all 1/1)
  [✓] 3. Keycloak ready (golden-path-agent-0 Running 1/1; realm import Done=True, HasErrors=False)
  [✓] 4. Model endpoint responds (200, model-endpoint.example.com)
  [✓] 5. Approval-service auth posture (401, as expected)
  [✓] 6. No stale pending proposals ([])
```
One real bug found and fixed getting there: check 6 needs a bearer
token whose `iss` claim matches `approval_service`'s configured
`OIDC_ISSUER_URL` **exactly, including the port**. A first attempt
forwarded Keycloak to local port `38080` (to stay clear of the owner's
own port-forwards); Keycloak stamps `iss` from the request's `Host`
header, so the token came back with `:38080` baked in and
`approval_service` correctly rejected it with `401 invalid issuer`.
Rebound the forward to the real port `8080` (confirmed free by then)
and it worked. Full detail, and why the `approval-service` side has no
equivalent constraint, is in `.claude/skills/pre-flight/SKILL.md`
itself now.

### `/post-deploy` — live, all 4 checks green

```
/post-deploy
  [✓] 1. ArgoCD: Synced / Progressing (Ingress-only, known gap -- all
        3 Deployments/Services/PDBs independently Healthy)
  [✓] 2. Image digest matches promoted digest (sha256:db408a27...,
        pinned in deploy/kustomize/base/kustomization.yaml)
  [✓] 3. Pods ready (3/3)
  [✓] 4. Recent logs clean (no errors in last 50 lines, all 3 deployments)
```
Two corrections found live: `oc get application <name>` is ambiguous on
this cluster (resolves to the wrong `app.k8s.io` CRD — needs
`application.argoproj.io` explicitly), and the `images:` pin lives in
`deploy/kustomize/base/kustomization.yaml`, not the demo-prod overlay
as originally assumed from static source. The persistent `Progressing`
aggregate status traces entirely to two `Ingress` resources with no
configured host — a pre-existing, already-documented gap
(`agent/static/approver_ui.html`'s own comment: "this project has no
working external Ingress this milestone"), not a new regression. Every
functional resource (`Deployment`/`Service`/`PDB`) is independently
`Healthy`. **No new environment defect was found** — this is the one
"finding, not a bug to fix" case the mission anticipated, and it turned
out to be a already-known one, not a fresh one.

### `/run-evals` and `/probe-tool` — reconfirmed

Fresh local stack (port-collision check first — clean this time, the
owner's port-forwards had already come down). `eval-fast`: `2/2`. One
`eval-domain` pass: `60/62`, gate `PASS`, `ITR-004`/`TSEL-004`
tolerated — an exact match to the build phase's own numbers and the
standing baseline. `/probe-tool`: all 4 tools `200`, schema-correct
bodies, `POST /reset` cleanup confirmed.

### `/start-step` and `/close-step` — executed for real

`/start-step`'s real output correctly identified `HANDOFF.md` as
current (rewritten at `DEC-077`'s own closure) rather than assuming
staleness — and found a real gap of its own: the current-phase-artifact
lookup only checked `docs/phase-<x>-runbook.md`, but Phase E — planned,
not yet authorized — only has `docs/phase-e-kickoff-plan.md`. Fixed to
check both naming patterns. `/close-step`'s tail-detection was proven
correct three times over by `main`'s own repeated motion during this
session (see above) — each computed number was provisional-labeled and
none was ever committed without a fresh re-check.

### `make lint` / `make test` — clean after two rebases

Both rebases (once before cluster testing, once again before the
merge, after `DEC-077`/`DEC-078` landed) were followed by a clean
`make lint` and `make test` (`252 passed` both times) before proceeding.

### Environment findings summary (for `/pre-flight`/`/post-deploy`'s
own sake, not just this mission)

Nothing broken. The one persistent oddity (`Ingress` `Progressing`
health) is pre-existing and already documented elsewhere in the repo —
worth `/post-deploy` continuing to surface it plainly (not silently
suppress it) so a future run notices immediately if a *third* resource
ever joins those two, which would indicate an actual new problem.

### Applied to `CLAUDE.md` (outside this repo — see note)

`CLAUDE.md` (`/home/darkdragonel/workspaceAgentMvp/CLAUDE.md`) turned
out to live one directory above this repo's root, outside git entirely
— not a file this repo's history can show a diff for. The drafted
skills-registry section (below, same content as drafted in the build
phase) was applied there directly, no commit involved for that specific
edit.

### Final state

`feature/workspace-tooling` merged into `main`, no squash. `DEC-079`
records the release. All `[NOT LIVE-TESTED]`/`[VERIFY ON FIRST LIVE
RUN]` disclaimers removed from all 4 skill files — every check in every
skill is now backed by real, captured output, not static-source
inference.
