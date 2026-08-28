"""OpenAI-compatible model client -- the agent talks to an endpoint
exposing an OpenAI-compatible API, never a provider-specific SDK.

Rules-based routing with one configured fallback (SysR-P-F-12,
SRS-AGT-IF-02) -- ADR-002 picked the fallback model (llama-scout-17b).
"""

import json

import openai

from . import config


class FakeModelClient:
    """Deterministic, network-free model client used in offline/eval mode.

    Has no real tool-selection awareness -- it never inspects `tools` to
    decide what to call. reason_node owns the fake-mode dispatch
    simulation (reproducing the pre-B3 hardcoded behavior exactly, so
    eval/cases/EXAMPLE-*.yaml's frozen harness-mechanics fixtures keep
    passing unchanged); this client's `complete()` always reports
    route="primary", reason_code="none" and no tool_calls of its own.
    """

    def complete(self, system_prompt: str, messages: list, tools: list | None = None):
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        text = f"[offline-fake-response] acknowledged: {last_user[:120]}"
        return text, [], "primary", "none", None, None


class OpenAICompatibleModelClient:
    """One physical model route. Raises on failure -- RoutedModelClient is
    responsible for catching, classifying, and retrying against a
    fallback route; this class has no retry logic of its own."""

    def __init__(self, base_url: str, api_key: str, model_name: str):
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model_name = model_name

    def complete(self, system_prompt: str, messages: list, tools: list | None = None):
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            tools=tools,
            temperature=config.MODEL_TEMPERATURE,
            seed=config.MODEL_SEED,
        )
        choice = response.choices[0].message
        tool_calls = []
        for tc in choice.tool_calls or []:
            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append({"name": tc.function.name, "arguments": arguments})
        # R4/ADR-006: SRS-AGT-IF-08 "token consumption" -- `usage` is a
        # standard OpenAI-compatible response field; not every backend
        # reports it, so this stays Optional throughout the call chain.
        usage = None
        if response.usage is not None:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        # response.model reports which model identity actually served the
        # request (can differ from the requested `model` name). Read-only
        # w.r.t. model inputs; threaded through for cross-session drift
        # correlation.
        response_model = response.model
        return choice.content, tool_calls, usage, response_model


def _classify_primary_failure(exc: Exception) -> str:
    """Maps an OpenAI-SDK exception to one of SRS-AGT-IF-02's closed reason
    codes. Order matters: APITimeoutError is-a APIConnectionError, and
    RateLimitError is-a APIStatusError, so the narrower checks must come
    first. Any APIStatusError that isn't specifically a 429 is folded into
    "primary_5xx" -- a simplification of the given closed 4-item enum
    (it has no separate "primary_4xx" bucket), noted here rather than
    silently expanding the enum.
    """
    if isinstance(exc, openai.APITimeoutError):
        return "primary_timeout"
    if isinstance(exc, openai.RateLimitError):
        return "primary_429"
    if isinstance(exc, openai.APIStatusError):
        return "primary_5xx"
    return "primary_unreachable"  # APIConnectionError and anything else unclassified


class RoutedModelClient:
    """Primary + one fallback route, both OpenAI-compatible, with logged
    reason codes (SysR-P-F-12). On any primary failure, retries exactly
    once against the fallback route; on total failure (fallback also
    fails, or none is configured), re-raises for reason_node's own
    try/except to route to fallback_node with fallback_reason="model_failure".
    """

    def __init__(self, primary: OpenAICompatibleModelClient, fallback: OpenAICompatibleModelClient | None):
        self._primary = primary
        self._fallback = fallback

    def complete(self, system_prompt: str, messages: list, tools: list | None = None):
        try:
            text, tool_calls, usage, response_model = self._primary.complete(system_prompt, messages, tools=tools)
            return text, tool_calls, "primary", "none", usage, response_model
        except Exception as primary_exc:  # noqa: BLE001 - reclassified below, not swallowed
            reason_code = _classify_primary_failure(primary_exc)
            if self._fallback is None:
                raise
            text, tool_calls, usage, response_model = self._fallback.complete(system_prompt, messages, tools=tools)
            return text, tool_calls, "fallback", reason_code, usage, response_model


def get_model_client():
    if config.AGENT_MODEL_MODE == "fake":
        return FakeModelClient()

    primary = OpenAICompatibleModelClient(config.MODEL_API_BASE_URL, config.MODEL_API_KEY, config.MODEL_NAME)
    fallback = None
    if config.MODEL_FALLBACK_API_BASE_URL and config.MODEL_FALLBACK_NAME:
        fallback = OpenAICompatibleModelClient(
            config.MODEL_FALLBACK_API_BASE_URL, config.MODEL_API_KEY, config.MODEL_FALLBACK_NAME
        )
    return RoutedModelClient(primary, fallback)
