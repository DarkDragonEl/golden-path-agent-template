"""Runs one eval case end-to-end and scores it: drives the case through
eval/executor.py::execute_case to get a full ExecutionTrace, then applies
eval/scorer.py::score_assertion to each declared assertion.

run_case(case) contract: for a case with `steps` (a multi-step invoke/resume
HITL flow), each step's assertions are scored against that step's own
recorded state/latency; for a case without `steps` (a single-turn case),
case.assertions are scored against the trace's final recorded state.
Returns {"case_id", "passed", "results": [...]}, the per-case shape
eval/reporter.py's write_report/print_summary consume.
"""

from .executor import execute_case
from .scorer import score_assertion


def run_case(case) -> dict:
    trace = execute_case(case)
    results = []
    passed = True

    if case.steps:
        for step, recorded in zip(case.steps, trace.steps):
            for assertion in step.assertions:
                ok, detail = score_assertion(assertion, recorded["state"], recorded["latency_ms"])
                results.append(
                    {"step": recorded["action"], "assertion": assertion.type, "passed": ok, "detail": detail}
                )
                passed = passed and ok
    else:
        recorded = trace.steps[-1] if trace.steps else {"state": {}, "latency_ms": 0}
        for assertion in case.assertions:
            ok, detail = score_assertion(assertion, recorded["state"], recorded["latency_ms"])
            results.append({"assertion": assertion.type, "passed": ok, "detail": detail})
            passed = passed and ok

    return {"case_id": case.id, "passed": passed, "results": results}
