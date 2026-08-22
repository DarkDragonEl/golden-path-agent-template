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


# Phase C (DEC-023): the legacy _LEGACY_WRITE_FLAG_TOOLS carve-out that
# used to live here is retired. It existed only to let
# eval/cases/EXAMPLE-002.yaml signal a write-classified call via a
# `write: true` argument flag on placeholder_lookup, rather than by
# calling a different tool -- exactly the pattern SRS-MIT-IF-03 bans for
# the real tools ("read vs. write is signaled by which operation is
# called, never by an argument flag"). EXAMPLE-002 now calls
# placeholder_write_action (policy/approval_rules.yaml) instead, so every
# tool call, with no exceptions, is classified purely by name.


def classify_action(tool_name: str, arguments: dict) -> str:
    """Tool-name classification taxonomy (SRS-AGT-SEC-03), loaded from
    policy/approval_rules.yaml via agent/config.py. An unrecognized or
    ambiguous tool name fails closed to "write" (config.DEFAULT_TOOL_CLASSIFICATION)
    — it is never treated as read-only or directly executable. `arguments`
    is accepted for interface stability with callers but no longer
    consulted (Phase C, DEC-023) -- classification is purely tool-name-keyed.
    """
    return config.TOOL_CLASSIFICATION.get(tool_name, config.DEFAULT_TOOL_CLASSIFICATION)


def requires_approval(tool_name: str, arguments: dict) -> bool:
    if config.APPROVAL_MODE == "auto":
        return False
    return classify_action(tool_name, arguments) == "write"
