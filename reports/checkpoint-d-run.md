# Checkpoint D — live run-through evidence

**Scope:** the accepted plan's own exit criterion, verbatim: "live
run-through — ask → cited answer → draft → approve → ticket exists;
second run: reject → nothing written; third: expiry → nothing written;
one full trace spanning the async approval gap, shown via D4's
mechanism." All scenarios below ran against the real, live
`golden-path-agent-demo-prod` deployment, over real HTTP, via `oc exec`
into the deployed agent pod (this session's own established pattern).

## 1. Ask → cited answer (read-only, no approval needed)

```
INVOKE: 200 pending_approval=False
final_output: "The unit of workload isolation within a cluster on the
  internal container platform is a Pod.\n\nSources: PLAT-003"
```

**Result: PASS** for the flow itself (retrieval ran, a citation was
produced, no approval was requested for a read). **Noted, not chased**:
the answer's own factual content doesn't match `PLAT-001.md`'s actual
text (which says the unit of isolation is the *namespace*, and cites the
wrong document, PLAT-003 not PLAT-001) — a retrieval/generation quality
question, pre-existing and unrelated to anything Phase D touched (no
Phase D work modified `agent/nodes/retrieve.py`/`agent/nodes/generate.py`
or the corpus); Phase B/C's own eval gates (60/62 passing, two named
tolerated gaps) are the actual authority on answer-quality regression,
not this one ad hoc walkthrough question. Flagged here for visibility,
not fixed as part of this checkpoint.

## 2. Draft → approve → ticket exists

```
INVOKE (write:true): 200 pending_approval=True
DECISION (demo-approver's real token): 200 state=approved, decided_by=fb790f55-... (demo-approver's real Keycloak sub)
RESUME: 200 final_output="Request REQ-30100 has been submitted (status: submitted)."
```

**Result: PASS.**

## 3. Reject → nothing written

```
INVOKE (write:true): 200 pending_approval=True
DECISION (reject): 200 state=rejected
RESUME: 200 final_output=None, fallback_reason="approval_not_granted:'rejected'"
tool_calls[0].result: None  <- never executed
```

**Result: PASS.**

## 4. Expiry → nothing written

`APPROVAL_TIMEOUT_SECONDS` temporarily lowered to `5` for this scenario
only (restored to the committed `3600` immediately after — **a real,
noted operational finding**: `demo-prod`'s ArgoCD `selfHeal: true`
reverted this manual `ConfigMap` patch mid-test once, during an earlier,
slower attempt — this is expected, documented behavior for a
GitOps-synced environment, not a bug; the fix was simply to keep the
patch→restart→test window short, which the second, clean attempt did).

```
INVOKE (write:true): 200 pending_approval=True, submitted at 05:04:29
[slept 9s, past the 5s timeout]
RESUME: 200 final_output=None, fallback_reason="approval_not_granted:'expired'"
tool_calls[0].result: None  <- never executed
```

**Result: PASS.**

## 5. One full trace spanning the async approval gap, via D4's mechanism

`tools/query_traces.py --session-id <scenario 2's session id>`, run
in-cluster against the real collector (`DECISIONS.md` `DEC-068`/`DEC-071`):

```
[05:41:42.879] golden-path-agent          span  agent.invoke             model.route=primary tool_calls.count=1 ...
[05:41:45.629] golden-path-agent-approval span  approval.create_proposal approval.event=proposal_intake approval.state=pending ...
[05:41:45.638] golden-path-agent          event model_call                model_call.node=decide model_call.route=primary ...
[05:41:45.638] golden-path-agent          event tool_call                 tool_call.tool_name=itsm_create_request classification=write ...
[05:41:45.642] golden-path-agent-approval span  approval.decide_proposal approval.event=proposal_decided approval.state=approved
                                                  approval.decided_by=fb790f55-51b6-42ef-addc-7480ce2ccd23   <- the real approver identity
[05:41:45.650] golden-path-agent          span  agent.resume             approval.decision=approved
                                                  final_output.preview=Request REQ-30100 has been submitted (status: submitted).
[05:41:45.787] golden-path-agent          event model_call               (the resume-side model call)
[05:41:45.787] golden-path-agent          event tool_call                (the real, executed write)
[05:41:45.787] golden-path-agent          event tool_call                (duplicate tool_call entry from the full tool_calls history -- expected, agent/state.py accumulates)
```

**Result: PASS.** A single query, filtered by `session.id` alone, shows
the complete story across **two independent processes** (`golden-path-agent`,
`golden-path-agent-approval`) with correctly ordered timestamps: the
draft, the submission, the (here, near-instant, but architecturally
identical to a real human-latency wait) decision by a real identity, and
the resume/execution — the attribute-correlation mechanism working
exactly as designed, not merely as claimed. A second query by
`--proposal-id` alone returns the narrower subset of spans that actually
carry a proposal at that point (`agent.invoke`'s own span legitimately
has no `proposal.id` yet, since no proposal exists when it starts) —
confirmed as expected, correct behavior, not a gap.

## Cleanup

All test-created pending proposals rejected/resolved; `APPROVAL_TIMEOUT_SECONDS`
confirmed back at the committed `3600`; scratch files removed from the
agent pod. `demo-prod`'s `Application` confirmed `Synced`; all three
`Deployment`s (`golden-path-agent`, `golden-path-agent-mcp`,
`golden-path-agent-approval`) confirmed `Running`/`Healthy`.

## Summary

| Scenario | Result |
|---|---|
| Ask → cited answer (flow) | PASS (content-accuracy note, out of Phase D scope) |
| Draft → approve → ticket exists | PASS |
| Reject → nothing written | PASS |
| Expiry → nothing written | PASS |
| Full trace spanning the async gap, session/proposal-id stitched | PASS |

Every scenario the accepted plan's own Checkpoint D exit criterion names
is confirmed live, against the real `demo-prod` deployment. This is also
the D3 `SRS-APR-QUAL-01` non-developer-walkthrough verification point —
the API-level flow behind the UI is confirmed working end to end; the
UI itself (`GET /ui`, real HTML, confirmed serving) needs the owner's own
live click-through (Authorization Code + PKCE requires a real browser)
to close that specific verification method, as already anticipated
("I'll be that walkthrough at Checkpoint D — design for it").
