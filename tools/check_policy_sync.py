"""CI pipeline policy-validation step (ADR-018): mechanical
drift check between policy/approval_rules.yaml (the runtime source of
truth, loaded by agent/config.py) and policy/opa/approval_policy.rego's
hand-maintained tool_classification/default_classification mirror.

approval_policy.rego's own header says the sync between the two is a
manual, by-hand discipline with no generator -- this script turns that
discipline into an enforced invariant instead of a hope. Fails (non-zero
exit) on any divergence: a tool present in one but not the other, or
classified differently in each, or a differing default_classification.

Requires the pinned OPA binary (PINS.md) to evaluate the rego's actual
data, not a second hand-written copy of it in Python -- comparing YAML
against a *parsed rego value*, not against a maintainer's guess at what
the rego says, is the whole point.

Two ways to supply the rego side, since `opa` and `python` don't share one
container image in the Tekton policy-validate Task (pipelines/tasks/policy-validate.yaml
runs `opa eval` in an opa-image step, dumps its JSON to the shared
workspace, then this script reads those files in a python-image step):

1. Local/dev use -- shell out to a working `opa eval` directly: set
   OPA_BIN to the full command (e.g. "podman run --rm -v
   $(pwd)/policy/opa:$(pwd)/policy/opa:Z docker.io/openpolicyagent/opa:1.19.1
   eval" -- note this script appends its own -d/query args, so OPA_BIN
   must end exactly where an `opa eval` invocation's own flags would
   begin, and the container mount path must match REPO paths since -d is
   passed as an absolute host path).
       python tools/check_policy_sync.py
2. CI use -- read pre-dumped opa eval -f json output from files:
       python tools/check_policy_sync.py \
         --rego-classification-file tool_classification.json \
         --rego-default-file default_classification.json
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
APPROVAL_RULES_PATH = REPO_ROOT / "policy" / "approval_rules.yaml"
OPA_POLICY_DIR = REPO_ROOT / "policy" / "opa"


def _load_python_side() -> tuple[dict, str]:
    bundle = yaml.safe_load(APPROVAL_RULES_PATH.read_text()) or {}
    classification = {r["tool_name"]: r["classification"] for r in bundle.get("rules", [])}
    default = bundle.get("default_classification", "write")
    return classification, default


def _opa_eval_shellout(query: str):
    opa_bin = os.environ.get("OPA_BIN", "opa eval")
    cmd = shlex.split(opa_bin) + ["-d", str(OPA_POLICY_DIR), "-f", "json", query]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parsed = json.loads(result.stdout)
    return parsed["result"][0]["expressions"][0]["value"]


def _opa_eval_from_file(path: Path):
    parsed = json.loads(path.read_text())
    return parsed["result"][0]["expressions"][0]["value"]


def _load_rego_side(classification_file: Path | None, default_file: Path | None) -> tuple[dict, str]:
    if classification_file and default_file:
        return _opa_eval_from_file(classification_file), _opa_eval_from_file(default_file)
    return (
        _opa_eval_shellout("data.golden_path.approval.tool_classification"),
        _opa_eval_shellout("data.golden_path.approval.default_classification"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rego-classification-file", type=Path, default=None)
    parser.add_argument("--rego-default-file", type=Path, default=None)
    args = parser.parse_args()

    py_classification, py_default = _load_python_side()
    rego_classification, rego_default = _load_rego_side(
        args.rego_classification_file, args.rego_default_file
    )

    problems = []
    if py_default != rego_default:
        problems.append(
            f"default_classification differs: policy/approval_rules.yaml={py_default!r} "
            f"vs policy/opa/approval_policy.rego={rego_default!r}"
        )

    all_tools = set(py_classification) | set(rego_classification)
    for tool_name in sorted(all_tools):
        py_val = py_classification.get(tool_name, "<absent>")
        rego_val = rego_classification.get(tool_name, "<absent>")
        if py_val != rego_val:
            problems.append(
                f"{tool_name!r}: policy/approval_rules.yaml={py_val!r} "
                f"vs policy/opa/approval_policy.rego={rego_val!r}"
            )

    if problems:
        print("POLICY SYNC CHECK FAILED -- policy/approval_rules.yaml and", file=sys.stderr)
        print("policy/opa/approval_policy.rego have drifted:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"policy sync check OK -- {len(all_tools)} tool(s), default={py_default!r} match exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
