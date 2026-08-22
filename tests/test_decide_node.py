"""DEC-013 candidate (decide-then-retrieve reordering): decide_node is the
sole tool-vs-no-tool decision point, called with no retrieved context and
no citation instructions. These tests cover its dispatch shapes and the
literal regression guard for the redesign itself (context never reaches
this call).
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

import agent.nodes.decide as decide_module  # noqa: E402
from agent.nodes.decide import decide_node  # noqa: E402


class _StubClient:
    def __init__(self, *, returns=None, raises=None):
        self._returns = returns
        self._raises = raises
        self.last_messages = None
        self.last_tools = "unset"

    def complete(self, system_prompt, messages, tools=None):
        self.last_messages = messages
        self.last_tools = tools
        if self._raises is not None:
            raise self._raises
        return self._returns


def _base_state(**overrides):
    state = {
        "input_query": "Show me open incidents related to CI pipelines.",
        "user_id": "pytest",
        "reasoning_steps": 0,
        "messages": [],
        "model_calls": [],
        "retrieved_docs": [{"doc_id": "PLAT-001", "version": "1", "passage_text": "unrelated context"}],
    }
    state.update(overrides)
    return state


def test_fake_mode_hardcodes_placeholder_write_action_dispatch_when_write_requested(monkeypatch):
    # Phase C (DEC-023): write is signaled by tool name, not an argument.
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "fake")
    state = _base_state(write_requested=True)
    result = decide_node(state)

    assert result["selected_tool"] == {
        "tool_name": "placeholder_write_action",
        "arguments": {"query": state["input_query"]},
    }


def test_fake_mode_hardcodes_placeholder_lookup_dispatch_when_write_not_requested(monkeypatch):
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "fake")
    state = _base_state(write_requested=False)
    result = decide_node(state)

    assert result["selected_tool"] == {
        "tool_name": "placeholder_lookup",
        "arguments": {"query": state["input_query"]},
    }


def test_model_failure_sets_fallback_reason_and_appends_none_route_to_model_calls(monkeypatch):
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "live")
    stub = _StubClient(raises=ConnectionError("boom"))
    monkeypatch.setattr(decide_module, "get_model_client", lambda: stub)

    result = decide_node(_base_state())

    assert result["fallback_reason"] == "model_failure:ConnectionError"
    assert result["model_route"] == "none"
    assert result["model_calls"] == [
        {
            "node": "decide",
            "route": "none",
            "reason_code": "model_failure:ConnectionError",
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
        }
    ]


def test_tool_call_selected_appends_primary_none_to_model_calls(monkeypatch):
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "live")
    stub = _StubClient(
        returns=(
            "",
            [{"name": "itsm_search_records", "arguments": {"record_type": "incident"}}],
            "primary",
            "none",
            {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28},
        )
    )
    monkeypatch.setattr(decide_module, "get_model_client", lambda: stub)

    result = decide_node(_base_state())

    assert result["selected_tool"] == {"tool_name": "itsm_search_records", "arguments": {"record_type": "incident"}}
    assert result["model_calls"] == [
        {
            "node": "decide",
            "route": "primary",
            "reason_code": "none",
            "prompt_tokens": 20,
            "completion_tokens": 8,
            "total_tokens": 28,
        }
    ]


def test_no_tool_call_sets_selected_tool_none(monkeypatch):
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "live")
    stub = _StubClient(returns=("no tool needed, this is a knowledge question", [], "primary", "none", None))
    monkeypatch.setattr(decide_module, "get_model_client", lambda: stub)

    result = decide_node(_base_state())

    assert result["selected_tool"] is None


def test_context_never_reaches_decide_prompt(monkeypatch):
    # The literal regression guard for the redesign's fix: even when
    # retrieved_docs is populated (e.g. left over from a prior turn),
    # decide_node must never stitch it into the user message it sends --
    # that responsibility belongs solely to generate_node.
    monkeypatch.setattr(decide_module.config, "AGENT_MODEL_MODE", "live")
    stub = _StubClient(returns=("no tool needed", [], "primary", "none", None))
    monkeypatch.setattr(decide_module, "get_model_client", lambda: stub)

    decide_node(_base_state())

    sent_content = stub.last_messages[0]["content"]
    assert "Context:" not in sent_content
    assert "PLAT-001" not in sent_content
    assert stub.last_tools is not None  # decide always calls with tools=TOOL_SCHEMAS
