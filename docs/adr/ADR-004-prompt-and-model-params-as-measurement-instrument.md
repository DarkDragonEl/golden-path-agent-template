# ADR-004: Prompt and Sampling Parameters Are Part of the Measurement Instrument

## Context
Eval results were noisy from pass to pass, and several things had changed
at once between the original baseline and later runs — a prompt-content
regression, retrieval/tokenizer code, and context-window tuning — making
it impossible to say which prior number was trustworthy. An audit found
the model client had never pinned sampling: every call rode the serving
endpoint's own default temperature and seed, an unmeasured and unbounded
source of variance sitting underneath all of it.

## Decision
Sampling is pinned on every model call, primary and fallback alike
(`temperature=0`, `seed=42`, overridable via env/policy bundle like any
other operating parameter). The system prompt, model choice, retrieval
code, and sampling configuration together form the eval measurement
instrument: changing any one of them invalidates in-flight category
comparisons, and results may only be compared across a change after a
fresh, frozen-state, multi-pass re-baseline on the other side of it.

## Consequences
- Pinning sampling collapsed the fraction of failing cases that flip
  pass/fail across repeated runs from roughly 87% to roughly 12.5%,
  turning most residual failures into firm, reproducible findings instead
  of noise.
- A residual flip rate remains, consistent with floating-point
  non-associativity in batched GPU inference; do not mistake it for a
  further prompt or config defect and do not expect pinning to reach zero.
- Any edit to the system prompt, retrieval code, or model/sampling config
  requires a fresh multi-pass, frozen-state re-baseline before its numbers
  are compared against anything measured before the change.
- A single eval pass, or a comparison spanning an un-frozen instrument
  state, is not sufficient evidence for a threshold or adoption decision.

## Supersedes / Superseded-by
None.

## Journal
DEC-012, DEC-015
