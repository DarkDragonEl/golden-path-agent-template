---
name: pre-flight
description: Verify the golden-path-agent demo-prod cluster environment (deployments, Keycloak, model endpoint, approval-service auth posture, stale proposal debris) is healthy before handing it to a human for a live walkthrough, demo, or Checkpoint sign-off. Use before any owner-facing session that depends on the cluster, or any time "is the environment ready" needs a real answer instead of a guess.
allowed-tools:
  - Bash(oc *)
  - Bash(curl *)
  - Bash(base64 *)
  - Read
---

# /pre-flight — demo-prod environment readiness check

**Classification: read-only.** Every check below is a `get`/`whoami`/GET
request. Nothing here creates, patches, or deletes a cluster resource,
approves/rejects a proposal, or writes to any service. Per this
project's governance rule (read-only work runs automatically; anything
state-changing requires explicit human invocation), this skill is safe
to auto-invoke.

**Provenance note.** Written from static source during
`feature/workspace-tooling`'s build phase, then **live-tested in full
against real `golden-path-agent-demo-prod`/`golden-path-agent-keycloak`**
during that same mission's release phase, once the parallel Checkpoint-D
session had finished. All 6 checks passed on the first live run after
one fix (see check 6's port note below); the two previously-uncertain
spots (Keycloak pod label, `KeycloakRealmImport` status field) are now
pinned to real confirmed values.

## Checks, in order

Never run `oc project <ns>` — it mutates the current kubeconfig context.
Every command below passes `-n <namespace>` explicitly instead, so this
skill never changes what namespace a later `oc` command in the same
shell would default to.

### 1. Session alive

```bash
oc whoami
oc project -q   # report-only — shows current context, does not switch it
```
**Green:** `oc whoami` prints a username. **Red:** an auth error — stop
here, nothing else in this skill can succeed without a live session.

### 2. Deployments ready (`golden-path-agent-demo-prod`)

```bash
oc get deployment golden-path-agent golden-path-agent-mcp golden-path-agent-approval \
  -n golden-path-agent-demo-prod \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.readyReplicas}{"/"}{.status.replicas}{"\n"}{end}'
```
**Green:** all three deployments print `readyReplicas == replicas`, both
`>= 1`. **Red:** any deployment missing, `readyReplicas` blank/0, or
mismatched counts. (There is no separate retrieval/vector-store
deployment — retrieval runs in-process inside `golden-path-agent`; do
not expect a fourth deployment here.)

### 3. Keycloak ready (`golden-path-agent-keycloak`)

```bash
oc get pods -n golden-path-agent-keycloak -l app.kubernetes.io/managed-by=keycloak-operator
# confirmed live: returns the Keycloak StatefulSet pod (golden-path-agent-0)
# plus a Completed realm-import job pod -- Completed/0-of-1-ready on that
# second one is normal for a finished Job, not a failure.

oc get keycloakrealmimport -n golden-path-agent-keycloak \
  -o jsonpath='{.items[0].status.conditions[?(@.type=="Done")].status}{"\n"}{.items[0].status.conditions[?(@.type=="HasErrors")].status}{"\n"}'
# confirmed live shape: three named conditions, Done/Started/HasErrors,
# each {status: "True"|"False", type, message}.
```
**Green:** the StatefulSet pod `Running`/`1/1`; `Done` = `"True"` and
`HasErrors` = `"False"`. **Red:** pod not ready, `Done` != `"True"`, or
`HasErrors` = `"True"`.

### 4. Model endpoint (MaaS) responds

Real values live in Secret `golden-path-agent-secrets` in
`golden-path-agent-demo-prod` (**not** the ConfigMap — the demo-prod
overlay deliberately keeps `MODEL_API_BASE_URL`/`MODEL_NAME`/
`MODEL_API_KEY` out of the ConfigMap):

```bash
BASE_URL=$(oc get secret golden-path-agent-secrets -n golden-path-agent-demo-prod -o jsonpath='{.data.MODEL_API_BASE_URL}' | base64 -d)
MODEL=$(oc get secret golden-path-agent-secrets -n golden-path-agent-demo-prod -o jsonpath='{.data.MODEL_NAME}' | base64 -d)
API_KEY=$(oc get secret golden-path-agent-secrets -n golden-path-agent-demo-prod -o jsonpath='{.data.MODEL_API_KEY}' | base64 -d)
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}],\"max_tokens\":1}"
```
**Green:** HTTP `200`. **Red:** any non-200, or curl can't reach
`$BASE_URL` at all — if the MaaS endpoint isn't directly reachable from
wherever this skill runs (only reachable in-cluster), rerun the same
curl via `oc exec` into the `golden-path-agent` pod instead of from the
skill's own shell; note which path was used in the output. Confirmed
live: directly reachable from outside the cluster (no `oc exec` needed)
— `200` against the real endpoint.

### 5. Approval-service auth posture (DEC-069's property)

There is **no `/proposals/pending` route** — the real "list pending"
endpoint is `GET /proposals` (optionally `?state=pending`). Reach it via
a port-forward to the `golden-path-agent-approval` service — any free
local port works here (confirmed live; unlike check 6, this call
carries no bearer token and so has no issuer/port to match, e.g. `8082`
is just a conventional suggestion, not a requirement):

```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:8082/proposals"
```
**Green:** HTTP `401` (unauthenticated request correctly rejected — this
is the exact property DEC-069 fixed and DEC-070 re-verified live;
confirmed again live during this skill's own release-phase testing).
**Red:** HTTP `200` — this means `AUTH_MODE` is not `oidc` in demo-prod,
i.e. the write-approval boundary is open. **This is a real finding, not
a flaky check — stop and report it, do not retry expecting a different
answer.**

### 6. No stale pending proposals in demo-prod

Needs a bearer token. `get_authenticated_caller` doesn't require the
approver role for `GET /proposals`, so any authenticated identity works
— get one via client-credentials against Keycloak, same mechanism
`agent/oidc_client.py` uses:

```bash
oc port-forward svc/golden-path-agent-service 8080:8080 -n golden-path-agent-keycloak &
CLIENT_SECRET=$(oc get secret golden-path-agent-secrets -n golden-path-agent-demo-prod -o jsonpath='{.data.APPROVAL_OIDC_CLIENT_SECRET}' | base64 -d)
TOKEN=$(curl -s -X POST "http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/golden-path-agent/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=golden-path-agent-approval-workload&client_secret=$CLIENT_SECRET" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
curl -s "http://localhost:8082/proposals?state=pending" -H "Authorization: Bearer $TOKEN"
```

**Real finding, confirmed live — the Keycloak port-forward's local port
must be exactly `8080`, not an arbitrary free port.** Keycloak stamps
the token's `iss` claim from the request's own `Host` header (hostname
*and* port), and `approval_service` validates `iss` against its
configured `OIDC_ISSUER_URL`
(`http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/golden-path-agent`)
byte-for-byte. Forwarding to a different local port (tried `38080`
first, to stay clear of the owner's own port-forwards on `8080`)
produces a token with `:38080` baked into `iss` and a hard `401 invalid
token: Invalid issuer` from `approval_service` — confirmed by decoding
the token and comparing against the ConfigMap's real value. The
hostname must also already resolve to `127.0.0.1` (a one-line
`/etc/hosts` entry — `docs/owner-walkthrough.md` documents adding this;
this check assumes it's already present, e.g. left over from a prior
walkthrough, and does not add or remove it itself). The
`approval-service` side has **no equivalent port constraint** — it
never validates its own URL against anything, so forwarding it to any
free local port works (confirmed live on `38082`, not the conventional
`8082`); only the Keycloak forward is picky, because it's the value
baked into the token, not just an address you happen to be curling.

**Green:** `[]` (empty array). **Red:** any proposal listed — debris
from a prior session (e.g. an unresolved walkthrough) that should be
resolved (reject, not silently ignored) before handing the environment
to someone new.

Clean up both port-forwards (`kill %1 %2` or by PID) when done — they're
this check's own scaffolding, not something to leave running.

## Output format

```
Pre-flight: golden-path-agent-demo-prod
  [✓] 1. Session alive (oc whoami: darkdragonel, project: golden-path-agent-demo-prod)
  [✓] 2. Deployments ready (3/3 -- agent, mcp, approval all 1/1)
  [✓] 3. Keycloak ready (golden-path-agent-0 Running 1/1; realm import Done=True, HasErrors=False)
  [✓] 4. Model endpoint responds (200, model-endpoint.example.com)
  [✓] 5. Approval-service auth posture (401, as expected)
  [✓] 6. No stale pending proposals ([])

Verdict: environment ready for owner handoff.
```
(this is real captured output from a live run against
`golden-path-agent-demo-prod` during `feature/workspace-tooling`'s
release phase, not a hypothetical example)

On any `[✗]`, stop at the first failing step and report it — don't run
later checks whose preconditions the failure already broke (e.g. don't
bother probing the model endpoint if step 1 shows no live session).
