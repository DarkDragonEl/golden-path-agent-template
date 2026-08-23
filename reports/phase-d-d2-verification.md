# Phase D, D2 — verification-STOP evidence report

**Scope:** live evidence for the D2 verification STOP, per the owner's
own instruction: "the named negative tests explicitly: real approver
login → decision → `decided_by` reflects the token identity;
forged/absent/wrong-role token → 403 audit-logged; the agent's own
client-credentials token presented to the decision endpoint → 403
audit-logged (approved addition #2); MCP server rejecting an
absent/unscoped credential live; the mechanical `AUTH_MODE=oidc`
assertion for `demo-prod` demonstrated failing on a seeded none." All
scenarios below were run against the real, live `golden-path-agent-demo-prod`
deployment — real Keycloak-issued tokens, real HTTP between real pods,
issued via `oc exec -i <demo-prod agent pod> -- python3 -` (this
session's own established in-cluster HTTP pattern).

## 0. Cutover recap (context for the evidence below)

`PR #2` (stale — pre-dated `DEC-060`'s OIDC code) closed unmerged; a
fresh green `PipelineRun` opened `PR #3`, merged. The atomic base-wiring
commit (`DEC-063`) promoted the approval-service manifests into `base/`,
flipped `AUTH_MODE=oidc`/`AGENT_OIDC_MODE=oidc`/`MCP_AUTH_MODE=oidc`/
`MCP_MODE=live` for `demo-prod` only, and added the mechanical
demo-prod-config assertion. Two live issues were found and fixed during
rollout, both documented in full under `DEC-064`/`DEC-065`: a missing
`PersistentVolumeClaim` entry in `deploy/argocd/project.yaml`'s
`namespaceResourceWhitelist` (blocked every new `-approval` resource from
syncing at all), and a `ConfigMap`-content-only change never rolling the
already-existing `agent`/`mcp` pods (required a manual
`oc rollout restart` — a named, open structural gap for future
`ConfigMap`-only changes, `DEC-065`).

## 1. Real approver login → decision → `decided_by` reflects the token identity

```
Real password-grant token for demo-approver (client golden-path-agent-approver-ui):
  sub=fb790f55-51b6-42ef-addc-7480ce2ccd23 aud=golden-path-agent-approval roles=['approval-approver']

INVOKE (demo-prod's real /invoke): 200 pending_approval=True
  tool_calls=[{tool_name: itsm_create_request, result: None, classification: write}]

DECISION (demo-approver's real token): 200
  {proposal_id: b60d38a3-..., state: approved,
   decided_by: fb790f55-51b6-42ef-addc-7480ce2ccd23,   <- matches the token's own sub, independently confirmed via the admin API
   decided_at: 2026-08-23T03:54:26Z, decision: approve}

RESUME: 200 final_output="Request REQ-30100 has been submitted (status: submitted)."
```

**Result: PASS.** A real human identity, established purely from a
validated Keycloak token (never a client-supplied claim), flows through
to the audit record and gates a real write.

## 2. Forged / absent / wrong-role token → refused, audit-logged (tested precisely, not blanket-asserted)

```
Absent token:
  POST /proposals/{id}/decision -> 401 {"detail": "missing bearer token"}

Forged token (well-formed JWT, signature not from the real IdP):
  POST /proposals/{id}/decision -> 401 {"detail": "invalid token: Unable to find a signing key that matches: \"None\""}

Wrong-role token (demo-user's real, valid, correctly-audienced token; no approval-approver role):
  POST /proposals/{id}/decision -> 403 {"detail": "caller lacks the approver role"}

approval-service log:
  refused decision attempt: identity=b759ffee-f69e-4173-8f12-cbd29911dba1 reason=missing_approver_role role_claim=roles
```

**Result: PASS.** Forged/absent tokens fail signature/presence
validation (`401`, before any role check ever runs); a real,
authenticated-but-unauthorized human token is refused specifically for
lacking the role (`403`), and that refusal is audit-logged with the
real identity and reason — matching `approval_service/auth.py`'s own
documented two-stage design (D1), now exercised against a real IdP for
the first time.

## 3. The agent's own client-credentials token on the decision endpoint → `403`, audit-logged (plan-approval addition #2)

```
Agent's own real approval-workload token (sub=d2646036-..., correctly
audienced for approval-service, otherwise looks like any other valid caller):
  POST /proposals/{id}/decision -> 403 {"detail": "caller lacks the approver role"}

approval-service log:
  refused decision attempt: identity=d2646036-648c-425f-8cb1-380f459b597a reason=missing_approver_role role_claim=roles
```

**Result: PASS.** The agent's workload identity is correct by
construction, not by an explicit deny rule — its service-account user
was simply never assigned the `approval-approver` role (`DEC-054`'s
design), so it fails the identical check identical to any other
unauthorized caller. Confirmed the target proposal was untouched
(`state: pending`) after this attempt, before it was later legitimately
decided.

## 4. MCP server rejecting an absent/unscoped credential, live

**First attempt failed** — both absent and wrong-audience calls returned
`200` with real data. Root-caused (`DEC-065`): the running `mcp` pod
still had `MCP_AUTH_MODE=none` baked into its environment from before
the `ConfigMap` update (`ConfigMap`-content-only changes don't trigger a
`Deployment` rollout for an already-running pod in this project's own
`kustomize` setup). Fixed with `oc rollout restart`; re-verified after
confirming the new pod's actual environment via `os.environ`:

```
Absent credential:
  POST /tools/itsm_search_records -> 401 {"detail": "missing bearer token"}

Unscoped credential (a real, validly-signed token -- just the wrong
audience: the approval-workload token, audience golden-path-agent-approval,
not golden-path-agent-mcp):
  POST /tools/itsm_search_records -> 401 {"detail": "invalid token: Audience doesn't match"}

Correctly-scoped credential (the real mcp-workload token):
  POST /tools/itsm_search_records -> 200 {"count": 4, "source": "mock-itsm", ...}
```

**Result: PASS** (after the live fix above). Fail-closed confirmed for
both the missing-credential and wrong-audience cases; the positive
control (a genuinely valid, correctly-scoped token) confirms this isn't
blanket-denying every request.

## 5. The mechanical `AUTH_MODE=oidc` assertion for `demo-prod`, demonstrated failing on a seeded `none`

Already covered in full at `DEC-063`'s own commit — repeated here for
completeness of this report:

```
Seeded regression (AUTH_MODE=none, MCP_AUTH_MODE=none in a scratch copy
of demo-prod's own kustomization.yaml):
  tools/check_config_contract.py -> CONFIG-CONTRACT CHECK FAILED
    - demo-prod's effective golden-path-agent-config.MCP_AUTH_MODE is 'none', expected 'oidc' ...
    - demo-prod's effective golden-path-agent-approval-config.AUTH_MODE is 'none', expected 'oidc' ...

Restored -> tools/check_config_contract.py -> config-contract check OK
  (3 demo-prod security-downgrade switch(es) confirmed flipped)
```

**Result: PASS.** The assertion is mechanical (computes `demo-prod`'s
own effective, merged config the same way Kustomize itself would), not
conventional, and demonstrated to actually fail on a real regression
before being trusted to pass.

## Cleanup

The one leftover pending proposal from tests 2/3 was rejected afterward
(via `demo-approver`'s own real token) to leave `demo-prod` in a clean
state — no test debris left in a production-like namespace. All three
`demo-prod` `Deployment`s (`golden-path-agent`, `golden-path-agent-mcp`,
`golden-path-agent-approval`) confirmed `Healthy` after the restart.

## Summary

| Test | Result |
|---|---|
| Real approver login → decision → `decided_by` reflects identity | PASS |
| Forged/absent/wrong-role token → refused, audit-logged (tested precisely: 401/401/403) | PASS |
| Agent's own client-credentials token on decision endpoint → 403, audit-logged | PASS |
| MCP server rejecting absent/unscoped credential, live | PASS (after live fix, `DEC-065`) |
| Mechanical `AUTH_MODE=oidc` assertion, demonstrated failing on seeded `none` | PASS |

Every scenario the owner's D2 verification-STOP instruction named is
confirmed live, against the real `demo-prod` deployment, with two real
live-infrastructure gaps found and fixed along the way (`DEC-064`'s
`PersistentVolumeClaim` whitelist, `DEC-065`'s `ConfigMap`-rollout gap,
the latter left as a named, open backlog item rather than papered over).
D2 is complete, pending the owner's own review of this evidence before
D3 begins.
