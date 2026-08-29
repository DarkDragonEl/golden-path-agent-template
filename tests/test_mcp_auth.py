"""Tests mcp_server/auth.py's get_authenticated_caller: identity+
audience validation only (no role concept for MCP tool calls). Mirrors
tests/test_approval_service.py's own JWKS-fixture pattern (RSA keypair,
hand-built fake JWKS client) so these tests need no live IdP.
"""

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from starlette.requests import Request

from mcp_server import auth

ISSUER = "https://idp.example.invalid/realms/demo"


def _rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _make_token(private_key, **claims):
    return pyjwt.encode(claims, private_key, algorithm="RS256")


class _FakeSigningKey:
    def __init__(self, key, algorithm_name="RS256"):
        self.key = key
        self.algorithm_name = algorithm_name


class _FakeJWKSClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


def _make_request(headers: dict) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {"type": "http", "headers": raw_headers}
    return Request(scope)


@pytest.fixture(autouse=True)
def _oidc_mode(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", ISSUER)


def test_auth_mode_none_returns_placeholder_identity_no_validation(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_MODE", "none")
    request = _make_request({})
    assert auth.get_authenticated_caller(request) == "dev-caller"


def test_missing_bearer_token_gets_401():
    request = _make_request({})
    with pytest.raises(HTTPException) as exc_info:
        auth.get_authenticated_caller(request)
    assert exc_info.value.status_code == 401


def test_malformed_authorization_header_gets_401():
    request = _make_request({"authorization": "not-a-bearer-token"})
    with pytest.raises(HTTPException) as exc_info:
        auth.get_authenticated_caller(request)
    assert exc_info.value.status_code == 401


def test_wrong_audience_token_gets_401(monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(private_key, sub="some-workload", aud="some-other-audience", iss=ISSUER)
    request = _make_request({"authorization": f"Bearer {token}"})

    with pytest.raises(HTTPException) as exc_info:
        auth.get_authenticated_caller(request)
    assert exc_info.value.status_code == 401


def test_wrong_issuer_token_gets_401(monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(
        private_key, sub="some-workload", aud=auth.MCP_AUDIENCE, iss="https://not-the-real-idp.invalid/realms/demo"
    )
    request = _make_request({"authorization": f"Bearer {token}"})

    with pytest.raises(HTTPException) as exc_info:
        auth.get_authenticated_caller(request)
    assert exc_info.value.status_code == 401


def test_valid_token_passes_and_returns_subject(monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(private_key, sub="golden-path-agent", aud=auth.MCP_AUDIENCE, iss=ISSUER)
    request = _make_request({"authorization": f"Bearer {token}"})

    assert auth.get_authenticated_caller(request) == "golden-path-agent"


def test_token_missing_sub_claim_gets_401(monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(private_key, aud=auth.MCP_AUDIENCE, iss=ISSUER)
    request = _make_request({"authorization": f"Bearer {token}"})

    with pytest.raises(HTTPException) as exc_info:
        auth.get_authenticated_caller(request)
    assert exc_info.value.status_code == 401
