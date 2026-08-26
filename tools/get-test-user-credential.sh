#!/usr/bin/env bash
# Read-only w.r.t. the repo; mutates the live cluster (resets one Keycloak
# user's password) -- explicit human invocation only, never auto-run.
#
# Self-service credential tool for holders of an individual cluster-admin
# login (see provision-demo-credentials.sh). Requires only `oc` access --
# no separate Keycloak admin secret needs to be handed out. Reads the
# golden-path-agent-keycloak-admin secret (readable because the caller is
# cluster-admin), resets the requested app-realm user's password to a fresh
# value, and prints it. Does NOT retrieve an existing password -- Keycloak
# never exposes plaintext of a password already set.
#
# Usage: ./get-test-user-credential.sh <username>
#   e.g. ./get-test-user-credential.sh test-user1
#        ./get-test-user-credential.sh test-approver1
#        ./get-test-user-credential.sh demo-approver
set -euo pipefail

USERNAME="${1:?usage: $0 <username>  (e.g. test-user1, demo-user, demo-approver)}"
REALM="golden-path-agent"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing required tool: $1" >&2; exit 1; }; }
need oc
need curl
need python3
need openssl

echo "Checking oc login..." >&2
oc whoami >/dev/null

GPA_HOST=$(oc get route golden-path-agent-keycloak -n golden-path-agent-keycloak -o jsonpath='{.spec.host}')
GPA_ADMIN_USER=$(oc get secret golden-path-agent-keycloak-admin -n golden-path-agent-keycloak -o jsonpath='{.data.username}' | base64 -d)
GPA_ADMIN_PASS=$(oc get secret golden-path-agent-keycloak-admin -n golden-path-agent-keycloak -o jsonpath='{.data.password}' | base64 -d)

TOKEN=$(curl -sk -X POST "https://${GPA_HOST}/realms/master/protocol/openid-connect/token" \
  -d "client_id=admin-cli" -d "grant_type=password" \
  -d "username=${GPA_ADMIN_USER}" -d "password=${GPA_ADMIN_PASS}" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

USER_ID=$(curl -sk "https://${GPA_HOST}/admin/realms/${REALM}/users?username=${USERNAME}&exact=true" \
  -H "Authorization: Bearer ${TOKEN}" | python3 -c "
import sys, json
users = json.load(sys.stdin)
if not users:
    print('NOT_FOUND')
else:
    print(users[0]['id'])
")

if [ "$USER_ID" = "NOT_FOUND" ]; then
  echo "ERROR: user '${USERNAME}' does not exist in realm '${REALM}'" >&2
  exit 1
fi

NEW_PASS=$(openssl rand -base64 24 | tr -d '=+/' | cut -c1-20)

curl -sk -o /dev/null -X PUT \
  "https://${GPA_HOST}/admin/realms/${REALM}/users/${USER_ID}/reset-password" \
  -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  -d "{\"type\":\"password\",\"value\":\"${NEW_PASS}\",\"temporary\":true}"

echo "New password set for '${USERNAME}' (realm: ${REALM}, temporary -- reset on first login):" >&2
echo "${USERNAME}	${NEW_PASS}"
