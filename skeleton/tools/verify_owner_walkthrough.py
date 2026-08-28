#!/usr/bin/env python3
"""Scripted, browser-free proof that the real Authorization Code + PKCE
flow (agent/static/approver_ui.html's own login()/handleRedirect() logic,
mirrored here step for step -- never the client's directAccessGrantsEnabled
shortcut) works end to end against a live deployment, before asking the
owner to click through the same path by hand.

Exercises both the positive path (demo-approver: submit a write-drafting
query -> pending -> approve -> ticket) and the negative path (demo-user:
same submission -> pending -> a decision attempt refused 403 server-side),
then leaves the target environment's pending-proposal list
empty.

Requires two port-forwards already running (see docs/owner-walkthrough.md
for the exact commands and the accompanying hosts-file mapping this script
also depends on for OIDC issuer resolution) plus a third matching whatever
local port the served page's own APPROVAL_SERVICE_ORIGIN default names
(this script discovers that port itself -- see fetch_approval_origin()):
  agent            -> http://localhost:18080  (AGENT_ORIGIN)
  Keycloak         -> http://localhost:8080, reached via the internal
                       Service DNS name mapped to 127.0.0.1 in /etc/hosts --
                       not a bare localhost URL.

This script used to hardcode APPROVAL_ORIGIN as a second copy of
agent/static/approver_ui.html's own APPROVAL_SERVICE_ORIGIN default --
exactly the kind of parallel constant that let a real docs/config
mismatch (18082 in the runbook vs. 8082 in the page) pass verification
undetected. It now parses the value out of the live served /ui HTML
instead, so a future drift between the page's default and this script
fails loudly rather than silently agreeing with itself.

Credentials are never hardcoded or logged -- set DEMO_APPROVER_PASSWORD and
DEMO_USER_PASSWORD from docs/owner-walkthrough.md's own retrieval command
immediately before running this script.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import string
import sys
import time
from urllib.parse import parse_qs, urlparse

import requests

AGENT_ORIGIN = os.environ.get("AGENT_ORIGIN", "http://localhost:18080")
CLIENT_ID = "${{ values.name }}-approver-ui"

# Set once, at the top of main(), by fetch_approval_origin() -- never
# hardcoded here. Every function below reads this module global
# rather than taking it as a parameter, to avoid threading it through the
# whole call chain for a value that's fixed for the life of one run.
APPROVAL_ORIGIN = None

# agent/static/approver_ui.html:208 -- the exact line this pattern parses:
#   const APPROVAL_SERVICE_ORIGIN = window.APPROVAL_SERVICE_ORIGIN || "http://localhost:8082";
_APPROVAL_ORIGIN_PATTERN = re.compile(
    r'const\s+APPROVAL_SERVICE_ORIGIN\s*=\s*window\.APPROVAL_SERVICE_ORIGIN\s*\|\|\s*"([^"]+)"'
)


REDIRECT_URI = f"{AGENT_ORIGIN}/ui"
EXPECTED_ISSUER_HOST = "${{ values.name }}-service.${{ values.name }}-keycloak.svc.cluster.local"

# eval/cases/domain/draft_request.yaml::DRQ-001, reused verbatim rather
# than inventing new query text -- an already-proven write-drafting fixture.
DRQ_001_QUERY = (
    "Please raise a request to get an extra namespace quota for my team, "
    "referencing the quota exhaustion known error."
)


class ScenarioFailure(Exception):
    pass


def fetch_approval_origin() -> str:
    """Derives the approval-service origin from the same source of truth
    a real browser uses: the live served /ui page's own hardcoded default,
    not a second copy of that value maintained here. An
    APPROVAL_ORIGIN env var, if set, is an explicit operator override for
    a non-default port-forward -- documented, not a silent fallback."""
    override = os.environ.get("APPROVAL_ORIGIN")
    if override:
        return override
    resp = requests.get(f"{AGENT_ORIGIN}/ui", timeout=10)
    resp.raise_for_status()
    match = _APPROVAL_ORIGIN_PATTERN.search(resp.text)
    if not match:
        raise ScenarioFailure(
            "could not find APPROVAL_SERVICE_ORIGIN's default in the served /ui HTML -- "
            "the page's own source changed shape; update _APPROVAL_ORIGIN_PATTERN, don't "
            "guess a value"
        )
    return match.group(1)


def ok(name: str, detail: str = "") -> None:
    print(f"PASS - {name}" + (f" ({detail})" if detail else ""))


def bad(name: str, detail: str) -> None:
    print(f"FAIL - {name}: {detail}")


def random_pkce_verifier() -> str:
    # Mirrors approver_ui.html::randomPkceVerifier() -- 64 chars, well
    # within the 43-128 char range RFC 7636 requires.
    charset = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(charset) for _ in range(64))


def sha256_b64url(value: str) -> str:
    digest = hashlib.sha256(value.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def random_state() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode()


def decode_jwt_claims(token: str) -> dict:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def fetch_oidc_issuer() -> str:
    resp = requests.get(f"{AGENT_ORIGIN}/ui/config", timeout=10)
    resp.raise_for_status()
    issuer = resp.json()["oidc_issuer_url"]
    if EXPECTED_ISSUER_HOST not in issuer:
        raise ScenarioFailure(f"unexpected issuer host in /ui/config: {issuer}")
    return issuer


def pkce_login(issuer_url: str, username: str, password: str) -> str:
    """Drives the real Authorization Code + PKCE grant exactly as
    approver_ui.html's login()/handleRedirect() do: a real GET against
    Keycloak's own login form, a real credentialed POST, a real
    authorization-code redirect, a real code_verifier token exchange.
    Never the client's directAccessGrantsEnabled shortcut (D2 used that
    for its own sandboxed testing -- using it here would defeat this
    script's entire purpose)."""
    session = requests.Session()
    verifier = random_pkce_verifier()
    challenge = sha256_b64url(verifier)
    state = random_state()

    auth_url = (
        f"{issuer_url}/protocol/openid-connect/auth"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=openid"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
        f"&state={state}"
    )
    login_page = session.get(auth_url, timeout=10)
    login_page.raise_for_status()

    match = re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', login_page.text)
    if not match:
        match = re.search(r'<form[^>]+action="([^"]+)"', login_page.text)
    if not match:
        raise ScenarioFailure("could not find Keycloak login form action in the returned HTML")
    form_action = match.group(1).replace("&amp;", "&")

    login_resp = session.post(
        form_action,
        data={"username": username, "password": password},
        allow_redirects=False,
        timeout=10,
    )
    location = login_resp.headers.get("Location")
    if not location:
        raise ScenarioFailure(
            f"login did not redirect (status {login_resp.status_code}) -- wrong password, or "
            "form field names changed"
        )

    query = parse_qs(urlparse(location).query)
    code = query.get("code", [None])[0]
    returned_state = query.get("state", [None])[0]
    if returned_state != state:
        raise ScenarioFailure("state mismatch on redirect -- possible CSRF")
    if not code:
        raise ScenarioFailure(f"no authorization code in redirect location: {location}")

    token_resp = session.post(
        f"{issuer_url}/protocol/openid-connect/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "code_verifier": verifier,
        },
        timeout=10,
    )
    token_resp.raise_for_status()
    access_token = token_resp.json()["access_token"]
    claims = decode_jwt_claims(access_token)
    if EXPECTED_ISSUER_HOST not in claims.get("iss", ""):
        raise ScenarioFailure(f"unexpected issuer in access token: {claims.get('iss')}")
    return access_token


