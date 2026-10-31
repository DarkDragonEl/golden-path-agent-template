"""Step 9b on an empty cluster registry, run under bash against a stub `oc`
on PATH -- no cluster, no network, same hermetic pattern as
test_bootstrap_joint_installplan.py.

Each component's gated PipelineRun deploys the other two beside it in
ephemeral-test, at their committed digests. When a committed digest is
absent from this cluster's registry, the run gets that sibling's newest
image built here instead; when no image of it exists at all, a build-only
seed run builds one first. With every committed digest present, nothing
changes.
"""

import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.sh"
PIPELINES = REPO_ROOT / "pipelines"
REGISTRY = "image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci"
IMAGESTREAMS = {"agent": "golden-path-agent", "mcp": "golden-path-agent-mcp", "approval": "golden-path-agent-approval"}

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="needs bash and jq (both required by bootstrap.sh itself)",
)

# ImageStreams come from $STUB_IS_JSON ({name: [{tag, image, created}]});
# a name not listed is NotFound. Created PipelineRuns are appended to
# $STUB_RUNS; every run reports $STUB_RUN_STATUS.
STUB_OC = textwrap.dedent(
    """\
    #!{python}
    import json, os, sys
    import yaml

    args = sys.argv[1:]
    streams = json.load(open(os.environ["STUB_IS_JSON"]))

    if args[:2] == ["get", "is"]:
        items = streams.get(args[2])
        if items is None:
            print('Error from server (NotFound): imagestreams "%s" not found' % args[2], file=sys.stderr)
            sys.exit(1)
        tags = {{}}
        for it in items:
            tags.setdefault(it["tag"], []).append({{"image": it["image"], "created": it["created"]}})
        print(json.dumps({{"status": {{"tags": [{{"tag": t, "items": i}} for t, i in tags.items()]}}}}))
    elif args[:2] == ["create", "--dry-run=client"]:
        print(json.dumps(yaml.safe_load(open(args[args.index("-f") + 1]))))
    elif args[0] == "create":
        obj = json.load(sys.stdin)
        with open(os.environ["STUB_RUNS"], "a") as f:
            f.write(json.dumps(obj) + "\\n")
        n = sum(1 for _ in open(os.environ["STUB_RUNS"]))
        print(obj["metadata"]["generateName"] + str(n), end="")
    elif args[:2] == ["get", "pipelinerun"]:
        print(os.environ.get("STUB_RUN_STATUS", "True"), end="")
    else:
        print("unexpected oc call: %s" % args, file=sys.stderr)
        sys.exit(2)
"""
)

DEFS = re.compile(r"^(?:CI_NS|CI_REGISTRY|COMPONENTS)=.*\n", re.M)
FUNCTIONS = (
    "committed_digest_for",
    "digest_in_registry",
    "latest_built_ref",
    "sibling_image_ref",
    "create_pipelinerun",
    "wait_pipelinerun",
    "seed_missing_images",
    "sibling_params_for",
)


def _function_source(name: str) -> str:
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", BOOTSTRAP.read_text(), re.S | re.M)
    assert match, f"{name}() is not defined at the top level of scripts/bootstrap.sh"
    return match.group(0)


def _committed(isname: str) -> str:
    base = yaml.safe_load((REPO_ROOT / "deploy/kustomize/base/kustomization.yaml").read_text())
    return next(i["digest"] for i in base["images"] if i["name"] == isname)


def _run(tmp_path, streams, command, run_status="True"):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    oc = bindir / "oc"
    oc.write_text(STUB_OC.format(python=sys.executable))
    oc.chmod(0o755)
    (tmp_path / "is.json").write_text(json.dumps(streams))
    runs = tmp_path / "runs.jsonl"
    text = BOOTSTRAP.read_text()
    harness = tmp_path / "harness.sh"
    harness.write_text(
        "set -euo pipefail\n"
        'log() { echo "[t] $*"; }\n'
        + "".join(DEFS.findall(text))
        + "".join(_function_source(f) for f in FUNCTIONS)
        + command
        + "\n"
    )
    env = {
        "PATH": f"{bindir}:/usr/bin:/bin",
        "STUB_IS_JSON": str(tmp_path / "is.json"),
        "STUB_RUNS": str(runs),
        "STUB_RUN_STATUS": run_status,
    }
    proc = subprocess.run(["bash", str(harness)], cwd=REPO_ROOT, env=env, capture_output=True, text=True)
    created = [json.loads(line) for line in runs.read_text().splitlines()] if runs.exists() else []
    return proc, created


def _built(digest, created="2026-10-30T20:00:00Z", tag="pr-abc"):
    return {"tag": tag, "image": digest, "created": created}


