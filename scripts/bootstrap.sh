#!/usr/bin/env bash
# Phase E, E1 (DECISIONS.md DEC-078 onward). Scripted replay of the manual
# bootstrap sequence docs/phase-c-runbook.md established by hand on the
# SNO, extended here with two operator Subscriptions
# (pipelines/bootstrap/pipelines-operator.yaml, gitops-operator.yaml)
# neither the SNO nor any prior phase ever had to author, since those
# operators were always pre-installed there by other work before this
# project touched it (docs/environments.md). This is the actual
# from-scratch operator-bootstrap leg Phase E exists to prove.
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
usage: bootstrap.sh <kubeconfig-path> [--reenable-sync] [--with-rhdh]

Bootstraps the golden-path-agent blueprint onto a fresh OpenShift cluster
from Git alone. The kubeconfig must already be authenticated (this script
never runs `oc login`). Re-runnable: picks up where a prior run stopped.

DEC-083 WARNING: if the target cluster's own golden-path-agent-root
Application has had its auto-sync deliberately disabled (a single-
active-cluster deprotection, e.g. the SNO after DEC-083), a plain re-run
of this script will detect that live-only freeze and SKIP re-applying
deploy/argocd/application-root.yaml, rather than silently re-enabling
auto-sync and resurrecting DEC-078's original cross-cluster-promotion
hazard via a routine maintenance command. Pass --reenable-sync only if
you deliberately intend to reverse that specific cluster's freeze.

--with-rhdh (Phase F4, DEC-092): also installs the RHDH Operator
(cluster-scoped, openshift-operators, AllNamespaces -- visible to every
tenant on a shared cluster, same precedent as Pipelines/GitOps) and
provisions its dedicated Postgres credentials Secret. Opt-in, unlike the
golden-path-agent-rhdh namespace and Keycloak client (provisioned
unconditionally below, matching every other platform-infra namespace in
this file) -- the operator install specifically has a real, cluster-wide
cost/visibility a plain namespace or Keycloak client does not, so it is
not forced onto every fresh-cluster bootstrap by default.
USAGE
  exit 1
}

[ $# -ge 1 ] || usage
[ -r "$1" ] || { echo "[bootstrap.sh] kubeconfig not readable: $1" >&2; exit 1; }
export KUBECONFIG="$1"
REENABLE_SYNC=false
WITH_RHDH=false
for arg in "${@:2}"; do
  case "$arg" in
    --reenable-sync) REENABLE_SYNC=true ;;
    --with-rhdh) WITH_RHDH=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

START_EPOCH=$(date -u +%s)
log() { echo "[bootstrap.sh $(date -u '+%H:%M:%S')] $*"; }

log "target: $(oc whoami --show-server) as $(oc whoami)"

approve_pending_installplan() {
  # $1 = namespace, $2 = exact CSV name to match. installPlanApproval:
  # Manual (this project's own "pin exact versions, no silent
  # auto-upgrade" discipline, PINS.md) means even the FIRST install of a
  # pinned startingCSV sits in RequiresApproval until explicitly patched
  # -- not previously exercised in this project, since Keycloak's OLM
  # path was always blocked earlier by DEC-055's poisoned catalog on the
  # SNO before it ever got this far. Safe precisely because the
  # InstallPlan's own CSV is checked against the pinned value before
  # patching -- never approves a plan for anything other than the exact
  # version this project committed.
  local ns="$1" csv="$2" plan approved
  plan=$(oc get installplan -n "$ns" -o jsonpath="{.items[?(@.spec.clusterServiceVersionNames[0]=='$csv')].metadata.name}" 2>/dev/null || echo "")
  [ -n "$plan" ] || return 0
  approved=$(oc get installplan "$plan" -n "$ns" -o jsonpath='{.spec.approved}' 2>/dev/null || echo "")
  if [ "$approved" != "true" ]; then
    log "  approving InstallPlan $plan ($csv) in $ns"
    oc patch installplan "$plan" -n "$ns" --type merge -p '{"spec":{"approved":true}}' >/dev/null
  fi
}

