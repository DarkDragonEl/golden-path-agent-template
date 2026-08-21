from pathlib import Path

from .. import config
from ..model_client import get_model_client
from ..tool_schemas import TOOL_SCHEMAS

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text()


def reason_node(state):
    steps = state.get("reasoning_steps", 0) + 1
    model = get_model_client()

    # SRS-AGT-F-01: every corpus-derived claim needs a citation naming the
    # source doc_id and version -- the model can't produce one unless the
    # context tells it which passage came from which document.
    context = "\n\n".join(
        f"[Source: {d.get('doc_id', '?')}, version {d.get('version', '?')}]\n"
        f"{d.get('passage_text', d.get('snippet', ''))}"
        for d in state.get("retrieved_docs", [])
    )
    user_message = state["input_query"]
    if context:
        user_message = f"Context:\n{context}\n\nQuestion: {user_message}"
    initiating_user = state.get("user_id")
    if initiating_user:
        # itsm_create_request's required `requested_for` field defaults to
        # whoever is actually asking -- without this, the model has no
        # identity to fill it with and may hesitate to draft at all.
        user_message = f"{user_message}\n\n(Requested by: {initiating_user})"

    try:
        text, tool_calls, route_used, reason_code = model.complete(
            _load_system_prompt(), [{"role": "user", "content": user_message}], tools=TOOL_SCHEMAS
        )
    except Exception as exc:  # noqa: BLE001 - total model failure (both routes exhausted, or none
        # configured) routes to fallback_node, per SysR-A-F-05/SysR-P-F-12; this
        # closes the operational category's model-failure known-gap (THRESHOLDS.md
        # removal trigger, SRS-EVH-F-04). `category:detail` shape, matching the
        # existing tool_error:<message> / approval_not_granted:<decision>
        # convention (agent/nodes/fallback.py, human_approval.py) -- only the
        # "model_failure" prefix is asserted by eval scoring, per
        # eval/cases/domain/operational.yaml's own stated convention.
        reason = f"model_failure:{type(exc).__name__}"
        return {
            "reasoning_steps": steps,
            "fallback_reason": reason,
            "model_route": "none",
            "model_route_reason_code": reason,
        }

    messages = state.get("messages", []) + [{"role": "assistant", "content": text or ""}]
    update = {
        "messages": messages,
        "reasoning_steps": steps,
        "model_route": route_used,
        "model_route_reason_code": reason_code,
    }

    if config.AGENT_MODEL_MODE == "fake":
        # FakeModelClient has no real tool-selection awareness -- reproduce
        # the pre-B3 deterministic dispatch exactly here, so
        # eval/cases/EXAMPLE-*.yaml's frozen harness-mechanics fixtures
        # (never domain content, SRS-EVH-F-03) keep passing unchanged.
        # tool_invoke_node itself no longer hardcodes anything -- this is
        # the one place fake-mode's legacy simulated selection lives now.
        update["selected_tool"] = {
            "tool_name": "placeholder_lookup",
            "arguments": {"query": state["input_query"], "write": bool(state.get("write_requested", False))},
        }
    elif tool_calls:
        # SRS-AGT-F-03: exactly one output type per turn -- the first tool
        # call is authoritative; no multi-step planning loop.
        call = tool_calls[0]
        update["selected_tool"] = {"tool_name": call["name"], "arguments": call["arguments"]}
    else:
        update["selected_tool"] = None  # a plain answer -- no tool needed this turn

    return update
