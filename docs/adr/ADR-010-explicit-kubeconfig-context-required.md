# ADR-010: Explicit kubeconfig Context Required

## Context
A shared kubeconfig file carries one ambient "current context" that any
concurrent process on the same machine — including an unrelated `oc login`
run by a different session — can silently overwrite mid-session,
redirecting subsequent commands at a different cluster with no visible
error at the point of the switch.

## Decision
Every cluster-targeting command must pin either an explicit `--context`
flag or use a dedicated kubeconfig file scoped to that cluster only —
never rely on the ambient shared current-context, and never more so than
for a command that mutates cluster state.

## Consequences
- A caught mistake on a read-only command costs only a re-run; the same
  mistake on a write (namespace, subscription, or manifest creation) risks
  silently mutating a cluster the operator did not intend to touch,
  plausibly one they do not even own resources on.
- When a result looks unexpected, verify identity before trusting it —
  cross-check the current context or API server against the expected host
  before acting further.
- This is a working-discipline rule, not automated tooling: no wrapper
  script enforces it. Adopters apply it by convention at each invocation;
  generalizing it into tooling is worth revisiting only if the same
  mistake class recurs.

## Supersedes / Superseded-by
None.

## Journal
DEC-086
