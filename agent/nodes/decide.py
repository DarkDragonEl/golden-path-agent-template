from pathlib import Path

from .. import config
from ..model_client import get_model_client
from ..tool_schemas import TOOL_SCHEMAS

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "decide_system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text()


def decide_node(state):
    """DEC-013 candidate (decide-then-retrieve reordering): the sole
    tool-vs-no-tool decision point. Receives only the user query +
    TOOL_SCHEMAS -- no retrieved context, no citation instructions -- so
    citation guidance can no longer compete with tool-calling instructions
    for the model's attention (DEC-012's diagnosed root cause). If no tool
    is selected, routing sends this to retrieve -> generate instead of
    answering here.
    """
    steps = state.get("reasoning_steps", 0) + 1
    model = get_model_client()

    user_message = state["input_query"]
    initiating_user = state.get("user_id")
    if initiating_user:
        # itsm_create_request's required `requested_for` field defaults to
        # whoever is actually asking -- without this, the model has no
        # identity to fill it with and may hesitate to draft at all.
        user_message = f"{user_message}\n\n(Requested by: {initiating_user})"

    try:
        text, tool_calls, route_used, reason_code, usage, response_model = model.complete(
            _load_system_prompt(), [{"role": "user", "content": user_message}], tools=TOOL_SCHEMAS
        )
    except Exception as exc:  # noqa: BLE001 - total model failure (both routes exhausted, or none
        # configured) routes to fallback_node, per SysR-A-F-05/SysR-P-F-12.
        reason = f"model_failure:{type(exc).__name__}"
        calls = state.get("model_calls", []) + [
            {
                "node": "decide",
                "route": "none",
                "reason_code": reason,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "response_model": None,
            }
        ]
        return {
            "reasoning_steps": steps,
            "fallback_reason": reason,
            "model_route": "none",
            "model_route_reason_code": reason,
            "model_calls": calls,
        }

    # On the no-tool branch below, `text` is kept in `messages` for
    # trace/debugging only -- it is never read as final_output. generate_node
    # produces the real, grounded answer from actual retrieved context. Do
    # not "fix" this by wiring text into final_output here -- that would
    # silently bypass SRS-AGT-F-01's grounding requirement.
    messages = state.get("messages", []) + [{"role": "assistant", "content": text or ""}]
    calls = state.get("model_calls", []) + [
        {
            "node": "decide",
            "route": route_used,
            "reason_code": reason_code,
            "prompt_tokens": (usage or {}).get("prompt_tokens"),
            "completion_tokens": (usage or {}).get("completion_tokens"),
            "total_tokens": (usage or {}).get("total_tokens"),
            "response_model": response_model,
        }
    ]
    update = {
        "messages": messages,
        "reasoning_steps": steps,
        "model_route": route_used,
        "model_route_reason_code": reason_code,
        "model_calls": calls,
    }

    if config.AGENT_MODEL_MODE == "fake":
        # FakeModelClient has no real tool-selection awareness -- reproduce
        # the pre-B3/pre-B4 deterministic dispatch exactly here, so
        # eval/cases/EXAMPLE-*.yaml's frozen harness-mechanics fixtures
        # (never domain content, SRS-EVH-F-03) keep passing unchanged.
        # Phase C (DEC-023): write is now signaled by which tool is
        # dispatched, not by an argument flag on placeholder_lookup --
        # EXAMPLE-002's write-classified case calls placeholder_write_action.
        if state.get("write_requested", False):
            update["selected_tool"] = {
                "tool_name": "placeholder_write_action",
                "arguments": {"query": state["input_query"]},
            }
        else:
            update["selected_tool"] = {
                "tool_name": "placeholder_lookup",
                "arguments": {"query": state["input_query"]},
            }
    elif tool_calls:
        # SRS-AGT-F-03: exactly one output type per turn -- the first tool
        # call is authoritative; no multi-step planning loop.
        call = tool_calls[0]
        update["selected_tool"] = {"tool_name": call["name"], "arguments": call["arguments"]}
    else:
        update["selected_tool"] = None  # answer from knowledge -- retrieve + generate handle this

    return update
