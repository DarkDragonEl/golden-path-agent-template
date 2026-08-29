#!/usr/bin/env bash
# Phase E, E1 (DECISIONS.md DEC-078). Scripted replay of the manual
# bootstrap sequence (docs/phase-c-runbook.md), extended with two
# operator Subscriptions this cluster needs from scratch (DEC-078).
#
# Never runs `oc login` -- credential handling stays the owner's own
# one-time step; this script assumes KUBECONFIG already points at an
# already-authenticated session against the target cluster.
#
# Idempotent for every `oc apply`/`oc apply -k` step. NOT idempotent for
# provision-identity-secrets.sh's own credential rotation (that script
# regenerates every run by design, DEC-059) -- re-running this script
# against an already-live cluster invalidates live Keycloak sessions.
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: bootstrap.sh <kubeconfig-path> [--reenable-sync] [--with-rhdh] [--constrained-node] [--env <file>]

Bootstraps the golden-path-agent blueprint onto a fresh OpenShift cluster
from Git alone. The kubeconfig must already be authenticated (this script
never runs `oc login`). Re-runnable: picks up where a prior run stopped.

--env <file> (DEC-138, default ./bootstrap.env): every input this script
needs that isn't discoverable from the cluster itself (model endpoint,
optionally a promotion-PR git token) -- see bootstrap.env.example for the
exact keys. Validated at step 0, before anything else touches the
cluster: missing required keys fail immediately with the full list, not
one at a time across several stopped-and-resumed runs.

DEC-083 WARNING: if the target cluster's own golden-path-agent-root
Application has had its auto-sync deliberately disabled (a single-
active-cluster deprotection, e.g. the SNO after DEC-083), a plain re-run
of this script will detect that live-only freeze and SKIP re-applying
deploy/argocd/application-root.yaml, rather than silently re-enabling
auto-sync and resurrecting DEC-078's original cross-cluster-promotion
hazard via a routine maintenance command. Pass --reenable-sync only if
you deliberately intend to reverse that specific cluster's freeze.

--with-rhdh (DEC-092): opt-in RHDH Operator install (cluster-scoped,
AllNamespaces) plus its Postgres credentials Secret -- opt-in because it
carries real cluster-wide visibility cost a plain namespace/client does
not.

--constrained-node: ADAPTER, NOT PART OF THE GOLDEN PATH
(adapters/constrained-node/README.md) -- exists only for bootstrapping
onto a shared, busy, resource-constrained cluster, e.g. to exercise
this project's own bootstrap sequence on a borrowed cluster. The
blueprint's own design assumes a clean cluster and never needs this
flag; a default run never touches adapters/constrained-node/ at all.
Lowers this project's own CPU/memory *requests* to a few tens of
millicores and a few dozen Mi (limits unchanged, Burstable QoS), since
scheduling on a busy shared node is gated by requests, not actual
usage. Applies adapters/constrained-node/deploy-overlays/constrained-node/
and .../approval-platform-constrained-node/ instead of demo-prod/
approval-platform directly (via a live-only ArgoCD Application
source.path patch, safe only because ADR-009's freeze already means
golden-path-agent-root's own auto-sync won't revert it -- root will
correctly show OutOfSync for as long as this adapter is in use, see its
own README), patches adapters/constrained-node/bootstrap-patches/
{keycloak-postgres,keycloak-cr,otel-collector}.yaml in place after
their normal apply, and (with --with-rhdh) points golden-path-agent-rhdh
at .../rhdh-constrained-node/ the same way. The committed golden-path
manifests themselves are never changed by this flag.
USAGE
  exit 1
}

[ $# -ge 1 ] || usage
[ -r "$1" ] || { echo "[bootstrap.sh] kubeconfig not readable: $1" >&2; exit 1; }
export KUBECONFIG="$1"
shift
REENABLE_SYNC=false
WITH_RHDH=false
CONSTRAINED_NODE=false
ENV_FILE="./bootstrap.env"
while [ $# -gt 0 ]; do
  case "$1" in
    --reenable-sync) REENABLE_SYNC=true; shift ;;
    --with-rhdh) WITH_RHDH=true; shift ;;
    --constrained-node) CONSTRAINED_NODE=true; shift ;;
    --env) [ $# -ge 2 ] || usage; ENV_FILE="$2"; shift 2 ;;
    *) echo "[bootstrap.sh] unknown argument: $1" >&2; usage ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

START_EPOCH=$(date -u +%s)
log() { echo "[bootstrap.sh $(date -u '+%H:%M:%S')] $*"; }

log "=== step 0/9: bootstrap.env inputs (DEC-138) ==="
# Validated before anything below touches the cluster (not even the
# read-only `oc whoami` a few lines down) -- every input this script
# needs but can't discover from the cluster itself, front-loaded into
# one fail-fast check instead of surfacing one at a time across several
# stopped-and-resumed runs (DEC-137's own step 6 STOP, now removed).
if [ ! -r "$ENV_FILE" ]; then
  echo "[bootstrap.sh] --env file not readable: $ENV_FILE (copy bootstrap.env.example and fill it in)" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a
REQUIRED_ENV_KEYS=(MODEL_API_BASE_URL MODEL_NAME MODEL_FALLBACK_API_BASE_URL MODEL_FALLBACK_NAME MODEL_API_KEY)
MISSING_ENV_KEYS=()
for key in "${REQUIRED_ENV_KEYS[@]}"; do
  [ -n "${!key:-}" ] || MISSING_ENV_KEYS+=("$key")
