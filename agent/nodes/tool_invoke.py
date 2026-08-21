from .. import config, policy
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
            {"tool_name": tool_name, "arguments": arguments, "result": result, "error": error}
        ]
        if error:
            return {"tool_calls": tool_calls}
        return {
            "tool_calls": tool_calls,
            "pending_approval": False,
            "approval_action": None,
            "final_output": format_tool_result(tool_name, result),
        }

    # Write-classified (SRS-AGT-F-04, SRS-MIT-SEC-01): draft only. This
    # node never invokes a write-classified tool -- human_approval_node is
    # the sole invoker, and only on an "approve" decision, reading these
    # exact persisted arguments back from checkpointed state
    # (DECISIONS.md DEC-008).
    tool_calls = tool_calls + [
        {"tool_name": tool_name, "arguments": arguments, "result": None, "error": None}
    ]
    return {
        "tool_calls": tool_calls,
        "pending_approval": True,
        "approval_action": {"tool_name": tool_name, "arguments": arguments},
    }
