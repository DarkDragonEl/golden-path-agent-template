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
usage: bootstrap.sh <kubeconfig-path> [--reenable-sync] [--with-rhdh] [--constrained-node]

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

--with-rhdh (DEC-092): opt-in RHDH Operator install (cluster-scoped,
AllNamespaces) plus its Postgres credentials Secret -- opt-in because it
carries real cluster-wide visibility cost a plain namespace/client does
not.

--constrained-node: shared/single-node profile (docs/cluster-profile.md)
-- lowers this project's own CPU/memory *requests* to a few tens of
millicores and a few dozen Mi (limits unchanged, Burstable QoS), since
scheduling on a busy shared node is gated by requests, not actual
usage. Applies deploy/kustomize/overlays/constrained-node/ and
.../approval-platform-constrained-node/ instead of demo-prod/
approval-platform directly (via a live-only ArgoCD Application
source.path patch, safe only because ADR-009's freeze already means
golden-path-agent-root's own auto-sync won't revert it), patches
platform/bootstrap/{keycloak-postgres,keycloak-cr,otel-collector}.yaml
in place after their normal apply, and (with --with-rhdh) points
golden-path-agent-rhdh at .../rhdh-constrained-node/ the same way. The
committed base manifests themselves are never changed by this flag.
USAGE
  exit 1
}

[ $# -ge 1 ] || usage
[ -r "$1" ] || { echo "[bootstrap.sh] kubeconfig not readable: $1" >&2; exit 1; }
export KUBECONFIG="$1"
REENABLE_SYNC=false
WITH_RHDH=false
CONSTRAINED_NODE=false
for arg in "${@:2}"; do
  case "$arg" in
    --reenable-sync) REENABLE_SYNC=true ;;
    --with-rhdh) WITH_RHDH=true ;;
    --constrained-node) CONSTRAINED_NODE=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

START_EPOCH=$(date -u +%s)
log() { echo "[bootstrap.sh $(date -u '+%H:%M:%S')] $*"; }

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

approve_pending_installplan_for_subscription() {
  # $1 = namespace, $2 = Subscription name. Approves whichever
  # InstallPlan that Subscription's own status currently references --
  # scoped to this one Subscription, never a blanket approval of
  # unrelated plans (DEC-055/DEC-080 discipline).
  local ns="$1" sub="$2" plan approved
  plan=$(oc get subscription "$sub" -n "$ns" -o jsonpath='{.status.installPlanRef.name}' 2>/dev/null || echo "")
  [ -n "$plan" ] || return 0
  approved=$(oc get installplan "$plan" -n "$ns" -o jsonpath='{.spec.approved}' 2>/dev/null || echo "")
  if [ "$approved" != "true" ]; then
    log "  approving InstallPlan $plan (subscription $sub) in $ns"
    oc patch installplan "$plan" -n "$ns" --type merge -p '{"spec":{"approved":true}}' >/dev/null
  fi
}

ensure_operator() {
  # $1 = namespace, $2 = human label, $3 = fresh-install manifest path
  # (exact startingCSV, used only when nothing pre-exists), $4 =
  # Subscription/package name, $5 = expected channel, $6 = minimum
  # acceptable version, $7 = timeout seconds.
  #
  # Adopter-provided discipline (DEC-135 addendum, docs/cluster-profile.md):
  # a Subscription for this exact package may already exist on the
  # target cluster -- installed by the adopter, or by a prior run of
  # this script -- not created by this invocation. Never reapply this
  # blueprint's own Subscription manifest onto one that already exists;
  # doing so could silently change its channel or approval settings.
  # Detect it, verify it meets the minimum version on the expected
  # channel, and let OLM finish an in-progress upgrade if it hasn't yet
  # -- install fresh only when no such Subscription exists at all.
  local ns="$1" label="$2" manifest="$3" name="$4" channel="$5" min_version="$6" timeout="$7"
  local existing_channel installed_csv installed_version waited=0 phase

  if oc get subscription "$name" -n "$ns" >/dev/null 2>&1; then
    existing_channel=$(oc get subscription "$name" -n "$ns" -o jsonpath='{.spec.channel}' 2>/dev/null || echo "")
    if [ "$existing_channel" != "$channel" ]; then
      log "$label: Subscription $name already exists in $ns on channel '$existing_channel', not this blueprint's expected '$channel' -- leftover-state case (docs/cluster-profile.md), not touching it. Resolve manually before continuing."
      return 1
    fi
    log "$label: Subscription $name already exists in $ns on the expected channel '$channel' -- treating as adopter-provided, not reapplying $manifest"
  else
    log "$label: no existing Subscription $name in $ns -- applying $manifest"
    oc apply -f "$manifest"
  fi

  while true; do
    installed_csv=$(oc get subscription "$name" -n "$ns" -o jsonpath='{.status.installedCSV}' 2>/dev/null || echo "")
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
    approve_pending_installplan_for_subscription "$ns" "$name"
    if [ "$waited" -ge "$timeout" ]; then
      log "  $name: still '${installed_csv:-<no CSV yet>}' (phase '${phase:-<none>}') after ${timeout}s -- not waiting further"
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
    --type strategic --patch-file platform/bootstrap/constrained-node-patches/keycloak-postgres.yaml >/dev/null
  oc patch keycloak golden-path-agent -n golden-path-agent-keycloak \
    --type merge --patch-file platform/bootstrap/constrained-node-patches/keycloak-cr.yaml >/dev/null
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
    --type strategic --patch-file platform/bootstrap/constrained-node-patches/otel-collector.yaml >/dev/null
fi

if [ "$WITH_RHDH" = "true" ]; then
  log "=== step 4b/9 (--with-rhdh, Phase F4, DEC-092): RHDH operator + Postgres secret ==="
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

S3 (golden-path-agent-github-token) is optional -- DEC-078: this
cluster's pipeline never gets promotion authority over the shared main
digest pin regardless; any resulting PR is closed unmerged.

Re-run this script with the same kubeconfig once the items above exist
-- every step above is idempotent and will skip straight through.
EOF
  exit 0
fi
log "model-endpoint secret and CI config present, continuing"

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
    deploy/kustomize/overlays/constrained-node "demo-prod"
  patch_app_path golden-path-agent-approval \
    deploy/kustomize/overlays/approval-platform-constrained-node "approval-platform"
  if [ "$WITH_RHDH" = "true" ]; then
    patch_app_path golden-path-agent-rhdh \
      deploy/kustomize/overlays/rhdh-constrained-node "rhdh"
  fi
fi

log "=== step 9/9: verification ==="
sleep 5
oc get applications.argoproj.io -n openshift-gitops

END_EPOCH=$(date -u +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
log "bootstrap sequence complete in ${ELAPSED}s ($((ELAPSED / 60))m elapsed this run)"
