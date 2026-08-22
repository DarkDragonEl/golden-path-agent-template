"""Drives the agent graph for a single eval case, capturing a full trace.

Two-phase invoke+resume driver for HITL-path cases: a case with `steps`
runs each step against the same compiled graph/thread, so a "resume" step
continues the exact paused execution the preceding "invoke" step left
behind (mirrors the real POST /approvals/{id}/resume flow in agent/api.py).

NOTE: all cases currently run in "offline" mode regardless of the `mode`
field on the case — live-mode dispatch is not implemented yet. `mode` is
kept as a documented, forward-looking field on EvalCase.
"""

import time
import uuid

from agent.graph import build_graph


class ExecutionTrace:
    def __init__(self):
        self.steps: list[dict] = []

    def record(self, action: str, state: dict, latency_ms: float) -> None:
        self.steps.append({"action": action, "state": state, "latency_ms": latency_ms})

    @property
    def final_state(self) -> dict:
        return self.steps[-1]["state"] if self.steps else {}


def _initial_state(session_id: str, case) -> dict:
    return {
        "session_id": session_id,
        "user_id": "eval-harness",
        "input_query": case.input["query"],
        "write_requested": bool(case.input.get("write", False)),
        "messages": [],
        "reasoning_steps": 0,
        "tool_calls": [],
        "model_calls": [],
        "pending_approval": False,
    }


def execute_case(case) -> ExecutionTrace:
    graph = build_graph()
    session_id = f"eval-{case.id}-{uuid.uuid4().hex[:8]}"
    thread_config = {"configurable": {"thread_id": session_id}}
    trace = ExecutionTrace()

    if case.steps:
        for step in case.steps:
            start = time.monotonic()
            if step.action == "invoke":
                state = graph.invoke(_initial_state(session_id, case), thread_config)
            elif step.action == "resume":
                graph.update_state(thread_config, {"approval_decision": step.decision})
                state = graph.invoke(None, thread_config)
            else:
                raise ValueError(f"unknown step action: {step.action}")
            latency_ms = (time.monotonic() - start) * 1000
            trace.record(step.action, state, latency_ms)
    else:
        start = time.monotonic()
        state = graph.invoke(_initial_state(session_id, case), thread_config)
        latency_ms = (time.monotonic() - start) * 1000
        trace.record("invoke", state, latency_ms)

    return trace
