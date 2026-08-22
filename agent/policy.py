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


# eval/cases/EXAMPLE-002.yaml is a frozen harness-mechanics fixture (never
# domain content — eval/README.md, DECISIONS.md DEC-005) whose write-
# classified case predates the tool-name taxonomy below: it signals via a
# legacy `write: true` argument flag on placeholder_lookup, not by calling
# a different tool. This is a narrow, explicitly-scoped carve-out that
# exists only to keep that pinned fixture green — every other tool call,
# including placeholder_lookup's own default (see
# policy/approval_rules.yaml), is classified purely by name.
#
# This is a second classification signal living alongside the taxonomy —
# precisely the pattern SRS-MIT-IF-03 bans for the real tools ("read vs.
# write is signaled by which operation is called, never by an argument
# flag"). It is tolerated here only because it's narrowly scoped to one
# pinned legacy fixture, not a general mechanism. RETIREMENT TRIGGER: this
# carve-out dies the moment placeholder_lookup itself retires — once
# EXAMPLE-*.yaml fixtures are its only consumers and can be migrated off
# the write:true mechanism per DECISIONS.md DEC-005's own terms, or Phase C
# at the latest. Phase B3 moved tool_invoke_node's own hardcoded dispatch
# into reason_node's fake-mode simulation (agent/nodes/reason.py) — that
# did NOT retire this carve-out, since EXAMPLE-002.yaml's own pinned input
# still depends on the write:true signal regardless of where the dispatch
# hardcoding lives.
_LEGACY_WRITE_FLAG_TOOLS = {"placeholder_lookup"}


def classify_action(tool_name: str, arguments: dict) -> str:
    """Tool-name classification taxonomy (SRS-AGT-SEC-03), loaded from
    policy/approval_rules.yaml via agent/config.py. An unrecognized or
    ambiguous tool name fails closed to "write" (config.DEFAULT_TOOL_CLASSIFICATION)
    — it is never treated as read-only or directly executable.
    """
    if tool_name in _LEGACY_WRITE_FLAG_TOOLS and arguments.get("write"):
        return "write"
    return config.TOOL_CLASSIFICATION.get(tool_name, config.DEFAULT_TOOL_CLASSIFICATION)


def requires_approval(tool_name: str, arguments: dict) -> bool:
    if config.APPROVAL_MODE == "auto":
        return False
    return classify_action(tool_name, arguments) == "write"
