"""Phase D2 -- agent/oidc_client.py's caching behavior: fetch on miss,
serve from cache while valid, refetch after expiry. time.monotonic() is
monkeypatched to control the clock deterministically -- no sleeping."""

import httpx
import pytest

from agent import oidc_client


@pytest.fixture(autouse=True)
def _clear_cache():
    oidc_client._token_cache.clear()
    yield
    oidc_client._token_cache.clear()


class _FakeResponse:
    def __init__(self, token: str, expires_in: int):
        self._body = {"access_token": token, "expires_in": expires_in}

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_first_call_fetches_and_returns_token(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append((url, data))
        return _FakeResponse("token-1", 300)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(oidc_client.time, "monotonic", lambda: 1000.0)

    token = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")

    assert token == "token-1"
    assert len(calls) == 1
    assert calls[0][0] == "https://idp.example.invalid/realms/demo/protocol/openid-connect/token"
    assert calls[0][1] == {"grant_type": "client_credentials", "client_id": "client-a", "client_secret": "secret-a"}


def test_cached_token_reused_within_lifetime(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(url)
        return _FakeResponse("token-1", 300)

    fake_clock = {"t": 1000.0}
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(oidc_client.time, "monotonic", lambda: fake_clock["t"])

    first = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")
    fake_clock["t"] = 1050.0  # well within the 300s lifetime minus the 30s buffer
    second = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")

    assert first == second == "token-1"
    assert len(calls) == 1


def test_expired_token_triggers_refetch(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(url)
        return _FakeResponse(f"token-{len(calls)}", 300)

    fake_clock = {"t": 1000.0}
    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(oidc_client.time, "monotonic", lambda: fake_clock["t"])

    first = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")
    fake_clock["t"] = 1000.0 + 300 - 30 + 1  # past expires_at (300s minus 30s safety buffer)
    second = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")

    assert first == "token-1"
    assert second == "token-2"
    assert len(calls) == 2


def test_different_client_id_is_a_separate_cache_key(monkeypatch):
    calls = []

    def fake_post(url, data=None, timeout=None):
        calls.append(data["client_id"])
        return _FakeResponse(f"token-for-{data['client_id']}", 300)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(oidc_client.time, "monotonic", lambda: 1000.0)

    a = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")
    b = oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-b", "secret-b")

    assert a == "token-for-client-a"
    assert b == "token-for-client-b"
    assert len(calls) == 2


def test_non_2xx_response_raises(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return httpx.Response(status_code=401, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        oidc_client.get_service_token("https://idp.example.invalid/realms/demo", "client-a", "secret-a")
