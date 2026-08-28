# ADR-018: CI pipeline ephemeral architecture

## Context
The CI pipeline's service account is denied any cluster-scoped grant,
ever — but namespace create/delete is cluster-scoped, ruling out a
naive "spin up/tear down a namespace per run" reading of "ephemeral."
The pipeline also needs two different proofs — real reasoning quality
against the live model, and the deployed workload's actual live HTTP
behavior — that one in-process harness can't both give. A rootless
container build under this same restricted account also hits a
well-known hard problem (no `subuid`/`subgid`, no elevated capabilities).

## Decision
"Ephemeral" means ephemeral *resources*, not an ephemeral namespace: the
test namespace is bootstrapped once, manually, and stays standing; each
run only creates/destroys the `Deployment`/`Service`/`ConfigMap` inside
it. The live-model reasoning gate (`eval-gate-live`) stays in-process,
re-running the same offline eval harness against the real model;
`security-tests`/`operational-tests` separately exercise the deployed
pods' actual HTTP surface directly. `container-build` uses the
cluster's own pre-built, platform-maintained `buildah` Task (Tekton's
`cluster` resolver) instead of a custom build step.

## Consequences
- New workload kinds require updating the standing namespace's `Role`,
  not a namespace-level grant.
- Reasoning-quality and live-deployment regressions are caught by
  different stages; a failure in one is not evidence about the other.
- Reusing the platform's `buildah` Task means accepting its own
  security-context requirement (a narrow, named SCC grant) instead of
  hand-maintaining a rootless-build workaround already solved upstream.
- Adopters must not reintroduce per-run namespace create/delete without
  revisiting the RBAC constraint that ruled it out.

## Supersedes / Superseded-by
Supersedes an earlier per-run ephemeral-namespace design and a custom
in-house `container-build` Task.

## Journal
DEC-024, DEC-025, DEC-030
