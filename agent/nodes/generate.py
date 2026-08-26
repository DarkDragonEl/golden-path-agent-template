"""The `generate` LangGraph node: the golden path's grounded-answer model
call, reached only via `decide_node`'s "no tool needed" branch after
`retrieve_node` (DEC-013's decide-then-retrieve reordering).

Contract: reads `state["input_query"]`/`state["retrieved_docs"]`/
`state["reasoning_steps"]`/`state["model_calls"]`; makes one model call
with a capped context (`config.REASONING_CONTEXT_TOP_K`/
`REASONING_EXCERPT_CHARS` -- see `agent/config.py`'s own comment for the
Phase B4 finding this caps) and no tool schemas at all; returns an update
owning `final_output` for this branch, or `fallback_reason` on total
model failure (SysR-A-F-05/SysR-P-F-12). SRS-AGT-F-01: every
corpus-derived claim in the response must be citable to a `doc_id`/
`version` from the injected context.
"""

from pathlib import Path

from .. import config
from ..model_client import get_model_client

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "generate_system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text()


def generate_node(state):
    """Second, separate model call -- context + citation instructions, no
    tool schemas at all (model.complete's `tools` defaults to None, an
    already-legal call shape). Only reached on decide_node's "no tool
    needed" branch, after retrieve_node. Owns final_output for this branch.

    SRS-AGT-F-01: every corpus-derived claim needs a citation naming the
    source doc_id and version -- the model can't produce one unless the
    context tells it which passage came from which document.
    """
    steps = state.get("reasoning_steps", 0) + 1
    model = get_model_client()

    # Capped subset + excerpt length (config.REASONING_CONTEXT_TOP_K/
    # REASONING_EXCERPT_CHARS), not the full retrieved_docs verbatim -- see
    # agent/config.py's comment for why. state["retrieved_docs"] itself is
    # untouched; only what reaches the model here is capped.
    docs_for_context = state.get("retrieved_docs", [])[: config.REASONING_CONTEXT_TOP_K]
    context = "\n\n".join(
        f"[Source: {d.get('doc_id', '?')}, version {d.get('version', '?')}]\n"
        f"{d.get('passage_text', d.get('snippet', ''))[: config.REASONING_EXCERPT_CHARS]}"
        for d in docs_for_context
    )
    user_message = state["input_query"]
    if context:
        user_message = f"Context:\n{context}\n\nQuestion: {user_message}"

    try:
        text, tool_calls, route_used, reason_code, usage, response_model = model.complete(
            _load_system_prompt(), [{"role": "user", "content": user_message}]
        )
    except Exception as exc:  # noqa: BLE001 - total model failure (both routes exhausted, or none
        # configured) routes to fallback_node, per SysR-A-F-05/SysR-P-F-12.
        reason = f"model_failure:{type(exc).__name__}"
        calls = state.get("model_calls", []) + [
            {
                "node": "generate",
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

    messages = state.get("messages", []) + [{"role": "assistant", "content": text or ""}]
    calls = state.get("model_calls", []) + [
        {
            "node": "generate",
            "route": route_used,
            "reason_code": reason_code,
            "prompt_tokens": (usage or {}).get("prompt_tokens"),
            "completion_tokens": (usage or {}).get("completion_tokens"),
            "total_tokens": (usage or {}).get("total_tokens"),
            "response_model": response_model,
        }
    ]
    return {
        "messages": messages,
        "reasoning_steps": steps,
        "model_route": route_used,
        "model_route_reason_code": reason_code,
        "model_calls": calls,
        "final_output": text or "",
        "pending_approval": False,
        "drafted_action": None,
        "approved_action": None,
    }
