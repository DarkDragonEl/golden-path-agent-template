#!/usr/bin/env bash
# scripts/install.sh
#
# One-button fresh-OpenShift-cluster install path for the golden-path-agent
# blueprint. This is a PURE SEQUENCER: it adds no bootstrap logic of its
# own beyond the interactive confirmation below and a single call to:
#
#   scripts/bootstrap.sh <kubeconfig-path>
#     -- operators, namespaces, RBAC, Keycloak, cluster-tier OTel,
#        pipeline/task definitions, the ArgoCD app-of-apps root, AND
#        (its own internal step 5/9) platform/bootstrap/provision-
#        identity-secrets.sh -- OIDC client secrets + demo-user
#        passwords (DECISIONS.md DEC-059: idempotent BY REGENERATION --
#        every run rotates fresh values, there is no "only if missing"
#        branch).
#
# ONLY ONE CALL, DELIBERATELY: bootstrap.sh's own step 5/9 already invokes
# provision-identity-secrets.sh once, non-interactively, as an inseparable
# part of its own sequence -- that is the run that actually rotates
# credentials and invalidates any live session. Calling
# provision-identity-secrets.sh a second time afterward would not add
# safety (the rotation already happened, unconditionally, inside
# bootstrap.sh) -- it would only rotate an already-fresh value again,
# and worse, it would put this wrapper's confirmation prompt AFTER the
# consequential rotation instead of before it. This wrapper's
# confirmation therefore gates the single call to bootstrap.sh itself,
# not a second script.
#
# This script NEVER passes --reenable-sync to bootstrap.sh, by default or
# via any flag defined here. That flag reverses a cluster-local auto-sync
# freeze (DECISIONS.md DEC-083) and is the cluster operator's own
# deliberate, explicit call -- never a choice a one-button installer
# should make on their behalf. Need it (or --with-rhdh)? Run
# scripts/bootstrap.sh directly -- see its own usage text.
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: install.sh <kubeconfig-path> [--yes]

Runs the fresh-OpenShift-cluster install path: scripts/bootstrap.sh
<kubeconfig-path>, which itself provisions identity secrets as one of
its own steps (DECISIONS.md DEC-059) -- rotating them every run, with no
"only if missing" branch.

<kubeconfig-path> is forwarded to scripts/bootstrap.sh exactly as that
script expects it: an already-authenticated kubeconfig. Like
scripts/bootstrap.sh, this wrapper never runs `oc login` -- authenticate
before running this script.

--yes   Skip the interactive confirmation before running bootstrap.sh.
        bootstrap.sh still runs either way -- this flag removes only the
        prompt, never the step.

This wrapper adds no logic beyond that confirmation: it never passes
--reenable-sync or --with-rhdh to scripts/bootstrap.sh. For either of
those, run scripts/bootstrap.sh directly instead of this script.
USAGE
  exit 1
}

[ $# -ge 1 ] || usage

KUBECONFIG_PATH=""
SKIP_CONFIRM=false
for arg in "$@"; do
  case "$arg" in
    --yes) SKIP_CONFIRM=true ;;
    -h|--help) usage ;;
    -*)
      echo "[install.sh] unrecognized flag: $arg" >&2
      usage
      ;;
    *)
      if [ -z "$KUBECONFIG_PATH" ]; then
        KUBECONFIG_PATH="$arg"
      else
        echo "[install.sh] unexpected extra argument: $arg" >&2
        usage
      fi
      ;;
  esac
done

[ -n "$KUBECONFIG_PATH" ] || usage

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

log() { echo "[install.sh] $*"; }

if [ "$SKIP_CONFIRM" != "true" ]; then
  cat >&2 <<'WARNING'

[install.sh] WARNING (DECISIONS.md DEC-059): scripts/bootstrap.sh's own
step 5/9 runs platform/bootstrap/provision-identity-secrets.sh
unconditionally. That script ROTATES the OIDC client secrets and
demo-user passwords every time it runs -- there is no "only if missing"
branch. Any live session using the current credentials will be
invalidated. Safe on a fresh install; on an already-live cluster, anyone
currently signed in will be signed out.

WARNING
  printf '[install.sh] Type "yes" to continue: ' >&2
  read -r CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "[install.sh] aborted before running scripts/bootstrap.sh (no confirmation given)." >&2
    exit 1
  fi
fi

log "running scripts/bootstrap.sh $KUBECONFIG_PATH"
if ! ./scripts/bootstrap.sh "$KUBECONFIG_PATH"; then
  echo "[install.sh] FAILED: scripts/bootstrap.sh exited non-zero." >&2
  exit 1
fi

log "install complete."
