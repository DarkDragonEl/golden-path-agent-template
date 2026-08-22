import pytest

from agent import policy

# Phase B2 note: the two tests below (renamed, not deleted) used to verify
# the *general* classification mechanism ("any tool + write:true argument
# => write"). agent/policy.py::classify_action is now a tool-name taxonomy
# (policy/approval_rules.yaml) with a fail-closed default (SRS-AGT-SEC-03);
# what these two tests actually exercise today is a narrow legacy carve-out
# kept alive only for eval/cases/EXAMPLE-002.yaml's frozen fixture (see
# agent/policy.py's _LEGACY_WRITE_FLAG_TOOLS). The general mechanism is
# covered by the taxonomy tests further down, including the SEC-03
# fail-closed inverse case the eval set doesn't cover yet.


def test_placeholder_lookup_without_write_flag_classified_as_read():
    # Formerly test_read_action_not_classified_as_write.
    assert policy.classify_action("placeholder_lookup", {"query": "x"}) == "read"


def test_placeholder_lookup_write_flag_legacy_carveout_classified_as_write():
    # Formerly test_write_flag_classified_as_write. This is EXAMPLE-002.yaml's
    # pinned mechanism specifically, not a general "any tool + write:true"
    # rule -- see the module note above.
    assert policy.classify_action("placeholder_lookup", {"query": "x", "write": True}) == "write"


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
    # executable -- verification the Phase A eval set doesn't cover yet
    # (srs/SRS-AGT.md's own Verification table for SEC-03 flags this gap).
    assert policy.classify_action("some_unlisted_tool", {}) == "write"
    assert policy.requires_approval("some_unlisted_tool", {}) is True


def test_only_a_recognized_write_flag_absent_placeholder_call_is_read_only_by_default():
    # A tool not carrying the legacy write flag and not in the taxonomy at
    # all still fails closed -- the legacy carve-out never widens the
    # fail-closed default, it only narrowly overrides placeholder_lookup's
    # own explicit "read" entry.
    assert policy.classify_action("another_unlisted_tool", {"write": True}) == "write"


def test_step_limit_raises_when_exceeded(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    with pytest.raises(policy.StepLimitExceeded):
        policy.check_step_limit({"reasoning_steps": 2})


def test_step_limit_allows_under_budget(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    policy.check_step_limit({"reasoning_steps": 1})  # should not raise
