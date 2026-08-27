"""Thin client the agent's tool_invoke/human_approval path uses to reach
the standalone approval service (DEC-008/DEC-045). Mirrors
mcp_server/client.py's own shape -- the contract
(approval_service/schemas.py) is what's frozen, not this client.

resolve_and_resume is the ONE place the query-decide-inject-resume logic
lives -- used by both agent/api.py's /resume endpoint and (via a patched
submit_proposal/get_proposal in tests) eval/domain_executor.py's resume
step. One executor, not two.
"""

import httpx

from . import config, oidc_client


def _auth_headers() -> dict:
    """AGENT_OIDC_MODE=none: no header at all, matching AUTH_MODE=none on
    the approval-service side (which does no validation). =oidc: attach
    this workload's own client-credentials bearer token."""
    if config.AGENT_OIDC_MODE != "oidc":
        return {}
    token = oidc_client.get_service_token(
        config.OIDC_ISSUER_URL, config.APPROVAL_OIDC_CLIENT_ID, config.APPROVAL_OIDC_CLIENT_SECRET
    )
    return {"Authorization": f"Bearer {token}"}


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
    response = httpx.post(
        f"{config.APPROVAL_SERVICE_ENDPOINT}/proposals", json=body, headers=_auth_headers(), timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def get_proposal(proposal_id: str, timeout: float = 10.0) -> dict:
    """SRS-APR-IF-05. Terminal-state query -- the ONLY source of truth
    for a decided proposal's outcome and, for `approved`, its unmodified
    `action_arguments`. DECISIONS.md DEC-008: the caller must execute
    exactly what this returns, never a locally cached copy."""
    response = httpx.get(
        f"{config.APPROVAL_SERVICE_ENDPOINT}/proposals/{proposal_id}", headers=_auth_headers(), timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def decide_proposal(proposal_id: str, decision: str, timeout: float = 10.0) -> dict:
    """SRS-APR-IF-02. Records a human decision on the standalone approval
    service. Only agent/cli.py's own --decision convenience path calls
    this directly, standing in for a real approver hitting the approval
    service's own API/UI -- resolve_and_resume remains the only path that
    turns a decision into graph/tool-execution state."""
    response = httpx.post(
        f"{config.APPROVAL_SERVICE_ENDPOINT}/proposals/{proposal_id}/decision",
        json={"decision": decision},
        headers=_auth_headers(),
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def resolve_and_resume(graph, thread_config: dict):
    """Query this session's pending proposal (SRS-APR-IF-05); if still
    `pending`, the graph is NOT touched. If terminal, inject the outcome
    using ONLY the values this query just returned (DEC-008: never a
    locally cached copy), then resume. Correlation key:
    `graph.get_state(thread_config).values["proposal_id"]`, set by
    tool_invoke_node at submission time."""
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
