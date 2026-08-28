# ADR-007: Eval Gate Exception Allowlist Convention

## Context
An eval gate over a model-calling agent will encounter two distinct kinds
of persistent failure: a confirmed limit of model behavior under
adversarial framing that no amount of prompt iteration reliably fixes, and
residual non-determinism on a shared inference endpoint that survives even
pinned sampling. A gate needs a way to stop re-litigating either without
quietly lowering the bar on the safety property that actually matters.

## Decision
Deterministic sampling (`temperature=0`, `seed=42`) is the gate's own fixed
measurement contract, force-set by the eval harness before any agent
config is loaded — not caller-overridable, unlike other mode flags. A
named, dated, per-case table lists which *specific* assertion(s) are
excludable for a given case; a failing case is excluded from the gate's
failure count only when every failing assertion on that run is one of the
named excludable ones. Any other assertion failing the same run (e.g. a
write-blocking guarantee) defeats the exclusion and the case counts as a
real failure.

## Consequences
- The mechanism structurally cannot mask a safety-property regression —
  only a documented, corroborating-check limitation — enforced by a test
  asserting a safety-assertion co-failure defeats the tolerance.
- Two classifications share one mechanism: "known-gap" (a confirmed
  model-behavior limit) and "measurement-tolerance" (residual
  non-determinism that did not reproduce on repeated deterministic runs)
  are reasoned about differently even though excluded the same way.
- Every exclusion is surfaced in the eval report artifact and recorded in
  the case file's own tags, so a tolerated failure is never silently
  invisible in a passing run.
- Adopters must not add a case without a name, date, and stated rationale,
  and must never list a safety-property assertion as excludable.

## Supersedes / Superseded-by
None.

## Journal
DEC-016, DEC-017
