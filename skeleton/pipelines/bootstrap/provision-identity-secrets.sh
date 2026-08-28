#!/usr/bin/env bash
# Scripted, committed, idempotent secret-provisioning mechanism:
# scripted provisioning, committed mechanism, never-committed values.
#
# WHAT THIS SIMULATES, STATED FOR THE WALKTHROUGH: in a real enterprise
# deployment, an ESO (external-secrets.io)/Vault integration -- already
# pinned as this project's own deferred phase-two integration point
# (PINS.md, docs/security-identity.md) -- would pull these same
# credentials from a real secrets manager and sync them into Kubernetes
# Secrets automatically, continuously. This script is the demo-scale
# realization of that exact interface: it plays the role a real
# ESO/Vault sync would play, materializing real, working credentials
# from "Git + one bootstrap command" instead of a managed integration
# this MVP's scope does not build. Not a shortcut being hidden -- this
# sentence is walkthrough material.
#
# IDEMPOTENT BY DESIGN, NOT BY DETECTION: every run regenerates fresh
# values for everything it manages -- there is no "only if missing"
# branch. This makes "rotate an existing environment" and "provision a
# fresh one" the exact same code path, rather than two behaviors to
# keep in sync by hand.
#
# VALUES NEVER IN GIT, MECHANISM ALWAYS IN GIT: every secret value below
# is generated or fetched at runtime, inside this script or inside a
# pod via `oc exec` (see WHY below), and flows only through shell
# variables and K8s Secret objects -- never echoed, never printed, never
# written to a file, no `set -x` anywhere in this script (would dump
# variable values, including these, to stderr).
#
# WHY `oc exec` FOR THE KEYCLOAK ADMIN-API CALLS: this script runs on an
# operator's own machine, outside the cluster network -- it cannot reach
# Keycloak's internal Service DNS directly, and there is no working
# external Ingress route (same limitation as every other Ingress in
# this project). Uses `oc exec -i <pod> -- python3 -`, targeting the
# Postgres pod already guaranteed to exist in
# ${{ values.name }}-keycloak -- no new pod spun up, no dependency on
# the agent already being deployed.
#
# Requires: oc (logged in, correct cluster context), python3 available
# locally is NOT required -- only inside the exec'd pod, which already
# has it.
set -euo pipefail

NS_KEYCLOAK=${{ values.name }}-keycloak
REALM=${{ values.name }}
CONSUMER_NAMESPACES=(${{ values.name }}-ephemeral-test ${{ values.name }}-demo-prod)

PG_POD=$(oc get pod -n "$NS_KEYCLOAK" -l app.kubernetes.io/name=${{ values.name }}-keycloak-db -o jsonpath='{.items[0].metadata.name}')

ADMIN_USER=$(oc get secret ${{ values.name }}-keycloak-admin -n "$NS_KEYCLOAK" -o jsonpath='{.data.username}' | base64 -d)
ADMIN_PASS=$(oc get secret ${{ values.name }}-keycloak-admin -n "$NS_KEYCLOAK" -o jsonpath='{.data.password}' | base64 -d)

