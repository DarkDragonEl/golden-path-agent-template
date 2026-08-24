# Owner walkthrough — live approver UI click-through (Checkpoint D closure)

## What this is

`SRS-APR-QUAL-01`'s non-developer walkthrough — the one item still open
from Checkpoint D. Everything the UI itself calls has already been proven
correct at the API level (`reports/checkpoint-d-run.md`,
`reports/phase-d-owner-walkthrough-verification.md`, the latter driving
the exact same Authorization Code + PKCE flow you're about to click
through, scripted end-to-end against real `demo-prod`, `DEC-074`). This is
your own click-through of that same flow in a real browser — completing
it is what formally closes Checkpoint D.

## Pre-flight verification (already done — read this before you start)

The first attempt at this walkthrough broke: login and submit worked, but
the pending-proposal card never appeared. Root cause, found and fixed
(`DEC-075`): the port-forward instructions below used to say local port
`18082` for the approval-service; the page's own code only ever looks for
it at `localhost:8082`. Nothing was listening on `8082`, so the page's
poll loop retried silently forever with no visible error. This is now
fixed in the instructions below, and the whole path has been re-verified
live, end to end, against real `demo-prod`:

- `tools/verify_owner_walkthrough.py` — scripted Authorization Code +
  PKCE flow, both the `demo-approver` path (submit → pending → approve →
  ticket) and the `demo-user` path (submit → pending → decision refused
  `403`) — **10/10 scenarios PASS**, most recently run against the exact
  port-forward commands below.
- `demo-prod` confirmed clean of pending debris both before and after
  that run (`GET /proposals` → `[]`).
- Full transcripts, root-cause investigation, and evidence:
  `reports/phase-d-owner-walkthrough-verification.md` (see the `DEC-075`
  addendum at the end) and `DECISIONS.md` `DEC-075`.

**If you already had port-forward terminals open from an earlier attempt,
restart the approval-service one using the corrected command in step 2
below** (local port `8082`, not `18082`) — an old terminal still forwarding
to `18082` will reproduce the exact same silent-hang symptom.

## Before you start (one-time local setup)

### 1. Retrieve your demo credentials

```sh
oc get secret golden-path-agent-demo-users -n golden-path-agent-keycloak \
  -o jsonpath='{.data.demo-approver-password}' | base64 -d
oc get secret golden-path-agent-demo-users -n golden-path-agent-keycloak \
  -o jsonpath='{.data.demo-user-password}' | base64 -d
```

Usernames are literally `demo-approver` and `demo-user`.

### 2. Start three port-forwards (keep all three terminals open for the whole walkthrough)

```sh
# Terminal 1 — the agent (serves the UI itself, and /invoke + /resume):
oc port-forward svc/golden-path-agent 18080:8080 -n golden-path-agent-demo-prod
# then open http://localhost:18080/ui

# Terminal 2 — the approval-service (the UI's polling/decision calls).
# The local port here MUST be 8082, not 18082 -- the page's own default
# only looks for the approval service at localhost:8082 (DEC-075):
oc port-forward svc/golden-path-agent-approval 8082:8082 -n golden-path-agent-demo-prod

# Terminal 3 — Keycloak (needed for the login redirect itself):
oc port-forward svc/golden-path-agent-service 8080:8080 -n golden-path-agent-keycloak
```

### 3. Map the Keycloak hostname on your machine (one-time, temporary)

The page fetches its OIDC issuer URL from the agent at load time, and that
URL is the cluster's own internal Service DNS name — your browser can't
resolve it on its own. Terminal 3 above forwards the real Keycloak service
to your machine's port 8080; this step just tells your machine that the
cluster's internal name for it means "my own port 8080":

```sh
echo "127.0.0.1 golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local" | sudo tee -a /etc/hosts
```

This is safe and fully reversible — it only affects how your own machine
resolves that one specific name, and only for as long as the line stays in
`/etc/hosts`. Remove it when you're done (see Cleanup below). This exact
mechanism is documented and verified in `DECISIONS.md` `DEC-074`.

## Part 1 — the approver path (demo-approver)

1. Open <http://localhost:18080/ui>.
2. Click **Log in** — you'll land on a real Keycloak login page. Sign in
   as `demo-approver` with the password from step 1.
3. In the query box, paste this exact text and check **"This is a write
   action"**:
   > Please raise a request to get an extra namespace quota for my team,
   > referencing the quota exhaustion known error.
4. Submit. You'll see "Waiting for approval..." — the page polls the
   approval service every 3 seconds.
5. A pending proposal appears with the drafted request's fields. Review
   them.
6. Click **Approve**.
7. You should see a result containing a ticket number in the form
   `REQ-#####`. That's a real record in the mock ITSM store, created only
   after your approval — nothing was written before you clicked Approve.

## Part 2 — the read-only path (demo-user)

1. Log out, then log back in as `demo-user` (same steps, different
   password from step 1).
2. Notice `demo-user` has no approver role — the UI marks this identity as
   view-only.
3. Submit another write query the same way as Part 1.
4. When the pending proposal appears, confirm there are **no
   Approve/Reject buttons** — instead a message stating you're not an
   approver for this proposal, read-only. This is enforced by the server,
   not just hidden in the page (`approval_service` returns `403` on a
   decision attempt from this identity, per `DEC-069`'s fix) — the UI
   simply reflects that.

## Cleanup

- If you leave a proposal pending from Part 2 (demo-user can't decide it),
  log back in as `demo-approver` and reject it so `demo-prod` doesn't carry
  pending debris into anyone else's session.
- Remove the temporary hosts-file entry:
  ```sh
  sudo sed -i '/golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local/d' /etc/hosts
  ```
- Stop the three `oc port-forward` processes (Ctrl-C in each terminal).

## What this proves

That `SRS-APR-QUAL-01`'s non-developer approver walkthrough works for a
real human, in a real browser, driving the real Authorization Code + PKCE
flow against a live deployment — approve creates a ticket, reject/refusal
creates nothing, and role enforcement holds even when the UI itself is
bypassed (confirmed independently in `reports/phase-d-owner-walkthrough-verification.md`).
Completing this closes Checkpoint D.

## Troubleshooting

- **Login page won't load / connection refused**: confirm all three
  `oc port-forward` terminals are still running and haven't dropped.
- **"state mismatch" or login seems to loop**: usually stale browser
  session state from a previous attempt — clear the page's session storage
  (or use a private/incognito window) and log in again.
- **Port already in use**: another process is holding `18080`, `8082`, or
  `8080` locally — stop it, or forward to a different local port; if you
  change the approval-service port from `8082`, you must also set
  `window.APPROVAL_SERVICE_ORIGIN` before the page loads (see the
  pre-flight section above and the comment in `approver_ui.html`) or
  polling will silently fail forever with no visible error.
- **Hosts-file entry typo**: double-check the line matches exactly
  `127.0.0.1 golden-path-agent-service.golden-path-agent-keycloak.svc.cluster.local`
  — a typo here surfaces as the login redirect failing to resolve at all.
