"""Runs one loaded `eval/loader.py::EvalCase` end to end and scores it.

Contract: `run_case` drives `eval/executor.py::execute_case` to produce a
full trace, then scores each step's (or, for a case with no `steps`, the
final recorded state's) assertions via `eval/scorer.py::score_assertion`.
Returns `{case_id, passed, results}` -- `results` is a list of per-
assertion `{assertion, passed, detail}` dicts (plus `step` when the case
has explicit steps), the shape `eval/reporter.py::write_report` embeds
verbatim as one entry of its own `cases` list.
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
