"""CI/CD promotion-gate entry point.

`python -m eval.cli run --all` — the pre-existing EXAMPLE-*.yaml
harness-mechanics smoke pair (unchanged: fast, offline, all-or-nothing;
this is what ci/pr-checks.yaml's fast PR gate calls).
`python -m eval.cli run --domain` — the 62-case eval/cases/domain/ suite,
category-threshold-aware (eval/thresholds.yaml), meaningful only in live
mode (AGENT_MODEL_MODE=live) since FakeModelClient has no real domain
behavior.
`python -m eval.cli run --case <id>` — an id lookup across *both* sets.

Sets AGENT_MODEL_MODE/MCP_MODE defaults (only if unset) *before* importing
anything that reads agent.config, so `eval run` is deterministic and
network-free by default without requiring the caller to remember to set
them.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

import yaml  # noqa: E402

from .domain_executor import execute_domain_case  # noqa: E402
from .domain_loader import load_all_domain_cases, load_domain_case_by_id  # noqa: E402
from .domain_scorer import score_domain_case  # noqa: E402
from .loader import load_all_cases, load_case  # noqa: E402
from .reporter import print_summary, write_report  # noqa: E402
from .runner import run_case  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "cases"
THRESHOLDS_PATH = Path(__file__).resolve().parent / "thresholds.yaml"


def _load_thresholds() -> dict:
    return yaml.safe_load(THRESHOLDS_PATH.read_text())["categories"]


def _gate_verdict_for_domain(results: list[dict]) -> tuple[bool, dict]:
    thresholds = _load_thresholds()
    per_category_failures: dict[str, int] = {}
    for r in results:
        if not r["passed"]:
            per_category_failures[r["category"]] = per_category_failures.get(r["category"], 0) + 1

    ok = True
    applied = {}
    for category, bounds in thresholds.items():
        failures = per_category_failures.get(category, 0)
        within = failures <= bounds["max_failures"]
        ok = ok and within
        applied[category] = {**bounds, "observed_failures": failures, "within_threshold": within}
    return ok, applied


def main():
    parser = argparse.ArgumentParser(description="Golden-path agent evaluation CLI")
    parser.add_argument("action", choices=["run"])
    parser.add_argument("--case", help="run a single case by id, looked up across both EXAMPLE-* and domain sets")
    parser.add_argument("--all", action="store_true", help="run the EXAMPLE-*.yaml harness-mechanics pair")
    parser.add_argument("--domain", action="store_true", help="run the eval/cases/domain/ suite (62 cases)")
    args = parser.parse_args()

    if args.case:
        try:
            case = load_case(CASES_DIR / f"{args.case}.yaml")
            results = [run_case(case)]
        except FileNotFoundError:
            case = load_domain_case_by_id(args.case)
            trace = execute_domain_case(case)
            results = [score_domain_case(case, trace)]
        write_report(results)
        print_summary(results)
        sys.exit(0 if all(r["passed"] for r in results) else 1)

    overall_ok = True

    if args.all:
        example_cases = load_all_cases(CASES_DIR)
        example_results = [run_case(c) for c in example_cases]
        write_report(example_results, config_reference="EXAMPLE-*.yaml harness-mechanics pair")
        print_summary(example_results)
        overall_ok = overall_ok and all(r["passed"] for r in example_results)

    if args.domain:
        domain_cases = load_all_domain_cases()
        domain_results = []
        for case in domain_cases:
            trace = execute_domain_case(case)
            domain_results.append(score_domain_case(case, trace))
        gate_ok, thresholds_applied = _gate_verdict_for_domain(domain_results)
        write_report(
            domain_results,
            eval_set_version="0.2.0",  # bumped alongside OPS-004's known-gap removal
            config_reference="eval/cases/domain/*.yaml",
            thresholds_applied=thresholds_applied,
            gate_verdict="pass" if gate_ok else "fail",
        )
        print_summary(domain_results)
        print(f"\ndomain gate verdict: {'PASS' if gate_ok else 'FAIL'}")
        for category, detail in thresholds_applied.items():
            marker = "ok" if detail["within_threshold"] else "OVER THRESHOLD"
            print(f"  {category}: {detail['observed_failures']}/{detail['max_failures']} max failures [{marker}]")
        overall_ok = overall_ok and gate_ok

    if not args.all and not args.domain:
        parser.error("pass --case <id>, --all, --domain, or both --all and --domain")
        return

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
