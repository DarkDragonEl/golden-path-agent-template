"""Step 3's upstream-kustomize Keycloak fallback must not replace the
`k8s.keycloak.org` CRDs another operator owns (guard in scripts/bootstrap.sh).

`scripts/bootstrap.sh` runs its steps at top level, so it cannot be
sourced whole. These tests extract `apply_rhbk_upstream_fallback` and
`foreign_keycloak_crd_owners` by name and run them under bash against a
stub `oc` on PATH -- no cluster, no network, same hermetic pattern as
test_provision_identity_secrets.py.
"""

import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.sh"
UPSTREAM = "platform/bootstrap/keycloak-operator-upstream/"
OWN_NS = "golden-path-agent-keycloak"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="needs bash and jq (both required by bootstrap.sh itself)",
)

# Answers `oc get csv -A -o json` from $STUB_CSV_JSON (or fails when
# $STUB_CSV_FAIL is set); logs every call as one JSON line.
STUB_OC = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys

    args = sys.argv[1:]
    with open(os.environ["STUB_LOG"], "a") as log:
        log.write(json.dumps(args) + "\\n")

    if args[:2] == ["get", "csv"]:
        if os.environ.get("STUB_CSV_FAIL"):
            print("error: forbidden", file=sys.stderr)
            sys.exit(1)
        print(open(os.environ["STUB_CSV_JSON"]).read())
"""
)


def _function_source(name: str) -> str:
    text = BOOTSTRAP.read_text()
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.S | re.M)
    assert match, f"{name}() is not defined at the top level of scripts/bootstrap.sh"
    return match.group(0)


def _csv(namespace: str, name: str, owned=("keycloaks.k8s.keycloak.org",), reason=None) -> dict:
    status = {"phase": "Succeeded"}
    if reason:
        status = {"phase": "Succeeded", "reason": reason}
    return {
        "metadata": {"namespace": namespace, "name": name},
        "spec": {"customresourcedefinitions": {"owned": [{"name": n} for n in owned]}},
        "status": status,
    }


def _run(tmp_path, csvs, fail_list=False):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    oc = bindir / "oc"
    oc.write_text(STUB_OC.format(python=sys.executable))
    oc.chmod(0o755)
    csv_json = tmp_path / "csv.json"
    csv_json.write_text(json.dumps({"items": csvs}))
    calls = tmp_path / "calls.log"
    harness = tmp_path / "harness.sh"
    harness.write_text(
        "set -euo pipefail\n"
        'log() { echo "[t] $*"; }\n'
        + _function_source("foreign_keycloak_crd_owners")
        + _function_source("apply_rhbk_upstream_fallback")
        + "apply_rhbk_upstream_fallback\n"
    )
    env = {
        "PATH": f"{bindir}:/usr/bin:/bin",
        "STUB_LOG": str(calls),
        "STUB_CSV_JSON": str(csv_json),
    }
    if fail_list:
        env["STUB_CSV_FAIL"] = "1"
    proc = subprocess.run(
        ["bash", str(harness)], cwd=REPO_ROOT, env=env, capture_output=True, text=True
    )
    logged = (
        [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    )
    return proc, logged


def _applied_upstream(logged) -> bool:
    return ["apply", "-k", UPSTREAM] in logged


def test_foreign_owner_refuses_and_never_applies(tmp_path):
    proc, logged = _run(
        tmp_path,
        [_csv("keycloak", "rhbk-operator.v26.4.16-opr.1")],
    )
    assert proc.returncode != 0
    assert not _applied_upstream(logged)
    assert not any(c[:1] == ["apply"] for c in logged)
    out = proc.stdout + proc.stderr
    assert "keycloak/rhbk-operator.v26.4.16-opr.1" in out
    assert "replace" in out and "CRD" in out


def test_foreign_owner_is_found_even_beside_a_copied_csv(tmp_path):
    proc, logged = _run(
        tmp_path,
        [
            _csv("other-ns", "rhbk-operator.v26.4.16-opr.1", reason="Copied"),
            _csv("keycloak", "rhbk-operator.v26.4.16-opr.1"),
        ],
    )
    assert proc.returncode != 0
    assert not _applied_upstream(logged)
    assert "other-ns/" not in proc.stdout + proc.stderr


def test_unreadable_csv_list_fails_closed(tmp_path):
    proc, logged = _run(tmp_path, [], fail_list=True)
    assert proc.returncode != 0
    assert not _applied_upstream(logged)


def test_only_copied_csvs_let_the_fallback_run(tmp_path):
    proc, logged = _run(
        tmp_path,
        [
            _csv("ns-a", "rhbk-operator.v26.4.16-opr.1", reason="Copied"),
            _csv("ns-b", "rhbk-operator.v26.4.16-opr.1", reason="Copied"),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _applied_upstream(logged)


def test_no_csv_lets_the_fallback_run(tmp_path):
    proc, logged = _run(tmp_path, [])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _applied_upstream(logged)


def test_own_namespace_and_unrelated_crds_do_not_block(tmp_path):
    proc, logged = _run(
        tmp_path,
        [
            _csv(OWN_NS, "rhbk-operator.v26.6.6-opr.1"),
            _csv("cert-manager", "cert-manager.v1", owned=("certificates.cert-manager.io",)),
            _csv("keycloak", "other-op.v1", owned=("keycloakrealmimports.k8s.keycloak.org",)),
        ],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _applied_upstream(logged)


def test_the_only_upstream_apply_is_inside_the_guarded_function():
    text = BOOTSTRAP.read_text()
    applies = [m.start() for m in re.finditer(r"oc apply -k " + re.escape(UPSTREAM), text)]
    assert len(applies) == 1, "exactly one upstream-kustomize apply is expected"
    func = re.search(
        r"^apply_rhbk_upstream_fallback\(\) \{\n.*?^\}\n", text, re.S | re.M
    )
    assert func, "apply_rhbk_upstream_fallback() is not defined"
    body = func.group(0)
    assert "foreign_keycloak_crd_owners" in body
    assert body.index("foreign_keycloak_crd_owners") < body.index("oc apply -k"), (
        "the owner check must run before the upstream apply"
    )
    assert "apply_rhbk_upstream_fallback ||" in text or "if ! apply_rhbk_upstream_fallback" in text, (
        "step 3 must stop when the guarded fallback refuses"
    )
