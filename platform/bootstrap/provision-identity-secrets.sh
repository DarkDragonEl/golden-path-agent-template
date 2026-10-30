#!/usr/bin/env bash
# DEC-059: scripted, committed, idempotent secret-provisioning
# mechanism -- the owner's own explicit directive: "scripted
# provisioning, committed mechanism, never-committed values."
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
# fresh one" the exact same code path (what Phase E's showcase-cluster
# replay will run) rather than two behaviors to keep in sync by hand.
#
# VALUES NEVER IN GIT, MECHANISM ALWAYS IN GIT: every secret value below
# is generated or fetched at runtime, inside this script or inside a
# pod via `oc exec` (see WHY below), and flows only through shell
# variables and K8s Secret objects -- never echoed, never printed, never
# written to a file, no `set -x` anywhere in this script (would dump
# variable values, including these, to stderr).
#
# WHY `oc exec`: this script runs outside the cluster network and
# cannot reach Keycloak's internal Service DNS directly, and (DEC-057)
# no external Ingress route exists yet. Reuses the DEC-034/DEC-052
# pattern: `oc exec -i <pod> -- python3 -` against the Postgres pod
# already guaranteed to exist by the DEC-057 entry gate.
#
# Requires: oc only -- python3 is needed inside the exec'd pod, not
# locally (confirmed DEC-057).
set -euo pipefail

NS_KEYCLOAK=golden-path-agent-keycloak
REALM=golden-path-agent
CONSUMER_NAMESPACES=(golden-path-agent-ephemeral-test golden-path-agent-demo-prod)

PG_POD=$(oc get pod -n "$NS_KEYCLOAK" -l app.kubernetes.io/name=golden-path-agent-keycloak-db -o jsonpath='{.items[0].metadata.name}')

ADMIN_USER=$(oc get secret golden-path-agent-keycloak-admin -n "$NS_KEYCLOAK" -o jsonpath='{.data.username}' | base64 -d)
ADMIN_PASS=$(oc get secret golden-path-agent-keycloak-admin -n "$NS_KEYCLOAK" -o jsonpath='{.data.password}' | base64 -d)

# --- Step 1: regenerate the two workload clients' secrets -----------------
# DEC-058: always regenerate via Keycloak's admin-API "regenerate client
# secret" endpoint, not the CRD's spec.placeholders mechanism -- one
# code path for both a fresh environment and rotation.
#
# DEC-080 (latent bug, fixed): captured into a plain assignment first,
# never substituted straight into a `read <<EOF` heredoc -- a command
# substitution inside a heredoc body discards its exit status, so set -e
# never saw a failed `oc exec` and step 2 wrote two empty secrets into
# every consumer namespace. A plain `VAR=$(...)` does propagate it.
CLIENT_SECRETS=$(oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = "http://golden-path-agent-service:8080"

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

approval_secret = regenerate_secret("golden-path-agent-approval-workload")
mcp_secret = regenerate_secret("golden-path-agent-mcp-workload")
print(approval_secret, mcp_secret)
PYEOF
)
read -r APPROVAL_SECRET MCP_SECRET <<<"$CLIENT_SECRETS"
unset CLIENT_SECRETS
if [ -z "$APPROVAL_SECRET" ] || [ -z "$MCP_SECRET" ]; then
  echo "[provision-identity-secrets.sh] FAILED to regenerate workload client secrets (empty result) -- not writing empty values" >&2
  exit 1
fi

