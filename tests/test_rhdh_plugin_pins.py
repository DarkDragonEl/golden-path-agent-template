"""DEC-143/DEC-145: RHDH's remote plugins are pinned, and pinned in one
place each. The Gitea scaffolder plugin's digest lives in
platform/rhdh-plugins/gitea-scaffolder/pin.env (bootstrap reads it) and
PINS.md (people read it); the two must agree. Every other OCI plugin in
the GitOps-synced plugin config is digest-pinned -- `{{inherit}}` only for
Red Hat's own registry, whose digests the operator's catalog index pins."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PIN_ENV = REPO_ROOT / "platform" / "rhdh-plugins" / "gitea-scaffolder" / "pin.env"
PLUGINS_CONFIG = REPO_ROOT / "deploy" / "kustomize" / "overlays" / "rhdh" / "dynamic-plugins-config.yaml"
GITEA_PINS_ROW = "Gitea scaffolder dynamic plugin (built image)"


def _pin_env() -> dict:
    values = {}
    for line in PIN_ENV.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def _plugins() -> list[dict]:
    configmap = yaml.safe_load(PLUGINS_CONFIG.read_text(encoding="utf-8"))
    return yaml.safe_load(configmap["data"]["dynamic-plugins.yaml"])["plugins"]


def test_gitea_plugin_digest_agrees_between_pin_env_and_pins_md():
    digest = _pin_env()["PLUGIN_DIGEST"]
    rows = [line for line in (REPO_ROOT / "PINS.md").read_text(encoding="utf-8").splitlines() if GITEA_PINS_ROW in line]
    assert len(rows) == 1, f"expected exactly one PINS.md row for {GITEA_PINS_ROW!r}"
    row_digests = re.findall(r"sha256:[0-9a-f]{64}", rows[0])
    if digest:
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest), digest
        assert row_digests == [digest], f"PINS.md row {row_digests} != pin.env {digest}"
    else:
        assert not row_digests and "not built yet" in rows[0], "pin.env is unpinned, so PINS.md must say 'not built yet'"


def test_every_remote_plugin_is_digest_pinned():
    for plugin in _plugins():
        package = plugin["package"]
        if not package.startswith("oci://"):
            continue
        if package.endswith(":{{inherit}}"):
            assert package.startswith("oci://registry.access.redhat.com/"), package
        else:
            assert re.search(r"@sha256:[0-9a-f]{64}(!|$)", package), f"not digest-pinned: {package}"


def test_tekton_and_community_argocd_are_enabled():
    enabled = {p["package"] for p in _plugins() if not p.get("disabled", False)}
    for name in ("backstage-community-plugin-tekton@", "backstage-community-plugin-argocd-backend@",
                 "backstage-community-plugin-argocd@"):
        assert any(name in pkg for pkg in enabled), f"{name} not enabled"
    assert not any("roadiehq-backstage-plugin-argo-cd" in pkg for pkg in enabled), "mixing Argo CD families"


def test_gitea_plugin_registry_is_not_committed():
    """The Gitea plugin comes only from the bootstrap-rendered include
    (RHDH_PLUGIN_REGISTRY is an operator input, DEC-145)."""
    assert not any("scaffolder-backend-module-gitea" in p["package"] for p in _plugins())
    configmap = yaml.safe_load(PLUGINS_CONFIG.read_text(encoding="utf-8"))
    includes = yaml.safe_load(configmap["data"]["dynamic-plugins.yaml"])["includes"]
    assert "/opt/app-root/src/gitea-plugin/dynamic-plugins.gitea.yaml" in includes
