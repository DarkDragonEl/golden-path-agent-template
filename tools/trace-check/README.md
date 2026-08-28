# tools/trace-check

A small, dependency-light Python 3 CLI that validates the requirements
traceability chain **StRS -> SyRS -> SRS -> (eval cases / tests)** and
exits non-zero on violation. Built as deliverable 2 of the requirements-
traceability work, before any implementation code exists.

Implementation: `trace_check.py` (single file — parsing, the four checks,
report generation, and the CLI entrypoint). Tests: `tests/test_trace_check.py`
at the repository root.

## Why one file

The scope here is genuinely small: four checks over five markdown documents,
one YAML case set, and (once implementation code exists) a handful of Python source
files. Splitting this into a package would trade one obvious place to look
for several, for no real benefit at this size. Internally the file is
organized into four clearly marked sections — Parsing, Checks, Report, CLI
— so it reads like a small package without being one.

## Dependencies

Python 3 stdlib plus `pyyaml` — already available via `requirements-dev.txt`
(which includes `requirements.txt`, where `pyyaml` is actually pinned).
`jsonschema` is also available in that file but is **not** imported here —
every validation this tool performs is regex/structural over markdown and
YAML, not JSON-Schema validation, so pulling it in would be an unused
dependency. No new dependency was added.

## ID conventions this tool parses

These patterns were confirmed against the real documents (`SyRS-AGP-001_EN.md`,
`StRS_Agentic_AI_Platform_EN.md`, all five `srs/SRS-*.md` files) during
this tool's own development, not assumed from memory.

| What | Pattern | Example |
|---|---|---|
| StR definition | `\*\*(StR-[A-Z]+-\d+)\.\*\*` | `- **StR-DX-01.** An agent developer shall...` |
| SysR definition | `\*\*(SysR-[A-Z]+-[A-Z]+-\d+)\s*—` | `- **SysR-P-F-01 — Template instantiation.** The...` |
| SRS definition | `\*\*(SRS-[A-Z]+-[A-Z]+-\d+)\s*—` | `- **SRS-APR-F-01 — Proposal intake.** The service...` |
| Inline Trace line | `\*Trace:\*\s*(.*?)\.\s*\*Verification:\*` (non-greedy, `re.DOTALL`) | `*Trace:* SysR-P-F-08. *Verification:* T ...` |
| Trace-target tokens | `\b(SysR-[A-Z]+-[A-Z]+-\d+\|StR-[A-Z]+-\d+)\b`, applied to the Trace-line capture group | extracts every SysR-*/StR-* token present, regardless of surrounding qualifier text such as `(by extension)` or `(partial — ...)` |
| srs/DEFERRED.md bullet | `^-\s*\*\*(SysR-[A-Z]+-[A-Z]+-\d+)\*\*\s*—\s*(.+)$` (`re.MULTILINE`) | `- **SysR-P-PERF-03** — staging-only rollback objective, not exercised in the demo` |
| Test-file `# verifies:` comment | `#\s*verifies:\s*([A-Za-z0-9,\-\s]+)` | `# verifies: SRS-APR-F-03, SRS-APR-F-05` |

`SRS-<COMP>-<CAT>-NN`'s category token (`F`, `IF`, `PERF`, `SEC`, `DATA`,
`QUAL`) is read as the third `-`-separated field of the id string.

### Why Trace-line extraction is span-based, not a flat document-wide scan

A naive implementation might do "find every bold `SRS-*` definition, find
every `*Trace:* ... *Verification:*` match in the whole document, zip them
together in order." This breaks on `srs/SRS-EVH.md`: its Associated
Documents section *quotes* `srs/SRS-AGT.md`'s own `SRS-AGT-QUAL-01` Trace
line in prose, before `SRS-EVH`'s own first requirement is even defined —
producing 14 Trace-shaped matches for 13 real `SRS-EVH-*` requirements.  A
flat zip silently misattributes every requirement's trace from that point
on.

`parse_srs_requirements()` instead computes, for each bold SRS definition,
the text **span** running from the end of that definition to the start of
the *next* bold SRS definition (or end of file for the last one), and
searches for the first `*Trace:* ... *Verification:*` match **inside that
span only**. A quoted trace line sitting in prose before any of a
document's own requirements are defined falls outside every span and is
correctly ignored.

