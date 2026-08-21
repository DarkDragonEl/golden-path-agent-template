import httpx2
import openai
import pytest

from agent.model_client import (
    FakeModelClient,
    RoutedModelClient,
    _classify_primary_failure,
)


def _request():
    return httpx2.Request("POST", "https://example.invalid/v1/chat/completions")


def _response(status_code):
    return httpx2.Response(status_code, request=_request())


class _StubClient:
    """Test double for OpenAICompatibleModelClient -- returns a fixed
    (text, tool_calls) or raises a fixed exception, without any real
    network call."""

    def __init__(self, *, returns=None, raises=None):
        self._returns = returns
        self._raises = raises
        self.calls = 0

    def complete(self, system_prompt, messages, tools=None):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._returns


def test_fake_model_client_returns_primary_none_and_no_tool_calls():
    text, tool_calls, route, reason_code = FakeModelClient().complete("sys", [{"role": "user", "content": "hi"}])
    assert tool_calls == []
    assert route == "primary"
    assert reason_code == "none"
    assert "hi" in text


def test_classify_primary_failure_timeout():
    exc = openai.APITimeoutError(request=_request())
    assert _classify_primary_failure(exc) == "primary_timeout"


def test_classify_primary_failure_rate_limit():
    exc = openai.RateLimitError("rate limited", response=_response(429), body=None)
    assert _classify_primary_failure(exc) == "primary_429"


def test_classify_primary_failure_status_error_not_429():
    exc = openai.APIStatusError("bad request", response=_response(400), body=None)
    assert _classify_primary_failure(exc) == "primary_5xx"

    exc2 = openai.InternalServerError("server error", response=_response(500), body=None)
    assert _classify_primary_failure(exc2) == "primary_5xx"


def test_classify_primary_failure_connection_error():
    exc = openai.APIConnectionError(request=_request())
    assert _classify_primary_failure(exc) == "primary_unreachable"


def test_classify_primary_failure_unclassified_exception_falls_back_to_unreachable():
    assert _classify_primary_failure(ValueError("something else entirely")) == "primary_unreachable"


def test_routed_client_primary_success_reports_primary_none():
    primary = _StubClient(returns=("answer", []))
    fallback = _StubClient(returns=("should not be used", []))
    client = RoutedModelClient(primary, fallback)

    text, tool_calls, route, reason_code = client.complete("sys", [])

    assert text == "answer"
    assert route == "primary"
    assert reason_code == "none"
    assert fallback.calls == 0


def test_routed_client_falls_back_on_primary_failure_with_reason_code():
    primary = _StubClient(raises=openai.APIConnectionError(request=_request()))
    fallback = _StubClient(returns=("fallback answer", [{"name": "itsm_search_records", "arguments": {}}]))
    client = RoutedModelClient(primary, fallback)

    text, tool_calls, route, reason_code = client.complete("sys", [])

    assert text == "fallback answer"
    assert tool_calls == [{"name": "itsm_search_records", "arguments": {}}]
    assert route == "fallback"
    assert reason_code == "primary_unreachable"
    assert fallback.calls == 1


def test_routed_client_reraises_when_primary_fails_and_no_fallback_configured():
    primary = _StubClient(raises=openai.APITimeoutError(request=_request()))
    client = RoutedModelClient(primary, None)

    with pytest.raises(openai.APITimeoutError):
        client.complete("sys", [])


def test_routed_client_reraises_when_both_primary_and_fallback_fail():
    primary = _StubClient(raises=openai.APIConnectionError(request=_request()))
    fallback = _StubClient(raises=openai.APIConnectionError(request=_request()))
    client = RoutedModelClient(primary, fallback)

    with pytest.raises(openai.APIConnectionError):
        client.complete("sys", [])
    assert fallback.calls == 1


def test_routed_client_never_calls_fallback_when_primary_succeeds():
    primary = _StubClient(returns=("ok", []))
    fallback = _StubClient(returns=("unused", []))
    RoutedModelClient(primary, fallback).complete("sys", [])
    assert fallback.calls == 0
