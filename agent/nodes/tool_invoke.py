"""Tool-execution node for a turn where decide_node selected a tool:
read-classified tools are invoked eagerly here; write-classified tools are
only ever drafted and submitted to the standalone approval service, never
executed by this node (SRS-AGT-F-04, SRS-MIT-SEC-01) — agent/nodes/
human_approval.py's human_approval_node is the sole invoker of an approved
write, and only from approved_action.

Node contract: reads state["selected_tool"] ({tool_name, arguments}, set by
decide_node — never None here, see agent/routers.py's decide_after_decide).
The read branch returns tool_calls plus final_output. The write branch
returns tool_calls, drafted_action, and pending_approval=True plus
proposal_id on a successful submission to the approval service (Phase D,
DECISIONS.md DEC-008/DEC-049), or pending_approval=False plus a
fallback_reason ("approval_service_failure:<ExcType>") if the approval
service itself is unreachable or errors.

Reads config.TOOL_TIMEOUT_SECONDS and config.AGENT_WORKLOAD_ID via
agent/config.py; classification comes from agent/policy.py::classify_action
against the policy bundle named by config.APPROVAL_RULES_REF.
"""

from .. import approval_client, config, policy
from ..tool_result_format import format_tool_result
from mcp_server.client import call_tool


def tool_invoke_node(state):
    """No hardcoded tool selection here (Phase B3 retired it) -- decide_node
    is solely responsible for deciding what state["selected_tool"] is, for
    both live mode (the model's real tool_calls) and fake/offline mode (a
    reproduction of the pre-B3 legacy dispatch, kept only so
    eval/cases/EXAMPLE-*.yaml's frozen fixtures keep passing). This node's
    job is purely execution-timing: read-classified now, write-classified
    drafted only.

    Precondition (DEC-013 candidate: decide-then-retrieve reordering):
    state["selected_tool"] is never None here -- the graph's
    decide_after_decide router sends that case to retrieve/generate
    instead. The "plain answer" branch this node used to own now belongs
    to generate_node.
    """
    selected = state["selected_tool"]
    tool_name = selected["tool_name"]
    arguments = selected["arguments"]

    classification = policy.classify_action(tool_name, arguments)
    tool_calls = state.get("tool_calls", [])

    if classification != "write":
        # Read-classified: execute eagerly.
        try:
            result = call_tool(tool_name, arguments, timeout=config.TOOL_TIMEOUT_SECONDS)
            error = None
        except Exception as exc:  # noqa: BLE001 - tool failures route to fallback, not a crash
            result = None
            error = str(exc)

        tool_calls = tool_calls + [
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
                "error": error,
                "classification": classification,
            }
        ]
        if error:
            return {"tool_calls": tool_calls}
        return {
            "tool_calls": tool_calls,
            "pending_approval": False,
            "drafted_action": None,
            "approved_action": None,
            "final_output": format_tool_result(tool_name, result),
        }

    # Write-classified (SRS-AGT-F-04, SRS-MIT-SEC-01): draft only, then
    # submit a proposal (DEC-008/DEC-049). human_approval_node is the sole
    # invoker, executing only approved_action, never this node's drafted
    # copy.
    tool_calls = tool_calls + [
        {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": None,
            "error": None,
            "classification": classification,
        }
    ]
    drafted_action = {"tool_name": tool_name, "arguments": arguments}

    # evidence_refs (SRS-APR-IF-01): always empty here -- retrieve_node is
    # never reached on a tool-selected turn (DEC-013). Legitimate at the
    # schema layer (DEC-046), not a bug; a richer evidence trail is
    # deferred scope.
    evidence_refs: list[str] = []

    try:
        submitted = approval_client.submit_proposal(
            action_type=tool_name,
            target_system_id="mock-itsm",  # this demo's one enterprise tool (SRS-MIT), matching
            # mcp_server/schemas.py's own "source": "mock-itsm" convention.
            action_arguments=arguments,
            evidence_refs=evidence_refs,
            initiating_user_id=state.get("user_id", ""),
            agent_workload_id=config.AGENT_WORKLOAD_ID,
            originating_session_id=state["session_id"],
            originating_request_id=state.get("request_id", ""),
            idempotency_key=state.get("request_id"),
        )
    except Exception as exc:  # noqa: BLE001 - approval-service unreachable/erroring routes to
        # fallback, per the same pattern decide_node/generate_node use for total model failure --
        # a distinct reason-code prefix names this as an approval-service failure, not a model one.
        reason = f"approval_service_failure:{type(exc).__name__}"
        return {
            "tool_calls": tool_calls,
            "drafted_action": drafted_action,
            "pending_approval": False,
            "fallback_reason": reason,
        }

    return {
        "tool_calls": tool_calls,
        "pending_approval": True,
        "proposal_id": submitted["proposal_id"],
        "drafted_action": drafted_action,
    }
