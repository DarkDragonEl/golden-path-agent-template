from .. import config, policy
from mcp_server.client import call_tool


def tool_invoke_node(state):
    query = state["input_query"]
    tool_name = "placeholder_lookup"
    # TODO(domain): once real model-driven tool selection lands (Phase B3,
    # agent/nodes/reason.py passing itsm_search_records/itsm_create_request
    # as OpenAI-style tools=), replace this hardcoded dispatch with the
    # tool name/arguments the model actually chose. `write` is a legacy
    # signal kept only so eval/cases/EXAMPLE-002.yaml's frozen
    # write-classified fixture keeps working — see agent/policy.py's
    # _LEGACY_WRITE_FLAG_TOOLS; new tools are classified purely by name via
    # policy/approval_rules.yaml.
    arguments = {"query": query, "write": bool(state.get("write_requested", False))}

    classification = policy.classify_action(tool_name, arguments)
    tool_calls = state.get("tool_calls", [])

    if classification != "write":
        # Read-classified: execute eagerly, as before.
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
            "final_output": result.get("result", "") if isinstance(result, dict) else str(result),
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
