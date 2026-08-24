# Owner-walkthrough prep: live verification (`DEC-074`)

## Scope

Before handing `docs/owner-walkthrough.md` to the owner for the one
remaining Checkpoint D closure step (their own live browser click-through
of `GET /ui`), this report proves the real Authorization Code + PKCE flow
that doc walks them through actually works end to end, scripted against
real, live `golden-path-agent-demo-prod` — including the browser-side OIDC
issuer-discovery gap found and resolved as part of this same work
(`DEC-074`). No real browser was available to drive this; the scripted
flow (`tools/verify_owner_walkthrough.py`) drives the identical protocol
steps `agent/static/approver_ui.html`'s own `login()`/`handleRedirect()`
logic does — a real GET against Keycloak's login form, a real credentialed
POST, a real authorization-code redirect, a real `code_verifier` token
exchange — never the client's `directAccessGrantsEnabled` shortcut used
for D2's own sandboxed testing.

## 0. Pre-flight

```
$ oc whoami
darkdragonel
$ oc get deployment,pod -n golden-path-agent-demo-prod
deployment.apps/golden-path-agent            1/1   1   1   25h
deployment.apps/golden-path-agent-approval   1/1   1   1   13h
deployment.apps/golden-path-agent-mcp        1/1   1   1   25h
pod/golden-path-agent-approval-...   1/1   Running   1   12h
pod/golden-path-agent-...            1/1   Running   1   12h
pod/golden-path-agent-mcp-...        1/1   Running   1   12h
```

All three Deployments healthy. Debris check: a `demo-approver` token was
obtained via the direct-grant path (D2's existing sandboxed-testing grant,
not the PKCE path under test) and used against `GET /proposals` —
**returned `[]`**. `demo-prod` started clean; no leftover pending
proposals from `checkpoint-d-run.md`'s own earlier evidence run.

**Confirmed live** (not assumed) that the browser-discovery gap
`DEC-074` describes is real: a token minted by reaching Keycloak over a
bare `localhost:8080` port-forward carried `iss=http://localhost:8080/realms/golden-path-agent`
and was rejected by `approval_service` with `{"detail": "invalid token:
Invalid issuer"}`.

## 1. OIDC browser-discovery resolution

Three port-forwards started:
```
oc port-forward svc/golden-path-agent 18080:8080 -n golden-path-agent-demo-prod
oc port-forward svc/golden-path-agent-approval 18082:8082 -n golden-path-agent-demo-prod
oc port-forward svc/golden-path-agent-service 8080:8080 -n golden-path-agent-keycloak
```
All three confirmed up (`Forwarding from 127.0.0.1:<port> -> <container port>`
for each).

Hosts-file line added (by the human operator, via `sudo`, since this
session's own sandboxed shell has no passwordless `sudo`/askpass helper):
```
127.0.0.1 golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local
```
Confirmed present via `grep` before use. **No fallback/resolver-override
deviation was needed** — the real hosts-file mechanism worked as designed
on the first attempt once added.

**Redirect-URI live-config check** (§2a of the approved plan, run before
any PKCE flow): fetched an admin token from Keycloak's own realm (`master`,
`admin-cli`) using the existing bootstrap-admin credential
(`Secret golden-path-agent-keycloak-admin`), then queried the live
representation of client `golden-path-agent-approver-ui` via the Admin
REST API:
```
redirectUris: ['*']
webOrigins:   ['*']
```
Matches the committed `keycloak-realm-import.yaml`. `http://localhost:18080/ui`
is already covered — **zero config changes made or needed.**

Token round-trip through the hosts-mapped path, decoded:
```
iss:   http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/golden-path-agent
aud:   golden-path-agent-approval
roles: ['approval-approver']
sub:   fb790f55-51b6-42ef-addc-7480ce2ccd23
```
`GET /proposals` with this token → `200 []` (not `401`). Confirms the
issuer string is byte-identical to what `approval_service` validates
server-side, and the mechanism works end to end.

## 2. `tools/verify_owner_walkthrough.py` — full run

