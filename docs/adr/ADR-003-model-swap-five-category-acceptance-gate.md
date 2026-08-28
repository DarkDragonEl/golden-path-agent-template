# ADR-003: Five-Category Acceptance Gate for Primary-Model Changes

## Context
Under the original primary model, two eval categories (`draft_request`,
`tool_selection`) failed decisively and repeatably against their
thresholds, motivating a config-only primary/fallback swap to a model that
cleared exactly those two categories. Measuring only the categories a
change targets is not sufficient: the swap was later found to regress
three other categories the change was never evaluated against, including
one with a hard, safety-adjacent zero-failure threshold.

## Decision
Any change to the primary model must pass the full five-category
acceptance test — `knowledge_qa`, `out_of_domain`, `itsm_read`,
`draft_request`, `tool_selection` — before being adopted, not only the
categories that motivated the change. A change that clears its motivating
categories but fails any of the other three is rejected and reverted.

## Consequences
- A narrowly-motivated model swap can no longer ship on partial evidence;
  all five categories must be measured and reported for every candidate,
  including losing ones.
- `out_of_domain`'s zero-failure threshold is the refusal boundary keeping
  the agent inside its documented domain — treat any regression there as
  disqualifying on its own, independent of gains elsewhere.
- The full measurement matrix (every model tested, every category,
  cap-on/cap-off where applicable) must be retained, not just the adopted
  configuration's numbers, so the trade-offs stay visible.
- A model that fails to clear all five is not adopted as primary even if
  it is otherwise the best-performing option measured.

## Supersedes / Superseded-by
Supersedes DEC-010's primary/fallback swap (`llama-scout-17b` primary),
which regressed `knowledge_qa`, `out_of_domain`, and `itsm_read` and was
reverted back to the original assignment; this gate is adopted precisely
because that swap shipped without it.

## Journal
DEC-010, DEC-011