wait_for_csv() {
  # $1 = namespace, $2 = exact CSV name, $3 = timeout seconds. Also
  # approves a pending InstallPlan for this exact CSV on every poll, so
  # this one loop handles both "InstallPlan not created yet" and
  # "InstallPlan created, sitting in RequiresApproval" races.
  local ns="$1" csv="$2" timeout="${3:-300}" waited=0 phase
  while true; do
    approve_pending_installplan "$ns" "$csv"
    phase=$(oc get csv "$csv" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
    case "$phase" in
      Succeeded) log "  $csv: Succeeded"; return 0 ;;
      Failed) log "  $csv: FAILED -- inspect 'oc get csv $csv -n $ns -o yaml'"; return 1 ;;
    esac
    if [ "$waited" -ge "$timeout" ]; then
      log "  $csv: still '${phase:-<not found>}' after ${timeout}s -- not waiting further"
      return 1
    fi
    sleep 10; waited=$((waited + 10))
  done
}

ensure_operator() {
  # $1 = namespace, $2 = human label, $3 = manifest path, $4 = exact startingCSV, $5 = timeout seconds
  local ns="$1" label="$2" manifest="$3" csv="$4" timeout="$5"
  if oc get csv "$csv" -n "$ns" -o jsonpath='{.status.phase}' 2>/dev/null | grep -q Succeeded; then
    log "$label: already Succeeded in $ns, skipping"
    return 0
  fi
  log "$label: applying $manifest"
  oc apply -f "$manifest"
  wait_for_csv "$ns" "$csv" "$timeout"
}

log "=== step 1/9: cluster-scoped operators (Pipelines, GitOps) ==="
ensure_operator openshift-operators "OpenShift Pipelines" \
  pipelines/bootstrap/pipelines-operator.yaml \
  openshift-pipelines-operator-rh.v1.22.5 300
ensure_operator openshift-operators "OpenShift GitOps" \
  pipelines/bootstrap/gitops-operator.yaml \
  openshift-gitops-operator.v1.20.6 300

log "=== step 2/9: namespaces + rbac ==="
oc apply -f pipelines/bootstrap/namespaces.yaml
oc apply -f pipelines/bootstrap/rbac.yaml

# Real gap found live this run, not documented anywhere before now:
# keycloak-cr.yaml's own header comment names golden-path-agent-keycloak-db-secret
# and golden-path-agent-keycloak-admin as "manually provisioned out-of-band" --
# docs/phase-d-runbook.md only ever wrote down the db-secret's creation
# command; the admin secret's was never captured anywhere in this
# project's docs (only referenced, never shown). Both are required
# BEFORE keycloak-postgres.yaml/keycloak-cr.yaml apply, or the Postgres
# and Keycloak pods immediately hit CreateContainerConfigError. Create-once
# semantics here (unlike provision-identity-secrets.sh's own
# regenerate-every-run downstream credentials, DEC-059) -- regenerating
# either of these after Postgres/Keycloak already trust the existing
# value would break a live instance, not just rotate a credential.
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
    rhbk-operator.v26.6.6-opr.1 300; then
  log "rhbk-operator OLM path did not reach Succeeded in time -- falling back to upstream kustomize (DEC-056 precedent)"
  KEYCLOAK_PATH="upstream-kustomize"
  oc apply -k platform/bootstrap/keycloak-operator-upstream/
fi
log "keycloak operator install path used this run: $KEYCLOAK_PATH"
oc apply -f platform/bootstrap/keycloak-postgres.yaml
oc apply -f platform/bootstrap/keycloak-cr.yaml
oc apply -f platform/bootstrap/keycloak-realm-import.yaml

log "=== step 4/9: cluster-tier otel collector ==="
oc apply -f platform/bootstrap/otel-collector.yaml