# --- Step 2: write the two client secrets + model-endpoint config into
# every consuming namespace -- golden-path-agent-secrets. `oc patch
# --type merge` on .data only touches the keys listed below, leaving any
# others alone. If the Secret does not exist yet in a given namespace (a
# genuinely fresh environment), create it fresh with all these keys
# instead.
#
# DEC-138: MODEL_API_KEY/MODEL_*_URL/MODEL_*_NAME come from bootstrap.env
# (validated and exported by scripts/bootstrap.sh's own step 0) --
# regenerated into this Secret every run, same discipline as
# APPROVAL_OIDC_CLIENT_SECRET/MCP_AUTH_TOKEN below, replacing what used
# to be a manually-created "Copy 3" (docs/phase-c-runbook.md, formerly
# S2).
B64_APPROVAL=$(printf '%s' "$APPROVAL_SECRET" | base64 -w0)
B64_MCP=$(printf '%s' "$MCP_SECRET" | base64 -w0)
B64_MODEL_API_KEY=$(printf '%s' "$MODEL_API_KEY" | base64 -w0)
B64_MODEL_API_BASE_URL=$(printf '%s' "$MODEL_API_BASE_URL" | base64 -w0)
B64_MODEL_NAME=$(printf '%s' "$MODEL_NAME" | base64 -w0)
B64_MODEL_FALLBACK_API_BASE_URL=$(printf '%s' "$MODEL_FALLBACK_API_BASE_URL" | base64 -w0)
B64_MODEL_FALLBACK_NAME=$(printf '%s' "$MODEL_FALLBACK_NAME" | base64 -w0)
for ns in "${CONSUMER_NAMESPACES[@]}"; do
  if oc get secret golden-path-agent-secrets -n "$ns" >/dev/null 2>&1; then
    oc patch secret golden-path-agent-secrets -n "$ns" --type merge \
      -p "{\"data\":{\"APPROVAL_OIDC_CLIENT_SECRET\":\"${B64_APPROVAL}\",\"MCP_AUTH_TOKEN\":\"${B64_MCP}\",\"MODEL_API_KEY\":\"${B64_MODEL_API_KEY}\",\"MODEL_API_BASE_URL\":\"${B64_MODEL_API_BASE_URL}\",\"MODEL_NAME\":\"${B64_MODEL_NAME}\",\"MODEL_FALLBACK_API_BASE_URL\":\"${B64_MODEL_FALLBACK_API_BASE_URL}\",\"MODEL_FALLBACK_NAME\":\"${B64_MODEL_FALLBACK_NAME}\"}}" >/dev/null
  else
    oc create secret generic golden-path-agent-secrets -n "$ns" \
      --from-literal=APPROVAL_OIDC_CLIENT_SECRET="$APPROVAL_SECRET" \
      --from-literal=MCP_AUTH_TOKEN="$MCP_SECRET" \
      --from-literal=MODEL_API_KEY="$MODEL_API_KEY" \
      --from-literal=MODEL_API_BASE_URL="$MODEL_API_BASE_URL" \
      --from-literal=MODEL_NAME="$MODEL_NAME" \
      --from-literal=MODEL_FALLBACK_API_BASE_URL="$MODEL_FALLBACK_API_BASE_URL" \
      --from-literal=MODEL_FALLBACK_NAME="$MODEL_FALLBACK_NAME" >/dev/null
  fi
  echo "provisioned workload client secrets + model-endpoint config in ${ns}/golden-path-agent-secrets"
done
unset B64_MODEL_API_KEY B64_MODEL_API_BASE_URL B64_MODEL_NAME B64_MODEL_FALLBACK_API_BASE_URL B64_MODEL_FALLBACK_NAME
unset APPROVAL_SECRET MCP_SECRET B64_APPROVAL B64_MCP

# --- Step 3: demo users' passwords -----------------------------------------
# Same rules as the client secrets above: generated fresh every run, set
# via the admin API's reset-password endpoint, never echoed. Stored as
# their own K8s Secret (not golden-path-agent-secrets -- these are
# walkthrough-operator-retrieved credentials for a human to actually log
# in with, a different consumer than the workload pods' envFrom).
DEMO_APPROVER_PASS=$(openssl rand -base64 18)
DEMO_USER_PASS=$(openssl rand -base64 18)

oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" "$DEMO_APPROVER_PASS" "$DEMO_USER_PASS" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm, approver_pass, user_pass = sys.argv[1:6]
BASE = "http://golden-path-agent-service:8080"

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

if oc get secret golden-path-agent-demo-users -n "$NS_KEYCLOAK" >/dev/null 2>&1; then
  oc patch secret golden-path-agent-demo-users -n "$NS_KEYCLOAK" --type merge \
    -p "{\"data\":{\"demo-approver-password\":\"$(printf '%s' "$DEMO_APPROVER_PASS" | base64 -w0)\",\"demo-user-password\":\"$(printf '%s' "$DEMO_USER_PASS" | base64 -w0)\"}}" >/dev/null
else
  oc create secret generic golden-path-agent-demo-users -n "$NS_KEYCLOAK" \
    --from-literal=demo-approver-password="$DEMO_APPROVER_PASS" \
    --from-literal=demo-user-password="$DEMO_USER_PASS" >/dev/null
fi
unset DEMO_APPROVER_PASS DEMO_USER_PASS
echo "provisioned demo user passwords in ${NS_KEYCLOAK}/golden-path-agent-demo-users"
echo "(retrieve for a live walkthrough with: oc get secret golden-path-agent-demo-users -n ${NS_KEYCLOAK} -o jsonpath='{.data.demo-approver-password}' | base64 -d)"

