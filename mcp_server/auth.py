"""Auth check for the POST /tools/{tool_name} REST route -- the one new
server-to-server surface this module gates (SRS scope: identity+audience
validation only, no role concept -- MCP tool calls have no equivalent of
approval_service's "approver role"). Mirrors approval_service/auth.py's
JWKS-discovery-and-cache shape and its algorithm-confusion-safe
validation (signing_key.algorithm_name) -- kept as a separate sibling
file rather than a shared module: these are two independently-owned
services in this repo's boundary model, and duplicating this much is
cheaper than introducing a shared auth library for one demo-scope route.

MCP_AUTH_MODE=none: no real IdP wired to this surface, no token
validation at all -- same posture as approval_service's AUTH_MODE=none.
MCP_AUTH_MODE=oidc: implemented for real, validated against this
server's own known audience.
"""

import os

import httpx
import jwt
from fastapi import HTTPException, Request

_DEV_CALLER_IDENTITY = "dev-caller"

# approval_service's equivalent (OIDC_AUDIENCE) is a *configured* value on
# its own config module; mcp_server has no config module to add a setting
# to without creating one for this alone. A hardcoded constant matching
# this one specific server's own identity is fine and arguably clearer.
MCP_AUDIENCE = "golden-path-agent-mcp"

# In-process JWKS-client cache, keyed by issuer URL -- same posture as
# approval_service/auth.py's own cache: no TTL/refresh beyond process
# lifetime, acceptable at demo tier.
_jwks_client_cache: dict[str, jwt.PyJWKClient] = {}


def _discover_jwks_uri(issuer_url: str) -> str:
    discovery_url = issuer_url.rstrip("/") + "/.well-known/openid-configuration"
    response = httpx.get(discovery_url, timeout=10.0)
    response.raise_for_status()
    return response.json()["jwks_uri"]


def _get_jwks_client(issuer_url: str) -> jwt.PyJWKClient:
    client = _jwks_client_cache.get(issuer_url)
    if client is None:
        jwks_uri = _discover_jwks_uri(issuer_url)
        client = jwt.PyJWKClient(jwks_uri)
        _jwks_client_cache[issuer_url] = client
    return client


def get_authenticated_caller(request: Request) -> str:
    """Fail-closed identity+audience validation, no role check. Raises
    HTTPException(401) for a missing/invalid/wrong-audience/wrong-issuer
    token. Returns the validated token's `sub` claim (MCP_AUTH_MODE=none:
    a fixed placeholder identity, mirroring approval_service's own
    AUTH_MODE=none dev identity)."""
    auth_mode = os.environ.get("MCP_AUTH_MODE", "none")
    if auth_mode == "none":
        return _DEV_CALLER_IDENTITY

    if auth_mode != "oidc":
        raise HTTPException(status_code=500, detail=f"unsupported MCP_AUTH_MODE: {auth_mode!r}")

    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    issuer_url = os.environ.get("OIDC_ISSUER_URL")
    try:
        jwks_client = _get_jwks_client(issuer_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=MCP_AUDIENCE,
            issuer=issuer_url,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from None

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="token missing 'sub' claim")

    return sub
