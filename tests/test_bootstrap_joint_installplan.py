"""Step 1's InstallPlan approver and joint plans, run under bash against a
stub `oc` on PATH -- no cluster, no network, same hermetic pattern as
test_bootstrap_rhbk_fallback_guard.py.

OLM bundles several pending Manual upgrades into one InstallPlan. The
approver may approve such a joint plan only when every extra CSV is the
current CSV of a Subscription for one of this blueprint's own operator
packages, on the channel `ensure_operator` is called with. Anything else
is refused, and so is any read that fails.
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
NS = "openshift-operators"
PIPELINES = "openshift-pipelines-operator-rh"
GITOPS = "openshift-gitops-operator"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="needs bash and jq (both required by bootstrap.sh itself)",
)

# Serves the three reads the approver makes from JSON files and logs every
# call. $STUB_FAIL = "plans" or "subs" makes that list unreadable.
STUB_OC = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys

    args = sys.argv[1:]
    with open(os.environ["STUB_LOG"], "a") as log:
        log.write(json.dumps(args) + "\\n")

    fail = os.environ.get("STUB_FAIL", "")
    subs = json.load(open(os.environ["STUB_SUBS_JSON"]))["items"]
    plans = json.load(open(os.environ["STUB_PLANS_JSON"]))["items"]

    def boom():
        print("error: forbidden", file=sys.stderr)
        sys.exit(1)

    if args[:2] == ["get", "subscription"]:
        if args[2] == "-n" or args[2].startswith("-"):
            if fail == "subs":
                boom()
            print(json.dumps({{"items": subs}}))
        else:
            sub = next(s for s in subs if s["metadata"]["name"] == args[2])
            print(sub.get("status", {{}}).get("currentCSV", ""), end="")
    elif args[:2] == ["get", "installplan"]:
        if fail == "plans":
            boom()
        if args[2].startswith("-"):
            print(json.dumps({{"items": plans}}))
        else:
            plan = next(p for p in plans if p["metadata"]["name"] == args[2])
            if any("jsonpath" in a for a in args):
                print(str(plan["spec"].get("approved", False)).lower(), end="")
            else:
                print(json.dumps(plan))
    elif args[:2] == ["patch", "installplan"]:
        pass
"""
)

CONSTANTS = re.compile(r"^(?:PIPELINES|GITOPS|RHDH)_(?:PKG|CHANNEL)=.*\n", re.M)


def _function_source(name: str, optional: bool = False) -> str:
    text = BOOTSTRAP.read_text()
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.S | re.M)
    if not match:
        assert optional, f"{name}() is not defined at the top level of scripts/bootstrap.sh"
        return ""
    return match.group(0)


def _sub(name, pkg, channel, current):
    return {
        "metadata": {"name": name},
        "spec": {"name": pkg, "channel": channel},
        "status": {"currentCSV": current},
    }


def _plan(name, csvs, approved=False):
    return {
        "metadata": {"name": name},
        "spec": {"approved": approved, "clusterServiceVersionNames": csvs},
    }


GITOPS_CSV = "openshift-gitops-operator.v1.20.6"
PIPELINES_CSV = "openshift-pipelines-operator-rh.v1.22.7"
GITOPS_SUB = _sub(GITOPS, GITOPS, "gitops-1.20", GITOPS_CSV)
PIPELINES_SUB = _sub(PIPELINES, PIPELINES, "pipelines-1.22", PIPELINES_CSV)