done
if [ "${#MISSING_ENV_KEYS[@]}" -gt 0 ]; then
  echo "[bootstrap.sh] $ENV_FILE is missing required keys: ${MISSING_ENV_KEYS[*]} (see bootstrap.env.example)" >&2
  exit 1
fi
log "  all required keys present in $ENV_FILE"

VERIFY_FAILED=false
verify_row() {
  # $1 = label, $2 = actual value, $3 = expected value (exact match => PASS).
  # Used by step 6's and step 9's verification tables (DEC-138) -- never
  # blocks by itself, only records; callers decide whether to exit 1
  # after printing the full table.
  local label="$1" actual="$2" expected="$3"
  if [ "$actual" = "$expected" ]; then
    printf '  PASS  %-55s %s\n' "$label" "$actual"
  else
    printf '  FAIL  %-55s got %-20s want %s\n' "$label" "$actual" "$expected"
    VERIFY_FAILED=true
  fi
}

log "target: $(oc whoami --show-server) as $(oc whoami)"

version_from_csv() {
  # e.g. openshift-pipelines-operator-rh.v1.22.5 -> 1.22.5
  echo "${1##*.v}"
}

version_ge() {
  # $1 >= $2, dotted-version comparison (GNU sort -V). Good enough for
  # the "at least this version" comparisons this script needs -- not a
  # full semver implementation.
  [ "$1" = "$2" ] && return 0
  [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -1)" = "$1" ]
}

find_subscription_for_package() {
  # $1 = namespace, $2 = package name (spec.name). Prints the
  # metadata.name of whichever Subscription in that namespace targets
  # this package, if any -- there should be at most one (OLM does not
  # support two Subscriptions to the same package in one
  # namespace/OperatorGroup). Matched by PACKAGE, not by this
  # blueprint's own fixed object name: an adopter's pre-existing
  # Subscription for the same package is not guaranteed to share this
  # blueprint's own naming convention (DEC-135 addendum found this live
  # -- a real cluster had the Pipelines operator already installed under
  # a Subscription object named differently than this blueprint's own
  # manifest, and matching by object name alone missed it, letting this
  # script create a second, conflicting Subscription for the same
  # package).
  local ns="$1" pkg="$2"
  oc get subscription -n "$ns" -o json 2>/dev/null | \
    jq -r --arg pkg "$pkg" '.items[] | select(.spec.name==$pkg) | .metadata.name' | head -1
}