ALL_COMMITTED = {is_: [_built(_committed(is_))] for is_ in IMAGESTREAMS.values()}
BUILT_HERE = {
    is_: [_built("sha256:" + str(n) * 64, "2026-10-30T21:00:00Z", "pr-new"),
          _built("sha256:" + "1" * 64, "2026-10-30T20:00:00Z", "pr-old")]
    for n, is_ in zip((2, 3, 4), IMAGESTREAMS.values())
}


def _params(proc):
    return {p["name"]: p["value"] for p in json.loads(proc.stdout.strip().splitlines()[-1])}


def test_committed_digests_present_change_nothing(tmp_path):
    proc, created = _run(tmp_path, ALL_COMMITTED, "seed_missing_images\nsibling_params_for agent")
    assert proc.returncode == 0, proc.stderr
    assert _params(proc) == {}
    assert created == []


def test_absent_committed_digest_uses_the_newest_image_built_here(tmp_path):
    proc, created = _run(tmp_path, BUILT_HERE, "seed_missing_images\nsibling_params_for agent")
    assert proc.returncode == 0, proc.stderr
    assert created == [], "images exist, so nothing is seeded"
    assert _params(proc) == {
        "mcp-image-ref": f"{REGISTRY}/golden-path-agent-mcp@sha256:{'3' * 64}",
        "approval-image-ref": f"{REGISTRY}/golden-path-agent-approval@sha256:{'4' * 64}",
    }
    assert "unpromoted" in proc.stderr


def test_only_the_absent_sibling_is_overridden(tmp_path):
    streams = {**BUILT_HERE, "golden-path-agent-mcp": ALL_COMMITTED["golden-path-agent-mcp"]}
    proc, _ = _run(tmp_path, streams, "sibling_params_for agent")
    assert proc.returncode == 0, proc.stderr
    assert set(_params(proc)) == {"approval-image-ref"}


def test_empty_registry_seeds_every_component_once(tmp_path):
    proc, created = _run(tmp_path, {}, "seed_missing_images")
    assert proc.returncode == 0, proc.stderr
    seeded = [{p["name"]: p["value"] for p in run["spec"]["params"]} for run in created]
    assert [r["metadata"]["generateName"] for r in created] == ["golden-path-agent-ci-seed-"] * 3
    assert [(s["imagestream"], s["dockerfile"]) for s in seeded] == [
        (is_, f"./Containerfile.{c}") for c, is_ in IMAGESTREAMS.items()
    ]


def test_a_failed_seed_stops_9b(tmp_path):
    proc, created = _run(tmp_path, {}, "seed_missing_images", run_status="False")
    assert proc.returncode != 0
    assert len(created) == 1, "stops at the first failed seed"


def test_a_sibling_with_no_image_at_all_refuses(tmp_path):
    proc, _ = _run(tmp_path, {}, "sibling_params_for agent")
    assert proc.returncode != 0
    assert "refusing to run" in proc.stderr


def test_gated_run_carries_the_sibling_params(tmp_path):
    proc, created = _run(
        tmp_path, BUILT_HERE,
        'create_pipelinerun pipelines/pipelinerun-template-agent.yaml "$(sibling_params_for agent)"',
    )
    assert proc.returncode == 0, proc.stderr
    params = {p["name"]: p["value"] for p in created[0]["spec"]["params"]}
    assert params["revision"] == "main"
    assert params["mcp-image-ref"].endswith("@sha256:" + "3" * 64)
    assert params["approval-image-ref"].endswith("@sha256:" + "4" * 64)


@pytest.mark.parametrize("component", list(IMAGESTREAMS))
def test_pipeline_passes_siblings_through_and_builds_its_own(component):
    pipeline = yaml.safe_load((PIPELINES / f"pipeline-{component}.yaml").read_text())["spec"]
    siblings = [c for c in IMAGESTREAMS if c != component]
    declared = {p["name"]: p.get("default") for p in pipeline["params"]}
    for sib in siblings:
        assert declared.get(f"{sib}-image-ref") == "", f"{sib}-image-ref must default to the committed digest"
    deploy = next(t for t in pipeline["tasks"] if t["name"] == "deploy-ephemeral")
    passed = {p["name"]: p["value"] for p in deploy["params"]}
    assert "digest-capture.results.digest" in passed[f"{component}-image-ref"]
    for sib in siblings:
        assert passed[f"{sib}-image-ref"] == f"$(params.{sib}-image-ref)"


def test_seed_pipeline_never_promotes_and_9b_seeds_first():
    seed = yaml.safe_load((PIPELINES / "pipeline-seed.yaml").read_text())["spec"]
    assert [t["name"] for t in seed["tasks"]] == ["fetch-source", "container-build", "digest-capture"]
    text = BOOTSTRAP.read_text()
    assert "oc apply -f pipelines/pipeline-seed.yaml" in text
    assert text.index("if ! seed_missing_images; then") < text.index("promote_component agent golden-path-agent")