def _run(tmp_path, subs, plans, fail=""):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    oc = bindir / "oc"
    oc.write_text(STUB_OC.format(python=sys.executable))
    oc.chmod(0o755)
    (tmp_path / "subs.json").write_text(json.dumps({"items": subs}))
    (tmp_path / "plans.json").write_text(json.dumps({"items": plans}))
    calls = tmp_path / "calls.log"
    text = BOOTSTRAP.read_text()
    harness = tmp_path / "harness.sh"
    harness.write_text(
        "set -euo pipefail\n"
        'log() { echo "[t] $*"; }\n'
        + "".join(CONSTANTS.findall(text))
        + _function_source("blueprint_operator_channel", optional=True)
        + _function_source("joint_plan_extra_accepted", optional=True)
        + _function_source("approve_pending_installplan_for_package")
        + f"approve_pending_installplan_for_package {NS} {GITOPS}\n"
    )
    env = {
        "PATH": f"{bindir}:/usr/bin:/bin",
        "STUB_LOG": str(calls),
        "STUB_SUBS_JSON": str(tmp_path / "subs.json"),
        "STUB_PLANS_JSON": str(tmp_path / "plans.json"),
        "STUB_FAIL": fail,
    }
    proc = subprocess.run(
        ["bash", str(harness)], cwd=REPO_ROOT, env=env, capture_output=True, text=True
    )
    logged = (
        [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []
    )
    return proc, logged


def _patched(logged):
    return [c for c in logged if c[:2] == ["patch", "installplan"]]


def test_plan_with_no_extra_csv_is_approved(tmp_path):
    proc, logged = _run(tmp_path, [GITOPS_SUB], [_plan("ip-1", [GITOPS_CSV])])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [c[2] for c in _patched(logged)] == ["ip-1"]


def test_joint_plan_with_blueprint_package_on_its_channel_is_approved(tmp_path):
    proc, logged = _run(
        tmp_path,
        [GITOPS_SUB, PIPELINES_SUB],
        [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV])],
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [c[2] for c in _patched(logged)] == ["ip-joint"]
    out = proc.stdout
    assert PIPELINES_CSV in out and PIPELINES in out and "pipelines-1.22" in out


def test_extra_csv_of_a_foreign_package_is_refused(tmp_path):
    foreign = _sub("cert-manager", "cert-manager", "stable-v1", "cert-manager.v1.99.0")
    proc, logged = _run(
        tmp_path,
        [GITOPS_SUB, foreign],
        [_plan("ip-joint", [GITOPS_CSV, "cert-manager.v1.99.0"])],
    )
    assert proc.returncode != 0
    assert not _patched(logged)
    assert "cert-manager.v1.99.0" in proc.stdout


def test_blueprint_package_on_another_channel_is_refused(tmp_path):
    wrong = _sub(PIPELINES, PIPELINES, "latest", PIPELINES_CSV)
    proc, logged = _run(
        tmp_path, [GITOPS_SUB, wrong], [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV])]
    )
    assert proc.returncode != 0
    assert not _patched(logged)


def test_extra_csv_with_no_subscription_is_refused(tmp_path):
    proc, logged = _run(
        tmp_path, [GITOPS_SUB], [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV])]
    )
    assert proc.returncode != 0
    assert not _patched(logged)


def test_one_good_extra_does_not_excuse_a_bad_one(tmp_path):
    foreign = _sub("cert-manager", "cert-manager", "stable-v1", "cert-manager.v1.99.0")
    proc, logged = _run(
        tmp_path,
        [GITOPS_SUB, PIPELINES_SUB, foreign],
        [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV, "cert-manager.v1.99.0"])],
    )
    assert proc.returncode != 0
    assert not _patched(logged)


def test_unreadable_plan_list_is_refused(tmp_path):
    proc, logged = _run(
        tmp_path,
        [GITOPS_SUB, PIPELINES_SUB],
        [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV])],
        fail="plans",
    )
    assert proc.returncode != 0
    assert not _patched(logged)


def test_unreadable_subscription_list_is_refused(tmp_path):
    proc, logged = _run(
        tmp_path,
        [GITOPS_SUB, PIPELINES_SUB],
        [_plan("ip-joint", [GITOPS_CSV, PIPELINES_CSV])],
        fail="subs",
    )
    assert proc.returncode != 0
    assert not _patched(logged)


def test_expected_channels_have_a_single_source():
    text = BOOTSTRAP.read_text()
    for channel in ("pipelines-1.22", "gitops-1.20", "fast-1.10"):
        assert text.count(channel) == 1, (
            f"{channel} must appear once (its definition); ensure_operator and the "
            "joint-plan check both read the variable"
        )
    for var in ("PIPELINES", "GITOPS", "RHDH"):
        assert re.search(
            rf'\$\{{?{var}_PKG\}}?"?\s+"?\$\{{?{var}_CHANNEL', text
        ), f"ensure_operator for {var} must be called with the shared values"