# --- Step 1: regenerate the two workload clients' secrets -----------------
# Always regenerate via Keycloak's own admin-API "regenerate client
# secret" endpoint (POST .../client-secret) -- chosen over the
# KeycloakRealmImport CRD's spec.placeholders import-time substitution
# mechanism specifically because this ONE call works identically whether
# the client was created two seconds ago or two months ago: one code
# path for both a fresh environment and rotation, not two mechanisms to
# keep in sync.
read -r APPROVAL_SECRET MCP_SECRET <<EOF
$(oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = "http://${{ values.name }}-service:8080"

def token(client_id, extra):
    body = {"grant_type": "password", "client_id": client_id, **extra}
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(f"{BASE}/realms/master/protocol/openid-connect/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["access_token"]

access_token = token("admin-cli", {"username": admin_user, "password": admin_pass})

def admin(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}/admin{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r) if r.length != 0 else None

def client_uuid(client_id):
    matches = admin("GET", f"/realms/{realm}/clients?clientId={urllib.parse.quote(client_id)}")
    return matches[0]["id"]

def regenerate_secret(client_id):
    uuid = client_uuid(client_id)
    result = admin("POST", f"/realms/{realm}/clients/{uuid}/client-secret")
    return result["value"]

approval_secret = regenerate_secret("${{ values.name }}-approval-workload")
mcp_secret = regenerate_secret("${{ values.name }}-mcp-workload")
print(approval_secret, mcp_secret)
PYEOF
)
EOF

# --- Step 2: write the two client secrets into every consuming namespace --
# ${{ values.name }}-secrets already exists in each of these namespaces
# (docs/phase-c-runbook.md Sec.2) with MODEL_API_KEY/MCP_AUTH_TOKEN
# keys -- `oc patch --type merge` on .data only touches the keys listed
# below, leaving those alone. If the Secret does not exist yet in a given
# namespace (a genuinely fresh environment, this bootstrap step run before
# that one), create it fresh with just these keys instead.
B64_APPROVAL=$(printf '%s' "$APPROVAL_SECRET" | base64 -w0)
B64_MCP=$(printf '%s' "$MCP_SECRET" | base64 -w0)
for ns in "${CONSUMER_NAMESPACES[@]}"; do
  if oc get secret ${{ values.name }}-secrets -n "$ns" >/dev/null 2>&1; then
    oc patch secret ${{ values.name }}-secrets -n "$ns" --type merge \
      -p "{\"data\":{\"APPROVAL_OIDC_CLIENT_SECRET\":\"${B64_APPROVAL}\",\"MCP_AUTH_TOKEN\":\"${B64_MCP}\"}}" >/dev/null
  else
    oc create secret generic ${{ values.name }}-secrets -n "$ns" \
      --from-literal=APPROVAL_OIDC_CLIENT_SECRET="$APPROVAL_SECRET" \
      --from-literal=MCP_AUTH_TOKEN="$MCP_SECRET" >/dev/null
  fi
  echo "provisioned workload client secrets in ${ns}/${{ values.name }}-secrets"
done
unset APPROVAL_SECRET MCP_SECRET B64_APPROVAL B64_MCP

# --- Step 3: demo users' passwords -----------------------------------------
# Same rules as the client secrets above: generated fresh every run, set
# via the admin API's reset-password endpoint, never echoed. Stored as
# their own K8s Secret (not ${{ values.name }}-secrets -- these are
# walkthrough-operator-retrieved credentials for a human to actually log
# in with, a different consumer than the workload pods' envFrom).
DEMO_APPROVER_PASS=$(openssl rand -base64 18)
DEMO_USER_PASS=$(openssl rand -base64 18)

oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" "$DEMO_APPROVER_PASS" "$DEMO_USER_PASS" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm, approver_pass, user_pass = sys.argv[1:6]
BASE = "http://${{ values.name }}-service:8080"

def token(client_id, extra):
    body = {"grant_type": "password", "client_id": client_id, **extra}
    data = urllib.parse.urlencode(body).encode()
    req = urllib.request.Request(f"{BASE}/realms/master/protocol/openid-connect/token", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["access_token"]

access_token = token("admin-cli", {"username": admin_user, "password": admin_pass})

def admin(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}/admin{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r) if r.length != 0 else None

def user_id(username):
    matches = admin("GET", f"/realms/{realm}/users?username={urllib.parse.quote(username)}&exact=true")
    return matches[0]["id"]

def set_password(username, password):
    uid = user_id(username)
    admin("PUT", f"/realms/{realm}/users/{uid}/reset-password",
          {"type": "password", "value": password, "temporary": False})

set_password("demo-approver", approver_pass)
set_password("demo-user", user_pass)
print("demo user passwords set")
PYEOF

if oc get secret ${{ values.name }}-demo-users -n "$NS_KEYCLOAK" >/dev/null 2>&1; then
  oc patch secret ${{ values.name }}-demo-users -n "$NS_KEYCLOAK" --type merge \
    -p "{\"data\":{\"demo-approver-password\":\"$(printf '%s' "$DEMO_APPROVER_PASS" | base64 -w0)\",\"demo-user-password\":\"$(printf '%s' "$DEMO_USER_PASS" | base64 -w0)\"}}" >/dev/null
else
  oc create secret generic ${{ values.name }}-demo-users -n "$NS_KEYCLOAK" \
    --from-literal=demo-approver-password="$DEMO_APPROVER_PASS" \
    --from-literal=demo-user-password="$DEMO_USER_PASS" >/dev/null
fi
unset DEMO_APPROVER_PASS DEMO_USER_PASS
echo "provisioned demo user passwords in ${NS_KEYCLOAK}/${{ values.name }}-demo-users"
echo "(retrieve for a live walkthrough with: oc get secret ${{ values.name }}-demo-users -n ${NS_KEYCLOAK} -o jsonpath='{.data.demo-approver-password}' | base64 -d)"

echo "provision-identity-secrets.sh: done."
