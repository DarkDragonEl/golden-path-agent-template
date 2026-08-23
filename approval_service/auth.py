"""FastAPI auth dependency -- SRS-APR-SEC-02/03. Establishes the deciding
approver's identity from the request's authenticated session (never a
client-supplied field, SEC-03) and enforces the approver role (SEC-02).

AUTH_MODE=none: no real IdP exists yet (D2 not landed) -- returns a fixed
placeholder identity, no token validation at all. This is what lets D1 be
built, tested, and demoed before D2's real IdP exists (config.py's own
comment: "lets D1 be built, tested, and demoed before D2's real IdP
exists"). AUTH_MODE=oidc: implemented for real here, not a second
NotImplementedError stub -- D2's own scope explicitly expects this branch
to already work once a real IdP exists.

Distinguishing "the agent's own workload token" from "an approver's
token" is deliberately NOT done here -- per the D1 brief, that is D2's
role-assignment concern (the agent's client never gets the approver
role). This module only ever asks one question: does the validated
token's role claim carry the configured approver role? An agent token
lacking that role is rejected by exactly the same logic that rejects
anyone else without it.
"""

import logging

import httpx
import jwt
from fastapi import HTTPException, Request

from . import config

_audit_logger = logging.getLogger("approval_service.audit")

_DEV_APPROVER_IDENTITY = "dev-approver"

# In-process JWKS-client cache, keyed by issuer URL -- no TTL/refresh
# beyond process lifetime, matching this repo's other in-process caches
# (agent/telemetry.py's prompt-version hashes, computed once at import).
# A JWKS key rotation needs a process restart to be picked up under
# AUTH_MODE=oidc today -- acceptable at demo tier; not a scaffolding this
# implementation step takes on.
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


def _extract_roles(claims: dict) -> list:
    raw = claims.get(config.APPROVER_ROLE_CLAIM)
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _validate_bearer_token(request: Request) -> dict:
    """Shared identity+audience validation -- the part `get_current_approver`
    and `get_authenticated_caller` both need. Raises HTTPException(401) for
    a missing/invalid/wrong-audience/wrong-issuer token; never checks a
    role (callers decide that, or don't)."""
    if config.AUTH_MODE != "oidc":
        raise HTTPException(status_code=500, detail=f"unsupported AUTH_MODE: {config.AUTH_MODE!r}")

    auth_header = request.headers.get("authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        jwks_client = _get_jwks_client(config.OIDC_ISSUER_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=config.OIDC_AUDIENCE,
            issuer=config.OIDC_ISSUER_URL,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid token: {exc}") from None

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="token missing 'sub' claim")

    return claims


def get_current_approver(request: Request) -> str:
    """SRS-APR-SEC-02/03. Returns the deciding approver's identity,
    established from the authenticated session -- never a client-supplied
    field (ProposalDecision carries none). Raises HTTPException(401) for
    a missing/invalid token; HTTPException(403), audit-logged, if the
    validated token lacks the configured approver role (SEC-02)."""
    if config.AUTH_MODE == "none":
        return _DEV_APPROVER_IDENTITY

    claims = _validate_bearer_token(request)
    sub = claims["sub"]

    roles = _extract_roles(claims)
    if config.APPROVER_ROLE_VALUE not in roles:
        _audit_logger.warning(
            "refused decision attempt: identity=%s reason=missing_approver_role role_claim=%s",
            sub,
            config.APPROVER_ROLE_CLAIM,
        )
        raise HTTPException(status_code=403, detail="caller lacks the approver role")

    return sub


_DEV_CALLER_IDENTITY = "dev-caller"


def get_authenticated_caller(request: Request) -> str:
    """SRS-APR-SEC-03's identity-propagation requirement, applied to the
    three endpoints DEC-069 found running with no auth check at all under
    AUTH_MODE=oidc (create_proposal, list_pending_proposals, get_proposal)
    -- fail-closed (SEC-01) demands SOME authenticated caller, but none of
    these three are role-gated the way decide_proposal is: IF-04/IF-05 are
    legitimately called by both the agent's own workload token and, for
    D3's UI, a human approver's token, and neither needs the approver role
    just to read. Identity+audience only, mirrors mcp_server/auth.py's own
    get_authenticated_caller exactly (same rationale: this service's own
    equivalent, no role concept for these three routes)."""
    if config.AUTH_MODE == "none":
        return _DEV_CALLER_IDENTITY

    claims = _validate_bearer_token(request)
    return claims["sub"]
