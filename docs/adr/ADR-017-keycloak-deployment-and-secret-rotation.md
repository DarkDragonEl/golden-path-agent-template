# ADR-017: Keycloak deployment and secret rotation

## Context
The platform needs a real identity provider for OIDC login and
role-based approval gating, on a shared cluster where the vendor
operator's OLM catalog was blocked, and where client secrets and
demo-user passwords must be provisioned/rotated without hand-editing
values into git.

## Decision
Keycloak installs via its own upstream, OLM-free kustomize path
(namespace-scoped, pinned to a released tag), backed by a plain
`Deployment`+`PVC` Postgres using the cluster's built-in PostgreSQL
`ImageStream`, not a database operator or external image. Auth wiring
reuses one existing realm; each workload registers as its own OIDC
client in it — never a second realm. All client secrets and demo-user
passwords are provisioned/rotated by one idempotent script calling
Keycloak's own admin-API "regenerate secret"/"reset password"
endpoints — one code path for both a fresh environment and a rotation.

## Consequences
- No dependency on a shared operator catalog for identity
  infrastructure; the vendor-distributed operator is a drop-in swap
  later, since both distributions own the same CRD group.
- Postgres reuses the cluster's own registry-credential-free image,
  avoiding a second fight with arbitrary-UID container constraints.
- Rotation is safe to re-run: it regenerates fresh values every run and
  merge-patches only its own keys into each consuming Secret, leaving
  unrelated keys untouched.
- Secret values are never committed or echoed by the script, only
  printed via an explicit, documented human-run retrieval command.
  Adopters must not create a second realm per workload.
- This script is the demo-scale stand-in for a real external-secrets/
  Vault integration, not that integration itself.

## Supersedes / Superseded-by
None.

## Journal
DEC-054, DEC-056, DEC-059, DEC-087 (item 2 only)
