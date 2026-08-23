"""DEC-013 candidate (decide-then-retrieve reordering): generate_node is
the second, separate model call -- context + citation instructions, no
tool schemas -- reached only on decide_node's "no tool needed" branch.
"""

import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

import agent.nodes.generate as generate_module  # noqa: E402
from agent.nodes.generate import generate_node  # noqa: E402


class _StubClient:
    def __init__(self, *, returns=None, raises=None):
        self._returns = returns
        self._raises = raises
        self.last_messages = None
        self.last_tools = "unset"
        self.last_kwargs = None

    def complete(self, system_prompt, messages, tools=None):
        self.last_messages = messages
        self.last_tools = tools
        if self._raises is not None:
            raise self._raises
        return self._returns


def _base_state(**overrides):
    state = {
        "input_query": "What is the maximum execution time for a CI job?",
        "reasoning_steps": 1,
        "messages": [],
        "model_calls": [
            {
                "node": "decide",
                "route": "primary",
                "reason_code": "none",
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            }
        ],
        "retrieved_docs": [],
    }
    state.update(overrides)
    return state


def test_context_formatted_into_user_message(monkeypatch):
    stub = _StubClient(returns=("An answer.\n\nSources: PLAT-003", [], "primary", "none", None, "granite-3-2-8b-instruct-20260101"))
    monkeypatch.setattr(generate_module, "get_model_client", lambda: stub)

    docs = [{"doc_id": "PLAT-003", "version": "2", "passage_text": "Some passage text."}]
    generate_node(_base_state(retrieved_docs=docs))

    sent_content = stub.last_messages[0]["content"]
    assert "[Source: PLAT-003, version 2]" in sent_content
    assert "Some passage text." in sent_content
    assert "Question: What is the maximum execution time for a CI job?" in sent_content


def test_no_context_omits_context_block(monkeypatch):
    stub = _StubClient(returns=("I can't answer that from the platform docs.", [], "primary", "none", None, "granite-3-2-8b-instruct-20260101"))
    monkeypatch.setattr(generate_module, "get_model_client", lambda: stub)

    generate_node(_base_state(retrieved_docs=[]))

    sent_content = stub.last_messages[0]["content"]
    assert "Context:" not in sent_content
    assert sent_content == "What is the maximum execution time for a CI job?"


def test_final_output_set_directly_from_model_text(monkeypatch):
    stub = _StubClient(
        returns=(
            "An answer.\n\nSources: PLAT-003",
            [],
            "primary",
            "none",
            {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52},
            "granite-3-2-8b-instruct-20260101",
        )
    )
    monkeypatch.setattr(generate_module, "get_model_client", lambda: stub)

    result = generate_node(_base_state())

    assert result["final_output"] == "An answer.\n\nSources: PLAT-003"
    assert result["pending_approval"] is False
    assert result["drafted_action"] is None
    assert result["approved_action"] is None
    assert result["model_calls"][-1]["total_tokens"] == 52


def test_model_failure_sets_fallback_reason_and_appends_none_route_to_model_calls(monkeypatch):
    stub = _StubClient(raises=ConnectionError("boom"))
    monkeypatch.setattr(generate_module, "get_model_client", lambda: stub)

    result = generate_node(_base_state())

    assert result["fallback_reason"] == "model_failure:ConnectionError"
    assert result["model_route"] == "none"
    assert result["model_calls"][-1] == {
        "node": "generate",
        "route": "none",
        "reason_code": "model_failure:ConnectionError",
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "response_model": None,
    }
    # decide's earlier entry must survive, not be overwritten.
    assert result["model_calls"][0]["node"] == "decide"
    assert result["model_calls"][0]["route"] == "primary"


def test_called_without_tools_kwarg(monkeypatch):
    # Regression guard: reintroducing TOOL_SCHEMAS here would resurrect
    # DEC-012's exact failure mode inside generate instead of decide.
    stub = _StubClient(returns=("An answer.", [], "primary", "none", None, "granite-3-2-8b-instruct-20260101"))
    monkeypatch.setattr(generate_module, "get_model_client", lambda: stub)

    generate_node(_base_state())

    assert stub.last_tools is None