### `srs/SRS-MIT.md`'s structural difference

`SRS-MIT.md` is interface-only depth: it has no consolidated §7
Traceability table and no §5/§6 at all. This does not affect parsing —
every requirement still carries its own inline `*Trace:* ... *Verification:*`
line, which is all this tool reads. The span-based algorithm handles a
document with no trailing sections identically to one that has them (the
last requirement's span simply runs to end-of-file either way).

### Why section 7 ("Traceability") tables are never parsed

Every SRS document with a §7 states explicitly that its own consolidated
table is informative and that `tools/trace-check` is the authoritative
validator once built. This tool honors that by construction: it only ever
reads the inline `*Trace:*` line that follows each requirement's own
shall-statement in §§1–5 body text, never the §7 summary table. This also
sidesteps a real hazard — a stale §7 table that drifted from its own
document's §§1–5 content would silently produce wrong answers if trusted.

## Eval case IDs

- **Definitions** (`eval/cases/domain/*.yaml`, `eval/cases/EXAMPLE-*.yaml`):
  each domain file is a YAML **list** of case objects; each `EXAMPLE-*.yaml`
  file is a single YAML **mapping**. `parse_eval_case_definitions()` handles
  both shapes uniformly (`isinstance(data, list)` vs `isinstance(data, dict)`).
- **References inside SRS Evidence prose** — bare (`KQA-001`), range
  (`KQA-001..015`, meaning KQA-001 through KQA-015 inclusive), or
  comma-separated lists (`OPS-001, OPS-002, OPS-003, OPS-005`). For a range,
  this tool checks **both endpoint IDs only** — it does not enumerate and
  check every id in between. This matches the manual verification
  convention already used in this session's own Phase B0 checkpoint
  reports, and is sufficient because every domain case file is a small,
  densely-numbered sequential set with no gaps.

### How reference scanning works: two complementary mechanisms

The SRS documents' prose is full of other `PREFIX-NNN`-shaped tokens that
are **not** eval case ids: mock ITSM record ids (`INC-10234`, `REQ-30021`),
corpus document ids (`PLAT-003`, `PROC-001`), decision/finding log ids
(`DEC-001`, `FIND-004`), bare SRS category shorthand (`F-04`, `IF-02`). A
regex that matched any `[A-Z]+-\d+` token *anywhere* in a document would
flag all of these as broken eval-case references — and, in the other
direction, a regex that only ever recognized tokens whose prefix is
*already* a known case-id family would never even notice a wholly
fabricated citation whose prefix matches no real family at all. Each
mechanism below targets one of those two failure modes; both feed the
same `orphan_eval_case` violation list, deduplicated by match position so
a reference caught by both is never reported twice.

**1. Known-prefix scan (`eval_case_prefix_set()` / `build_eval_case_ref_regex()`),
across each document's entire text.** `eval_case_prefix_set()` derives the
set of real case-id prefixes (`KQA`, `ITR`, `TSEL`, `DRQ`, `OOD`, `UAW`,
`INJ`, `OPS`, `EXAMPLE`) **from the actually-loaded case set itself** —
not a hardcoded list in source — and `build_eval_case_ref_regex()` only
matches tokens whose prefix is one of those. `DEC-`, `FIND-`, `PLAT-`,
`PROC-`, `INC-`, `REQ-` never appear as real case-id prefixes, so they are
never matched. This catches "wrong number within a real family" typos
anywhere in a document (e.g. citing `KQA-099` when only `KQA-001..015`
exist), but **cannot** catch a wholly invented prefix — see mechanism 2.
The regex also guards against matching a known prefix as a bare
*substring* of a longer, unrelated, hyphen-joined id: without a
`(?<!-)` lookbehind, `OPS` (a real eval-case prefix — `eval/cases/domain/operational.yaml`
defines `OPS-001..005`) would match the tail of the real SysR id
`SysR-P-OPS-02` on its `OPS-02` segment, reporting a false
`orphan_eval_case` violation against a perfectly valid SysR citation. The
guard is general (any hyphen-preceded position is excluded), not a
one-off exclusion for this single collision.

**2. Path-adjacency scan (`find_eval_case_refs_near_paths()`), scoped to
text immediately following a real `` `eval/cases/...yaml` `` path
mention.** Every real eval-case-id citation in these five documents is
written in exactly this position — immediately after, or inside the
first parenthesized group immediately after, a concrete backtick-quoted
`eval/cases/<file>.yaml` reference (confirmed empirically against the
real corpus before this mechanism was added). That structural fact is
what makes it safe to run this mechanism **unrestricted by known
prefixes** — it matches any `[A-Z]+-\d+(?:\.\.\d+)?`-shaped token in that
tight window, so a hallucinated prefix such as `FAKE-001..999` is caught
even though `FAKE` is not, and never was, a real case-id family. The
tight scoping is what keeps this safe: unrelated ID-shaped tokens
elsewhere in the same long sentence (`F-04` inside `SRS-APR-F-02/F-04`,
`INC-10234`, `PLAT-003`, `DEC-001`) never sit directly after a path
mention, so they are never swept in.

This check is scoped to the five `srs/SRS-*.md` files only, per the
mission's own wording ("appearing in any srs/SRS-*.md file's Evidence
prose"). Mechanism 1 scans each document's **entire** text rather than
isolating "Evidence:"-labeled spans specifically — case ids only ever
appear in evidence-adjacent prose in these documents to begin with, so
whole-document scanning is a safe simplification that avoids inventing a
second, fuzzier "what counts as Evidence prose" boundary. Mechanism 2 is
inherently scoped by its path-adjacency requirement instead.

## The test-file requirement-reference convention (this tool's own choice)

There is no existing precedent in this repository's `tests/*.py` to match
— no implementation code exists yet, so no test file references an SRS id. This
tool adopts a **comment convention**:

```python
# verifies: SRS-APR-F-03
```

or, for one test verifying several requirements:

```python
# verifies: SRS-APR-F-03, SRS-APR-F-05
```

A comment matching `#\s*verifies:\s*([A-Za-z0-9,\-\s]+)` is recognized
against every **real Python comment** in a `.py` file — not only inside a
docstring or immediately above an assertion, but anywhere a genuine `#`
comment appears — and the captured group is split on commas. Only tokens
matching `SRS-[A-Z]+-F-\d+` are kept (check (d)'s own scope is F-category
requirements only, per the deliverable's own scope: "every
SRS-F requirement is referenced by ≥1 test or eval case").

`find_py_files()` scans `.py` files under `tests/`, `agent/`, and
`mcp_server/` — not only `tests/` — even though only `tests/` has content
today, so that once `agent/` or `mcp_server/` gain implementation-level
verification comments, no change to this tool is needed.

**Implementation note: matching is done against real comment tokens,
found with Python's own `tokenize` module — never a whole-file text
sweep.** Two distinct hazards motivate this, both caught during this
tool's own development/review, not left latent:

1. *A regex sweep cannot distinguish a real comment from identical text
   inside a string literal.* This is a genuine self-referential risk for
   this tool specifically: `tests/test_trace_check.py` — which
   `find_py_files()` sweeps like any other file under `tests/` — contains
   the literal text `# verifies: ...` as *sample input* inside
   triple-quoted fixture strings, for unit-testing `parse_verifies_comments()`
   itself. A naive text-level sweep would misread those fixture strings
   as live comments the moment check (d) runs without `--docs-only`,
   silently crediting whatever ids happen to appear in the fixtures as
   "verified" with zero real tests behind them. `tokenize` cannot make
   this mistake: it resolves string-literal boundaries before it ever
   emits a `COMMENT` token, so text inside a string is a `STRING` token,
   never a `COMMENT` token, regardless of content. See
   `tests/test_trace_check.py::test_parse_verifies_comments_ignores_ids_inside_string_literals`
   and `::test_real_tests_own_test_file_contributes_no_spurious_verifies_ids`
   for the regression tests, and note that fixture's own IDs are
   deliberately fake (`SRS-FAKE-F-*`), not real `SRS-APR-*` ids, as a
   second, independent layer of defense against this same hazard.
2. *A naive whole-file-text regex would over-match across physical
   lines.* `VERIFIES_RE`'s captured group, `[A-Za-z0-9,\-\s]+`, includes
   `\s`, which also matches newlines. Applied to a whole file's text at
   once (rather than to one already-isolated comment token), this would
   greedily swallow everything after the comment — blank lines, the next
   statement, even the next function — producing one corrupted
   multi-line "token" that then fails the `SRS-[A-Z]+-F-\d+` fullmatch
   and silently drops every id on that comment line. Since each
   `tokenize.COMMENT` token is, by construction, exactly one physical
   line (Python's `#` syntax has no multi-line form), matching
   `VERIFIES_RE` against each comment token independently sidesteps this
   with no possible ambiguity about which following lines could ever
   legitimately belong to it — the same guarantee a manual
   `text.splitlines()` approach was originally written to provide, now
   obtained for free from `tokenize` along with hazard (1)'s fix.

A `.py` file that fails to tokenize (invalid Python — e.g. a syntax
error) contributes whatever comments tokenized successfully before the
failure and no more; it does not crash the whole trace-check run.

### Why a comment convention, not a test-name suffix

Both were considered. A comment convention was chosen because:

1. **It doesn't constrain how test functions or classes get organized.**
   A test-name-suffix convention (e.g. `test_foo__SRS_APR_F_03`)
   forces every verifying test's *name* to encode the requirement id,
   which fights against writing a test name that actually describes the
   behavior under test.
2. **A comment can sit next to the exact assertion that verifies a
   requirement**, not just at the top of a function — useful when one test
   function exercises several assertions verifying different requirements.
3. **One test can verify multiple requirements** either as one
   comma-separated comment line, or as separate `# verifies:` comment
   lines near each relevant assertion — both are supported, since the
   scanner finds every match in the file, not just the first.

The honest tradeoff: a comment convention is easier to let go stale (a
comment can silently stop matching reality after a refactor, where a
test-name suffix at least fails loudly if a test is renamed without
thought). This tool does not try to solve that; it is a code-review
discipline question, not something a static scanner can fully enforce.

## `known-gap` tag lifecycle check — current `--docs-only` limitation

`srs/SRS-EVH.md`'s `SRS-EVH-F-04` requires that once a `known-gap`-tagged
eval case's named implementation gap closes (e.g. `agent/nodes/reason.py`
gains a model-failure fallback path), the case's continued `known-gap` tag
becomes a **build failure**, not a silent exemption.

This tool does not yet implement that mechanical detection. Doing so
requires a concrete "has the gap closed?" signal — `SRS-EVH-F-04` itself
marks this choice `PROPOSED — pending owner review` (static inspection of
`agent/nodes/reason.py` for a `try`/`except` around the model call, versus
an explicit sentinel such as a manifest flag) — and no such signal exists
yet because the fallback path this check would be detecting the presence
of has not been built. Building the detector before the owner decides
its mechanism would mean guessing at, and likely having to redo, that
mechanism. This is intentionally deferred to when that fallback path
lands and the owner's choice is resolved — consistent with the
same forward-reference posture `srs/SRS-EVH.md` itself uses for this exact
mechanism ("this document states what that mechanism must satisfy; it does
not specify the mechanism's own implementation").

In the meantime, `known-gap`-tagged cases are simply out of this tool's
scope entirely — this tool validates the *requirements* chain, not eval
case pass/fail outcomes (that is `eval/`'s own harness, `SRS-EVH`'s
subject). Nothing here currently reads the `known-gap` tag at all.

## The four checks

- **(a) SysR -> SRS coverage.** Every SysR id defined in
  `SyRS-AGP-001_EN.md` (all 63 — the SyRS's own §2c text establishes that
  the entire document already is the demo-scoped set) must appear as an
  extracted trace-target somewhere across the five `srs/SRS-*.md` files'
  inline Trace lines, **or** be listed in `srs/DEFERRED.md` with a reason.
- **(b) SRS -> SysR trace validity.** Every bold-defined `SRS-*-*-NN`
  requirement must have its own inline Trace line, and that line must cite
  at least one SysR id that is itself real and defined (from check (a)'s
  universe). A Trace line citing only StR ids, citing zero resolvable ids,
  or a requirement with no Trace line at all, is a violation.
- **(c) No broken/orphan IDs.** Every `StR-*`, `SysR-*`, and `SRS-*-*-NN`
  token appearing *anywhere* (not just in Trace lines) across
  `StRS_Agentic_AI_Platform_EN.md`, `SyRS-AGP-001_EN.md`, all five
  `srs/SRS-*.md` files, `srs/FINDINGS.md`, `DECISIONS.md`,
  `srs/REVIEW_INDEX.md`, and `srs/DEFERRED.md` (if present) must resolve to
  a real definition. Also: no `SRS-*-*-NN` id may be bold-defined more than
  once across the five documents combined. Also: every eval-case-id
  reference in the five SRS documents' prose must resolve to a real case
  id (see above).
- **(d) SRS-F -> test/eval coverage.** Every `SRS-*-F-*` requirement must
  be referenced by ≥1 test file (`# verifies:` comment) or ≥1 eval case
  (a `tags` entry of the form `req:<SRS-id>` — extending `eval/README.md`'s
  pre-existing `req:<id>` convention, previously used only with `SysR-*`
  ids, to also accept `SRS-*` ids). **This check's logic is fully
  implemented and unit-tested regardless of `--docs-only`** — see
  `tests/test_trace_check.py`'s dedicated check-(d) test, which runs it
  directly against a synthetic fixture. The CLI simply never invokes it in
  `--docs-only` mode, reporting `status: "SKIPPED"` instead, because Phase
  B has not produced any tests yet and every one of the 26 current SRS-F
  requirements would otherwise report as an (expected, uninteresting)
  violation.

## Running it

Mirrors the `make trace` target:

```bash
python tools/trace-check/trace_check.py --docs-only
```

or, explicitly:

```bash
python tools/trace-check/trace_check.py --docs-only --root /path/to/golden-path-agent-template
```

Flags:

- `--docs-only` — skip check (d), as described above. Always passed today
  (no implementation code exists yet); the flag exists from day one so CI
  wiring never has to change once it does.
- `--root PATH` — repository root to scan. Defaults to the directory two
  levels above `trace_check.py` (computed from `__file__`, never
  hardcoded). Note: `SyRS-AGP-001_EN.md` and `StRS_Agentic_AI_Platform_EN.md`
  live one level *above* this repository root in this workspace layout
  (they are workspace-level frozen source documents, not part of the
  `golden-path-agent-template` git repository) — this tool looks for them
  at both `--root` and `--root`'s parent directory and uses whichever it
  finds, so it works whether or not that parent-directory layout holds in
  some other checkout.
- `--json-out PATH` — where to write the machine-readable report. Defaults
  to `reports/trace-check.json` relative to `--root`.

## Exit code contract

`0` when every **active** check (a, b, c always; d only when *not*
`--docs-only`) has `status: "PASS"`. `1` otherwise. A human-readable
summary — a small table (check name, status, violation count), a numbered
violation list, and a coverage summary line — is always printed to stdout,
regardless of exit code.

## JSON report

Written to `reports/trace-check.json` (or `--json-out`). Shape:

```json
{
  "run_mode": "docs-only" | "full",
  "generated_at": "2026-08-14T12:00:00+00:00",
  "checks": {
    "a": {"status": "PASS", "violations": []},
    "b": {"status": "PASS", "violations": []},
    "c": {"status": "PASS", "violations": []},
    "d": {"status": "SKIPPED", "reason": "...", "violations": []}
  },
  "counts": {
    "sysr_total": 63, "str_total": 29,
    "srs_requirement_total": 73, "srs_f_requirement_total": 26,
    "eval_case_total": 64
  },
  "coverage": {"SysR-P-F-08": ["SRS-APR-F-01", "SRS-APR-F-02", "..."]},
  "deferred": [{"sysr_id": "...", "reason": "..."}]
}
```

`coverage` maps every *traced* SysR id to the list of SRS requirement ids
whose Trace line cites it (SysRs with zero trace citations simply do not
appear as a key — check (a)'s violation list is where those show up).
