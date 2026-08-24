# feature/workspace-tooling — report

Mission: build a first generation of Claude Code skills/commands (a
pre-flight environment check, a packaged eval-runner, a tool prober, a
post-deploy verifier) plus a provisional UI map of the approver UI, on
an isolated branch, without colliding with the separate live session
that was fixing the owner-walkthrough UI flow to close Checkpoint D at
the same time.

## What was built

| File | What it is | Live-tested this mission? |
|---|---|---|
| `.claude/skills/pre-flight/SKILL.md` | 6-check demo-prod readiness gate | No — entirely `oc`-gated, cluster access was excluded from this mission by design |
| `.claude/skills/run-evals/SKILL.md` | Wraps `make up` + an N-pass `eval-domain` loop (no native `--passes` flag exists) against `eval/thresholds.yaml` + `KNOWN_GAP_TOLERANCES` | **Yes** — see Verification below |
| `.claude/skills/probe-tool/SKILL.md` | Calls the mock ITSM MCP tools directly over REST, bypassing the model | **Yes** — see Verification (a real bug was found and fixed here) |
| `.claude/skills/post-deploy/SKILL.md` | ArgoCD sync/health + image-digest-matches-promoted-digest check | No — same reason as `pre-flight` |
| `.claude/commands/start-step.md` | Session-bootstrap brief: `HANDOFF.md` + last 5 DEC entries + `PINS.md` + current runbook | Read-only, not separately "tested" beyond being read for sanity |
| `.claude/commands/close-step.md` | Drafts (never commits) a DEC entry + report skeleton | Same |
| `docs/drafts/AGENT-UI-MAP.draft.md` | Provisional approver-UI map, built from the real `agent/static/approver_ui.html` source | Not browser-tested — explicitly provisional per its own header |

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