if [ "$WITH_RHDH" = "true" ]; then
  log "=== step 4b/9 (--with-rhdh, Phase F4, DEC-092): RHDH operator + Postgres secret ==="
  ensure_operator openshift-operators "RHDH" \
    platform/bootstrap/rhdh-operator.yaml \
    rhdh-operator.v1.10.3 300
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
./platform/bootstrap/provision-identity-secrets.sh

log "=== step 6/9: manual secret + config check ==="
# Real gap found live: provision-identity-secrets.sh (step 5) creates
# golden-path-agent-secrets in demo-prod itself if it doesn't yet exist
# (with just APPROVAL_OIDC_CLIENT_SECRET/MCP_AUTH_TOKEN) -- an
# existence-only check here would wrongly treat that stub as satisfying
# docs/phase-c-runbook.md S2's "Copy 3", which also needs MODEL_API_KEY
# and the four MODEL_*_URL/NAME keys, none of which have a ConfigMap
# fallback for the API key. Check for the specific key that matters
# instead of mere secret existence.
#
# Second real gap found live, running the pipeline itself (deploy-ephemeral
# failed CreateContainerConfigError): golden-path-agent-ci-config, a plain
# ConfigMap (not a Secret -- MODEL_API_BASE_URL/MODEL_NAME/MODEL_FALLBACK_*
# are not credential material) read by both deploy-ephemeral and
# eval-gate-live, was never created by anything in pipelines/bootstrap/
# and never documented in docs/phase-c-runbook.md despite deploy-ephemeral.yaml's
# own header comment calling it "C1a bootstrap" -- evidently created by
# hand on the SNO at some point and never captured. Now documented in
# docs/phase-c-runbook.md S2b and checked here.
NEEDS_MANUAL=false
if ! oc get secret golden-path-agent-secrets -n golden-path-agent-demo-prod \
    -o jsonpath='{.data.MODEL_API_KEY}' 2>/dev/null | grep -q .; then
  NEEDS_MANUAL=true
  log "  missing: golden-path-agent-secrets (MODEL_API_KEY) in golden-path-agent-demo-prod -- docs/phase-c-runbook.md S2"
fi
if ! oc get configmap golden-path-agent-ci-config -n golden-path-agent-ci >/dev/null 2>&1; then
  NEEDS_MANUAL=true
  log "  missing: golden-path-agent-ci-config in golden-path-agent-ci -- docs/phase-c-runbook.md S2b"
fi
if [ "$NEEDS_MANUAL" = "true" ]; then
  cat <<'EOF'

[bootstrap.sh] STOPPING -- manual secret/config provisioning required
before demo-prod can sync a working pod and before deploy-ephemeral can
run (docs/phase-c-runbook.md S2 and S2b have the exact commands).

S3 (golden-path-agent-github-token, open-promotion-pr's PAT) is optional
-- NOTE (DEC-078): this session's Option 2 does not grant this cluster's
pipeline promotion authority over the shared main digest pin regardless
of whether that secret exists; any resulting PR gets closed unmerged.

Re-run this script with the same kubeconfig once the items above exist
-- every step above is idempotent and will skip straight through.
EOF
  exit 0
fi
log "model-endpoint secret and CI config present, continuing"

log "=== step 7/9: pipeline + task definitions ==="
# Real gap found live: applying pipelines/pipeline.yaml and
# pipelines/tasks/*.yaml was never written down anywhere in this
# project's docs or scripts -- on the SNO this was evidently done ad hoc
# during Phase C's own live session and never captured. Without this, a
# PipelineRun fails immediately with CouldntGetPipeline.
oc apply -f pipelines/pipeline.yaml -n golden-path-agent-ci
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

log "=== step 9/9: verification ==="
sleep 5
oc get applications.argoproj.io -n openshift-gitops

END_EPOCH=$(date -u +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
log "bootstrap sequence complete in ${ELAPSED}s ($((ELAPSED / 60))m elapsed this run)"
