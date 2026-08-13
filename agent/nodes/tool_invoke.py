from .. import config, policy
from mcp_server.client import call_tool


def tool_invoke_node(state):
    query = state["input_query"]
    tool_name = "placeholder_lookup"
    # TODO(domain): once the real tool schema in mcp_server/schemas.py is
    # defined, replace this argument construction with a real mapping from
    # agent state to that schema's input fields. `write` is a generic
    # placeholder signal for "this call would modify external state" —
    # it exists so the human-approval path is exercisable before any real
    # domain tool is chosen.
    arguments = {"query": query, "write": bool(state.get("write_requested", False))}

    try:
        result = call_tool(tool_name, arguments, timeout=config.TOOL_TIMEOUT_SECONDS)
        error = None
    except Exception as exc:  # noqa: BLE001 - tool failures route to fallback, not a crash
        result = None
        error = str(exc)

    tool_calls = state.get("tool_calls", []) + [
        {"tool_name": tool_name, "arguments": arguments, "result": result, "error": error}
    ]

    if error:
        return {"tool_calls": tool_calls}

    pending = policy.requires_approval(tool_name, arguments)
    update = {
        "tool_calls": tool_calls,
        "pending_approval": pending,
        "approval_action": {"tool_name": tool_name, "arguments": arguments} if pending else None,
    }
    if not pending:
        update["final_output"] = result.get("result", "") if isinstance(result, dict) else str(result)
    return update
