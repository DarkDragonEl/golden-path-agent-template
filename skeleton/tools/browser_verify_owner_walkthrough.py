#!/usr/bin/env python3
"""Real-browser (headless Chromium, Playwright) proof that the approver UI
itself -- not a protocol-level mimicry of it -- works end to end, before
asking the owner to click through it by hand. Where
tools/verify_owner_walkthrough.py drives the same HTTP calls the page
makes, this script drives the page's own JavaScript: clicks the real login
button, fills the real Keycloak login form, waits for the real 3-second
poll loop to surface the pending proposal, clicks the real approve button,
and reads the rendered result out of the DOM. Same for the demo-user
negative path -- asserted from the DOM (decide buttons absent, read-only
note present), not inferred from an API response.

One deliberate deviation from docs/owner-walkthrough.md's literal
path: Keycloak hostname
resolution is done via Chromium's own --host-resolver-rules flag, not a
/etc/hosts edit. A real human's browser has no such flag, so
docs/owner-walkthrough.md still instructs the real hosts-file edit -- this
script's approach is a testing convenience for a headless, unattended run,
not a claim that /etc/hosts is unnecessary for the human path.

Every scenario captures: a screenshot per step (reports/browser-walkthrough-
screenshots/), every console message (the run FAILS on any console error),
and the full network log (every request that fails to complete at all is
also a hard failure -- that is exactly the class of bug this guards against).

Requires two port-forwards already running (see docs/owner-walkthrough.md):
  agent            -> http://localhost:18080  (AGENT_ORIGIN)
  Keycloak         -> http://localhost:8080   (mapped via host-resolver-
                       rules below, not /etc/hosts)
Approval-service's origin is discovered from the live /ui page itself
(same fix as tools/verify_owner_walkthrough.py) -- port-forward it
to whatever that page's default says (currently 8082).

Credentials are never hardcoded or logged -- set DEMO_APPROVER_PASSWORD and
DEMO_USER_PASSWORD from docs/owner-walkthrough.md's own retrieval command
immediately before running this script.
"""

import os
import re
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

AGENT_ORIGIN = os.environ.get("AGENT_ORIGIN", "http://localhost:18080")
KEYCLOAK_HOST = "${{ values.name }}-service.${{ values.name }}-keycloak.svc.cluster.local"
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "reports" / "browser-walkthrough-screenshots"

DRQ_001_QUERY = (
    "Please raise a request to get an extra namespace quota for my team, "
    "referencing the quota exhaustion known error."
)


class ScenarioFailure(Exception):
    pass


def ok(name: str, detail: str = "") -> None:
    print(f"PASS - {name}" + (f" ({detail})" if detail else ""))


def bad(name: str, detail: str) -> None:
    print(f"FAIL - {name}: {detail}")


def shot(page, step_num: int, name: str) -> str:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{step_num:02d}_{name}.png"
    page.screenshot(path=str(SCREENSHOT_DIR / filename), full_page=True)
    return filename


class Recorder:
    """Attached to one Playwright page; collects console messages and the
    full request/response lifecycle so a run can be judged after the fact
    against both, not just against whether the final assertion passed."""

    def __init__(self, page):
        self.console_errors = []
        self.console_all = []
        self.requests_failed = []
        self.responses = []
        page.on("console", self._on_console)
        page.on("requestfailed", self._on_request_failed)
        page.on("response", self._on_response)

    def _on_console(self, msg):
        entry = f"[{msg.type}] {msg.text}"
        self.console_all.append(entry)
        if msg.type == "error":
            self.console_errors.append(entry)

    def _on_request_failed(self, request):
        self.requests_failed.append(
            f"{request.method} {request.url} -- {request.failure}"
        )

    def _on_response(self, response):
        self.responses.append((response.request.method, response.url, response.status))

    def assert_clean(self, expected_non_2xx_substrings=()):
        if self.console_errors:
            raise ScenarioFailure(f"console errors occurred: {self.console_errors}")
        if self.requests_failed:
            raise ScenarioFailure(f"requests failed to complete: {self.requests_failed}")
        unexpected = [
            (m, u, s)
            for (m, u, s) in self.responses
            if s >= 400 and not any(sub in u for sub in expected_non_2xx_substrings)
        ]
        if unexpected:
            raise ScenarioFailure(f"unexpected error-status responses: {unexpected}")


