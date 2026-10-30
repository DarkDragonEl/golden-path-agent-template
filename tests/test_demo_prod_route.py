"""DEC-149 (M22): demo-prod's host-less agent Route is Argo CD-managed.

Four pieces must stay wired together or the Route either never syncs
(not whitelisted), gets fought over (host not ignored), or is applied
twice (bootstrap still applies it). Pure YAML/text checks; the rendered
object itself is covered by test_overlays_build.py.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ROUTE = ROOT / "deploy/kustomize/overlays/demo-prod/route-agent.yaml"


def _load(rel: str) -> dict:
    return yaml.safe_load((ROOT / rel).read_text())


def test_route_is_hostless_and_in_the_demo_prod_overlay():
    route = yaml.safe_load(ROUTE.read_text())
    assert route["kind"] == "Route"
    assert "host" not in route["spec"], "a committed host would be environment-specific (ADR-016)"
    overlay = _load("deploy/kustomize/overlays/demo-prod/kustomization.yaml")
    assert "route-agent.yaml" in overlay["resources"]


def test_appproject_whitelists_route():
    project = _load("deploy/argocd/project.yaml")
    assert {"group": "route.openshift.io", "kind": "Route"} in project["spec"]["namespaceResourceWhitelist"]


def test_application_ignores_assigned_host_and_respects_it():
    spec = _load("deploy/argocd/apps/demo-prod.yaml")["spec"]
    assert "RespectIgnoreDifferences=true" in spec["syncPolicy"]["syncOptions"]
    ignored = [
        pointer
        for rule in spec["ignoreDifferences"]
        if rule["group"] == "route.openshift.io" and rule["kind"] == "Route"
        for pointer in rule["jsonPointers"]
    ]
    assert "/spec/host" in ignored


def test_bootstrap_no_longer_applies_the_agent_route():
    assert not (ROOT / "pipelines/bootstrap/demo-prod-route.yaml").exists()
    assert "demo-prod-route" not in (ROOT / "scripts/bootstrap.sh").read_text()
