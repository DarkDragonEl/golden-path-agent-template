"""CI/CD promotion-gate entry point: `python -m eval.cli run --all` exits
nonzero on any failed assertion.

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

from .loader import load_all_cases, load_case  # noqa: E402
from .reporter import print_summary, write_report  # noqa: E402
from .runner import run_case  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent / "cases"


def main():
    parser = argparse.ArgumentParser(description="Golden-path agent evaluation CLI")
    parser.add_argument("action", choices=["run"])
    parser.add_argument("--case", help="run a single case by id (filename without .yaml)")
    parser.add_argument("--all", action="store_true", help="run every case in eval/cases/")
    args = parser.parse_args()

    if args.all:
        cases = load_all_cases(CASES_DIR)
    elif args.case:
        cases = [load_case(CASES_DIR / f"{args.case}.yaml")]
    else:
        parser.error("pass --case <id> or --all")
        return

    results = [run_case(c) for c in cases]
    write_report(results)
    print_summary(results)

    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