def fetch_approval_origin() -> str:
    resp = requests.get(f"{AGENT_ORIGIN}/ui", timeout=10)
    resp.raise_for_status()
    match = re.search(
        r'const\s+APPROVAL_SERVICE_ORIGIN\s*=\s*window\.APPROVAL_SERVICE_ORIGIN\s*\|\|\s*"([^"]+)"',
        resp.text,
    )
    if not match:
        raise ScenarioFailure("could not find APPROVAL_SERVICE_ORIGIN's default in the served /ui HTML")
    return match.group(1)


def login_via_browser(page, recorder, username: str, password: str, step_start: int) -> int:
    """Drives the real login button -> real Keycloak form -> real redirect
    back to /ui. Returns the next free screenshot step number."""
    step = step_start
    page.click("#login-btn")
    page.wait_for_selector("#kc-form-login", timeout=15000)
    shot(page, step, f"keycloak_login_form_{username}")
    step += 1

    page.fill("#username", username)
    page.fill("#password", password)
    page.click("#kc-login")
    page.wait_for_function(
        "() => !document.getElementById('query-view').hidden", timeout=15000
    )
    shot(page, step, f"logged_in_{username}")
    step += 1

    identity_text = page.inner_text("#identity-line")
    if username not in identity_text:
        raise ScenarioFailure(f"identity line doesn't mention {username}: {identity_text!r}")
    ok(f"{username} real-browser login", identity_text)
    return step


def submit_write_query(page) -> None:
    page.fill("#query-input", DRQ_001_QUERY)
    if not page.is_checked("#write-checkbox"):
        page.check("#write-checkbox")
    page.click("#submit-btn")


def wait_for_pending_review(page, timeout_s: int = 30) -> float:
    """Waits for the real poll loop (3s interval, agent/static/
    approver_ui.html::pollPending) to surface review-view. Returns elapsed
    seconds as evidence real polling happened, not an instant mock."""
    start = time.time()
    page.wait_for_function(
        "() => !document.getElementById('review-view').hidden", timeout=timeout_s * 1000
    )
    return time.time() - start


def cleanup_via_api(approval_origin: str, approver_token: str) -> int:
    resp = requests.get(
        f"{approval_origin}/proposals", headers={"Authorization": f"Bearer {approver_token}"}, timeout=10
    )
    resp.raise_for_status()
    pending = resp.json()
    for p in pending:
        r = requests.post(
            f"{approval_origin}/proposals/{p['proposal_id']}/decision",
            json={"decision": "reject"},
            headers={"Authorization": f"Bearer {approver_token}"},
            timeout=10,
        )
        r.raise_for_status()
    verify = requests.get(
        f"{approval_origin}/proposals", headers={"Authorization": f"Bearer {approver_token}"}, timeout=10
    )
    verify.raise_for_status()
    if verify.json():
        raise ScenarioFailure(f"still pending after cleanup: {verify.json()}")
    return len(pending)


