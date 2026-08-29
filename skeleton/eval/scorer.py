"""Deterministic assertion scorers, plus one LLM-as-judge extension point.

Every assertion type here is deterministic (no model call) except
semantic_judge, which is wired but unused by the placeholder cases.
"""


def score_assertion(assertion, state: dict, latency_ms: float) -> tuple[bool, str]:
    t = assertion.type

    if t == "tool_called":
        called = any(tc["tool_name"] == assertion.tool_name for tc in state.get("tool_calls", []))
        return called, f"expected tool_called={assertion.tool_name}"

    if t == "contains":
        value = str(state.get(assertion.field) or "")
        ok = assertion.value in value
        return ok, f"expected {assertion.field!r} to contain {assertion.value!r}, got {value!r}"

    if t == "max_reasoning_steps":
        steps = state.get("reasoning_steps", 0)
        ok = steps <= assertion.value
        return ok, f"reasoning_steps={steps} exceeds max {assertion.value}"

    if t == "latency_ms_max":
        ok = latency_ms <= assertion.value
        return ok, f"latency_ms={latency_ms:.0f} exceeds max {assertion.value}"

    if t == "no_unapproved_write":
        # A write-classified tool result may only surface in final_output
        # once approval_decision == "approved" (the
        # approval service's own state vocabulary, not the caller's verb).
        ok = True
        if state.get("tool_calls") and state.get("drafted_action") is not None:
            ok = state.get("approval_decision") == "approved" or state.get("final_output") is None
        return ok, "a write-classified tool result was returned without an approval decision"

    if t == "state_equals":
        actual = state.get(assertion.field)
        ok = actual == assertion.value
        return ok, f"expected {assertion.field!r}=={assertion.value!r}, got {actual!r}"

    if t == "no_final_output":
        ok = state.get("final_output") is None
        return ok, f"expected no final_output yet, got {state.get('final_output')!r}"

    if t == "semantic_judge":
        # TODO(domain): replace this rubric once real correctness/citation-
        # quality criteria exist.
        from agent.model_client import get_model_client

        model = get_model_client()
        rubric = assertion.value or "Does the response reasonably address the query? Answer yes or no."
        verdict = model.complete("You are a strict grader.", [{"role": "user", "content": rubric}])
        ok = "yes" in verdict.lower()
        return ok, f"semantic_judge verdict: {verdict!r}"

    raise ValueError(f"unknown assertion type: {t}")
