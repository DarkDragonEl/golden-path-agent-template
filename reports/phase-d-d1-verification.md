# Phase D, D1 — verification-STOP evidence report

**Scope:** live-cluster evidence for the D1 verification STOP, per the
owner's plan-approval instruction: "hold at the D1 verification STOP with
the live cluster run-through evidence (approve/reject/expiry,
pod-restart-survives-pending, live concurrency race)." All scenarios
below were run against a real, standing deployment of the actual pushed
image (`sha256:35414e4de0c1529ce3edf8295b0983a92907164567083f67d6cd407cc7440427`,
the digest `golden-path-agent-ci-vx9qj`'s `container-build`/`digest-capture`
stages produced) in `golden-path-agent-ephemeral-test`, `AUTH_MODE=none`.
Commands were issued via `oc exec -i <agent-pod> -- python3 -` (the
project's established in-cluster HTTP-call pattern, `DEC-034` — the
image has no `curl`), so every request in this report actually
originates from inside the deployed agent pod, over the real cluster
network, through the real `NetworkPolicy`.

## 0. Pipeline green (step (d) closure)

Two `PipelineRun`s against `main`:
- `golden-path-agent-ci-jsxgv` (commits through `380a7dc`) — 12/13
  stages passed; `security-tests` failed with
  `fallback_reason: approval_service_failure:ConnectError` — the
  deployed agent pod's `APPROVAL_SERVICE_ENDPOINT` was still defaulting
  to `localhost:8082` (`DEC-051`).
- `golden-path-agent-ci-vx9qj` (commits through `fd141bb`, after the
  `DEC-051` fix) — **all 13 stages succeeded**, including
  `security-tests` and `open-promotion-pr` (opened `PR #2`, left for the
  owner's own merge decision — it touches only
  `base/kustomization.yaml`'s digest field, never `base/approval/`, per
  `DEC-046`/`DEC-050`).

RBAC (`DEC-045`'s diffs, `pipelines/bootstrap/rbac.yaml`) applied live
via `oc apply` (server-side dry-run first, confirmed only the two
intended objects changed) and verified via `oc policy who-can`
(authoritative for this cluster — `oc auth can-i --as=` gave a false
negative specifically on `imagestreams/layers`, reproduced against an
already-working pre-existing grant too, so treated as a tool quirk, not
a real gap — see `DEC-051`).

## 1. Approve — submit → approve → execute

```
INVOKE: 200 pending_approval=True, tool_calls=[{tool_name: itsm_create_request, result: None, classification: write}]
PENDING LIST: proposal b4c25bc1-..., evidence_refs=[], initiating_user_id=d1-verify-approve,
              agent_workload_id=golden-path-agent, originating_session_id matches
DECISION (approve): 200 state=approved, decided_by=dev-approver, decided_at=2026-08-23T01:49:44Z
RESUME: 200 final_output="Request REQ-30100 has been submitted (status: submitted)."
        tool_calls[1].result = {record_id: REQ-30100, status: submitted, source: mock-itsm}
TERMINAL STATE (IF-05): state=approved, action_arguments unchanged from submission
```

**Result: PASS.** Full submit→approve→execute round-trip over real HTTP
between three real pods; a real ticket (`REQ-30100`) was created only
after approval.

## 2. Reject — submit → reject → zero mutation

```
INVOKE: 200 pending_approval=True
DECISION (reject): 200 state=rejected, decided_by=dev-approver
RESUME: 200 final_output="This request could not be completed safely right now
        (escalation reason: approval_not_granted:'rejected'). A human should review this session."
        tool_calls: [{result: None, error: None, classification: write}]  <- never executed
SECOND RESUME (after terminal): 404 "no pending approval for this session"
```

**Result: PASS.** The write was never executed (`result: None`
throughout); the escalation message correctly names the rejection. A
second resume call after the graph has already advanced past the
interrupt correctly 404s rather than re-executing or erroring.

## 2b. Premature resume does not consume the interrupt (bonus, beyond
what was asked, cheap to also confirm live)

```
INVOKE: 200 pending_approval=True
PREMATURE RESUME (while still pending): 200 pending_approval=True, final_output=None  <- unchanged, graph untouched
DECISION (approve): 200 state=approved
REAL RESUME: 200 final_output="Request REQ-30101 has been submitted (status: submitted)."
```

**Result: PASS.** Matches the podman smoke-test finding from `DEC-049`,
now also confirmed against the real cluster deployment.

## 3. F-02 — concurrent-decision race

Two decision requests (`approve` and `reject`) fired at the same
`proposal_id` from two threads inside the agent pod, synchronized with a
`threading.Barrier` so both `POST`s leave at effectively the same
instant.

```
approve_thread: 200 state=approved, decided_at=2026-08-23T01:50:34.337983+00:00
reject_thread:  409 {detail: {proposal_id: ..., state: approved}}
FINAL TERMINAL STATE: state=approved  <- single winner, not double-applied
```

