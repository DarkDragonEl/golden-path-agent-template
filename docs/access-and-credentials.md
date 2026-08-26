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

Per this documentation stream's own brief, two further scripts are meant
to extend the model above beyond the two static demo users:

- **`tools/provision-demo-credentials.sh`** — intended to provision a
  per-person account (rather than everyone sharing `demo-approver`/
  `demo-user`), so multiple people can hold the approver role
  independently during a walkthrough or showcase session.
- **`tools/get-test-user-credential.sh`** — an intended self-service
  reset flow, so a person who needs a fresh credential for their own
  provisioned account can retrieve one without an operator running the
  full provisioning script above.

**Verification status, stated plainly**: neither script is present in
this worktree. Checked directly, not assumed: the working tree (`tools/`
lists no file by either name), the full git history across every local
and remote branch/ref (`git log --all -- '**/<name>.sh'`, zero hits for
both), and the stash list (empty). This documentation stream's mandate
was to read each script, run an anonymity check, and `git add` them — an
isolated worktree cannot do any of that for a file it cannot see. This is
most likely explained by how `git worktree` checkouts work: an untracked
file sitting in another checkout's working directory (the coordinating
session's own checkout, or wherever Phase H0's audit ran) is never copied
into a new worktree, since only committed content transfers. **Neither
script is tracked by this commit, and neither is linked from this
document** — the two bullets above describe only the intended purpose,
not a verified implementation. The coordinating session should supply
these two files' actual content to whichever stream tracks them next, so
the anonymity check and `git add` this mission calls for can actually
happen.

**Consequence of the self-service reset flow's own design, once it does
land**: a reset flow that rotates a named user's password means two
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
