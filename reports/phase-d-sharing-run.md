# Phase D sharing artifact — the full clickable flow: ask → answer →
draft → approve/reject/expiry → ticket → trace

Per `E2E_DEMO_PLAN.md`'s E3 ("after D: the full clickable flow — ask →
cited answer → draft → approve/reject/expiry → ticket in the mock ITSM →
end-to-end trace"), this is the Phase D sharing moment — sequenced after
Checkpoint D's own formal closure (`DECISIONS.md` `DEC-077`), not before,
so it describes a completed Checkpoint D, matching
`docs/phase-e-kickoff-plan.md` §5.1's own recommendation. **One caveat up
front, stated plainly**: like Phase C's own sharing artifact, this was
captured against the shared SNO lab cluster this milestone actually used
(`docs/environments.md`'s shared-cluster deviation note), not the
dedicated Phase E showcase cluster — the showcase's own bootstrap is
proven separately (`reports/phase-e-refresh-log.md`), but its
`demo-prod`-equivalent isn't yet serving a promoted digest
(`DECISIONS.md` `DEC-078`'s Option 2, awaiting the hosted-registry
migration follow-up). This report documents the SNO's own real, working
system; the showcase replays the identical flow once that follow-up
lands.

**Captured:** 2026-08-22 through 2026-08-23 (`reports/checkpoint-d-run.md`,
`reports/phase-d-owner-walkthrough-verification.md`). Every transcript
below is real, `oc`-captured or browser-captured output against the live
`golden-path-agent-demo-prod` deployment — cluster-internal
hostnames/namespace names are this project's own already-public naming
convention, never a real external endpoint; the live MaaS model endpoint
and the OpenShift cluster's own identity never appear (same anonymity
discipline as every prior sharing artifact, reinforced this session by
`DECISIONS.md` `DEC-082`'s pre-push sweep finding and fixing a real
violation of exactly this rule elsewhere in the repo).

## What a colleague is watching

1. A real question asked of the deployed agent, answered with a citation
   — no approval needed for a read.
2. A write request drafted, held at the approval boundary, approved by a
   real Keycloak identity, and the resulting ticket created in the mock
   ITSM — nothing executes before a human decides.
3. The same draft, rejected — and separately, left to expire — in both
   cases confirmed that **nothing was ever written**.
4. The owner's own live browser click-through of the approver UI
   (`GET /ui`, Authorization Code + PKCE) — the same flow above, but a
   real human clicking, not a scripted HTTP call.
5. One trace query spanning the async approval gap — a single
   `session.id` stitching two independent processes into one story.

## 1. Ask → cited answer (read-only, no approval needed)

```
INVOKE: 200 pending_approval=False
final_output: "The unit of workload isolation within a cluster on the
  internal container platform is a Pod.\n\nSources: PLAT-003"
```

**PASS** — retrieval ran, a citation was produced, no approval was
requested for a read. (A pre-existing, unrelated retrieval/generation
content-accuracy note is on record in `reports/checkpoint-d-run.md` —
Phase B/C's own eval gates, 60/62 passing, are the actual authority on
answer-quality regression, not one ad hoc walkthrough question.)

## 2. Draft → approve → ticket exists

```
INVOKE (write:true): 200 pending_approval=True
DECISION (demo-approver's real token): 200 state=approved, decided_by=<demo-approver's real Keycloak identity>
RESUME: 200 final_output="Request REQ-30100 has been submitted (status: submitted)."
```

**PASS.**

## 3. Reject → nothing written

```
INVOKE (write:true): 200 pending_approval=True
DECISION (reject): 200 state=rejected
RESUME: 200 final_output=None, fallback_reason="approval_not_granted:'rejected'"
tool_calls[0].result: None  <- never executed
```

**PASS.**

## 4. Expiry → nothing written

```
INVOKE (write:true): 200 pending_approval=True, submitted
[slept past a temporarily-shortened timeout]
RESUME: 200 final_output=None, fallback_reason="approval_not_granted:'expired'"
tool_calls[0].result: None  <- never executed
```

**PASS.** (A real operational finding surfaced getting here, on record
in `reports/checkpoint-d-run.md`: `demo-prod`'s ArgoCD `selfHeal: true`
will revert a manual `ConfigMap` timeout-override patch mid-test if the
patch→test window runs long — expected GitOps behavior, not a bug; the
fix was keeping that window short.)

## 5. The owner's own live browser click-through

`docs/owner-walkthrough.md`, run live, 2026-08-23 (`DECISIONS.md`
`DEC-077`) — the one item Checkpoint D was left open on
(`SRS-APR-QUAL-01`'s non-developer walkthrough, a real human in a real
browser):

- **`demo-approver`**: logged in via the real Keycloak login page,
  submitted the write-drafting query, watched the pending proposal
  appear, clicked Approve, confirmed the ticket was created.
- **`demo-user`** (private/incognito window, per `DEC-076`'s corrected
  instructions — Keycloak's own SSO session otherwise silently
  re-authenticates the same identity on a second "Log in"): logged in,
  confirmed the decide controls are absent/refused for a non-approver
  identity.