```
$ export DEMO_APPROVER_PASSWORD=<redacted>
$ export DEMO_USER_PASSWORD=<redacted>
$ python3 tools/verify_owner_walkthrough.py

PASS - GET /ui/config returns the expected internal-DNS issuer (http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/golden-path-agent)
PASS - demo-approver PKCE login (sub=fb790f55-51b6-42ef-addc-7480ce2ccd23, roles=['approval-approver'])
PASS - submit write query -> pending (session=65afc16d-1197-45fe-b626-ef68eff1a4ac, proposal=4c787f0d-7aff-4702-8e81-fdac85ceb455, polls=1)
PASS - approve (decided_by=fb790f55-51b6-42ef-addc-7480ce2ccd23)
PASS - resume -> ticket created (REQ-30100)
PASS - demo-user PKCE login (sub=b759ffee-f69e-4173-8f12-cbd29911dba1, roles=None)
PASS - demo-user submit write query -> pending (session=fdea7f61-39ef-4fa4-ab44-828e059da85e, proposal=2f493459-b87f-47dc-a238-e2881f325486)
PASS - demo-user decision attempt refused server-side (403) (matches DEC-069's fix)
PASS - cleanup (1 leftover proposal(s) resolved, demo-prod clean)

All scenarios PASSED
EXIT CODE: 0
```

### 3. Positive path (demo-approver)

- Real PKCE login against Keycloak's actual login form — `state` verified
  on redirect, real `code_verifier` used in the token exchange.
- Query submitted (verbatim, `eval/cases/domain/draft_request.yaml`'s
  `DRQ-001` fixture): *"Please raise a request to get an extra namespace
  quota for my team, referencing the quota exhaustion known error."*,
  `write: true`.
- Reached `pending` on the **first** 3-second poll.
- Approved — `decided_by` on the response matched the access token's own
  `sub` exactly (server establishes identity from the bearer token, per
  `SEC-03` — never a client-supplied field).
- Resumed — final output contained ticket `REQ-30100`.

**Note on the ticket number**: `REQ-30100` is the same number
`reports/checkpoint-d-run.md` recorded for its own, earlier, unrelated
test. Investigated, not assumed benign: `mcp_server/itsm_store.py`'s
record-id counter (`_next_request_seq`) is explicitly in-memory-only by
design (`SRS-MIT-IF-05`'s "persists ... within one running instance," not
across restarts), starting from a fixed floor value on every process
start. `golden-path-agent-mcp`'s pod shows `RESTARTS: 1` — the counter
reset to its floor and this run's request became the first new one minted
in the pod's current lifetime, landing on the same starting number by
construction. Confirmed via direct read of `itsm_store.py`, not inferred.
This is a genuinely new record, not a duplicate or an idempotency-key
collision.

### 4. Negative path (demo-user)

- Real PKCE login as `demo-user` — decoded token confirmed **no**
  `approval-approver` role (`roles` claim absent entirely for this
  identity, consistent with `DEC-058`'s realm setup: only `demo-approver`
  was granted the role).
- Second write query submitted and reached `pending` the same way.
- Decision attempt (`approve`) with `demo-user`'s own token → **`403`**,
  matching `DEC-069`'s fix (three approval-service endpoints previously had
  no auth check at all; this route's role check is what's under test
  here, and it held). This is the server-side enforcement backing the
  client's `hasApproverRole()` gate that hides the decide buttons in the
  real UI.

### 5. Cleanup