# --- Step 4: RHDH's own OIDC client (DEC-092) ------
# DEC-092: KeycloakRealmImport is a one-shot Job-based import --
# re-applying the CR with a client added does NOT create it once
# Done=True. Fresh environments get it via keycloak-realm-import.yaml
# directly; an already-provisioned realm needs this create-if-missing
# step instead.
NS_RHDH=golden-path-agent-rhdh

RHDH_CLIENT_EXISTS=$(oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = "http://golden-path-agent-service:8080"

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

matches = admin("GET", f"/realms/{realm}/clients?clientId=golden-path-agent-rhdh")
if not matches:
    admin("POST", f"/realms/{realm}/clients", {
        "clientId": "golden-path-agent-rhdh",
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "redirectUris": ["*"],
        "webOrigins": ["*"],
    })
print("done")
PYEOF
)
[ "$RHDH_CLIENT_EXISTS" = "done" ] || { echo "[provision-identity-secrets.sh] FAILED to ensure golden-path-agent-rhdh client exists" >&2; exit 1; }

RHDH_OIDC_SECRET=$(oc exec -i -n "$NS_KEYCLOAK" "$PG_POD" -- python3 - "$ADMIN_USER" "$ADMIN_PASS" "$REALM" <<'PYEOF'
import json, sys, urllib.request, urllib.parse

admin_user, admin_pass, realm = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = "http://golden-path-agent-service:8080"

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

matches = admin("GET", f"/realms/{realm}/clients?clientId=golden-path-agent-rhdh")
uuid = matches[0]["id"]
secret_result = admin("POST", f"/realms/{realm}/clients/{uuid}/client-secret")
print(secret_result["value"], end="")
PYEOF
)
# DEC-147 (M12/M13): with RHDH, its public URL and the browser-reachable
# Keycloak discovery URL come from the two Routes scripts/bootstrap.sh
# created at step 4b (hosts passed in as RHDH_HOST/KEYCLOAK_HOST) and are
# rewritten every run -- never committed, never typed in by hand.
OIDC_URL_DATA=""
if [ "${WITH_RHDH:-false}" = "true" ]; then
  if [ -z "${RHDH_HOST:-}" ] || [ -z "${KEYCLOAK_HOST:-}" ]; then
    echo "[provision-identity-secrets.sh] FAILED: WITH_RHDH=true needs RHDH_HOST and KEYCLOAK_HOST (scripts/bootstrap.sh step 4b passes both)" >&2
    exit 1
  fi
  RHDH_PUBLIC_URL="https://${RHDH_HOST}"
  RHDH_OIDC_METADATA_URL="https://${KEYCLOAK_HOST}/realms/${REALM}/.well-known/openid-configuration"
  OIDC_URL_DATA=",\"PUBLIC_URL\":\"$(printf '%s' "$RHDH_PUBLIC_URL" | base64 -w0)\",\"OIDC_METADATA_URL\":\"$(printf '%s' "$RHDH_OIDC_METADATA_URL" | base64 -w0)\""
fi
if oc get secret golden-path-agent-rhdh-oidc-secret -n "$NS_RHDH" >/dev/null 2>&1; then
  oc patch secret golden-path-agent-rhdh-oidc-secret -n "$NS_RHDH" --type merge \
    -p "{\"data\":{\"OIDC_CLIENT_SECRET\":\"$(printf '%s' "$RHDH_OIDC_SECRET" | base64 -w0)\"${OIDC_URL_DATA}}}" >/dev/null
else
  # DEC-092 (addendum): SESSION_SECRET is generated only here, at first
  # creation -- regenerating it on an existing environment would
  # invalidate every active session, unlike OIDC_CLIENT_SECRET. Omitting
  # it entirely produces "Authentication failed, authentication requires
  # session support" on the first login attempt.
  oc create secret generic golden-path-agent-rhdh-oidc-secret -n "$NS_RHDH" \
    --from-literal=OIDC_CLIENT_ID=golden-path-agent-rhdh \
    --from-literal=OIDC_CLIENT_SECRET="$RHDH_OIDC_SECRET" \
    --from-literal=OIDC_METADATA_URL="${RHDH_OIDC_METADATA_URL:-http://golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local:8080/realms/${REALM}/.well-known/openid-configuration}" \
    ${RHDH_PUBLIC_URL:+--from-literal=PUBLIC_URL="$RHDH_PUBLIC_URL"} \
    --from-literal=SESSION_SECRET="$(openssl rand -base64 32)" >/dev/null
