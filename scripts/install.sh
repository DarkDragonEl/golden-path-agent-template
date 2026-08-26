#!/usr/bin/env bash
# scripts/install.sh
#
# One-button fresh-OpenShift-cluster install path for the golden-path-agent
# blueprint. This is a PURE SEQUENCER: it adds no bootstrap logic of its
# own beyond ordering these two existing scripts and the interactive
# confirmation below. All real work happens inside:
#
#   1. scripts/bootstrap.sh <kubeconfig-path>
#      -- operators, namespaces, RBAC, Keycloak, cluster-tier OTel,
#         pipeline/task definitions, the ArgoCD app-of-apps root.
#   2. platform/bootstrap/provision-identity-secrets.sh
#      -- OIDC client secrets + demo-user passwords (DECISIONS.md
#         DEC-059: idempotent BY REGENERATION -- every run rotates fresh
#         values, there is no "only if missing" branch).
#
# NOTE ON THE TWO-CALL SHAPE: scripts/bootstrap.sh's own step 5/9 already
# calls platform/bootstrap/provision-identity-secrets.sh once,
# non-interactively, as part of its own unattended sequence (bootstrap.sh
# is designed to run end to end with no prompts). This wrapper calls the
# same script again, explicitly, afterward -- gated behind the
# confirmation below -- so a human operator running this one-button path
# always sees and confirms the credential-rotation warning at least once.
# Re-running it is safe by design (DEC-059); the cost is one extra
# rotation, not a correctness problem.
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

Runs the fresh-OpenShift-cluster install path end to end, in order:
  1. scripts/bootstrap.sh <kubeconfig-path>
  2. platform/bootstrap/provision-identity-secrets.sh

<kubeconfig-path> is forwarded to scripts/bootstrap.sh exactly as that
script expects it: an already-authenticated kubeconfig. Like
scripts/bootstrap.sh, this wrapper never runs `oc login` -- authenticate
before running this script.

--yes   Skip the interactive confirmation before step 2 (the
        credential-rotating script). Both scripts still run, in order,
        either way -- this flag removes only the prompt, never a step.

This wrapper adds no logic beyond this sequencing: it never passes
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

# provision-identity-secrets.sh (step 2) takes no kubeconfig argument of
# its own -- it expects KUBECONFIG already set in its environment, the
# same way scripts/bootstrap.sh's own internal call to it relies on that
# script's `export KUBECONFIG="$1"`. Exporting it here is wiring, not new
# decision logic: without it, step 2's own `oc` calls would silently fall
# back to the ambient default kubeconfig instead of the cluster this
# script was told to target.
export KUBECONFIG="$KUBECONFIG_PATH"

log "step 1/2: scripts/bootstrap.sh $KUBECONFIG_PATH"
if ! ./scripts/bootstrap.sh "$KUBECONFIG_PATH"; then
  echo "[install.sh] FAILED: scripts/bootstrap.sh exited non-zero -- stopping, not continuing to identity-secret provisioning." >&2
  exit 1
fi

if [ "$SKIP_CONFIRM" != "true" ]; then
  cat >&2 <<'WARNING'

[install.sh] WARNING (DECISIONS.md DEC-059): about to run
platform/bootstrap/provision-identity-secrets.sh. This ROTATES the OIDC
client secrets and demo-user passwords every time it runs -- there is no
"only if missing" branch. Any live session using the current credentials
will be invalidated. Safe on a fresh install; on an already-live cluster,
anyone currently signed in will be signed out.

WARNING
  printf '[install.sh] Type "yes" to continue: ' >&2
  read -r CONFIRM
  if [ "$CONFIRM" != "yes" ]; then
    echo "[install.sh] aborted before identity-secret provisioning (no confirmation given)." >&2
    exit 1
  fi
fi

log "step 2/2: platform/bootstrap/provision-identity-secrets.sh"
if ! ./platform/bootstrap/provision-identity-secrets.sh; then
  echo "[install.sh] FAILED: platform/bootstrap/provision-identity-secrets.sh exited non-zero." >&2
  exit 1
fi

log "install complete."
