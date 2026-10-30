#!/usr/bin/env bash
# DEC-144 (M16): builds RHDH's Gitea scaffolder dynamic plugin
# (@backstage/plugin-scaffolder-backend-module-gitea, backstage v1.49.0 --
# matched to RHDH 1.10.3's backend, DEC-118) with Red Hat's
# rhdh-dynamic-plugin-factory, pushes it to an external registry, and
# prints the pushed digest. Run on an operator workstation, never in a
# cloud session: it pushes with the operator's own registry login.
#
# Usage:
#   podman login <registry-host>     # once; the push reuses this login
#   RHDH_PLUGIN_REGISTRY=<registry-host>/<namespace> ./build.sh [--write-pin]
#
# --write-pin records the digest in pin.env. PINS.md's matching row is
# updated by hand (the script prints it); tests/test_rhdh_plugin_pins.py
# fails until both agree. Phase 2 (in-cluster build) is not this script.
#
# Requires: podman (with /dev/fuse), git, skopeo.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# Pinned factory image: the RHDH-1.10 build of the tool (PINS.md, Phase G Stage 3).
FACTORY_IMAGE="quay.io/rhdh-community/dynamic-plugins-factory:1.10@sha256:ab3ab5eb73ba2f2080697f334478b9987c68468ce878d18802a4baeb90dac96c"
BACKSTAGE_REPO="https://github.com/backstage/backstage"
BACKSTAGE_REF="v1.49.0"

WRITE_PIN=false
[ "${1:-}" = "--write-pin" ] && WRITE_PIN=true

: "${RHDH_PLUGIN_REGISTRY:?set RHDH_PLUGIN_REGISTRY=<registry-host>/<namespace> (never committed)}"
case "$RHDH_PLUGIN_REGISTRY" in
  */*) ;;
  *) echo "RHDH_PLUGIN_REGISTRY must be <registry-host>/<namespace>, got '$RHDH_PLUGIN_REGISTRY'" >&2; exit 1 ;;
esac
for tool in podman git skopeo; do
  command -v "$tool" >/dev/null || { echo "missing required tool: $tool" >&2; exit 1; }
done
REGISTRY_URL="${RHDH_PLUGIN_REGISTRY%%/*}"
REGISTRY_NAMESPACE="${RHDH_PLUGIN_REGISTRY#*/}"

# The factory's push reads credentials from an auth file; reuse the
# operator's own `podman login` (never a password on the command line).
AUTH_FILE="${REGISTRY_AUTH_FILE:-${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/containers/auth.json}"
[ -r "$AUTH_FILE" ] || { echo "no registry auth file at $AUTH_FILE -- run 'podman login $REGISTRY_URL' first (or set REGISTRY_AUTH_FILE)" >&2; exit 1; }

# shellcheck disable=SC1091 # pin.env lives next to this script
. "$HERE/pin.env"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/outputs"
cp -r "$HERE/config" "$WORK/config"

# Shallow clone + --use-local: the factory's own clone is a full,
# unshallowed backstage/backstage history (~7GB, DEC-118).
git clone -q --depth 1 --branch "$BACKSTAGE_REF" "$BACKSTAGE_REPO" "$WORK/source"
SOURCE_VERSION=$(sed -n 's/^ *"version": *"\([^"]*\)".*/\1/p' "$WORK/source/plugins/scaffolder-backend-module-gitea/package.json" | head -1)
if [ "$SOURCE_VERSION" != "$PLUGIN_VERSION" ]; then
  echo "pin.env says PLUGIN_VERSION=$PLUGIN_VERSION but $BACKSTAGE_REF ships $SOURCE_VERSION -- update pin.env deliberately, don't build a surprise" >&2
  exit 1
fi

podman run --rm \
  --device /dev/fuse \
  -v "$WORK/config:/config:z" \
  -v "$WORK/source:/source:z" \
  -v "$WORK/outputs:/outputs:z" \
  -v "$AUTH_FILE:/auth.json:ro,z" \
  -e REGISTRY_AUTH_FILE=/auth.json \
  -e REGISTRY_URL="$REGISTRY_URL" \
  -e REGISTRY_NAMESPACE="$REGISTRY_NAMESPACE" \
  "$FACTORY_IMAGE" \
  --use-local --workspace-path . --push-images

IMAGE_REF="${RHDH_PLUGIN_REGISTRY}/${PLUGIN_IMAGE_NAME}:${PLUGIN_VERSION}"
DIGEST=$(skopeo inspect --authfile "$AUTH_FILE" --format '{{.Digest}}' "docker://${IMAGE_REF}")
case "$DIGEST" in
  sha256:*) ;;
  *) echo "could not resolve a digest for $IMAGE_REF (got '$DIGEST')" >&2; exit 1 ;;
esac

echo
echo "pushed:  ${IMAGE_REF}"
echo "digest:  ${DIGEST}"
if [ "$WRITE_PIN" = "true" ]; then
  sed -i "s/^PLUGIN_DIGEST=.*/PLUGIN_DIGEST=${DIGEST}/" "$HERE/pin.env"
  echo "pin.env: PLUGIN_DIGEST updated"
fi
echo "PINS.md: set the 'Gitea scaffolder dynamic plugin (built image)' row's digest to ${DIGEST}"
