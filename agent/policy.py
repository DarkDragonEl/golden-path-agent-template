"""Guardrails for the "deliberately constrained agent": step/timeout limits
and the read-vs-write action classification that drives the human-approval
gate.
"""

from . import config


class StepLimitExceeded(Exception):
    pass


def check_step_limit(state: dict) -> None:
    steps = state.get("reasoning_steps", 0)
    if steps >= config.MAX_REASONING_STEPS:
        raise StepLimitExceeded(
            f"reasoning_steps={steps} >= MAX_REASONING_STEPS={config.MAX_REASONING_STEPS}"
        )


def classify_action(tool_name: str, arguments: dict) -> str:
    """TODO(domain): define the real consequential-action taxonomy for this
    agent's one primary tool integration (e.g. specific operations that
    count as writes). Until a real tool exists, the only signal available
    is an explicit `write` flag on the call arguments; anything without it
    defaults to "read" per the proposal's read-only-by-default principle.
    """
    return "write" if arguments.get("write") else "read"


def requires_approval(tool_name: str, arguments: dict) -> bool:
    if config.APPROVAL_MODE == "auto":
        return False
    return classify_action(tool_name, arguments) == "write"
