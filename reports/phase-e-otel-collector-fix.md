# Phase E — OTel collector fix and verification

Owner reported "otel is not working" on the showcase cluster
(`golden-path-agent-demo-prod`) and asked for it to be tested and fixed.
This report captures the live investigation, the fix, and the end-to-end
verification — all commands below were actually run against the live
cluster/local stack, not inferred from static reads.

**Commit**: `a6e1625` (`fix(otel): repin traces-http sidecar off the CI
ImageStream, split mcp's OTEL_SERVICE_NAME`), pushed to `origin/main`.
**Date**: 2026-08-24/25 (UTC timestamps below are as captured live).

---

## 1. Baseline — reproducing the failure live

```
$ oc get pods -n golden-path-agent-otel -o wide
NAME                                               READY   STATUS             RESTARTS   AGE
golden-path-agent-otel-collector-6597957fb-wt2qv   1/2     ImagePullBackOff   0          17h
```

```
$ oc describe pod ... | sed -n '/Events:/,$p'
Events:
  Type     Reason   Age                    From     Message
  ----     ------   ----                   ----     -------
  Normal   BackOff  119s (x4706 over 17h)  kubelet  Back-off pulling image "image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci/golden-path-agent@sha256:d61497ead8455f537e458763ae3399fc2ae2a8564eb722399070099670a9b2a6"
  Warning  Failed   119s (x4706 over 17h)  kubelet  Error: ImagePullBackOff
```

```
$ oc get endpoints golden-path-agent-otel-collector -n golden-path-agent-otel -o yaml
subsets:
- notReadyAddresses:
  - ip: 10.234.0.84
    targetRef: {name: golden-path-agent-otel-collector-6597957fb-wt2qv, ...}
  ports: [traces-http:19999, otlp-http:4318]
```
Zero ready endpoints — `addresses` is absent, only `notReadyAddresses`. Both
containers in a pod must be `Ready` for the pod (and therefore the Service
endpoint) to count as ready; `traces-http`'s `ImagePullBackOff` was starving
the whole Service.

