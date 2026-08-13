import pytest

from agent import policy


def test_read_action_not_classified_as_write():
    assert policy.classify_action("placeholder_lookup", {"query": "x"}) == "read"


def test_write_flag_classified_as_write():
    assert policy.classify_action("placeholder_lookup", {"query": "x", "write": True}) == "write"


def test_step_limit_raises_when_exceeded(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    with pytest.raises(policy.StepLimitExceeded):
        policy.check_step_limit({"reasoning_steps": 2})


def test_step_limit_allows_under_budget(monkeypatch):
    monkeypatch.setattr(policy.config, "MAX_REASONING_STEPS", 2)
    policy.check_step_limit({"reasoning_steps": 1})  # should not raise