def submit_write_query(username: str) -> str:
    resp = requests.post(
        f"{AGENT_ORIGIN}/invoke",
        json={"query": DRQ_001_QUERY, "write": True, "user_id": username},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["session_id"]


def poll_pending(session_id: str, token: str, timeout_s: int = 30, interval_s: int = 3) -> dict:
    deadline = time.time() + timeout_s
    attempts = 0
    while time.time() < deadline:
        attempts += 1
        resp = requests.get(
            f"{APPROVAL_ORIGIN}/proposals",
            params={"originating_session_id": session_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        proposals = resp.json()
        if proposals:
            return proposals[0], attempts
        time.sleep(interval_s)
    raise ScenarioFailure(f"no pending proposal for session {session_id} within {timeout_s}s")


def decide(proposal_id: str, token: str, decision: str) -> requests.Response:
    return requests.post(
        f"{APPROVAL_ORIGIN}/proposals/{proposal_id}/decision",
        json={"decision": decision},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )


def resume(session_id: str) -> dict:
    resp = requests.post(f"{AGENT_ORIGIN}/approvals/{session_id}/resume", json={}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_pending(token: str) -> list:
    resp = requests.get(
        f"{APPROVAL_ORIGIN}/proposals", headers={"Authorization": f"Bearer {token}"}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def main() -> int:
    global APPROVAL_ORIGIN

    approver_password = os.environ.get("DEMO_APPROVER_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not approver_password or not user_password:
        print("FAIL - set DEMO_APPROVER_PASSWORD and DEMO_USER_PASSWORD before running")
        return 1

    failures = 0

    try:
        APPROVAL_ORIGIN = fetch_approval_origin()
        ok("approval-service origin derived from the live served /ui page", APPROVAL_ORIGIN)
    except Exception as exc:  # noqa: BLE001
        bad("derive approval-service origin from /ui", str(exc))
        return 1  # nothing else can run without knowing where to poll

    try:
        issuer = fetch_oidc_issuer()
        ok("GET /ui/config returns the expected internal-DNS issuer", issuer)
    except Exception as exc:  # noqa: BLE001 - top-level scenario boundary, intentionally broad
        bad("GET /ui/config", str(exc))
        return 1  # nothing else can run without a valid issuer

    approver_token = None
    try:
        approver_token = pkce_login(issuer, "demo-approver", approver_password)
        claims = decode_jwt_claims(approver_token)
        if "approval-approver" not in claims.get("roles", []):
            raise ScenarioFailure(f"demo-approver token missing approval-approver role: {claims.get('roles')}")
        ok("demo-approver PKCE login", f"sub={claims['sub']}, roles={claims['roles']}")
    except Exception as exc:  # noqa: BLE001
        bad("demo-approver PKCE login", str(exc))
        failures += 1

    if approver_token:
        try:
            session_id = submit_write_query("demo-approver")
            proposal, attempts = poll_pending(session_id, approver_token)
            proposal_id = proposal["proposal_id"]
            ok("submit write query -> pending", f"session={session_id}, proposal={proposal_id}, polls={attempts}")

            decided_resp = decide(proposal_id, approver_token, "approve")
            decided_resp.raise_for_status()
            decided = decided_resp.json()
            if decided["decided_by"] != decode_jwt_claims(approver_token)["sub"]:
                raise ScenarioFailure(
                    f"decided_by ({decided['decided_by']}) does not match token sub"
                )
            ok("approve", f"decided_by={decided['decided_by']}")

            result = resume(session_id)
            final_output = str(result.get("final_output", ""))
            ticket_match = re.search(r"REQ-\d+", final_output)
            if not ticket_match:
                raise ScenarioFailure(f"no REQ-##### ticket in final_output: {final_output!r}")
            ok("resume -> ticket created", ticket_match.group(0))
        except Exception as exc:  # noqa: BLE001
            bad("positive path (demo-approver)", str(exc))
            failures += 1

    user_token = None
    try:
        user_token = pkce_login(issuer, "demo-user", user_password)
        claims = decode_jwt_claims(user_token)
        if "approval-approver" in claims.get("roles", []):
            raise ScenarioFailure(f"demo-user unexpectedly holds approval-approver role: {claims.get('roles')}")
        ok("demo-user PKCE login", f"sub={claims['sub']}, roles={claims.get('roles')}")
    except Exception as exc:  # noqa: BLE001
        bad("demo-user PKCE login", str(exc))
        failures += 1

    if user_token:
        try:
            session_id = submit_write_query("demo-user")
            proposal, attempts = poll_pending(session_id, user_token)
            proposal_id = proposal["proposal_id"]
            ok("demo-user submit write query -> pending", f"session={session_id}, proposal={proposal_id}")

            refused = decide(proposal_id, user_token, "approve")
            if refused.status_code != 403:
                raise ScenarioFailure(f"expected 403, got {refused.status_code}: {refused.text}")
            ok("demo-user decision attempt refused server-side (403)", "authorization enforced server-side, not just hidden in the UI")
        except Exception as exc:  # noqa: BLE001
            bad("negative path (demo-user)", str(exc))
            failures += 1

    if approver_token:
        try:
            pending = list_pending(approver_token)
            for leftover in pending:
                cleanup_resp = decide(leftover["proposal_id"], approver_token, "reject")
                cleanup_resp.raise_for_status()
            pending_after = list_pending(approver_token)
            if pending_after:
                raise ScenarioFailure(f"still pending after cleanup: {pending_after}")
            ok("cleanup", f"{len(pending)} leftover proposal(s) resolved, demo-prod clean")
        except Exception as exc:  # noqa: BLE001
            bad("cleanup", str(exc))
            failures += 1

    print()
    if failures:
        print(f"{failures} scenario(s) FAILED")
        return 1
    print("All scenarios PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