Real gaps found and fixed getting to this point, not glossed over: an
OIDC browser-discovery issuer-hostname mismatch (`DEC-074`), a
wrong-port-forward instruction in an earlier runbook draft (`DEC-075`,
found live on the owner's own first attempt), and the missing-logout SSO
behavior above (`DEC-076`, found first by an automated real-browser
Playwright drive immediately before the owner's own session, so the
owner's click-through hit a corrected instruction, not a fresh bug).
`demo-prod` left clean afterward; port-forwards stopped.

## 6. One full trace spanning the async approval gap

`tools/query_traces.py --session-id <scenario 2's session id>`, against
the real cluster-tier OTel Collector (`DECISIONS.md` `DEC-068`/`DEC-071`):

```
[T+0.0s] golden-path-agent          span  agent.invoke             model.route=primary tool_calls.count=1
[T+2.8s] golden-path-agent-approval span  approval.create_proposal approval.event=proposal_intake approval.state=pending
[T+2.8s] golden-path-agent          event model_call                model_call.node=decide model_call.route=primary
[T+2.8s] golden-path-agent          event tool_call                 tool_call.tool_name=itsm_create_request classification=write
[T+2.8s] golden-path-agent-approval span  approval.decide_proposal approval.event=proposal_decided approval.state=approved
                                            approval.decided_by=<the real approver identity>
[T+2.8s] golden-path-agent          span  agent.resume             approval.decision=approved
                                            final_output.preview=Request REQ-30100 has been submitted (status: submitted).
[T+2.9s] golden-path-agent          event model_call               (the resume-side model call)
[T+2.9s] golden-path-agent          event tool_call                (the real, executed write)
```

**PASS.** A single query, filtered by `session.id` alone, shows the
complete story across two independent processes (`golden-path-agent`,
`golden-path-agent-approval`) with correctly ordered timestamps — the
draft, the submission, the decision by a real identity, and the
resume/execution. The attribute-correlation mechanism works exactly as
designed, not merely as claimed.

## What this shows

- **The approval boundary genuinely blocks execution**, in both
  directions colleagues will ask about first: rejection and silent
  expiry both leave `tool_calls[0].result` unexecuted, not just
  UI-hidden.
- **The UI is not a facade over an already-working API** — the owner's
  own click-through, and an independent automated real-browser drive
  immediately before it, both exercised the actual browser-facing OIDC
  flow (Authorization Code + PKCE), not a mocked or bypassed one — and
  both found and fixed real bugs along the way (`DEC-074`–`DEC-076`),
  the kind a protocol-level test alone wouldn't have caught.
- **One trace, one query, two processes, correctly stitched** — the
  async approval gap (a human decision in between) doesn't break
  correlation, because `session.id`/`proposal.id` carry across the
  boundary by design, not by convention alone.

## What this is NOT yet

- **Steps 4–6** (`StRS_Agentic_AI_Platform_EN.md` §18.2/§19: staging
  integration, controlled pilot, the production architecture decision)
  — explicitly phase-two; this milestone covers Steps 1–3 only.
- **No external HTTP routing this milestone** — no working `Ingress`
  exists yet for any of this project's services; every interaction above
  went through `oc port-forward` or in-cluster `oc exec`, including the
  owner's own browser session.
- **Attestation / per-agent sandbox profiles** — `Annex_A_Open_Items_EN.md`
  OI-03's explicitly-deferred tier. Said here, not faked.
- **ESO/Vault secrets integration** — deferred phase-two
  (`docs/security-identity.md`, `PINS.md`).
  `pipelines/bootstrap/provision-identity-secrets.sh`'s own header
  comment names itself as this milestone's demo-scale realization of
  what a real ESO/Vault sync would do continuously.
- **A real in-app logout control** — `DEC-076`'s finding; a named,
  not-yet-implemented Phase E hardening candidate (touches the image,
  needs separate authorization per `CLAUDE.md`'s scope guard).
- **The `DEC-065` `ConfigMap`-rollout gap** — a `ConfigMap`-only change
  to a GitOps-synced overlay doesn't roll already-running pods; the
  `checksum/config`-annotation pattern is named as this gap's Phase E
  hardening candidate, not yet implemented.
- **The four named known-gaps** (`INJ-006`, `UAW-003`, `ITR-004`,
  `TSEL-004`) — declared final per `HANDOFF.md` invariant #7. `INJ-006`:
  jailbreak framing can still get a write action drafted, but the
  human-approval gate held 100% across every measurement — defense in
  depth demonstrated, not a weakness hidden.
- **Not yet run against the showcase cluster's own `demo-prod`** — its
  bootstrap is proven (`reports/phase-e-refresh-log.md`), but it has no
  promoted digest yet (`DECISIONS.md` `DEC-078` Option 2). This report
  documents the SNO's real, working system; replaying it on the showcase
  is the next sharing-readiness milestone, gated on `DEC-078`'s first
  follow-up commit.
