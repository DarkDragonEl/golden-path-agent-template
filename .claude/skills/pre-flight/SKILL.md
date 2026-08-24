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

**Provenance note — read before running.** This file was authored during
the `feature/workspace-tooling` mission entirely from static source
(`deploy/kustomize/`, `pipelines/bootstrap/`, `approval_service/api.py`,
`agent/config.py`, `.env.example`) with **zero cluster access** — that
mission's non-interference rules excluded `oc` entirely, since a
different session held live cluster access at the time. Every command
below is grounded in a real name found in those files, but the skill has
**never been run against a real cluster**. Two specific spots are marked
`[VERIFY ON FIRST LIVE RUN]` where the source didn't pin an exact field —
everything else is a real name, not a guess. Update this note once a
live run confirms (or corrects) the marked spots.

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
oc get pods -n golden-path-agent-keycloak
# [VERIFY ON FIRST LIVE RUN] narrow with the operator's real label, e.g.:
#   oc get pods -n golden-path-agent-keycloak -l app.kubernetes.io/managed-by=keycloak-operator
oc get keycloakrealmimport -n golden-path-agent-keycloak -o yaml
# [VERIFY ON FIRST LIVE RUN] confirm the exact status-condition field
# the Keycloak Operator's KeycloakRealmImport CRD uses (commonly a
# `status.conditions[]` entry with type Done/Started — pin the real
# jsonpath here once seen live, e.g.:
#   -o jsonpath='{.items[0].status.conditions[?(@.type=="Done")].status}'
```
**Green:** the Keycloak CR's pod(s) all `Running`/`Ready`; the realm
import's completion condition is `True`. **Red:** any pod not ready, or
the realm import still in progress / failed.

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
skill's own shell; note which path was used in the output.

### 5. Approval-service auth posture (DEC-069's property)

There is **no `/proposals/pending` route** — the real "list pending"
endpoint is `GET /proposals` (optionally `?state=pending`). Reach it via
a port-forward to the `golden-path-agent-approval` service, port `8082`
(the DEC-075-corrected local port — not `18082`):

```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://localhost:8082/proposals"
```
**Green:** HTTP `401` (unauthenticated request correctly rejected — this
is the exact property DEC-069 fixed and DEC-070 re-verified live).
**Red:** HTTP `200` — this means `AUTH_MODE` is not `oidc` in demo-prod,
i.e. the write-approval boundary is open. **This is a real finding, not
a flaky check — stop and report it, do not retry expecting a different
answer.**

### 6. No stale pending proposals in demo-prod

```bash
# Requires a bearer token (any authenticated identity — get_authenticated_caller
# does not require the approver role for GET /proposals). Obtain one the same
# way agent/oidc_client.py does: client-credentials grant against
# OIDC_ISSUER_URL using APPROVAL_OIDC_CLIENT_ID's credentials.
curl -s "http://localhost:8082/proposals?state=pending" -H "Authorization: Bearer $TOKEN" | jq 'length'
```
**Green:** `0`. **Red:** any proposal listed — debris from a prior
session (e.g. an unresolved walkthrough) that should be resolved
(reject, not silently ignored) before handing the environment to
someone new.

## Output format

```
Pre-flight: golden-path-agent-demo-prod
  [✓] 1. Session alive (oc whoami: <user>)
  [✓] 2. Deployments ready (3/3)
  [✓] 3. Keycloak ready (pod Running, realm import Done)
  [✓] 4. Model endpoint responds (200)
  [✓] 5. Approval-service auth posture (401, as expected)
  [✓] 6. No stale pending proposals (0)

Verdict: environment ready for owner handoff.
```
On any `[✗]`, stop at the first failing step and report it — don't run
later checks whose preconditions the failure already broke (e.g. don't
bother probing the model endpoint if step 1 shows no live session).
