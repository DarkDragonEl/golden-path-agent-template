from pathlib import Path

from ..model_client import get_model_client

_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"


def _load_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text()


def reason_node(state):
    steps = state.get("reasoning_steps", 0) + 1
    model = get_model_client()

    context = "\n\n".join(d.get("snippet", "") for d in state.get("retrieved_docs", []))
    user_message = state["input_query"]
    if context:
        user_message = f"Context:\n{context}\n\nQuestion: {user_message}"

    reply = model.complete(_load_system_prompt(), [{"role": "user", "content": user_message}])
    messages = state.get("messages", []) + [{"role": "assistant", "content": reply}]
    return {"messages": messages, "reasoning_steps": steps}
