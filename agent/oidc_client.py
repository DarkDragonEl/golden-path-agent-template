"""OAuth2 client-credentials token fetch for the agent's own workload
identity -- used to authenticate outbound calls this workload
makes to approval_service and the MCP tool server once AGENT_OIDC_MODE
is "oidc".

In-process cache keyed by (issuer_url, client_id) -- no TTL-refresh
thread, no external store, module-level dict: mirrors
approval_service/auth.py's own JWKS-client cache pattern exactly
(acceptable at demo tier, not a scaffolding this implementation step
takes on). time.monotonic() for expiry math, never wall-clock -- avoids
clock-skew/DST issues over a long-running process.
"""

import time

import httpx

_EXPIRY_SAFETY_BUFFER_SECONDS = 30

_token_cache: dict[tuple[str, str], tuple[str, float]] = {}


def get_service_token(issuer_url: str, client_id: str, client_secret: str, *, timeout: float = 10.0) -> str:
    """Client-credentials grant against the realm's token endpoint.
    Returns the cached token while it remains valid; fetches and caches
    a fresh one on a miss or expiry."""
    cache_key = (issuer_url, client_id)
    cached = _token_cache.get(cache_key)
    if cached is not None:
        token, expires_at = cached
        if time.monotonic() < expires_at:
            return token

    response = httpx.post(
        f"{issuer_url}/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        timeout=timeout,
    )
    response.raise_for_status()
    body = response.json()

    token = body["access_token"]
    expires_at = time.monotonic() + body["expires_in"] - _EXPIRY_SAFETY_BUFFER_SECONDS
    _token_cache[cache_key] = (token, expires_at)
    return token