The one proposal left pending by the negative-path submission (demo-user
can't decide it, by design) was resolved via the `demo-approver` token,
`reject` — matching the pre-flight debris-check's own default. Re-queried
`GET /proposals` → `[]`. `demo-prod` left clean.

Hosts-file entry removed after the run, by the human operator via `sudo`
(`/etc/hosts` is `root:root` mode `644`; this session's own shell has no
TTY/askpass helper for `sudo`, the same reason the operator added the
line in the first place):
```
sudo sed -i '/golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local/d' /etc/hosts
```
**Confirmed removed** — `grep golden-path-agent-service /etc/hosts`
returns no match; the file's remaining content is only the stock loopback
entries and comments.

## Summary

| Scenario | Result |
|---|---|
| Cluster/pod health pre-flight | PASS |
| Pending-debris check (pre) | PASS (clean) |
| Browser-discovery gap reproduced (bare localhost issuer → 401) | Confirmed |
| Redirect-URI live-config check | PASS (`["*"]`, no change needed) |
| Hosts-mapped issuer round-trip | PASS (`iss`/`aud`/`roles`/`sub` all correct) |
| `GET /ui/config` issuer value | PASS |
| demo-approver PKCE login | PASS |
| Submit → pending | PASS (1 poll) |
| Approve (`decided_by` = token `sub`) | PASS |
| Resume → ticket `REQ-30100` | PASS |
| demo-user PKCE login (no approver role) | PASS |
| Submit → pending (demo-user) | PASS |
| Decision attempt refused (403) | PASS |
| Cleanup (`GET /proposals` → `[]`) | PASS |
| Hosts-file entry removed | Confirmed (`grep` returns no match) |

No fallback/deviation from the planned hosts-mapped mechanism was needed
at any point in this run.

---

# Addendum: `DEC-075` incident — owner's first attempt broke, root cause, fix, re-verification

## Symptom (reported by the owner)

Login worked (real `demo-approver` identity, role shown), submit
appeared to work, but the pending-proposal card never appeared — stuck on
"Waiting for approval..." for several minutes. A diagnostic curl to
`/proposals/pending` returned `{"detail": "missing bearer token"}`, which
at the time looked like confirmation auth was enforcing correctly.

## Root-cause investigation

- **The diagnostic curl was a red herring**: `/proposals/pending` is not a
  real endpoint. It matches `GET /proposals/{proposal_id}` with
  `proposal_id="pending"`, which also requires auth and returns the same
  error shape regardless of whether the real pending-list endpoint
  (`GET /proposals?originating_session_id=...`) works at all.
- **Live logs, both services, `--since=2h`, `--timestamps`**, container
  uptime confirmed continuous since well before the owner's attempt (no
  restart could have hidden anything): the owner's browser never sent a
  single `POST /invoke` in the entire window — only `GET /ui` and
  `GET /ui/config`.
- **Direct reproduction**: `curl -X POST http://localhost:18080/invoke`
  (same-origin, no auth needed, identical body to what the UI sends)
  succeeded immediately — `200`, `pending_approval: true` — and
  `approval_service` logged a real `POST /proposals 201 Created`. This
  proved the backend graph, the agent's own workload-token acquisition,
  and proposal creation were all healthy the entire time.
- **Confirmed clean elsewhere too**: `AUTO_APPROVE_IN_DEV=false`,
  `AGENT_OIDC_MODE=oidc`, `MCP_AUTH_MODE=oidc` in `demo-prod`'s live
  ConfigMap; `mcp` logs show zero unexpected activity (correct — a write
  action must never reach the tool before approval, `DEC-008`).
- **The actual defect**: `agent/static/approver_ui.html:208` hardcodes
  `APPROVAL_SERVICE_ORIGIN`'s default to `http://localhost:8082`.
  `docs/phase-d-runbook.md`'s port-forward instructions (copied verbatim
  into `docs/owner-walkthrough.md`) said to forward approval-service to
  local port **`18082`**. Confirmed live: nothing was listening on local
  `8082` at all. `pollPending()`'s own error handling treats a connection
  failure the same as a transient server hiccup (`// Network hiccup --
  keep polling`), so the UI retried silently forever with zero visible
  error — exactly matching the reported symptom. `/invoke` itself is
  same-origin (`AGENT_ORIGIN = window.location.origin`) and was never
  affected, which is why login and submit both appeared to work.

## A gap in this report's own earlier verification, named plainly

`tools/verify_owner_walkthrough.py`'s first version hardcoded
`APPROVAL_ORIGIN = "http://localhost:18082"` — the *correct* port, but a
second, independently-maintained copy of a value the real page already
defines. That let the run recorded above pass cleanly without ever
exercising the actual default a real browser uses. Fixed properly, not by
swapping in the other hardcoded number: the script now parses
`APPROVAL_SERVICE_ORIGIN`'s default straight out of the live-served
`GET /ui` HTML (`fetch_approval_origin()`), so it always tracks whatever
the real page actually has. Full reasoning and the named `/ui/config`
hardening candidate (not implemented — touches the image) are in
`DECISIONS.md` `DEC-075`.