fi
unset RHDH_OIDC_SECRET OIDC_URL_DATA
echo "provisioned RHDH OIDC client secret in ${NS_RHDH}/golden-path-agent-rhdh-oidc-secret"

# Phase G, Stage 3 (DECISIONS.md DEC-098/DEC-099/DEC-110/DEC-118, G6 Path A
# landing). Mirrors the Gitea scaffolder machine account's own token
# (already provisioned, live-proven to actual destruction, DEC-100) from
# its home namespace (golden-path-agent-gitea) into golden-path-agent-rhdh
# -- Kubernetes Secrets cannot be referenced across namespaces, and RHDH's
# publish:gitea action needs this exact token as its own write credential
# (integrations.gitea's password field, substituted via Backstage's
# ${VAR} syntax in catalog-locations-config.yaml, same pattern as the
# OIDC secret above -- never a literal in that ConfigMap). Same
# regenerate-every-run idempotence as the rest of this script: this is a
# resync of the source token's current value, not a one-time copy that
# could drift if the source is ever rotated.
#
# DEC-137: Gitea has no consumer without --with-rhdh (nothing else in
# this blueprint reads it), so this section is a no-op, not a failure,
# when RHDH wasn't requested. When RHDH WAS requested, the namespace and
# token Secret this section reads are scripts/bootstrap.sh's own step
# 4c's responsibility.
#
# DEC-138: step 4c now generates its own admin password (create-once,
# same as golden-path-agent-keycloak-admin) and runs the org/account/
# token setup unconditionally -- there is no longer any out-of-band
# input step 4c can be waiting on. On a correct run this guard is
# therefore UNREACHABLE whenever --with-rhdh is set: kept as a fail-fast
# check, not deleted, precisely so that if it ever DOES fire, that is
# unambiguously a defect in step 4c (or a manual namespace/secret
# deletion), not a normal "come back later" state.
NS_GITEA=golden-path-agent-gitea
if [ "${WITH_RHDH:-false}" != "true" ]; then
  echo "WARNING: --with-rhdh not set -- skipping Gitea scaffolder credential copy (RHDH is Gitea's only consumer)"
elif ! oc get namespace "$NS_GITEA" >/dev/null 2>&1 || \
    ! oc get secret golden-path-agent-gitea-scaffolder-token -n "$NS_GITEA" >/dev/null 2>&1; then
  echo "[provision-identity-secrets.sh] FAILED (unreachable on a correct run, DEC-138): golden-path-agent-gitea namespace or golden-path-agent-gitea-scaffolder-token Secret not found -- scripts/bootstrap.sh's step 4c should always create both unconditionally now. Inspect step 4c's own output for what actually happened." >&2
  exit 1
else
  GITEA_SCAFFOLDER_USERNAME=$(oc get secret golden-path-agent-gitea-scaffolder-token -n "$NS_GITEA" -o jsonpath='{.data.username}' | base64 -d)
  GITEA_SCAFFOLDER_TOKEN=$(oc get secret golden-path-agent-gitea-scaffolder-token -n "$NS_GITEA" -o jsonpath='{.data.token}' | base64 -d)
  # GITEA_HOST (DEC-131): the Gitea Route's own live hostname, queried here
  # rather than hardcoded -- this cluster's apps domain is environment
  # config, not a committed value. Only one Route exists in this namespace
  # (the auto-created Gitea Route, DEC-100), so the first item is
  # unambiguous. Consumed the same way as the two credential fields above:
  # via Backstage's ${VAR} syntax in catalog-locations-config.yaml, never a
  # literal in that ConfigMap.
  GITEA_HOST=$(oc get route -n "$NS_GITEA" -o jsonpath='{.items[0].spec.host}')
  if [ -z "$GITEA_HOST" ]; then
    echo "FAIL: no Route found in ${NS_GITEA} -- Gitea must be live before RHDH's catalog config can resolve GITEA_HOST" >&2
    exit 1
  fi
  if oc get secret golden-path-agent-rhdh-gitea-scaffolder-secret -n "$NS_RHDH" >/dev/null 2>&1; then
    oc patch secret golden-path-agent-rhdh-gitea-scaffolder-secret -n "$NS_RHDH" --type merge \
      -p "{\"data\":{\"GITEA_SCAFFOLDER_USERNAME\":\"$(printf '%s' "$GITEA_SCAFFOLDER_USERNAME" | base64 -w0)\",\"GITEA_SCAFFOLDER_TOKEN\":\"$(printf '%s' "$GITEA_SCAFFOLDER_TOKEN" | base64 -w0)\",\"GITEA_HOST\":\"$(printf '%s' "$GITEA_HOST" | base64 -w0)\"}}" >/dev/null
  else
    oc create secret generic golden-path-agent-rhdh-gitea-scaffolder-secret -n "$NS_RHDH" \
      --from-literal=GITEA_SCAFFOLDER_USERNAME="$GITEA_SCAFFOLDER_USERNAME" \
      --from-literal=GITEA_SCAFFOLDER_TOKEN="$GITEA_SCAFFOLDER_TOKEN" \
      --from-literal=GITEA_HOST="$GITEA_HOST" >/dev/null
  fi
  unset GITEA_SCAFFOLDER_USERNAME GITEA_SCAFFOLDER_TOKEN GITEA_HOST
  echo "provisioned RHDH's copy of the Gitea scaffolder credential + live GITEA_HOST in ${NS_RHDH}/golden-path-agent-rhdh-gitea-scaffolder-secret"
