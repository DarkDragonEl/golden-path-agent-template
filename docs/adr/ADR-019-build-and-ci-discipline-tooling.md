# ADR-019: Build and CI discipline tooling

## Context
Several project rules exist only as hand-authored artifacts with no
check that they stay true: the runtime policy engine's rules and its
OPA-rego mirror can drift apart silently; a config key added to one
deployment surface can be forgotten on another, or left as an
unresolved placeholder in a manifest consumed as-committed; and a
CI-only need (HTTP calls into a deployed pod) can tempt adding a client
tool to the application image, which the immutable-artifact rule exists
to prevent.

## Decision
Three CI-time discipline checks, none a second runtime enforcement
point: (1) a policy-sync check parsing the OPA rego's actual data (via
`opa eval`, not a hand-copied re-assertion) and diffing it against the
runtime policy source of truth, failing on drift; (2) a config-contract
checker that AST-parses the code for every no-default environment
variable, verifies each is declared on every deployment surface
consuming it as-committed (or tolerated with a stated reason), and
scans those manifests for unresolved placeholder-shaped values; (3) CI
scripts needing a deployed pod's HTTP surface use stdlib
`urllib.request` via `oc exec`, not a CLI client in the image.

## Consequences
- The rego mirror stays a validation gate only; `agent/policy.py`
  remains the sole runtime policy decision point. Both checkers are
  proven to catch real regressions (a renamed tool, a removed key, a
  reintroduced placeholder), not just to run clean.
- A new no-default config key or policy tool name must be reflected on
  every consuming surface or named in the tolerance list with a reason.
- The application image's dependency surface stays exactly what the
  runtime needs; adopters must not add a CLI HTTP client to it for a
  CI-only convenience.

## Supersedes / Superseded-by
None.

## Journal
DEC-023, DEC-034, DEC-044
