# ADR-008: Identity Config Contract Enforcement

## Context
Enabling OIDC-based auth for the approval service and MCP tool calls
introduced config keys with no safe default (issuer URL, audience,
auth-mode flags). Promoting these into shared base manifests risks a real
hazard: a live-synced environment running with auth silently disabled,
even briefly, or a required key left undeclared until a request needs it.

## Decision
A mechanical config-contract checker computes each config-bearing
service's effective merged config (base default plus overlay override,
the merge semantics Kustomize itself uses) and asserts security-relevant
switches resolve to their secure value wherever auth must be enforced;
every no-default key must be declared for every service that defines one.
Auth-enabling manifests are promoted into the shared base in the same
atomic commit as flipping the enforcement mode and adding the
corresponding contract check, so a live-synced environment is never
exposed to auth-disabled config for even one sync cycle.

## Consequences
- The checker must fail closed on a seeded regression — proven, not
  assumed, by reverting an auth switch to its insecure value and
  confirming the checker catches it before trusting it as a gate.
- The completeness scan must be extended per config-bearing module; each
  service with its own config surface needs its own completeness check.
- A `ConfigMap` changing in Git and syncing via GitOps does not, by
  itself, restart already-running pods — a `Deployment` only watches its
  own pod-template, not referenced-object content — so a manual rollout
  restart is required after any config-only change until a content-hash
  pod-template annotation is added (not implemented at this scope).
- Adopters must not assume a merged config change takes effect without an
  explicit rollout, or promote an auth-mode flip apart from its manifests.

## Supersedes / Superseded-by
None.

## Journal
DEC-046, DEC-053, DEC-063, DEC-065
