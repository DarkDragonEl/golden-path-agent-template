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
