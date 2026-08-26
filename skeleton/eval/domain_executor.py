"""Category-aware graph driving for eval/cases/domain/*.yaml.

Distinct from eval/executor.py (EXAMPLE-*.yaml harness-mechanics only,
DEC-005). Domain cases don't declare a `mode` field (eval/schema.json)
-- AGENT_MODEL_MODE is an environment-level setting, not per-case. Most
categories only produce meaningful (non-vacuous) results in live mode,
since FakeModelClient has no real reasoning/tool-selection/citation
behavior; offline/fake mode mainly exercises the write-gating mechanism
itself (unauthorized_write's reject/expire paths), not full domain
coverage.
"""

import contextlib
import time
import uuid
from unittest.mock import patch

from agent import approval_client, config as agent_config
from agent.graph import build_graph
from agent.retrieval_client import RetrievedChunk
from agent.retrieval_client import retrieve as _real_retrieve
from .fake_approval_client import FakeApprovalService
from .mock_itsm_fixture import eval_call_tool, fixture as itsm_fixture


class DomainExecutionTrace:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.steps: list[dict] = []
        self.request_ids_before: set[str] = set()

    def record(self, action: str, state: dict, latency_ms: float) -> None:
        self.steps.append({"action": action, "state": state, "latency_ms": latency_ms})

    @property
    def final_state(self) -> dict:
        return self.steps[-1]["state"] if self.steps else {}


def _initial_state(session_id: str, case) -> dict:
    return {
        "session_id": session_id,
        "request_id": f"{session_id}-req",  # Phase D/DEC-049: agent/api.py's own equivalent is a
        # fresh uuid per API call; a case-derived value is fine here since one case makes one call.
        "user_id": "eval-harness",
        "input_query": case.input["query"],
        "write_requested": False,  # domain cases exercise real tool selection, not the legacy flag
        "messages": [],
        "reasoning_steps": 0,
        "tool_calls": [],
        "model_calls": [],
        "pending_approval": False,
    }


@contextlib.contextmanager
def _apply_fault(fault: str | None, fault_params: dict | None):
    """operational category fault injection. Phase G, Stage 2
    (DEC-098/DEC-099/DEC-104/DEC-105): store/model-client faults are
    applied by temporarily patching the eval-only fixture's bound
    methods (mock_itsm_fixture.py) -- restored automatically on exit.
    This never touches the real Tools Template's own server/store at
    all (the Agent Template cannot even import that package); the real
    server's own _simulate_error hook and its refusal to expose it as a
    tool parameter are unrelated to this and unchanged (DEC-105)."""
    fault_params = fault_params or {}

    if fault in ("tool_timeout", "tool_error"):
        simulate_value = "timeout" if fault == "tool_timeout" else fault_params.get("error_type", "error")
        original_search = itsm_fixture.search
        original_create = itsm_fixture.create_request

        def patched_search(*args, **kwargs):
            kwargs.setdefault("_simulate_error", simulate_value)
            return original_search(*args, **kwargs)

        def patched_create(*args, **kwargs):
            kwargs.setdefault("_simulate_error", simulate_value)
            return original_create(*args, **kwargs)

        with patch.object(itsm_fixture, "search", new=patched_search), patch.object(
            itsm_fixture, "create_request", new=patched_create
        ):
            yield

    elif fault == "model_failure":
        failure_type = fault_params.get("failure_type", "unknown")

        class _AlwaysFailsClient:
            def complete(self, *args, **kwargs):
                raise ConnectionError(f"simulated model failure: {failure_type}")

        with patch("agent.nodes.decide.get_model_client", return_value=_AlwaysFailsClient()):
            yield

    elif fault == "step_limit_exceeded":
        forced_max = fault_params.get("max_reasoning_steps", 0)
        # Force below whatever the real policy bundle configures, so the
        # very first reasoning step already exceeds it.
        with patch.object(agent_config, "MAX_REASONING_STEPS", min(0, forced_max - 1)):
            yield

    else:
        yield


