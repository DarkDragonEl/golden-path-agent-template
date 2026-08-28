# ADR-022: Skeleton Design

## Context
Turning this repository into a reusable template requires a parameterized
skeleton a CLI or Scaffolder action can render into a new project under a
distinct name/owner. The chosen templating approach is Backstage-native
`values`/nunjucks syntax as the single source of truth, rendered by a small,
offline-testable nunjucks-compatible CLI renderer plus RHDH's own stock
`fetch:template` action — no custom RHDH plugin code. The skeleton must also
decide which source-repo content is generic template content versus specific
to this repository's own history or methodology.

## Decision
The skeleton (`skeleton/`) is a hand-curated, committed directory holding
only generic template content, rendered by a `template-schema.json`
parameter schema (required `name`/`owner`; optional `description`/
`repoOwner`/`repoName`, the latter two load-bearing only for the publish
stretch goal) and a three-pass, longest-match-first substitution ordering
(full repo slug, then repo-name-only, then base-name). This repository's own
decision/session history and its requirements-traceability tooling
(`tools/trace-check/`, `tests/test_trace_check.py`, the `Makefile` `trace`
target) were never part of that curated content — a rendered project has no
`srs/` corpus at render time for that tooling to check against, and
traceability tooling is not a required output.

## Consequences
- A rendered project never carries this repository's SyRS→StRS→SRS
  traceability discipline by default; adopting it later is a deliberate,
  separate opt-in, not a restored oversight.
- Substitution correctness depends on the three-pass ordering; any new
  identifier pattern must be checked against it, not assumed to work.
- The renderer stays nunjucks-compatible but minimal, not a heavier engine.
- Skeleton correctness is proven by executing rendered output, not diffing
  against the source — a diff alone has already missed a real defect.

## Supersedes / Superseded-by
None.

## Journal
DEC-088, DEC-090, DEC-087 (item 1 only)
