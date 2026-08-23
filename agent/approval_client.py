"""Thin client the agent's tool_invoke/human_approval path uses to reach
the standalone approval service (Phase D, DECISIONS.md DEC-008/DEC-045).
Mirrors mcp_server/client.py's own shape -- the contract
(approval_service/schemas.py) is what's frozen, not this client.

resolve_and_resume is the ONE place the "query the terminal state, decide
whether to touch the graph, inject, resume" logic lives -- used by both
agent/api.py's real /resume endpoint and, via a patched submit_proposal/
get_proposal in tests, eval/domain_executor.py's own resume step. One
executor for this logic, not two (matching the runbook's own
"one executor built once" principle for the phase-two HTTP eval
executor).
"""

import httpx

from . import config


def submit_proposal(
    *,
    action_type: str,
    target_system_id: str,
    action_arguments: dict,
    evidence_refs: list[str],
    initiating_user_id: str,
    agent_workload_id: str,
    originating_session_id: str,
    originating_request_id: str,
    idempotency_key: str | None = None,
    timeout: float = 10.0,
) -> dict:
    """SRS-APR-IF-01. Returns {"proposal_id": ..., "state": "pending"}
    (or the existing proposal's current state, on an idempotency_key
    replay -- SRS-APR-F-07)."""
    body = {
        "action_type": action_type,
        "target_system_id": target_system_id,
        "action_arguments": action_arguments,
        "evidence_refs": evidence_refs,
        "initiating_user_id": initiating_user_id,
        "agent_workload_id": agent_workload_id,
        "originating_session_id": originating_session_id,
        "originating_request_id": originating_request_id,
    }
    if idempotency_key is not None:
        body["idempotency_key"] = idempotency_key
    response = httpx.post(f"{config.APPROVAL_SERVICE_ENDPOINT}/proposals", json=body, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_proposal(proposal_id: str, timeout: float = 10.0) -> dict:
    """SRS-APR-IF-05. Terminal-state query -- the ONLY source of truth
    for a decided proposal's outcome and, for `approved`, its unmodified
    `action_arguments`. DECISIONS.md DEC-008: the caller must execute
    exactly what this returns, never a locally cached copy."""
    response = httpx.get(f"{config.APPROVAL_SERVICE_ENDPOINT}/proposals/{proposal_id}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def resolve_and_resume(graph, thread_config: dict):
    """Query this session's pending proposal (SRS-APR-IF-05); if still
    `pending`, return the graph's current state unchanged -- the graph is
    NOT touched. If terminal, inject the outcome into graph state, using
    ONLY the values this query just returned (DECISIONS.md DEC-008: never
    a locally cached copy of the drafted arguments), then resume.

    `graph.get_state(thread_config).values["proposal_id"]` is the
    correlation key -- set by tool_invoke_node at submission time.
    """
    snapshot = graph.get_state(thread_config)
    proposal_id = snapshot.values.get("proposal_id")
    proposal = get_proposal(proposal_id)

    if proposal["state"] == "pending":
        return snapshot.values

    approved_action = None
    if proposal["state"] == "approved":
        drafted = snapshot.values.get("drafted_action") or {}
        approved_action = {
            "tool_name": drafted.get("tool_name"),
            "arguments": proposal["action_arguments"],  # the service's own value, not drafted's
            "proposal_id": proposal_id,
            "approver_id": proposal.get("decided_by"),
            "decided_at": proposal.get("decided_at"),
        }

    graph.update_state(
        thread_config,
        {"approved_action": approved_action, "approval_decision": proposal["state"]},
    )
    return graph.invoke(None, thread_config)