Confirmed the actual failure mode from inside the live `agent` pod (the
exact call `agent/telemetry.py`'s exporter makes):
```
$ oc exec -i golden-path-agent-6fc987955f-f64wg -n golden-path-agent-demo-prod -- python3 -c '...'
EXPECTED FAILURE: URLError [Errno 111] Connection refused (after 0.1s)
```

Triggered a real write request to get a session to test the query path with
(`session=118bcb92-f241-4c7d-8f6a-3aac3f242efc`,
`proposal=6303213c-309e-499b-af7a-cdf993ed847b`), then:
```
$ timeout 8 oc port-forward svc/golden-path-agent-otel-collector 8888:8888 -n golden-path-agent-otel
error: unable to forward port because pod is not running. Current status=Pending
```
The documented query path (`tools/query_traces.py` via port-forward) is
itself unreachable in the broken state — confirming the full causal chain
from root cause through to observable, real symptom. The baseline proposal
was rejected afterward to leave no stale debris (`pending after cleanup: []`).

**Root cause**: `pipelines/bootstrap/otel-collector.yaml`'s `traces-http`
sidecar (added per DEC-068, since the upstream collector image is
distroless) was pinned to a digest borrowed from this project's own
`golden-path-agent-ci/golden-path-agent` ImageStream — an ImageStream whose
whole purpose is CI churn, so it prunes old build digests over time by
design. That digest was pruned, contradicting DEC-068's own stated intent
("this digest does not need to track future promotions"). Not GitOps-managed
(`oc get applications -n openshift-gitops` lists only
`golden-path-agent-demo-prod`/`golden-path-agent-root`), so it required both
a Git fix and a manual `oc apply`.

---

## 2. Fix

**Image choice** (user decision: durable decouple, not a quick re-pin):
`registry.access.redhat.com/ubi9/python-312-minimal` — a Red Hat-published
UBI image, no auth/rate limits, zero relationship to this project's own
CI/promotion lifecycle.

```
$ skopeo inspect docker://registry.access.redhat.com/ubi9/python-312-minimal:latest
"Digest": "sha256:813ff135a87941ab1417b50c8db68a84ee40a8fc484c87f8a80458d3cafe74b1"
```

Live-tested locally with the exact sidecar command before pinning
(`podman run ... python3 -m http.server 19999 --bind 0.0.0.0 --directory /var/otel`)
— served a probe file correctly via `127.0.0.1` (an initial `curl` via
`localhost` hit the same podman IPv6-localhost quirk DEC-034 already
documents; not an issue with the image itself).

**Files changed** (`git diff --stat`):
```
PINS.md                                    |  1 +
deploy/kustomize/base/deployment-mcp.yaml  |  9 +++++++
pipelines/bootstrap/otel-collector.yaml    | 44 ++++++++++++++++++++-----------
3 files changed, 39 insertions(+), 15 deletions(-)
```
- `pipelines/bootstrap/otel-collector.yaml`: `traces-http`'s `image:` repinned
  to the UBI digest above; rationale comment rewritten to explain both the
  old failure and the new pin.
- `PINS.md`: new Phase E row for the sidecar base image (component, digest,
  source, verified date, why-decoupled note).
- `deploy/kustomize/base/deployment-mcp.yaml`: added a container-level
  `env: [{name: OTEL_SERVICE_NAME, value: golden-path-agent-mcp}]` on the
  `mcp` container (secondary fix, user-confirmed in scope) — it previously
  inherited `golden-path-agent` from the shared ConfigMap, indistinguishable
  from the agent's own spans.

Both files are outside the `Containerfile`'s `COPY` list, so per `CLAUDE.md`
workflow rule 1 this was committed directly to `main` (no feature branch),
matching established Phase C/D practice. Validated before committing:
YAML parses cleanly (`yaml.safe_load_all`) and
`oc apply --dry-run=server -f pipelines/bootstrap/otel-collector.yaml`
showed only the expected `deployment.apps/... configured` (Configmap/Service
unchanged).

```
$ git commit -m "fix(otel): repin traces-http sidecar off the CI ImageStream, split mcp's OTEL_SERVICE_NAME"
[main a6e1625] ...
$ git push origin main
   bfe9682..a6e1625  main -> main
```

**Applied live** (namespace isn't GitOps-managed):
```
$ oc apply -f pipelines/bootstrap/otel-collector.yaml
configmap/golden-path-agent-otel-collector-config unchanged
deployment.apps/golden-path-agent-otel-collector configured
service/golden-path-agent-otel-collector unchanged

$ oc rollout status deployment/golden-path-agent-otel-collector -n golden-path-agent-otel --timeout=90s
deployment "golden-path-agent-otel-collector" successfully rolled out
```

`deploy/kustomize` (the MCP fix) **is** GitOps-managed (`selfHeal: true`),
but ArgoCD hadn't picked up the new commit within this run's window, so a
refresh was forced rather than waiting out its poll interval:
```
$ oc annotate application.argoproj.io golden-path-agent-demo-prod -n openshift-gitops argocd.argoproj.io/refresh=hard --overwrite
$ oc get application.argoproj.io golden-path-agent-demo-prod -n openshift-gitops -o jsonpath='{.status.sync.status}  {.status.sync.revision}'
Synced  a6e162527d813caecc0bd76359bf9140e70dd2e3
```

---

## 3. Post-fix verification

**Collector pod/Service healthy**:
```
$ oc get pods -n golden-path-agent-otel
golden-path-agent-otel-collector-8ff68c4fd-kv7d9   2/2   Running   0   21s

$ oc get endpoints golden-path-agent-otel-collector -n golden-path-agent-otel -o yaml
subsets:
- addresses:            # <-- was notReadyAddresses before
  - ip: 10.233.0.204
    targetRef: {name: golden-path-agent-otel-collector-8ff68c4fd-kv7d9, ...}
```
Both containers' logs clean (`otel-collector`: "Everything is ready. Begin
running and processing data."; `traces-http`: "Serving HTTP on 0.0.0.0 port
19999 ...").

**MCP service-name fix landed**:
```
$ oc get pod -n golden-path-agent-demo-prod -l app.kubernetes.io/component=mcp -o jsonpath='{.items[0].spec.containers[0].env}'
[{"name": "OTEL_SERVICE_NAME", "value": "golden-path-agent-mcp"}]
```

**OTLP export path reachable** (same call as the baseline, now succeeds):
```
CONNECTED (HTTP error expected for a garbage body): 415 Unsupported Media Type
```

**Real end-to-end write → approve → resume flow**, driven from inside the
`agent` pod via the same `directAccessGrantsEnabled` shortcut D2 already
established for non-browser verification
(`golden-path-agent-approver-ui` client):
```
session_id: de3c13f8-f042-4f13-b30a-67a09caba458
proposal_id: f6913f03-d9f3-4978-8cd8-43d6dda614e4
decision: {"state": "approved", "decided_by": "675e324e-7b07-43d6-80f2-9088b91bff7a", ...}
resume result: final_output = "Request REQ-30100 has been submitted (status: submitted)."
```

**Trace query — the actual proof, not just plumbing health**
(`tools/query_traces.py --session-id ... / --proposal-id ...` via
`oc port-forward svc/golden-path-agent-otel-collector 8888:8888`):

```
[..87.987] golden-path-agent           span  agent.invoke              request.id=8d75e26f-... model.route=primary model.route_reason_code=none tool_calls.count=1 approval.decision=None
[..90.886] golden-path-agent-approval  span  approval.create_proposal  request.id=8d75e26f-... approval.event=proposal_intake approval.state=pending
[..90.917] golden-path-agent           event model_call                model_call.route=primary model_call.reason_code=none ...
[..90.917] golden-path-agent           event tool_call                 tool_call.tool_name=itsm_create_request tool_call.classification=write
[..01.316] golden-path-agent-approval  span  approval.decide_proposal  approval.event=proposal_decided approval.state=approved approval.decided_by=675e324e-...
[..01.340] golden-path-agent           span  agent.resume              tool_calls.count=2 approval.decision=approved final_output.preview=Request REQ-30100 has been submitted (status: submitted).
[..01.748] golden-path-agent           event tool_call                 tool_call.tool_name=itsm_create_request tool_call.classification=write tool_call.error=None
```

Confirms, per `SysR-P-IF-06`/`SysR-A-TEL-01`: spans/events from **both**
`golden-path-agent` and `golden-path-agent-approval`, correlated purely by
`request.id`/session/proposal attribute values (DEC-071's mechanism — no
shared trace ID across the async approval gap), with
`model_call.route`/`reason_code`, `tool_call.tool_name`/`classification`,
and `approval.decision` all present and correct.

**`/pre-flight` re-run, all 6 checks green** post-fix (session alive;
3/3 deployments ready; Keycloak ready; model endpoint 200; approval-service
401 as expected; no stale pending proposals).

---

## 4. Independent local-stack sanity pass

Never previously live-verified (only structurally read) — `make up-offline`
(deterministic, `AGENT_MODEL_MODE=fake`/`MCP_MODE=mock`, no live model
calls needed for an OTel check):

```
$ curl -sX POST http://localhost:18080/invoke -d '{"query": "...", "user_id": "otel-local-verify"}'
{"session_id": "0d8bf07c-c086-44d1-8b31-ccd9fa7a5c18", ...}

$ podman logs golden-path-otel-collector-dev | grep -A20 0d8bf07c-...
Attributes:
     -> session.id: Str(0d8bf07c-c086-44d1-8b31-ccd9fa7a5c18)
     -> request.id: Str(01c75b71-5b64-43aa-b647-71ada66830ec)
     ...
Events: SpanEvent #0 -> Name: model_call
```
Span appears in the local collector's own stdout with the matching
`session.id` — the local dev OTel path (`scripts/dev.sh`,
`deploy/otel/otel-collector-config.yaml`) is genuinely live, not just
structurally correct. `make down` afterward — stack torn down cleanly
(no leftover containers, network removed).

---

## Summary

| | Before | After |
|---|---|---|
| Collector pod | `1/2 ImagePullBackOff` | `2/2 Running` |
| Service endpoints | `notReadyAddresses` (0 ready) | `addresses` (1 ready) |
| OTLP export from agent pod | connection refused | connects (415 on a garbage test body — real protobuf traffic already flowing, per the trace query above) |
| Trace query path | port-forward fails (`pod is not running`) | full cross-service trace returned |
| MCP service name | shared `golden-path-agent` with agent | own `golden-path-agent-mcp` |
| Local dev OTel path | never live-verified | live-verified, span confirmed |

Nothing left open from this fix — the new sidecar pin has no relationship
to this project's own CI/promotion lifecycle, so the specific failure class
that broke it (CI ImageStream pruning) cannot recur.
