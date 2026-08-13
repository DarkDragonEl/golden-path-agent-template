"""OpenAI-compatible model client, per the proposal's contract-driven
architecture principle: the agent talks to an endpoint that exposes an
OpenAI-compatible API, never a provider-specific SDK.
"""

import openai

from . import config


class FakeModelClient:
    """Deterministic, network-free model client used in offline/eval mode."""

    def complete(self, system_prompt: str, messages: list) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        return f"[offline-fake-response] acknowledged: {last_user[:120]}"


class OpenAICompatibleModelClient:
    def __init__(self):
        self._client = openai.OpenAI(
            base_url=config.MODEL_API_BASE_URL,
            api_key=config.MODEL_API_KEY,
        )

    def complete(self, system_prompt: str, messages: list) -> str:
        response = self._client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}, *messages],
        )
        return response.choices[0].message.content


def get_model_client():
    if config.AGENT_MODEL_MODE == "fake":
        return FakeModelClient()
    return OpenAICompatibleModelClient()