fi

# RHDH's plugin-install init container pulls with skopeo, not the kubelet,
# so it needs its own auth.json (golden-path-agent-rhdh-registry-auth,
# mounted by the Backstage CR). DEC-147 (M17): the internal-registry entry
# is the golden-path-agent-rhdh-plugin-puller ServiceAccount's long-lived
# token (platform/bootstrap/rhdh-plugin-puller.yaml) -- no longer the
# operator's own expiring `oc whoami -t`. DEC-145: if the external plugin
# registry is private, RHDH_PLUGIN_REGISTRY_USERNAME/_PASSWORD
# (bootstrap.env, optional) add its entry. Regenerated every run.
if [ "${WITH_RHDH:-false}" != "true" ]; then
  echo "WARNING: --with-rhdh not set -- skipping RHDH's plugin registry credential"
else
  REGISTRY_HOST="image-registry.openshift-image-registry.svc:5000"
  PULLER_WAITED=0
  until REGISTRY_TOKEN=$(oc get secret golden-path-agent-rhdh-plugin-puller-token -n "$NS_RHDH" -o jsonpath='{.data.token}' 2>/dev/null | base64 -d) && [ -n "$REGISTRY_TOKEN" ]; do
    if [ "$PULLER_WAITED" -ge 60 ]; then
      echo "[provision-identity-secrets.sh] FAILED: golden-path-agent-rhdh-plugin-puller-token has no token after 60s (applied by scripts/bootstrap.sh step 4b)" >&2
      exit 1
    fi
    sleep 5; PULLER_WAITED=$((PULLER_WAITED + 5))
  done
  REGISTRY_AUTH_JSON=$(REGISTRY_TOKEN="$REGISTRY_TOKEN" python3 -c "
import base64, json, os, sys
def entry(user, password):
    return {'auth': base64.b64encode(f'{user}:{password}'.encode()).decode()}
auths = {sys.argv[1]: entry('serviceaccount', os.environ['REGISTRY_TOKEN'])}
external = os.environ.get('RHDH_PLUGIN_REGISTRY', '').split('/', 1)[0]
if external and os.environ.get('RHDH_PLUGIN_REGISTRY_USERNAME'):
    auths[external] = entry(os.environ['RHDH_PLUGIN_REGISTRY_USERNAME'], os.environ.get('RHDH_PLUGIN_REGISTRY_PASSWORD', ''))
print(json.dumps({'auths': auths}))
" "$REGISTRY_HOST")
  if oc get secret golden-path-agent-rhdh-registry-auth -n "$NS_RHDH" >/dev/null 2>&1; then
    oc patch secret golden-path-agent-rhdh-registry-auth -n "$NS_RHDH" --type merge \
      -p "{\"data\":{\"auth.json\":\"$(printf '%s' "$REGISTRY_AUTH_JSON" | base64 -w0)\"}}" >/dev/null
  else
    oc create secret generic golden-path-agent-rhdh-registry-auth -n "$NS_RHDH" \
      --from-literal=auth.json="$REGISTRY_AUTH_JSON" >/dev/null
  fi
  unset REGISTRY_TOKEN REGISTRY_AUTH_JSON
  echo "provisioned RHDH's plugin registry credential in ${NS_RHDH}/golden-path-agent-rhdh-registry-auth (ServiceAccount-backed)"
fi

echo "provision-identity-secrets.sh: done."
