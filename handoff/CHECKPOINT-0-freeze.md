# Checkpoint 0 — freeze the entry

No STOP here per the mission plan; continuing straight into Phase 1. This
report exists so the starting state is on record before any content edits
begin.

## 0.1 — widened `tools/journal_census.py`

- `DEC` is now case-insensitive with an optional hyphen, so it also
  catches a decision number hiding inside a Python identifier
  (`check_dec009_route_assertion`, `tests/test_dec009_route_assertion.py`,
  `test_dec046_*`). The literal `\bdec-?\d{3}\b` regex given in the
  mission spec does **not** actually catch those — `\b` treats `_` as a
  word character, so there is no boundary between `_` and `d` in
  `check_dec009_...`, and the match silently fails. Implemented instead as
  `(?<![a-zA-Z])dec-?\d{3}(?!\d)`: not preceded by a letter (still blocks
  a false positive like `codec_005`, which has a letter — `o` — right
  before its `dec`), not followed by a digit (so a longer run like
  `dec0091` isn't partially matched). Verified against both the intended
  catches and the near-miss false positive before wiring it in.
- Added `DECISIONS_MD` (`DECISIONS\.md`) and `ROADMAP` (`agent-roadmap`)
  patterns.
- File **names**, not just contents, are now scanned for `DEC` (a hit on
  the name itself is reported at line `0`).
- The old blanket `("docs/adr/", "DEC")` prefix allowlist is gone,
  replaced by a line-precise rule: only the line directly under each
  ADR's own `## Journal` heading is exempt. A `DEC-NNN` anywhere else in
  the same ADR's body is now a real finding (confirmed: this surfaced
  `docs/adr/ADR-003-model-swap-five-category-acceptance-gate.md:33` and
  `docs/adr/index.md:41,44`, which the old blanket rule was silently
  hiding).
- `README.md`'s closing "Decision history:" paragraph and
  `docs/adr/index.md`'s opening paragraph are each the one exempt line/
  block for `DECISIONS_MD`/`ROADMAP` — every other mention in either file
  (there are several) is now a real finding, on purpose.

## 0.2 / 0.3 — diff mode + gate wiring

- `--diff BASE_REF`: regression-only, compares unallowed-occurrence counts
  per `(path, pattern)` against `BASE_REF`, not raw line numbers — so
  unrelated line drift elsewhere in a file never reads as a false
  regression.
- Verified live: `--diff main` with no content changes → 0 regressions,
  exit 0. Appending a synthetic `DEC-999: synthetic regression test line`
  to `docs/local-dev.md` → 1 regression reported
  (`docs/local-dev.md DEC 6 -> 7 (+1)`), exit 1. Reverted; back to exit 0.
- `make lint-journal` (`JOURNAL_BASE ?= origin/main`) — verified runs and
  exits 0 against `origin/main`.
- `pipelines/tasks/journal-census.yaml` (new Task, wired into all three
  `pipeline-*.yaml`, ahead of `container-build`): fetches the base
  revision, prints the full census as informational (`|| true`), then
  runs `--diff` as the real, blocking gate. `ci/pr-checks.yaml` (the
  non-executing reference shape) got the matching stage for parity.
- Caught immediately by its own gate: my first draft of
  `journal-census.yaml`'s and `ci/pr-checks.yaml`'s explanatory comments
  named the sibling history repo directly, which is exactly what the new
  `ROADMAP`/`DECISIONS_MD` patterns exist to catch. Reworded before
  commit — `--diff main` is clean.

## 0.4 — skeleton lint

- Extended `tools/verify_skeleton.py` (not a new file — it already
  renders both templates via the one shared `render_skeleton()` call site
  `tools/instantiate_agent_project.py`'s own CLI also uses, so reusing it
  avoids a second, divergent rendering path) with a third sweep: the same
  `journal_census.py` allowlist/line-exempt logic, run against the
  rendered output via a new `discover_files_walk()` +
  `build_report_for_files()` (the existing git-aware `discover_files()`
  doesn't apply — a fresh render has no `.git` of its own).
- Verified live: **272** journal-vocabulary findings in the rendered
  Agent Template, more in the Tools Template — expected, this is the
  pre-I5/I6/I7 backlog reaching the rendered output too, not a bug.
  `tests/test_dec009_route_assertion.py` from the earlier lowercase-
  identifier fix showed up correctly inside the rendered tree.
- New `pipelines/tasks/verify-skeleton.yaml`, wired into
  `pipeline-agent.yaml` only (skeleton/skeleton-tools are the template-
  instantiation feature, out of scope for the mcp/approval pipelines —
  same reasoning `pipeline-mcp.yaml`'s own comment already gives for
  excluding `policy-validate`/`eval-gate-*`). Deliberately **non-blocking**
  for now (`|| true`): the other two sweeps in that file already pass
  clean, but the new journal sweep inherits the same backlog as
  `journal-census.yaml` and would fail every PR on debt it didn't cause.
  Expected to flip to blocking once Phase 6 drives the census to zero.

## Numbers (working tree, current branch, before any content edits)

| Pattern | Occurrences |
|---|---|
| DEC | 1,639 |
| PHASE | 375 |
| DECISIONS_MD | 287 |
| CHECKPOINT | 54 |
| STAGE | 52 |
| WORKTREE | 10 |
| MISSION | 9 |
| ROADMAP | 8 |
| HANDOFF | 7 |
| COORD_SESSION | 1 |
| OI (keep-list, never a finding) | 63 |

**763 unallowed `(path, pattern)` findings across 343 files** — this is
the real, current backlog `journal_census.py` (no `--diff`) reports; it is
expected to be red until Phase 5/6, and `--diff main` (the actual commit
gate) is clean.

`make test` — 254 passed, matching `README.md`'s own documented figure;
no runtime path was touched this phase.

## Next

Phase 1: build the per-DEC triage inventory and write
`handoff/CHECKPOINT-1-triage.md`. **STOP** there for owner adjudication —
no ADR is drafted and no citation is edited until that table comes back.