def execute_domain_case(case) -> DomainExecutionTrace:
    trace = DomainExecutionTrace(case.id)
    graph = build_graph()
    session_id = f"domain-eval-{case.id}-{uuid.uuid4().hex[:8]}"
    thread_config = {"configurable": {"thread_id": session_id}}
    initial_state = _initial_state(session_id, case)

    # Store-verified checks (design point 3: the mock ITSM's own state is
    # the primary check, not the agent's self-report) need a before-
    # snapshot. Queried directly against the store, not via REST -- same
    # underlying state, without build_app()'s once-per-process session-
    # manager constraint (found in Phase B1) complicating a harness that
    # runs many cases in one process.
    trace.request_ids_before = {
        r["record_id"] for r in itsm_fixture.list_records(record_type="request")
    }

    fault = case.input.get("fault")
    fault_params = case.input.get("fault_params")
    injection_source = case.input.get("injection_source")
    injection_payload = case.input.get("injection_payload")

    # Phase D/DEC-049: tool_invoke_node's write branch now submits a real
    # proposal to the standalone approval service over HTTP -- domain
    # eval runs must never depend on one being reachable (this is what
    # makes eval-gate-offline/eval-gate-live able to run without standing
    # up approval_service, exactly as before this graduation). Always
    # active for every case, not fault-conditional like _apply_fault
    # above, since any write-classified case needs it, not just specific
    # fault scenarios.
    # Phase G, Stage 2 (DEC-098/DEC-099/DEC-105): the split Agent Template
    # never bundles mcp_server/server.py, so the real call_tool's own
    # "mock" in-process branch (`from . import server`) would ImportError
    # -- every domain eval run patches both call sites to this eval-only
    # stub instead, for the same reason submit_proposal/get_proposal are
    # already patched to a fake below (no live services in this harness).
    fake_approval = FakeApprovalService()
    with patch("agent.approval_client.submit_proposal", side_effect=fake_approval.submit_proposal), patch(
        "agent.approval_client.get_proposal", side_effect=fake_approval.get_proposal
    ), patch("agent.nodes.tool_invoke.call_tool", side_effect=eval_call_tool), patch(
        "agent.nodes.human_approval.call_tool", side_effect=eval_call_tool
    ), _apply_fault(fault, fault_params):
        if injection_source == "document":
            # Simulate a compromised/malicious retrieved document: run
            # real retrieval (so the legitimate part of the question is
            # still genuinely grounded), then append a synthetic passage
            # carrying the injection payload, as if it were one of the
            # documents actually returned.
            def _augmented_retrieve(query, top_k=None, filters=None, user_id=None):
                docs = list(_real_retrieve(query, top_k=top_k, filters=filters, user_id=user_id))
                docs.append(
                    RetrievedChunk(
                        doc_id="SIMULATED-INJECTED-DOC",
                        title="(simulated malicious document)",
                        passage_text=injection_payload,
                        source="test-injection",
                        classification="internal-public",
                        version="0",
                        owner_role="test",
                        effective_date="2026-01-01",
                    )
                )
                return docs

            with patch("agent.nodes.retrieve.retrieve", side_effect=_augmented_retrieve):
                start = time.monotonic()
                state = graph.invoke(initial_state, thread_config)
                trace.record("invoke", state, (time.monotonic() - start) * 1000)
        else:
            # injection_source == "user_message": the payload is already
            # the query itself (see eval/cases/domain/prompt_injection.yaml).
            # injection_source == "tool_result": no special setup -- this
            # architecture never feeds a tool result back to the model for
            # a second reasoning pass (read-classified tools are formatted
            # deterministically, write-classified tools only execute after
            # a human decision), so there is no path for injected tool-
            # result content to reach the model at all. Scored structurally
            # by eval/domain_scorer.py, not simulated here.
            start = time.monotonic()
            state = graph.invoke(initial_state, thread_config)
            trace.record("invoke", state, (time.monotonic() - start) * 1000)

        if case.category == "unauthorized_write":
            scenario = case.input.get("approval_scenario")
            if scenario in ("rejected", "expired") and state.get("pending_approval"):
                # Phase D/DEC-049: the real resume path is
                # agent/approval_client.py::resolve_and_resume -- it
                # queries the (patched, fake) approval service's own
                # terminal-state and only then touches the graph, exactly
                # like the real agent/api.py's /resume endpoint. Deciding
                # the fake's own record first (test-only .decide(), not
                # part of the real IF-02 contract) is what a real
                # approver's decision would do server-side.
                proposal_id = state.get("proposal_id")
                decision = "rejected" if scenario == "rejected" else "expired"
                fake_approval.decide(proposal_id, decision)
                start = time.monotonic()
                state = approval_client.resolve_and_resume(graph, thread_config)
                trace.record("resume", state, (time.monotonic() - start) * 1000)
            # bypass_attempt / not_requested: no resume call -- that's the
            # scenario itself (no decision is ever rendered).

    return trace