## Fix shipped

Docs-only, no image rebuild: `docs/phase-d-runbook.md` and
`docs/owner-walkthrough.md` now instruct forwarding approval-service to
local port `8082` (matching the page's real default), with an explicit
warning against silently picking a different port.
`tools/verify_owner_walkthrough.py` derives the port from the live page
instead of hardcoding it.

## Re-verification, full run, corrected script

```
$ export DEMO_APPROVER_PASSWORD=<redacted>
$ export DEMO_USER_PASSWORD=<redacted>
$ python3 tools/verify_owner_walkthrough.py

PASS - approval-service origin derived from the live served /ui page (http://localhost:8082)
PASS - GET /ui/config returns the expected internal-DNS issuer (http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/golden-path-agent)
PASS - demo-approver PKCE login (sub=fb790f55-51b6-42ef-addc-7480ce2ccd23, roles=['approval-approver'])
PASS - submit write query -> pending (session=4e373706-cd85-47c3-9b05-d9d8e766fcad, proposal=5666e99c-bfc3-4329-a89e-2b9f21d4aec9, polls=1)
PASS - approve (decided_by=fb790f55-51b6-42ef-addc-7480ce2ccd23)
PASS - resume -> ticket created (REQ-30101)
PASS - demo-user PKCE login (sub=b759ffee-f69e-4173-8f12-cbd29911dba1, roles=None)
PASS - demo-user submit write query -> pending (session=0b304479-a597-4d6a-8e46-03dead025202, proposal=8839d1e7-2149-4c72-a6bc-183f0fd07b2f)
PASS - demo-user decision attempt refused server-side (403) (matches DEC-069's fix)
PASS - cleanup (2 leftover proposal(s) resolved, demo-prod clean)

All scenarios PASSED
EXIT CODE: 0
```

The "2 leftover proposal(s)" resolved during cleanup were: the proposal
created by this incident's own live `/invoke` reproduction (ticket
`REQ-30100`, already resolved as approved during diagnosis — the leftover
was a second, unrelated stray) and this run's own demo-user negative-path
proposal. `REQ-30101` (this run's positive-path ticket) reflects the
in-memory record-id counter having advanced by one from the diagnostic
reproduction earlier in this same session — expected, not a duplicate,
same mechanism documented above for `REQ-30100`.

**Final clean-state check**, independent of the script's own cleanup step:
```
$ curl -H "Authorization: Bearer <demo-approver token>" http://localhost:8082/proposals
[]
```
`demo-prod` confirmed clean.

## Hosts-file entry — ownership note

Unlike the run recorded earlier in this report (where this session added
and removed the entry itself), **this entry is owner-managed for the
remainder of the walkthrough**: the owner added it directly (confirmed via
`grep`, present as of this addendum) and will remove it themselves as the
final step of their own click-through, not this session. This session did
not touch `/etc/hosts` at any point during this incident's diagnosis or
fix — every check here was read-only (`grep`).

## Summary (this addendum)

| Scenario | Result |
|---|---|
| Reported symptom reproduced via log analysis (zero `/invoke` in owner's window) | Confirmed |
| Backend health check (`/invoke` direct reproduction) | PASS — proved backend was never the problem |
| `AUTO_APPROVE_IN_DEV`/OIDC-mode config sanity | PASS (all correct) |
| Root cause isolated (port-forward instructions vs. page's hardcoded default) | Confirmed, `agent/static/approver_ui.html:208` |
| Fix applied (docs-only, no image rebuild) | Done |
| Verification-script gap fixed (derive from live page, not a parallel constant) | Done |
| Full corrected smoke test | PASS (10/10 scenarios) |
| `demo-prod` clean after fix | PASS (`[]`) |
| Hosts-file entry | Present, owner-managed, not removed by this session |
