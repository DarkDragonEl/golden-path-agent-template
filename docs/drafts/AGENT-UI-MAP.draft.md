# Approver UI map (DRAFT)

**PROVISIONAL.** Drafted during the `feature/workspace-tooling` mission
by reading the actual page source (`agent/static/approver_ui.html`, in
full) and `docs/owner-walkthrough.md`, while a separate, live session was
actively fixing the walkthrough's port-forward instructions in the same
repo (DEC-075, uncommitted at draft time). The element IDs, states, and
API calls below are read directly out of the shipped JavaScript, not
inferred or guessed from screenshots — but the page was mid-fix
elsewhere in the same commit window, and this draft has not been
exercised against a live browser. **Must be verified against the real
running UI before promotion to `docs/AGENT-UI-MAP.md`.**

## Page inventory

One page, two backing endpoints, both served by the agent
(`AGENT_ORIGIN`, same-origin — no CORS needed for these two):

- `GET /ui` — the static page itself.
- `GET /ui/config` — fetched once at page load, returns
  `{oidc_issuer_url}`. Deliberately not templated into the HTML
  server-side, so the static file stays byte-for-byte cacheable and
  "environment config" stays separate from "static asset" (the page's
  own source comment cites this project's contracts-not-couplings
  convention explicitly).

**States** (`appState` in the page's JS): `login → query → waiting →
review → result`. Exactly one of five `<section>` views is visible at a
time; the rest carry `hidden`.

## Element map (real IDs, read from source)

**`#login-view`**
- `#login-btn` — button, "Log in". Kicks off a PKCE redirect.
- `#login-error` — error text (state mismatch, missing verifier, token
  exchange failure).

**`#query-view`**
- `#query-form` wrapping:
  - `#query-input` — text input, placeholder `e.g. create a ticket
    for...`, required.
  - `#write-checkbox` — checkbox, label "This is a write action". Its
    value is sent explicitly as `write: true/false` in the `/invoke`
    call body — the UI declares intent up front; this is a separate
    signal from the agent's own tool-classification policy, not a
    substitute for it.
  - `#submit-btn` — "Submit".

**`#waiting-view`**
- `#waiting-text` — "Waiting for approval..." while polling, or a
  decision-outcome message / "Finalizing..." while resuming.
- `#start-over-btn-waiting` — "Start over".

**`#review-view`** — one proposal, rendered as a `<dl>` of 9 fields:
`#proposal-id`, `#proposal-action-type`, `#proposal-target-system`,
`#proposal-arguments` (pretty-printed JSON), `#proposal-evidence`
(pretty-printed JSON), `#proposal-initiating-user`,
`#proposal-agent-workload`, `#proposal-session`, `#proposal-request`.
Below that:
- `#decision-buttons` (`#approve-btn`, `#reject-btn`) — **hidden unless**
  the logged-in user's JWT `roles` claim includes `approval-approver`.
- `#decision-readonly-note` — "You are not an approver for this
  proposal -- read only." Shown exactly when `#decision-buttons` is
  hidden. **This is a client-side convenience, not the real enforcement**
  — the actual boundary is server-side: `POST .../decision` returns a
  real `403` for a non-approver token regardless of what this page
  shows, per `approval_service`'s own role check. Worth stating in the
  map explicitly: hiding the buttons is UX, not security.
- `#decision-outcome` — decision result / error text.

**`#result-view`**
- `#result-final-output`, `#result-fallback`.
- `#start-over-btn` — "Start over / new query".

## Flows

**Approver happy path** (`demo-approver`): `#login-btn` → redirect to
Keycloak (`{OIDC_ISSUER_URL}/protocol/openid-connect/auth`, client
`golden-path-agent-approver-ui`, Auth Code + PKCE/S256) → back with
`?code&state` → token exchange → `#query-view` → fill query, check
`#write-checkbox` → `#submit-btn` → `POST {AGENT_ORIGIN}/invoke
{query, write, user_id}`. If the response has no pending approval, it
goes straight to `#result-view`. Otherwise: `#waiting-view`, polling
`GET {APPROVAL_SERVICE_ORIGIN}/proposals?state=pending&
originating_session_id=<id>` every 3s until a proposal appears →
`#review-view` → `#approve-btn` → `POST
{APPROVAL_SERVICE_ORIGIN}/proposals/{id}/decision {decision:"approve"}`
→ on success, `POST {AGENT_ORIGIN}/approvals/{session_id}/resume {}` →
`#result-view` with `final_output` (the `REQ-#####` ticket reference on
a successful ITSM write) and `fallback_reason` (empty on a clean run).

**Read-only path** (`demo-user`, no `approval-approver` role): identical
up through `#review-view`; `#decision-buttons` never renders,
`#decision-readonly-note` shows instead. No client path to decide
exists — and even a forged direct call to the decision endpoint gets a
real server-side `403`, not just a hidden button.

**Reject path**: identical to approve, `#reject-btn` → `{decision:
"reject"}` → same resume flow → `#result-view`, no ticket created,
`fallback_reason` populated.

**Race / expiry path**: while polling, if the tracked proposal
disappears from the pending list without this tab having decided it
(someone else decided first, or it expired server-side), the page calls
`doResume()` anyway — no error surfaced, it just resolves to whatever
terminal state the server already recorded. Worth demonstrating
deliberately in a walkthrough, not just documenting.

**Session-expiry / error edges**: `401` on any poll or decide call →
back to `#login-view` with an explanatory message (no silent retry
loop). `409` on decide, with a non-`pending` state in the body → treated
the same as the race path above (someone else already decided).

## Test personas

- **`demo-approver`** — has the `approval-approver` realm role.
- **`demo-user`** — no roles.

Both are synthetic users in the `golden-path-agent` Keycloak realm
(namespace `golden-path-agent-keycloak`). Passwords are provisioned into
Secret `golden-path-agent-demo-users` (keys `demo-approver-password` /
`demo-user-password`) by `pipelines/bootstrap/provision-identity-
secrets.sh` — referenced here by name only, never by value, per this
mission's own rule.

## Known timing

Polling interval is a hardcoded `setInterval(pollPending, 3000)` in the
page's own JS — confirmed in source, not estimated. The model call
inside `/invoke` is expected to dominate end-to-end latency (it's the
only network hop in the flow with no fixed interval and no local
mock), though this draft has not independently benchmarked it.

## Supporting endpoints referenced by this page

Same-origin (`AGENT_ORIGIN`): `GET /ui`, `GET /ui/config`, `POST
/invoke`, `POST /approvals/{session_id}/resume`.

Cross-origin (`APPROVAL_SERVICE_ORIGIN`, page-load-configurable via
`window.APPROVAL_SERVICE_ORIGIN`, default `http://localhost:8082` — the
DEC-075-corrected port-forward target, not `18082`): `GET
/proposals?state=pending&originating_session_id=...`, `POST
/proposals/{id}/decision`.

---

This draft is the substrate for a future `/ui-walkthrough` browser
automation (Phase E, Chrome-driven) — explicitly out of scope for this
mission.
