# Access and credentials

Consolidates the credential story for this demo: who the demo accounts
are, how their secrets are provisioned, how a self-service reset is
meant to work, and how showcase access is granted. See
`docs/security-identity.md` for the approval-gate control flow itself and
`docs/naming-conventions.md` for the realm/client/secret naming patterns
referenced below.

**No real credential value appears anywhere in this document, ever.**
Every value below is retrieved live, at the time you need it, from the
cluster — never written down, never committed, never pasted into a
report.

## The demo-accounts model

One Keycloak realm (`golden-path-agent`) defines two demo users
(`platform/bootstrap/keycloak-realm-import.yaml`, `DEC-058`):

| User | Role | Purpose |
|---|---|---|
| `demo-approver` | `approval-approver` | Can decide (approve/reject) a pending write proposal |
| `demo-user` | none | Deliberately lacks the role — the wrong-role-denied negative test (`DEC-054`) |

Both users are declared without any password in the realm-import manifest
itself — a `KeycloakRealmImport` has no clean way to embed a real
Keycloak-format password hash without either committing a plaintext value
or hand-replicating Keycloak's own hash format, and this project does
neither. Passwords are set (and rotated) entirely post-apply, by the
script below.

## Provisioning and rotation: `platform/bootstrap/provision-identity-
secrets.sh`

This script (Phase D, `DEC-059`) is the demo-scale stand-in for what a
real ESO/Vault integration would do continuously in an enterprise
deployment (see the script's own header comment). Every run:

1. Regenerates the `golden-path-agent-approval-workload` and
   `golden-path-agent-mcp-workload` client secrets via Keycloak's admin
   API, and writes them into the `golden-path-agent-secrets` Secret in
   every consuming namespace.
2. Regenerates fresh, random passwords for `demo-approver` and
   `demo-user` via the admin API's reset-password endpoint, and stores
   them in the `golden-path-agent-demo-users` Secret
   (`golden-path-agent-keycloak` namespace) — retrieved with:
   `oc get secret golden-path-agent-demo-users -n golden-path-agent-keycloak -o jsonpath='{.data.demo-approver-password}' | base64 -d`
3. Ensures the `golden-path-agent-rhdh` OIDC client exists and rotates
   its secret, generating `SESSION_SECRET` once, only at first creation
   (rotating it would invalidate every active RHDH session).

**This script mutates the live cluster.** It is idempotent by design, not
by detection — every run regenerates fresh values for everything it
manages; there is no "only if missing" branch. Running it against an
environment mid-demo will rotate every credential it manages, including
both demo users' passwords and both workload client secrets, whether or
not anyone else was relying on the previous values.

## Per-person provisioned accounts and the self-service reset flow

Two further scripts extend the model above beyond the two static demo
users (added to this repo, and anonymity-checked, by the coordinating
session — see the note below on why they didn't reach this doc's first
draft):

- **[`tools/provision-demo-credentials.sh`](../tools/provision-demo-credentials.sh)**
  — provisions independent, per-person credentials instead of everyone
  sharing `demo-approver`/`demo-user`: N cluster-admin identities in the
  `sso` realm (OpenShift OIDC login, each bound individually to the
  `cluster-admin` ClusterRole), N app-level test-user identities and N
  app-level test-approver identities in the `golden-path-agent` realm
  (mirroring `demo-user`/`demo-approver` respectively). Existing shared
  accounts are left untouched. Writes generated passwords to a local,
  gitignored, mode-600 file (`provisioned-credentials.<timestamp>.txt`)
  — distribute rows individually, then delete the file.
- **[`tools/get-test-user-credential.sh`](../tools/get-test-user-credential.sh)**
  — self-service reset flow for holders of an individual cluster-admin
  login: requires only `oc` access (no separate Keycloak admin secret
  handed out), resets one named app-realm user's password to a fresh
  value, and prints it. Usage: `./tools/get-test-user-credential.sh
  <username>` (e.g. `test-user1`, `test-approver1`, `demo-approver`).

**Both scripts mutate the live cluster.** Neither is safe to run without
warning whoever else might be using the same environment.

**Note on this doc's own drafting**: this documentation stream ran in an
isolated `git worktree`, and these two scripts were untracked (not yet
committed anywhere) at the time it branched — untracked files in one
checkout never propagate to a fresh `git worktree`, only committed
content does. The stream correctly declined to fabricate their content
and flagged the gap explicitly rather than guessing; the coordinating
session then read both scripts from the checkout where they did exist,
ran its own anonymity check, and tracked them as part of landing this
stream's work.

**Consequence of the self-service reset flow's own design**: a reset
flow that rotates a named user's password means two
people racing to reset credentials for *the same* provisioned username
will invalidate each other's just-retrieved password. Coordinate who
holds which provisioned account during a showcase rather than sharing
one username across concurrent viewers.

## Showcase access

Who receives the showcase URL/viewer account, and when, is tracked in
`docs/showcase-access.md` — a deliberately unfilled schedule template,
not duplicated here. That document also carries the anonymity-sweep
procedure required before any sharing moment.

## Summary of hard rules

- Both credential-provisioning scripts named in this document mutate the
  live cluster — never run either against an environment mid-walkthrough
  without warning whoever else might be using it.
- The self-service reset flow rotates the target user's password —
  concurrent resets of the same username invalidate each other.
- No credential value is ever committed to this repository, printed in a
  report, or written into any file under `docs/`. Retrieve values live,
  from the cluster, at the time you need them.