def main() -> int:
    approver_password = os.environ.get("DEMO_APPROVER_PASSWORD")
    user_password = os.environ.get("DEMO_USER_PASSWORD")
    if not approver_password or not user_password:
        print("FAIL - set DEMO_APPROVER_PASSWORD and DEMO_USER_PASSWORD before running")
        return 1

    try:
        approval_origin = fetch_approval_origin()
        ok("approval-service origin derived from the live served /ui page", approval_origin)
    except Exception as exc:  # noqa: BLE001
        bad("derive approval-service origin from /ui", str(exc))
        return 1

    failures = 0
    step = 1
    approver_token = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[f"--host-resolver-rules=MAP {KEYCLOAK_HOST} 127.0.0.1"],
        )
        context = browser.new_context()
        page = context.new_page()
        recorder = Recorder(page)

        try:
            # --- Positive path: demo-approver ---
            page.goto(f"{AGENT_ORIGIN}/ui")
            shot(page, step, "initial_load")
            step += 1

            step = login_via_browser(page, recorder, "demo-approver", approver_password, step)
            approver_token = page.evaluate("accessToken")

            # Pre-flight debris check, using the token this real login just
            # obtained -- clean before adding new state, matching prior
            # sessions' own pre-flight discipline.
            leftover = cleanup_via_api(approval_origin, approver_token)
            ok("pre-flight debris check", f"{leftover} leftover proposal(s) resolved" if leftover else "clean")

            submit_write_query(page)
            shot(page, step, "query_submitted")
            step += 1

            page.wait_for_function("() => !document.getElementById('waiting-view').hidden", timeout=10000)
            shot(page, step, "waiting_for_approval")
            step += 1

            elapsed = wait_for_pending_review(page)
            shot(page, step, "pending_proposal_review")
            step += 1
            proposal_id = page.inner_text("#proposal-id")
            decision_buttons_hidden = page.get_attribute("#decision-buttons", "hidden")
            if decision_buttons_hidden is not None:
                raise ScenarioFailure("decide buttons unexpectedly hidden for demo-approver")
            ok(
                "real 3s poll loop surfaced the pending proposal",
                f"proposal={proposal_id}, elapsed={elapsed:.1f}s",
            )

            page.click("#approve-btn")
            page.wait_for_function("() => !document.getElementById('result-view').hidden", timeout=15000)
            shot(page, step, "result_ticket")
            step += 1
            final_output = page.inner_text("#result-final-output")
            ticket_match = re.search(r"REQ-\d+", final_output)
            if not ticket_match:
                raise ScenarioFailure(f"no REQ-##### ticket in rendered result: {final_output!r}")
            ok("clicked real Approve button -> ticket rendered in DOM", ticket_match.group(0))

        except Exception as exc:  # noqa: BLE001
            bad("positive path (demo-approver, real browser)", str(exc))
            failures += 1

        # approver_ui.html has no logout mechanism, and
        # Keycloak's SSO session cookie means a second "Log in" click in
        # the SAME cookie jar silently re-authenticates as whoever logged
        # in first -- confirmed live, the login form never even renders.
        # A fresh browser context is the automated equivalent of a private/
        # incognito window (isolated cookie jar) -- not a workaround, the
        # correct way to switch identities given no in-app logout exists.
        # docs/owner-walkthrough.md's Part 2 is corrected to match.
        user_context = browser.new_context()
        user_page = user_context.new_page()
        user_recorder = Recorder(user_page)

        try:
            # --- Negative path: demo-user ---
            user_page.goto(f"{AGENT_ORIGIN}/ui")
            shot(user_page, step, "fresh_context_for_demo_user")
            step += 1

            step = login_via_browser(user_page, user_recorder, "demo-user", user_password, step)
            page = user_page  # remaining negative-path code below reuses `page`
            identity_text = page.inner_text("#identity-line")
            if "not an approver" not in identity_text:
                raise ScenarioFailure(f"identity line doesn't show non-approver framing: {identity_text!r}")

            submit_write_query(page)
            page.wait_for_function("() => !document.getElementById('waiting-view').hidden", timeout=10000)
            shot(page, step, "demo_user_waiting")
            step += 1

            wait_for_pending_review(page)
            shot(page, step, "demo_user_pending_review")
            step += 1

            decision_buttons_hidden = page.get_attribute("#decision-buttons", "hidden")
            if decision_buttons_hidden is None:
                raise ScenarioFailure("decide buttons present in DOM for demo-user -- should be hidden")
            readonly_note_hidden = page.get_attribute("#decision-readonly-note", "hidden")
            if readonly_note_hidden is not None:
                raise ScenarioFailure("read-only note hidden for demo-user -- should be visible")
            readonly_text = page.inner_text("#decision-readonly-note")
            if "not an approver" not in readonly_text:
                raise ScenarioFailure(f"unexpected read-only note text: {readonly_text!r}")
            ok(
                "demo-user: decide buttons absent from DOM, read-only note rendered",
                readonly_text,
            )

        except Exception as exc:  # noqa: BLE001
            bad("negative path (demo-user, real browser)", str(exc))
            failures += 1

        # --- Console / network diagnostics, evaluated across BOTH contexts ---
        total_responses = len(recorder.responses) + len(user_recorder.responses)
        try:
            recorder.assert_clean(expected_non_2xx_substrings=())
            user_recorder.assert_clean(expected_non_2xx_substrings=())
            ok(
                "console + network diagnostics clean across the whole run (both browser contexts)",
                f"{total_responses} responses observed, 0 console errors, 0 failed requests",
            )
        except Exception as exc:  # noqa: BLE001
            bad("console/network diagnostics", str(exc))
            failures += 1

        # --- Cleanup ---
        try:
            if approver_token:
                leftover = cleanup_via_api(approval_origin, approver_token)
                ok("cleanup", f"{leftover} leftover proposal(s) resolved, demo-prod clean")
            else:
                bad("cleanup", "no approver token captured -- cannot verify demo-prod is clean")
                failures += 1
        except Exception as exc:  # noqa: BLE001
            bad("cleanup", str(exc))
            failures += 1

        user_context.close()
        browser.close()

    print()
    print(f"Screenshots written to: {SCREENSHOT_DIR}")
    print(f"Total network responses observed: {total_responses}")
    if failures:
        print(f"{failures} scenario(s) FAILED")
        return 1
    print("All scenarios PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
