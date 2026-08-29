import pytest

from agent import policy

# ADR-019: the legacy write:true argument-flag carve-out that
# used to live in agent/policy.py is retired -- classification is now
# purely tool-name-keyed, with no exceptions. The two tests below prove
# exactly that: placeholder_lookup classifies "read" regardless of any
# write argument (the carve-out is truly gone, not just unused), and the
# new placeholder_write_action tool (which EXAMPLE-002.yaml now calls
# instead) classifies "write" via the ordinary taxonomy lookup, same as
# every real domain tool.


def test_placeholder_lookup_classified_as_read_regardless_of_write_argument():
    assert policy.classify_action("placeholder_lookup", {"query": "x"}) == "read"
    assert policy.classify_action("placeholder_lookup", {"query": "x", "write": True}) == "read"


def test_placeholder_write_action_classified_as_write_via_taxonomy():
    assert policy.classify_action("placeholder_write_action", {"query": "x"}) == "write"


def test_itsm_search_records_classified_as_read():
    assert policy.classify_action("itsm_search_records", {"record_type": "incident"}) == "read"


def test_itsm_create_request_classified_as_write():
    assert (
        policy.classify_action(
            "itsm_create_request",
            {"short_description": "x", "description": "x", "category": "access", "requested_for": "x"},
        )
        == "write"
    )


def test_unknown_tool_fails_closed_to_write():
    # SRS-AGT-SEC-03: an action whose tool name is not in the taxonomy is
    # always treated as write-capable, never read-only or directly
    # executable -- verification this eval set doesn't cover yet
    # (srs/SRS-AGT.md's own Verification table for SEC-03 flags this gap).
    assert policy.classify_action("some_unlisted_tool", {}) == "write"
    assert policy.requires_approval("some_unlisted_tool", {}) is True


def test_step_limit_raises_when_exceeded(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    with pytest.raises(policy.StepLimitExceeded):
        policy.check_step_limit({"reasoning_steps": 2})


def test_step_limit_allows_under_budget(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    policy.check_step_limit({"reasoning_steps": 1})  # should not raise
