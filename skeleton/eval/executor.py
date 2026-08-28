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
from unittest.mock import patch

from agent import approval_client
from agent.graph import build_graph
from .fake_approval_client import FakeApprovalService
from .mock_itsm_fixture import eval_call_tool

# The case file's own `decision:` field is the verb a human approver
# submits (SRS-APR-IF-02's own ProposalDecision.decision vocabulary,
# "approve"|"reject") -- distinct from the approval service's STATE
# vocabulary a decided proposal transitions to (ProposalState,
# "approved"|"rejected"|"expired"). This maps one to the other; it is not
# a second, competing vocabulary.
_VERB_TO_STATE = {"approve": "approved", "reject": "rejected"}


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
        "request_id": f"{session_id}-req",
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

    # tool_invoke_node's write branch submits a real
    # proposal to the standalone approval service over HTTP -- the
    # EXAMPLE-*.yaml harness-mechanics suite must not depend on one being
    # reachable, exactly like eval/domain_executor.py's own
    # _FakeApprovalService (mirrored here, not reimplemented, via the
    # same eval/fake_approval_client.py).
    #
    # call_tool is patched at
    # both node-import boundaries too, same reasoning as
    # domain_executor.py's own identical patch -- this repo never bundles
    # mcp_server/server.py, so the real call_tool's "mock" branch would
    # ImportError, and MCP_MODE=live has no reachable endpoint in a
    # hermetic unit-test run.
    fake_approval = FakeApprovalService()
    with patch("agent.approval_client.submit_proposal", side_effect=fake_approval.submit_proposal), patch(
        "agent.approval_client.get_proposal", side_effect=fake_approval.get_proposal
    ), patch("agent.nodes.tool_invoke.call_tool", side_effect=eval_call_tool), patch(
        "agent.nodes.human_approval.call_tool", side_effect=eval_call_tool
    ):
        if case.steps:
            for step in case.steps:
                start = time.monotonic()
                if step.action == "invoke":
                    state = graph.invoke(_initial_state(session_id, case), thread_config)
                elif step.action == "resume":
                    proposal_id = state.get("proposal_id")
                    fake_approval.decide(proposal_id, _VERB_TO_STATE[step.decision])
                    state = approval_client.resolve_and_resume(graph, thread_config)
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