approve_pending_installplan_for_package() {
  # $1 = namespace, $2 = Subscription object name (NOT the package name
  # -- confirmed live that a CSV's own bundle name is not guaranteed to
  # be prefixed by its package identifier: package "rhdh" resolves to
  # CSV "rhdh-operator.v1.10.3", which a package-name-prefix match would
  # miss entirely).
  #
  # Reads this Subscription's own status.currentCSV -- the exact CSV
  # OLM has resolved for THIS Subscription specifically -- and finds the
  # InstallPlan whose spec.clusterServiceVersionNames contains that
  # EXACT name. Deliberately not status.installPlanRef: confirmed live
  # (DEC-135 addendum) that field can reference a different
  # Subscription's plan entirely on a cluster with several simultaneous
  # Manual-approval upgrades pending in one shared AllNamespaces
  # OperatorGroup. An exact CSV-name match against every plan's own
  # contents has no such ambiguity.
  #
  # Refuses to approve a plan that also lists any OTHER CSV (fail
  # closed, CLAUDE.md). OLM can bundle several pending Manual-approval
  # upgrades into one joint InstallPlan when they resolve together in
  # the same pass -- approving it would upgrade those other targets
  # too, which this call was never asked to touch.
  local ns="$1" sub="$2" target_csv plan other_csvs approved
  target_csv=$(oc get subscription "$sub" -n "$ns" -o jsonpath='{.status.currentCSV}' 2>/dev/null || echo "")
  [ -n "$target_csv" ] || return 0
  plan=$(oc get installplan -n "$ns" -o json 2>/dev/null | jq -r --arg csv "$target_csv" '
    .items[]
    | select(.spec.approved != true)
    | select(.spec.clusterServiceVersionNames[]? == $csv)
    | .metadata.name' | head -1)
  [ -n "$plan" ] || return 0
  other_csvs=$(oc get installplan "$plan" -n "$ns" -o json 2>/dev/null | jq -r --arg csv "$target_csv" '
    [.spec.clusterServiceVersionNames[] | select(. != $csv)] | join(", ")')
  if [ -n "$other_csvs" ]; then
    log "  InstallPlan $plan also bundles: $other_csvs -- NOT auto-approving a joint plan for targets this run wasn't asked to touch. Resolve manually."
    return 1
  fi
  approved=$(oc get installplan "$plan" -n "$ns" -o jsonpath='{.spec.approved}' 2>/dev/null || echo "")
  if [ "$approved" != "true" ]; then
    log "  approving InstallPlan $plan ($target_csv) in $ns"
    oc patch installplan "$plan" -n "$ns" --type merge -p '{"spec":{"approved":true}}' >/dev/null
  fi
}

ensure_operator() {
  # $1 = namespace, $2 = human label, $3 = fresh-install manifest path
  # (exact startingCSV, used only when nothing pre-exists), $4 =
  # package name (spec.name), $5 = expected channel, $6 = minimum
  # acceptable version, $7 = timeout seconds.
  #
  # Adopter-provided discipline (DEC-135 addendum, docs/cluster-profile.md):
  # a Subscription for this exact PACKAGE may already exist on the
  # target cluster -- installed by the adopter (possibly under a
  # different object name than this blueprint's own manifest uses), or
  # by a prior run of this script -- not created by this invocation.
  # Never reapply this blueprint's own Subscription manifest when one
  # already exists for the package; doing so creates a second,
  # conflicting Subscription for the same package (confirmed live,
  # DEC-135 addendum) rather than silently updating the existing one.
  # Detect it, verify it meets the minimum version on the expected
  # channel, and let OLM finish an in-progress upgrade if it hasn't yet
  # -- install fresh only when no Subscription for this package exists
  # at all.
  local ns="$1" label="$2" manifest="$3" package="$4" channel="$5" min_version="$6" timeout="$7"
  local sub_name existing_channel installed_csv installed_version waited=0 phase

  sub_name=$(find_subscription_for_package "$ns" "$package")
  if [ -n "$sub_name" ]; then
    existing_channel=$(oc get subscription "$sub_name" -n "$ns" -o jsonpath='{.spec.channel}' 2>/dev/null || echo "")
    if [ "$existing_channel" != "$channel" ]; then
      log "$label: Subscription $sub_name already provides package $package in $ns on channel '$existing_channel', not this blueprint's expected '$channel' -- leftover-state case (docs/cluster-profile.md), not touching it. Resolve manually before continuing."
      return 1
    fi
    log "$label: Subscription $sub_name already provides package $package in $ns on the expected channel '$channel' -- treating as adopter-provided, not applying $manifest"
  else
    log "$label: no existing Subscription for package $package in $ns -- applying $manifest"
    oc apply -f "$manifest"
    sub_name=$(find_subscription_for_package "$ns" "$package")
  fi

  while true; do
    installed_csv=$(oc get subscription "$sub_name" -n "$ns" -o jsonpath='{.status.installedCSV}' 2>/dev/null || echo "")
    if [ -n "$installed_csv" ]; then
      phase=$(oc get csv "$installed_csv" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
      installed_version=$(version_from_csv "$installed_csv")
      if [ "$phase" = "Succeeded" ] && version_ge "$installed_version" "$min_version"; then
        log "  $installed_csv: Succeeded, >= minimum $min_version"
        return 0
      fi
      if [ "$phase" = "Failed" ]; then
        log "  $installed_csv: FAILED -- inspect 'oc get csv $installed_csv -n $ns -o yaml'"
        return 1
      fi
    fi
    approve_pending_installplan_for_package "$ns" "$sub_name"
    if [ "$waited" -ge "$timeout" ]; then
      log "  $sub_name: still '${installed_csv:-<no CSV yet>}' (phase '${phase:-<none>}') after ${timeout}s -- not waiting further"
      return 1
    fi
    sleep 10; waited=$((waited + 10))
  done
}

log "=== step 1/9: cluster-scoped operators (Pipelines, GitOps) ==="
ensure_operator openshift-operators "OpenShift Pipelines" \
  pipelines/bootstrap/pipelines-operator.yaml \
  openshift-pipelines-operator-rh pipelines-1.22 1.22.5 300
ensure_operator openshift-operators "OpenShift GitOps" \
  pipelines/bootstrap/gitops-operator.yaml \
  openshift-gitops-operator gitops-1.20 1.20.6 300

log "=== step 2/9: namespaces + rbac ==="
oc apply -f pipelines/bootstrap/namespaces.yaml
oc apply -f pipelines/bootstrap/rbac.yaml

# Both secrets required BEFORE keycloak-postgres.yaml/keycloak-cr.yaml
# apply, or those pods hit CreateContainerConfigError. Create-once, not
# regenerate-every-run like DEC-059's downstream credentials --
# regenerating either after Keycloak trusts it would break a live
# instance, not just rotate a credential (DEC-059).
if ! oc get secret golden-path-agent-keycloak-db-secret -n golden-path-agent-keycloak >/dev/null 2>&1; then
  log "creating golden-path-agent-keycloak-db-secret (first time on this cluster)"
  oc create secret generic golden-path-agent-keycloak-db-secret \
    -n golden-path-agent-keycloak \
    --from-literal=POSTGRESQL_USER=keycloak \
    --from-literal=POSTGRESQL_PASSWORD="$(openssl rand -base64 18)" \
    --from-literal=POSTGRESQL_DATABASE=keycloak >/dev/null
fi
if ! oc get secret golden-path-agent-keycloak-admin -n golden-path-agent-keycloak >/dev/null 2>&1; then
  log "creating golden-path-agent-keycloak-admin (first time on this cluster)"
  oc create secret generic golden-path-agent-keycloak-admin \
    -n golden-path-agent-keycloak \
    --from-literal=username=admin \
    --from-literal=password="$(openssl rand -base64 18)" >/dev/null
fi

log "=== step 3/9: keycloak ==="
KEYCLOAK_PATH="olm"
if ! ensure_operator golden-path-agent-keycloak "rhbk-operator" \
    platform/bootstrap/keycloak-operator.yaml \
    rhbk-operator stable-v26.6 26.6.6-opr.1 300; then
  log "rhbk-operator OLM path did not reach Succeeded in time -- falling back to upstream kustomize (DEC-056 precedent)"
  KEYCLOAK_PATH="upstream-kustomize"
  oc apply -k platform/bootstrap/keycloak-operator-upstream/
fi
log "keycloak operator install path used this run: $KEYCLOAK_PATH"
oc apply -f platform/bootstrap/keycloak-postgres.yaml
oc apply -f platform/bootstrap/keycloak-cr.yaml
oc apply -f platform/bootstrap/keycloak-realm-import.yaml
if [ "$CONSTRAINED_NODE" = "true" ]; then
  log "  --constrained-node: patching keycloak-db/keycloak requests"
  oc patch deployment golden-path-agent-keycloak-db -n golden-path-agent-keycloak \
    --type strategic --patch-file adapters/constrained-node/bootstrap-patches/keycloak-postgres.yaml >/dev/null
  oc patch keycloak golden-path-agent -n golden-path-agent-keycloak \
    --type merge --patch-file adapters/constrained-node/bootstrap-patches/keycloak-cr.yaml >/dev/null
fi

log "=== step 4/9: cluster-tier otel collector ==="
oc apply -f platform/bootstrap/otel-collector.yaml
if [ "$CONSTRAINED_NODE" = "true" ]; then
  log "  --constrained-node: patching otel-collector requests"
  # --type strategic, not merge: the otel-collector Deployment has TWO
  # containers (otel-collector, traces-http) -- a plain JSON Merge
  # Patch would replace the whole containers list with just the one
  # entry in this patch file, silently deleting the sidecar. Strategic
  # merge patches list items by their own `name` key instead.
  oc patch deployment golden-path-agent-otel-collector -n golden-path-agent-otel \
    --type strategic --patch-file adapters/constrained-node/bootstrap-patches/otel-collector.yaml >/dev/null
fi

if [ "$WITH_RHDH" = "true" ]; then
  log "=== step 4b/9 (--with-rhdh, Phase F4, DEC-092): RHDH operator + Postgres secret ==="
  # DEC-136: this blueprint is meant to be the SOLE owner of the rhdh
  # package's Subscription going forward (a prior, unrelated cluster
  # owner's own rhdh-operator Subscription was intentionally retired in
  # favor of this one). A Subscription for package rhdh under any name
  # OTHER than this blueprint's own ("rhdh") is therefore drift, not a
  # legitimate adopter to fold into the general adopter-provided path
  # -- abort rather than silently adopt or create a second one. A
  # Subscription already named "rhdh" is this blueprint's own, from an
  # earlier (possibly partial) run of this exact script -- ensure_operator
  # handles that case exactly like Pipelines/GitOps/RHBK's, including
  # its own channel-mismatch abort if that ever drifted too.
  EXISTING_RHDH_SUB=$(find_subscription_for_package openshift-operators rhdh)
  if [ -n "$EXISTING_RHDH_SUB" ] && [ "$EXISTING_RHDH_SUB" != "rhdh" ]; then
    log "  ABORT: Subscription $EXISTING_RHDH_SUB already provides package rhdh in openshift-operators -- this blueprint expects to be the sole owner (DEC-136). Not adopting, not creating a second one. Resolve manually before re-running with --with-rhdh."
    exit 1
  fi
  ensure_operator openshift-operators "RHDH" \
    platform/bootstrap/rhdh-operator.yaml \
    rhdh fast-1.10 1.10.3 300
  # Real gap found live (Phase F4): the RHDH Operator's external-DB secret
  # needs both the OpenShift postgresql S2I image's own env vars
  # (POSTGRESQL_USER/PASSWORD/DATABASE) AND the operator's own
  # POSTGRES_HOST/PORT/USER/PASSWORD keys (docs/external-db.md,
  # spec.database.authSecretName) -- one Secret with both key sets, not
  # two, to avoid duplicating the same password material.
  if ! oc get secret golden-path-agent-rhdh-db-secret -n golden-path-agent-rhdh >/dev/null 2>&1; then
    log "creating golden-path-agent-rhdh-db-secret (first time on this cluster)"
    RHDH_DB_PASSWORD=$(openssl rand -base64 18)
    oc create secret generic golden-path-agent-rhdh-db-secret \
      -n golden-path-agent-rhdh \
      --from-literal=POSTGRESQL_USER=rhdh \
      --from-literal=POSTGRESQL_PASSWORD="$RHDH_DB_PASSWORD" \
      --from-literal=POSTGRESQL_DATABASE=rhdh \
      --from-literal=POSTGRES_HOST=golden-path-agent-rhdh-db \
      --from-literal=POSTGRES_PORT=5432 \
      --from-literal=POSTGRES_USER=rhdh \
      --from-literal=POSTGRES_PASSWORD="$RHDH_DB_PASSWORD" >/dev/null
    unset RHDH_DB_PASSWORD
  fi
  log "RHDH operator ready, DB secret provisioned -- Postgres/Backstage CR themselves are GitOps-managed (deploy/kustomize/overlays/rhdh/, deploy/argocd/apps/rhdh.yaml), applied automatically by golden-path-agent-root's own selfHeal sync, not by this script"

  log "=== step 4c/9 (--with-rhdh, DEC-137/DEC-138): Gitea (RHDH scaffolder's git host) ==="
  # DEC-137: G1 (DEC-100/DEC-103) stood this up by hand; G6 then made
  # provision-identity-secrets.sh depend on it (golden-path-agent-gitea-
  # scaffolder-token) without this script ever gaining a step to create
  # it -- a real blueprint gap, only surfaced by this cluster's first
  # true from-scratch bootstrap. Gated on --with-rhdh: Gitea exists to
  # serve RHDH's Scaffolder publish:gitea action and has no other
  # consumer in this blueprint.
  #
  # DEC-138: the admin password is generated here, in-script, create-once
  # -- exactly like golden-path-agent-keycloak-admin at step 2 -- rather
  # than staying a manually-provisioned prerequisite. Nothing below this
  # point is conditional on it anymore: it always exists by the time
  # gitea-cr.yaml is applied, so the wait and the org/account/token setup
  # always run.
  GITEA_NS=golden-path-agent-gitea
  oc apply -k platform/bootstrap/gitea-operator-upstream/
  if ! oc get secret golden-path-agent-gitea-admin-password -n "$GITEA_NS" >/dev/null 2>&1; then
    log "  creating golden-path-agent-gitea-admin-password (first time on this cluster)"
    oc create secret generic golden-path-agent-gitea-admin-password -n "$GITEA_NS" \
      --from-literal=adminPassword="$(openssl rand -base64 24)" >/dev/null
  fi
  oc apply -f platform/bootstrap/gitea-cr.yaml
  log "  waiting for Gitea CR to report adminSetupComplete"
  GITEA_WAITED=0
  GITEA_TIMEOUT=300
  while true; do
    GITEA_READY=$(oc get gitea golden-path-agent-gitea -n "$GITEA_NS" \
      -o jsonpath='{.status.adminSetupComplete}' 2>/dev/null || echo "")
    [ "$GITEA_READY" = "true" ] && { log "  Gitea: adminSetupComplete"; break; }
    if [ "$GITEA_WAITED" -ge "$GITEA_TIMEOUT" ]; then
      log "  Gitea: still not ready after ${GITEA_TIMEOUT}s -- inspect 'oc get gitea golden-path-agent-gitea -n $GITEA_NS -o yaml'"
      exit 1
    fi
    sleep 10; GITEA_WAITED=$((GITEA_WAITED + 10))
  done
  GITEA_ROUTE=$(oc get gitea golden-path-agent-gitea -n "$GITEA_NS" -o jsonpath='{.status.giteaRoute}')
  log "  waiting for Gitea route to answer 200: $GITEA_ROUTE"
  GITEA_HTTP_WAITED=0
  while true; do
    GITEA_HTTP_CODE=$(curl -sk -o /dev/null -w '%{http_code}' "$GITEA_ROUTE" 2>/dev/null || echo "000")
    [ "$GITEA_HTTP_CODE" = "200" ] && { log "  Gitea route: 200"; break; }
    if [ "$GITEA_HTTP_WAITED" -ge 120 ]; then
      log "  Gitea route still not answering 200 after 120s (last: $GITEA_HTTP_CODE) -- inspect 'curl -vk $GITEA_ROUTE'"
      exit 1
    fi
    sleep 5; GITEA_HTTP_WAITED=$((GITEA_HTTP_WAITED + 5))
  done

  gitea_api() {
    # $1 = method, $2 = path (leading /), $3 = json body (optional).
    # Admin-authenticated (golden-path-agent-admin), for org/account/
    # team management only -- never used for the scaffolder's own
    # token, which self-authenticates (see below).
    local method="$1" path="$2" body="${3:-}"
    if [ -n "$body" ]; then
      curl -sk -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" -X "$method" \
        -H 'Content-Type: application/json' -d "$body" "${GITEA_ROUTE}${path}"
    else
      curl -sk -u "${GITEA_ADMIN_USER}:${GITEA_ADMIN_PASSWORD}" -X "$method" "${GITEA_ROUTE}${path}"
    fi
  }

  GITEA_ADMIN_USER=golden-path-agent-admin
  GITEA_ADMIN_PASSWORD=$(oc get secret golden-path-agent-gitea-admin-password -n "$GITEA_NS" -o jsonpath='{.data.adminPassword}' | base64 -d)
  GITEA_ORG=golden-path-agent-projects
  GITEA_SCAFFOLDER_USER=golden-path-agent-scaffolder

  # Org: create-once, idempotent (DEC-100 precedent).
  if ! gitea_api GET "/api/v1/orgs/${GITEA_ORG}" | jq -e '.id' >/dev/null 2>&1; then
    log "  creating Gitea org $GITEA_ORG"
    gitea_api POST "/api/v1/orgs" "{\"username\":\"${GITEA_ORG}\"}" >/dev/null
  fi

  # Scaffolder account's own login password: create-once (DEC-059 --
  # this is the account's persisted credential, not a rotatable
  # downstream copy; regenerating it here would silently desync from
  # what Gitea itself has stored, unlike the token below which Gitea
  # is explicitly asked to reissue every run).
  if oc get secret golden-path-agent-gitea-scaffolder-password -n "$GITEA_NS" >/dev/null 2>&1; then
    GITEA_SCAFFOLDER_PASSWORD=$(oc get secret golden-path-agent-gitea-scaffolder-password -n "$GITEA_NS" -o jsonpath='{.data.password}' | base64 -d)
  else
    log "  creating golden-path-agent-gitea-scaffolder-password (first time on this cluster)"
    GITEA_SCAFFOLDER_PASSWORD=$(openssl rand -base64 24)
    oc create secret generic golden-path-agent-gitea-scaffolder-password -n "$GITEA_NS" \
      --from-literal=password="$GITEA_SCAFFOLDER_PASSWORD" >/dev/null
  fi

  # Scaffolder account: create-once, idempotent, non-admin (DEC-100).
  if ! gitea_api GET "/api/v1/users/${GITEA_SCAFFOLDER_USER}" | jq -e '.id' >/dev/null 2>&1; then
    log "  creating Gitea scaffolder account $GITEA_SCAFFOLDER_USER"
    gitea_api POST "/api/v1/admin/users" \
      "{\"username\":\"${GITEA_SCAFFOLDER_USER}\",\"password\":\"${GITEA_SCAFFOLDER_PASSWORD}\",\"email\":\"${GITEA_SCAFFOLDER_USER}@example.com\",\"must_change_password\":false}" >/dev/null
  fi

  # Narrowly-scoped team: write on repo.code/repo.pulls only, never the
  # org's default Owners team (DEC-100's own live-proven finding).
  GITEA_TEAM_ID=$(gitea_api GET "/api/v1/orgs/${GITEA_ORG}/teams" | jq -r '.[] | select(.name=="scaffolder") | .id' | head -1)
  if [ -z "$GITEA_TEAM_ID" ]; then
    log "  creating Gitea team 'scaffolder' in $GITEA_ORG"
    gitea_api POST "/api/v1/orgs/${GITEA_ORG}/teams" \
      '{"name":"scaffolder","permission":"write","units":["repo.code","repo.pulls"],"units_map":{"repo.code":"write","repo.pulls":"write"}}' >/dev/null
    GITEA_TEAM_ID=$(gitea_api GET "/api/v1/orgs/${GITEA_ORG}/teams" | jq -r '.[] | select(.name=="scaffolder") | .id' | head -1)
  fi
  gitea_api PUT "/api/v1/teams/${GITEA_TEAM_ID}/members/${GITEA_SCAFFOLDER_USER}" >/dev/null

  # Token: regenerated every run (DEC-059 downstream discipline,
  # matching provision-identity-secrets.sh's own resync-from-source
  # pattern for this exact secret) -- self-authenticated as the
  # scaffolder account itself, never the admin, since a token's own
  # scopes are bound to whichever account creates it. write:repository
  # alone was proven live (DEC-100) to fail org-repo creation;
  # write:organization is also required.
  curl -sk -u "${GITEA_SCAFFOLDER_USER}:${GITEA_SCAFFOLDER_PASSWORD}" -X DELETE \
    "${GITEA_ROUTE}/api/v1/users/${GITEA_SCAFFOLDER_USER}/tokens/golden-path-agent-bootstrap" >/dev/null 2>&1 || true
  GITEA_TOKEN_JSON=$(curl -sk -u "${GITEA_SCAFFOLDER_USER}:${GITEA_SCAFFOLDER_PASSWORD}" -X POST \
    -H 'Content-Type: application/json' \
    -d '{"name":"golden-path-agent-bootstrap","scopes":["write:repository","write:organization"]}' \
    "${GITEA_ROUTE}/api/v1/users/${GITEA_SCAFFOLDER_USER}/tokens")
  GITEA_TOKEN=$(echo "$GITEA_TOKEN_JSON" | jq -r '.sha1')
  if [ -z "$GITEA_TOKEN" ] || [ "$GITEA_TOKEN" = "null" ]; then
    log "  FAILED to create Gitea scaffolder token: $GITEA_TOKEN_JSON"
    exit 1
  fi
  if oc get secret golden-path-agent-gitea-scaffolder-token -n "$GITEA_NS" >/dev/null 2>&1; then
    oc patch secret golden-path-agent-gitea-scaffolder-token -n "$GITEA_NS" --type merge \
      -p "{\"data\":{\"username\":\"$(printf '%s' "$GITEA_SCAFFOLDER_USER" | base64 -w0)\",\"token\":\"$(printf '%s' "$GITEA_TOKEN" | base64 -w0)\"}}" >/dev/null
  else
    oc create secret generic golden-path-agent-gitea-scaffolder-token -n "$GITEA_NS" \
      --from-literal=username="$GITEA_SCAFFOLDER_USER" \
      --from-literal=token="$GITEA_TOKEN" >/dev/null
  fi
  unset GITEA_ADMIN_PASSWORD GITEA_SCAFFOLDER_PASSWORD GITEA_TOKEN GITEA_TOKEN_JSON
  log "  provisioned Gitea org/scaffolder account/token in $GITEA_NS"
fi

log "=== waiting for Keycloak to report Ready before provisioning identity secrets ==="
KC_WAITED=0
KC_TIMEOUT=300
while true; do
  KC_READY=$(oc get keycloak golden-path-agent -n golden-path-agent-keycloak \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "")
  [ "$KC_READY" = "True" ] && { log "  Keycloak: Ready"; break; }
  if [ "$KC_WAITED" -ge "$KC_TIMEOUT" ]; then
    log "  Keycloak: still not Ready after ${KC_TIMEOUT}s -- inspect 'oc get keycloak golden-path-agent -n golden-path-agent-keycloak -o yaml'"
    exit 1
  fi
  sleep 10; KC_WAITED=$((KC_WAITED + 10))
done

# Real race found live: the Keycloak CR's own Ready condition reflects
# the base instance coming up, NOT that KeycloakRealmImport has finished
# loading the realm's clients/users into it -- the two run
# asynchronously. provision-identity-secrets.sh queries the admin API
# for clients that only exist once the import Job completes; without
# this wait it can 404 on a client lookup moments after Keycloak itself
# goes Ready. Wait on the import's own Done condition too, separately.
log "=== waiting for KeycloakRealmImport to report Done ==="
RI_WAITED=0
RI_TIMEOUT=180
while true; do
  RI_DONE=$(oc get keycloakrealmimport golden-path-agent -n golden-path-agent-keycloak \
    -o jsonpath='{.status.conditions[?(@.type=="Done")].status}' 2>/dev/null || echo "")
  [ "$RI_DONE" = "True" ] && { log "  KeycloakRealmImport: Done"; break; }
  if [ "$RI_WAITED" -ge "$RI_TIMEOUT" ]; then
    log "  KeycloakRealmImport: still not Done after ${RI_TIMEOUT}s -- inspect 'oc get keycloakrealmimport golden-path-agent -n golden-path-agent-keycloak -o yaml'"
    exit 1
  fi
  sleep 5; RI_WAITED=$((RI_WAITED + 5))
done

log "=== step 5/9: identity secrets (idempotent by regeneration -- DEC-059) ==="
WITH_RHDH="$WITH_RHDH" ./platform/bootstrap/provision-identity-secrets.sh

log "=== step 6/9: CI config + verification (DEC-138) ==="
# golden-path-agent-ci-config (a plain ConfigMap -- MODEL_API_BASE_URL/
# MODEL_NAME/MODEL_FALLBACK_* are not credential material) is read by
# both deploy-ephemeral and eval-gate-live (docs/phase-c-runbook.md,
# formerly S2b). Created here, idempotent by regeneration (DEC-059),
# from bootstrap.env's own values -- step 0 already validated they're
# present. golden-path-agent-secrets' own MODEL_API_KEY (+ the same four
# URL/NAME keys) is provision-identity-secrets.sh's job, step 5, same
# regeneration discipline, since it already owns that Secret's other
# keys per-namespace.
oc create configmap golden-path-agent-ci-config -n golden-path-agent-ci \
  --from-literal=MODEL_API_BASE_URL="$MODEL_API_BASE_URL" \
  --from-literal=MODEL_NAME="$MODEL_NAME" \
  --from-literal=MODEL_FALLBACK_API_BASE_URL="$MODEL_FALLBACK_API_BASE_URL" \
  --from-literal=MODEL_FALLBACK_NAME="$MODEL_FALLBACK_NAME" \
  --dry-run=client -o yaml | oc apply -f - >/dev/null
log "  provisioned golden-path-agent-ci-config in golden-path-agent-ci"

# Verification table only (DEC-138) -- no STOP. Everything checked here
# was just created by steps 0/5/6 of THIS SAME run from validated
# inputs; a FAIL means a real defect in this script, not a missing
# manual step for the owner to go provision and re-run for.
for ns in golden-path-agent-demo-prod golden-path-agent-ephemeral-test; do
  verify_row "$ns/golden-path-agent-secrets MODEL_API_KEY" \
    "$(oc get secret golden-path-agent-secrets -n "$ns" -o jsonpath='{.data.MODEL_API_KEY}' 2>/dev/null | grep -q . && echo present || echo missing)" \
    "present"
done
verify_row "golden-path-agent-ci/golden-path-agent-ci-config" \
  "$(oc get configmap golden-path-agent-ci-config -n golden-path-agent-ci >/dev/null 2>&1 && echo present || echo missing)" \
  "present"
if [ "$WITH_RHDH" = "true" ]; then
  verify_row "golden-path-agent-gitea/golden-path-agent-gitea-scaffolder-token" \
    "$(oc get secret golden-path-agent-gitea-scaffolder-token -n golden-path-agent-gitea >/dev/null 2>&1 && echo present || echo missing)" \
    "present"
fi
if [ -n "${GITHUB_TOKEN:-}" ]; then
  log "  GITHUB_TOKEN set in $ENV_FILE -- S3 (promotion-PR git credential) provisioning not yet wired to bootstrap.env, still manual (docs/phase-c-runbook.md S3)"
else
  log "  GITHUB_TOKEN not set -- S3 skipped (optional, DEC-078: this cluster's pipeline never gets promotion authority over the shared main digest pin regardless)"
fi
if [ "$VERIFY_FAILED" = "true" ]; then
  log "  one or more checks FAILED -- see table above. These are all created earlier in this same run from already-validated bootstrap.env inputs, so a FAIL here is a defect in this script, not a missing manual step."
  exit 1
fi

log "=== step 7/9: pipeline + task definitions ==="
# Without this apply, a PipelineRun fails with CouldntGetPipeline
# (DEC-078). DEC-098/DEC-099 (G2): the single golden-path-agent-ci
# Pipeline is retired -- apply all three independent component
# Pipelines instead.
oc apply -f pipelines/pipeline-agent.yaml -n golden-path-agent-ci
oc apply -f pipelines/pipeline-mcp.yaml -n golden-path-agent-ci
oc apply -f pipelines/pipeline-approval.yaml -n golden-path-agent-ci
oc apply -f pipelines/tasks/ -n golden-path-agent-ci

log "=== step 8/9: argocd app-of-apps root ==="
oc apply -f deploy/argocd/project.yaml

# DEC-083 guard: deploy/argocd/application-root.yaml and
# deploy/argocd/apps/demo-prod.yaml are single files every cluster
# bootstraps identically from the same Git history -- a cluster-local
# "deprotect this cluster's demo-prod" decision (DEC-083's SNO freeze)
# is therefore necessarily a live-only patch, never a commit to those
# shared files. That makes it silently reversible by a routine re-run of
# this exact step, on this exact cluster, unless guarded here: detect an
# existing golden-path-agent-root Application whose own auto-sync is
# already disabled live, and refuse to re-apply application-root.yaml
# (which would restore spec.syncPolicy.automated to the committed
# {prune:true, selfHeal:true}) without an explicit, deliberate flag.
ROOT_EXISTS=false
oc get applications.argoproj.io golden-path-agent-root -n openshift-gitops >/dev/null 2>&1 && ROOT_EXISTS=true
if [ "$ROOT_EXISTS" = "true" ]; then
  ROOT_AUTOMATED=$(oc get applications.argoproj.io golden-path-agent-root -n openshift-gitops \
    -o jsonpath='{.spec.syncPolicy.automated}' 2>/dev/null || echo "")
  if [ -z "$ROOT_AUTOMATED" ] && [ "$REENABLE_SYNC" != "true" ]; then
    log "  golden-path-agent-root: auto-sync already disabled live on this cluster (DEC-083-style freeze) -- NOT re-applying deploy/argocd/application-root.yaml, which would silently restore automated:{prune:true,selfHeal:true} and resurrect DEC-078's cross-cluster-promotion hazard. Re-run with --reenable-sync if you deliberately intend to reverse this cluster's freeze."
  else
    oc apply -f deploy/argocd/application-root.yaml
  fi
else
  oc apply -f deploy/argocd/application-root.yaml
fi

if [ "$CONSTRAINED_NODE" = "true" ]; then
  log "=== step 8b/9 (--constrained-node): pointing demo-prod/approval-platform at the shared/single-node overlays ==="
  # Live-only, same safety precondition as the ADR-009 guard just above:
  # this only sticks because golden-path-agent-root's own auto-sync is
  # already disabled on this cluster, so nothing will silently revert
  # these Application objects' own spec.source.path back to the
  # committed demo-prod/approval-platform/rhdh value on the next sync.
  # demo-prod/approval-platform/rhdh's OWN selfHeal (unaffected by
  # root's freeze) then reconciles their live resources against
  # WHICHEVER path is set here, same as it always does.
  patch_app_path() {
    # $1 = Application name, $2 = new source path, $3 = human label
    local app="$1" path="$2" label="$3" waited=0
    while ! oc get applications.argoproj.io "$app" -n openshift-gitops >/dev/null 2>&1; do
      if [ "$waited" -ge 60 ]; then
        log "  $label ($app): did not appear within 60s of root's own sync -- not patched, check manually"
        return 1
      fi
      sleep 5; waited=$((waited + 5))
    done
    oc patch applications.argoproj.io "$app" -n openshift-gitops --type merge \
      -p "{\"spec\":{\"source\":{\"path\":\"$path\"}}}" >/dev/null
    log "  $label ($app): source.path -> $path"
  }
  patch_app_path golden-path-agent-demo-prod \
    adapters/constrained-node/deploy-overlays/constrained-node "demo-prod"
  patch_app_path golden-path-agent-approval \
    adapters/constrained-node/deploy-overlays/approval-platform-constrained-node "approval-platform"
  if [ "$WITH_RHDH" = "true" ]; then
    patch_app_path golden-path-agent-rhdh \
      adapters/constrained-node/deploy-overlays/rhdh-constrained-node "rhdh"
  fi
fi

log "=== step 9/9: verification ==="
VERIFY_FAILED=false
oc get applications.argoproj.io -n openshift-gitops

# demo-prod's two Deployments are the one thing here that can genuinely
# still be mid-rollout moments after step 8's apply (image pull, pod
# start) -- poll briefly rather than a single point-in-time snapshot
# that could FAIL on pure timing. Application sync status settles much
# faster (ArgoCD's own reconcile, not a pod lifecycle), so those stay
# single-shot checks below.
for deploy_name in golden-path-agent golden-path-agent-mcp; do
  DEPLOY_WAITED=0
  while true; do
    READY=$(oc get deployment "$deploy_name" -n golden-path-agent-demo-prod -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "")
    [ "${READY:-0}" = "1" ] && break
    if [ "$DEPLOY_WAITED" -ge 120 ]; then break; fi
    sleep 10; DEPLOY_WAITED=$((DEPLOY_WAITED + 10))
  done
  verify_row "demo-prod Deployment/$deploy_name ready replicas" "${READY:-0}" "1"
done
if [ "$VERIFY_FAILED" = "true" ]; then
  log "  a 0/1 above on a cluster where no PipelineRun has ever executed is the documented ImagePullBackOff condition (DEC-080): the inherited base digest was never pushed to this cluster's own internal registry. Not something this script's own bootstrap steps fix -- run the pipeline."
fi

# root's own diff is expected to be non-empty specifically when
# --constrained-node live-patched its children's spec.source.path away
# from what's committed (step 8b) -- that drift is the whole mechanism,
# safe only because root's own auto-sync is frozen and will never
# "correct" it back. Checking root itself for Synced would be checking
# this script's own intentional design against itself.
if [ "$CONSTRAINED_NODE" = "true" ]; then
  verify_row "Application golden-path-agent-root sync (--constrained-node: OutOfSync is the intended state)" \
    "$(oc get applications.argoproj.io golden-path-agent-root -n openshift-gitops -o jsonpath='{.status.sync.status}' 2>/dev/null)" \
    "OutOfSync"
else
  verify_row "Application golden-path-agent-root sync" \
    "$(oc get applications.argoproj.io golden-path-agent-root -n openshift-gitops -o jsonpath='{.status.sync.status}' 2>/dev/null)" \
    "Synced"
fi
verify_row "Application golden-path-agent-demo-prod sync" \
  "$(oc get applications.argoproj.io golden-path-agent-demo-prod -n openshift-gitops -o jsonpath='{.status.sync.status}' 2>/dev/null)" \
  "Synced"
verify_row "Application golden-path-agent-approval sync" \
  "$(oc get applications.argoproj.io golden-path-agent-approval -n openshift-gitops -o jsonpath='{.status.sync.status}' 2>/dev/null)" \
  "Synced"
if [ "$WITH_RHDH" = "true" ]; then
  verify_row "Application golden-path-agent-rhdh sync" \
    "$(oc get applications.argoproj.io golden-path-agent-rhdh -n openshift-gitops -o jsonpath='{.status.sync.status}' 2>/dev/null)" \
    "Synced"
fi

END_EPOCH=$(date -u +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
log "bootstrap sequence complete in ${ELAPSED}s ($((ELAPSED / 60))m elapsed this run)"
if [ "$VERIFY_FAILED" = "true" ]; then
  log "  one or more step 9 checks FAILED -- see table above"
  exit 1
fi
log "  all step 9 checks PASSED"
