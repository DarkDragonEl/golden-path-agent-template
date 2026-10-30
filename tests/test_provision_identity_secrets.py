"""platform/bootstrap/provision-identity-secrets.sh, run hermetically
against a stub `oc` (and `openssl`) on PATH -- no cluster, no network.

Regression guard for the DEC-080 latent bug (HANDOFF.md: "its
`read <<EOF $(...) EOF` pattern doesn't propagate a failing subprocess's
exit code through `set -e`"): step 1's client-secret regeneration ran its
`oc exec` inside a command substitution inside a heredoc, so a failed exec
fell through with both secrets silently empty and step 2 wrote those
empty values into every consumer namespace's golden-path-agent-secrets.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "platform" / "bootstrap" / "provision-identity-secrets.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("base64") is None,
    reason="needs bash and coreutils base64",
)

# The stub answers exactly the oc calls the script makes. Every call is
# appended to $STUB_LOG as one JSON line, so tests can assert on what was
# (or was not) written. `oc exec` reads the in-pod Python script from
# stdin and picks its canned output by what that script does, so the
# stub stays independent of call order.
STUB_OC = textwrap.dedent(
    """\
    #!{python}
    import base64, json, os, sys

    args = sys.argv[1:]
    stdin = sys.stdin.read() if args[:1] == ["exec"] else ""
    with open(os.environ["STUB_LOG"], "a") as log:
        log.write(json.dumps(args) + "\\n")

    def b64(value):
        print(base64.b64encode(value.encode()).decode(), end="")

    if args[:2] == ["get", "pod"]:
        print("golden-path-agent-keycloak-db-0", end="")
    elif args[:2] == ["get", "secret"]:
        jsonpath = [a for a in args if a.startswith("jsonpath=")]
        if args[2] == "golden-path-agent-keycloak-admin" and jsonpath:
            b64("admin" if "username" in jsonpath[0] else "admin-password")
        else:
            sys.exit(1)  # "NotFound": the script takes its create path
    elif args[:1] == ["exec"]:
        if os.environ.get("STUB_EXEC_FAIL", "") and os.environ["STUB_EXEC_FAIL"] in stdin:
            print("error: unable to upgrade connection: container not found", file=sys.stderr)
            sys.exit(1)
        if os.environ.get("STUB_EXEC_EMPTY", "") and os.environ["STUB_EXEC_EMPTY"] in stdin:
            sys.exit(0)
        if "regenerate_secret(" in stdin:
            print("approval-secret-value mcp-secret-value")
        elif "set_password(" in stdin:
            print("demo user passwords set")
        elif "if not matches:" in stdin:
            print("done")
        else:
            print("rhdh-oidc-secret-value", end="")
    elif args[:2] == ["whoami", "-t"]:
        print("stub-session-token")
    elif args[:1] in (["create"], ["patch"]):
        pass
    else:
        print("stub oc: unexpected call: " + " ".join(args), file=sys.stderr)
        sys.exit(2)
    """
)

STUB_OPENSSL = "#!/bin/sh\necho stub-random-value\n"


@pytest.fixture
def stub_env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("oc", STUB_OC.format(python=sys.executable)), ("openssl", STUB_OPENSSL)):
        path = bin_dir / name
        path.write_text(body)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
    log = tmp_path / "oc-calls.jsonl"
    log.touch()
    env = {
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "STUB_LOG": str(log),
        "MODEL_API_KEY": "stub-model-key",
        "MODEL_API_BASE_URL": "http://model.example.com/v1",
        "MODEL_NAME": "stub-model",
        "MODEL_FALLBACK_API_BASE_URL": "http://fallback.example.com/v1",
        "MODEL_FALLBACK_NAME": "stub-fallback",
    }
    return env, log


def run_script(env, **overrides):
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={**env, **overrides},
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def workload_secret_writes(log):
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    return [c for c in calls if c[:1] in (["create"], ["patch"]) and "golden-path-agent-secrets" in c]


def test_happy_path_writes_regenerated_client_secrets(stub_env):
    """Positive control: the stub is faithful enough for the script to
    run to completion and write what step 1 actually regenerated."""
    env, log = stub_env
    result = run_script(env)
    assert result.returncode == 0, result.stderr
    writes = workload_secret_writes(log)
    assert len(writes) == 2  # ephemeral-test + demo-prod
    for call in writes:
        assert "--from-literal=APPROVAL_OIDC_CLIENT_SECRET=approval-secret-value" in call
        assert "--from-literal=MCP_AUTH_TOKEN=mcp-secret-value" in call


def test_failing_oc_exec_fails_script_before_any_secret_write(stub_env):
    env, log = stub_env
    result = run_script(env, STUB_EXEC_FAIL="regenerate_secret(")
    assert result.returncode != 0
    assert workload_secret_writes(log) == []
    assert "provision-identity-secrets.sh: done." not in result.stdout


def test_empty_regeneration_output_fails_script_before_any_secret_write(stub_env):
    """An exec that exits 0 but prints nothing must not be mistaken for
    two (empty) secrets either."""
    env, log = stub_env
    result = run_script(env, STUB_EXEC_EMPTY="regenerate_secret(")
    assert result.returncode != 0
    assert workload_secret_writes(log) == []
