# ADR-024: Static HTML Approver UI

## Context
Human approval of agent-proposed writes needs a UI an approver can actually
use without an elaborate portal or dedicated training. A CLI subcommand
would satisfy the workflow but not the requirement to demonstrate the
decision live, visually, in a browser.

## Decision
The approver UI is a single self-contained static HTML file
(`agent/static/approver_ui.html`, inline CSS/JS, no framework or build
toolchain), served by the agent's own FastAPI app at `GET /ui`. The page
authenticates directly via Authorization Code + PKCE and calls the approval
service's own endpoints directly for decision-context, decide, and list —
never proxied through the agent — polling the approval service every 3
seconds to detect new or externally-resolved proposals.

## Consequences
- No portal framework or build pipeline is introduced for approvals; adding
  one later is a deliberate scope change, not a natural extension of this
  page.
- The access token lives in memory only, never `localStorage`/
  `sessionStorage`, so it does not outlive the browser tab; approve/reject
  buttons are gated client-side on the approver role claim for UX only — the
  approval service's own server-side check is the real enforcement, and must
  remain so regardless of what the client does.
- The page's origin differs from the approval service's, so the approval
  service allows permissive CORS origins; safe only because every route
  still requires a valid bearer token — removing that check would make the
  permissive CORS setting unsafe.
- The page must keep handling "another approver already decided it" as a
  normal, race-safe outcome, not an error, and fetches the OIDC issuer URL
  at load from `GET /ui/config` rather than templating it server-side, so
  `GET /ui` stays a genuinely static, cached read.

## Supersedes / Superseded-by
None.

## Journal
DEC-072
