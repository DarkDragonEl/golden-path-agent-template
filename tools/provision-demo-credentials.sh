#!/usr/bin/env bash
# Read-only w.r.t. the repo; mutates the live cluster (creates Keycloak users +
# ClusterRoleBindings) -- explicit human invocation only, never auto-run.
#
# Provisions independent, per-person credentials instead of sharing the single
# demo `admin` / `demo-user` / `demo-approver` accounts:
#   - N cluster-admin identities in the `sso` realm (OpenShift OIDC login),
#     each bound individually to the cluster-admin ClusterRole.
#   - N app-level test-user identities in the `golden-path-agent` realm
#     (no realm roles -- mirrors demo-user, not demo-approver).
#   - N app-level test-approver identities in the `golden-path-agent` realm
#     (assigned the `approval-approver` realm role -- mirrors demo-approver).
#
# Existing shared accounts (admin / demo-user / demo-approver) are left
# untouched.
set -euo pipefail

CLUSTER_ADMIN_COUNT="${CLUSTER_ADMIN_COUNT:-5}"
TEST_USER_COUNT="${TEST_USER_COUNT:-5}"
TEST_APPROVER_COUNT="${TEST_APPROVER_COUNT:-5}"
OUT_FILE="${OUT_FILE:-./provisioned-credentials.$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null || echo run).txt}"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing required tool: $1" >&2; exit 1; }; }
need oc
need curl
need python3
need openssl

gen_password() { openssl rand -base64 24 | tr -d '=+/' | cut -c1-20; }

kc_token() {
  local host="$1" user="$2" pass="$3"
  curl -sk -X POST "https://${host}/realms/master/protocol/openid-connect/token" \
    -d "client_id=admin-cli" -d "grant_type=password" \
    -d "username=${user}" -d "password=${pass}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
}

kc_create_user() {
  local host="$1" token="$2" realm="$3" username="$4" password="$5"
  curl -sk -o /dev/null -w "%{http_code}" -X POST \
    "https://${host}/admin/realms/${realm}/users" \
    -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"enabled\":true,\"emailVerified\":true,\"email\":\"${username}@example.invalid\"}"
  local uid
  uid=$(curl -sk "https://${host}/admin/realms/${realm}/users?username=${username}&exact=true" \
    -H "Authorization: Bearer ${token}" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  curl -sk -o /dev/null -X PUT \
    "https://${host}/admin/realms/${realm}/users/${uid}/reset-password" \
    -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" \
    -d "{\"type\":\"password\",\"value\":\"${password}\",\"temporary\":true}"
}

kc_assign_realm_role() {
  local host="$1" token="$2" realm="$3" username="$4" role="$5"
  local uid role_json
  uid=$(curl -sk "https://${host}/admin/realms/${realm}/users?username=${username}&exact=true" \
    -H "Authorization: Bearer ${token}" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
  role_json=$(curl -sk "https://${host}/admin/realms/${realm}/roles/${role}" \
    -H "Authorization: Bearer ${token}")
  curl -sk -o /dev/null -X POST \
    "https://${host}/admin/realms/${realm}/users/${uid}/role-mappings/realm" \
    -H "Authorization: Bearer ${token}" -H "Content-Type: application/json" \
    -d "[${role_json}]"
}

echo "=== Provisioning ${CLUSTER_ADMIN_COUNT} cluster-admin account(s) in the sso realm ==="
SSO_HOST=$(oc get route keycloak -n keycloak -o jsonpath='{.spec.host}')
SSO_ADMIN_USER=$(oc get secret keycloak-initial-admin -n keycloak -o jsonpath='{.data.username}' | base64 -d)
SSO_ADMIN_PASS=$(oc get secret keycloak-initial-admin -n keycloak -o jsonpath='{.data.password}' | base64 -d)
SSO_TOKEN=$(kc_token "$SSO_HOST" "$SSO_ADMIN_USER" "$SSO_ADMIN_PASS")

{
  echo "# Provisioned demo credentials -- $(date -u +%FT%TZ 2>/dev/null || echo unknown-time)"
  echo "# KEEP THIS FILE OUT OF GIT. Distribute rows individually, then delete."
  echo
  echo "## Cluster-admin (OpenShift console / oc login), realm=sso"
} > "$OUT_FILE"

for i in $(seq 1 "$CLUSTER_ADMIN_COUNT"); do
  uname="cluster-admin-user${i}"
  pass=$(gen_password)
  code=$(kc_create_user "$SSO_HOST" "$SSO_TOKEN" "sso" "$uname" "$pass")
  if [ "$code" != "201" ]; then
    echo "WARN: user ${uname} create returned HTTP ${code} (may already exist) -- skipping RBAC bind check manually" >&2
  fi
  oc create clusterrolebinding "keycloak-sso-user:${uname}:cluster-admin" \
    --clusterrole=cluster-admin --user="${uname}" --dry-run=client -o yaml | oc apply -f -
  echo "${uname}	${pass}" >> "$OUT_FILE"
  echo "created cluster-admin: ${uname}"
done

echo
echo "=== Provisioning ${TEST_USER_COUNT} app test-user account(s) in the golden-path-agent realm ==="
GPA_HOST=$(oc get route golden-path-agent-keycloak -n golden-path-agent-keycloak -o jsonpath='{.spec.host}')
GPA_ADMIN_USER=$(oc get secret golden-path-agent-keycloak-admin -n golden-path-agent-keycloak -o jsonpath='{.data.username}' | base64 -d)
GPA_ADMIN_PASS=$(oc get secret golden-path-agent-keycloak-admin -n golden-path-agent-keycloak -o jsonpath='{.data.password}' | base64 -d)
GPA_TOKEN=$(kc_token "$GPA_HOST" "$GPA_ADMIN_USER" "$GPA_ADMIN_PASS")

{
  echo
  echo "## App test users (no special realm role, mirrors demo-user), realm=golden-path-agent"
} >> "$OUT_FILE"

for i in $(seq 1 "$TEST_USER_COUNT"); do
  uname="test-user${i}"
  pass=$(gen_password)
  code=$(kc_create_user "$GPA_HOST" "$GPA_TOKEN" "golden-path-agent" "$uname" "$pass")
  if [ "$code" != "201" ]; then
    echo "WARN: user ${uname} create returned HTTP ${code} (may already exist)" >&2
  fi
  echo "${uname}	${pass}" >> "$OUT_FILE"
  echo "created test-user: ${uname}"
done

echo
echo "=== Provisioning ${TEST_APPROVER_COUNT} app test-approver account(s) in the golden-path-agent realm ==="

{
  echo
  echo "## App test approvers (approval-approver realm role, mirrors demo-approver), realm=golden-path-agent"
} >> "$OUT_FILE"

for i in $(seq 1 "$TEST_APPROVER_COUNT"); do
  uname="test-approver${i}"
  pass=$(gen_password)
  code=$(kc_create_user "$GPA_HOST" "$GPA_TOKEN" "golden-path-agent" "$uname" "$pass")
  if [ "$code" != "201" ]; then
    echo "WARN: user ${uname} create returned HTTP ${code} (may already exist)" >&2
  fi
  kc_assign_realm_role "$GPA_HOST" "$GPA_TOKEN" "golden-path-agent" "$uname" "approval-approver"
  echo "${uname}	${pass}" >> "$OUT_FILE"
  echo "created test-approver: ${uname}"
done

chmod 600 "$OUT_FILE"
echo
echo "Credentials written to: ${OUT_FILE} (mode 600, gitignored -- verify before sharing)"
echo "Passwords are temporary: each account is forced to set a new password on first login."