**Result: PASS.** Exactly one decision won; the loser was refused with
the actual current state in the response body (not a generic error);
the terminal record reflects only the winning decision.

## 4. Expiry — submit → expire → zero mutation (no restart)

`APPROVAL_TIMEOUT_SECONDS` temporarily lowered to `5` for this and the
next two scenarios (`ConfigMap` patch + `oc rollout restart`, restored
to the committed value `3600` afterward — a deliberate, temporary
verification-only change, never committed to the repo).

```
INVOKE: 200 pending_approval=True, submitted at 01:51:28
[slept 9s, past the 5s timeout, for the periodic in-process scanner to fire]
STATE AFTER TIMEOUT: state=expired, decided_by=None, decided_at=None
RESUME: 200 final_output="...escalation reason: approval_not_granted:'expired'..."
        tool_calls: [{result: None, classification: write}]  <- never executed
LATE DECISION AFTER EXPIRY: 409 {detail: {proposal_id: ..., state: expired}}
```

**Result: PASS.** Confirms the D1 contracts-STOP requirement (`DEC-046`
item 3): an expired proposal's `decided_by`/`decided_at` stay `None`
(distinguishing "nobody decided" from "somebody decided no"), and the
agent-side client treats `expired` identically to `rejected` for
execution purposes (`SRS-APR-F-03`'s "indistinguishable from rejection").

## 5. Restart-overdue-expiry pickup (owner addition #3)

Submit, then kill the approval-service pod **within 4 seconds** — before
even one 5-second timeout window could elapse, so the *old* pod's own
periodic scanner never had a chance to catch it. The record must survive
the restart, and the record's actual overdue-ness must be caught
immediately at the new pod's *startup*, not only on the next periodic
tick.

```
INVOKE: 200 pending_approval=True, proposal bffbc77e-..., submitted 01:51:52
[pod golden-path-agent-approval-7d8f964454-zm7hc deleted at 01:51:56 -- 4s after submission]
[new pod golden-path-agent-approval-7d8f964454-tnq55 Running/Ready at 01:52:09 -- ~13s later]
STATE IMMEDIATELY AFTER RESTART: state=expired, decided_by=None, decided_at=None
RESUME: 200 final_output="...escalation reason: approval_not_granted:'expired'..."
```

**Result: PASS.** The record survived the pod's death (`DATA-01`), and
its overdue timeout was recognized the moment the new pod's mandatory
startup sweep ran — not deferred to the next periodic-loop iteration.

## 6. Pod-restart-survives-pending (not yet overdue)

`APPROVAL_TIMEOUT_SECONDS` raised back to `120` for this scenario, so a
restart well inside that window must find the record still `pending`,
not prematurely expired by the restart itself.

```
INVOKE: 200 pending_approval=True, proposal 8a64ab58-..., submitted 01:52:50
[pod golden-path-agent-approval-5ff7bc95c6-r4gkm deleted; new pod Running/Ready shortly after]
STATE IMMEDIATELY AFTER RESTART: state=pending, decided_by=None, decided_at=None
DECISION (approve, against the RESTARTED pod): 200 state=approved
RESUME: 200 final_output="Request REQ-30102 has been submitted (status: submitted)."
```

**Result: PASS.** The record correctly survived the restart as `pending`
(not prematurely expired), and the restarted pod's decision/query/resume
path is fully functional immediately — proven by completing a real
approve→execute round-trip (`REQ-30102`) against the post-restart pod.

## Cleanup

`APPROVAL_TIMEOUT_SECONDS` restored to the committed value (`3600`) via
the same `ConfigMap` patch mechanism. The entire manually-applied
manifest set (rendered the same way `deploy-ephemeral` renders it, with
the real pushed digest, since this verification needed a *standing*
deployment outside any single `PipelineRun`'s own
`deploy-ephemeral`/`destroy-ephemeral` lifecycle) was deleted via
`oc delete -f` against the same rendered file. Confirmed via
`oc get all -n golden-path-agent-ephemeral-test`: `No resources found`.

## Summary

| Scenario | Result |
|---|---|
| Approve → execute | PASS |
| Reject → zero mutation | PASS |
| Premature resume does not consume interrupt | PASS |
| F-02 concurrent-decision race | PASS |
| Expiry → zero mutation, `decided_by`/`decided_at` stay `None` | PASS |
| Restart-overdue-expiry pickup (owner addition #3) | PASS |
| Pod-restart-survives-pending (not yet overdue) | PASS |

Every scenario the owner's D1 verification-STOP instruction named
(approve/reject/expiry, pod-restart-survives-pending, live concurrency
race) is confirmed live, plus two extras exercised at negligible
incremental cost (premature-resume, restart-overdue-pickup, the latter
explicitly required by plan-approval addition #3). D1 is complete,
pending the owner's own review of this evidence before D2 begins.
