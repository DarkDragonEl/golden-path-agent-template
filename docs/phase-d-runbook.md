# Phase D runbook — manual bootstrap steps

Same discipline as `docs/phase-c-runbook.md`: every step here is a
deliberate manual action, done once by a human operator with cluster
access, never by the Tekton pipeline itself (its `ServiceAccount` has no
cluster-scoped grants at all, `DEC-024`).

## 1. D2 entry gate — Keycloak namespace + operator + database (held for
owner ack before applying, `DEC-053`)

```sh
# 1. Namespace (cluster-scoped action -- flagged per the owner's own
#    kickoff instruction, same category as the three existing namespaces).
oc apply -f pipelines/bootstrap/namespaces.yaml

# 2. rhbk-operator -- the one flagged cluster-scoped step in the whole
#    Phase D plan (CRD registration). OperatorGroup/Subscription
#    themselves are namespace-scoped.
oc apply -f pipelines/bootstrap/keycloak-operator.yaml

# Wait for the CSV to succeed before anything depends on the CRDs it registers:
oc get csv -n golden-path-agent-keycloak -w
# expect: rhbk-operator.v26.6.6-opr.1   Succeeded

# 3. Keycloak's own database credential -- a plain Secret, manually
#    provisioned, never committed (same pattern as golden-path-agent-secrets,
#    docs/phase-c-runbook.md Sec.2).
oc create secret generic golden-path-agent-keycloak-db-secret \
  -n golden-path-agent-keycloak \
  --from-literal=POSTGRESQL_USER=keycloak \
  --from-literal=POSTGRESQL_PASSWORD='<generate a real value, never this placeholder>' \
  --from-literal=POSTGRESQL_DATABASE=keycloak

# 4. Postgres (plain Deployment+PVC, no new operator -- PINS.md).
oc apply -f pipelines/bootstrap/keycloak-postgres.yaml
oc rollout status deployment/golden-path-agent-keycloak-db -n golden-path-agent-keycloak
```

Verify RBAC/blast-radius the same way every prior bootstrap step in this
project has (`docs/phase-c-runbook.md` §1's own pattern) — don't assume
from the YAML alone:

```sh
oc auth can-i create namespace --as=system:serviceaccount:golden-path-agent-ci:golden-path-agent-ci-pipeline
# expect: no -- the pipeline's own ServiceAccount never gains cluster-scoped
# permissions just because a human operator used one here.
```

**Not yet part of this section**: the `Keycloak` CR itself and the
`KeycloakRealmImport` -- those are D2 *implementation*, gated behind the
D2 design STOP (`DECISIONS.md`, realm/client shape review), not this
entry gate. Added to this runbook once implementation is authorized.

## D3: reaching the approver UI locally

This milestone has no working external `Ingress` route yet (already
documented as a known limitation elsewhere in this project). A human
operator walking through `agent/static/approver_ui.html` (served at
`GET /ui`) needs **two separate** `oc port-forward` sessions running at
once, since the page talks to the agent and the approval-service as two
different origins by design (direct-to-service, not proxied through the
agent):

```sh
# Terminal 1 -- the agent (serves the UI itself, and /invoke + /resume):
oc port-forward svc/golden-path-agent 18080:8080 -n <ns>
# then open http://localhost:18080/ui

# Terminal 2 -- the approval-service (the UI's polling/decision calls):
oc port-forward svc/golden-path-agent-approval 18082:8082 -n <ns>
```

The page's default `APPROVAL_SERVICE_ORIGIN` (`http://localhost:8082`)
already matches Terminal 2's conventional port above, so no per-page
edit is needed for that default layout; if a different local port is
forwarded instead, set `window.APPROVAL_SERVICE_ORIGIN` before the
page's own script runs (see the comment in `approver_ui.html` itself).
