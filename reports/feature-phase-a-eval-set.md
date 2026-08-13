# Phase A: Evaluation Set — Test Report

Branch: `feature/phase-a-eval-set` (based on baseline commit on `main`).

**StR-EVL-03 / SysR-P-LC-04 evidence (repository-history inspection):** the
baseline tree at `72c1c15` contains no domain implementation — see
`TODO_DOMAIN.md` at that commit, which lists every domain surface
(`corpus/`, `agent/retrieval_client.py::retrieve()`,
`agent/prompts/system_prompt.md`, `mcp_server/schemas.py`'s placeholder
tool, `agent/policy.py::classify_action`, `eval/cases/`, deploy config
bindings) as an unfilled `TODO(domain)`. This eval set is authored and
committed on `feature/phase-a-eval-set`, branched from that same
implementation-free baseline, making the "before the complete agent
implementation is built" ordering self-contained in the git history rather
than requiring an external claim.

## Checkpoint 1 — exemplars

Scope: `eval/schema.json`, `eval/corpus-manifest.yaml` (20 docs, complete),
`eval/THRESHOLDS.md`, `eval/README.md`, `eval/validate.py`, 2–3 (up to 4 for
`operational`, to show the `known-gap` pattern) exemplar cases per category
in `eval/cases/domain/*.yaml` (25 cases total). No Phase B implementation
files touched.

### Commands run and results

**1. Git setup**
```
$ git init && git branch -m main
$ git add -A && git commit -m "Baseline: golden-path-agent-template scaffold"
[main (root-commit) 72c1c15] Baseline: golden-path-agent-template scaffold
 80 files changed, 2381 insertions(+)
$ git checkout -b feature/phase-a-eval-set
Switched to a new branch 'feature/phase-a-eval-set'
```
Before staging, confirmed `.env`, `eval/results/*.json`, and
`corpus/seed/*` (except `.gitkeep`) were excluded by the existing
`.gitignore` (`git check-ignore -v` + a synthetic test file), so the
baseline commit carries no local secrets or ephemeral output.

**2. Structural validation (new)**
```
$ python3 eval/validate.py
Case counts: {'knowledge_qa.yaml': 3, 'itsm_read.yaml': 3, 'tool_selection.yaml': 3,
'draft_request.yaml': 3, 'out_of_domain.yaml': 3, 'unauthorized_write.yaml': 3,
'prompt_injection.yaml': 3, 'operational.yaml': 4} total: 25
All cases valid.
```
Exit code 0. Every exemplar validates against `schema.json`'s per-category
`expected` shape, all `id`s are globally unique, file↔category names match,
and `knowledge_qa`'s `source_doc_ids` (`PLAT-002`, `PLAT-003`) resolve
against `corpus-manifest.yaml`.

**3. Existing eval harness — regression check (untouched code)**
```
$ python3 -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002

2/2 cases passed
```
Exit code 0 — unchanged from the pre-Phase-A baseline.

**4. Existing test suite**
```
$ python3 -m pytest -q
..............                                                           [100%]
14 passed in 0.65s
```

**5. Existing lint target**
```
$ make lint
python -m py_compile $(find agent mcp_server eval -name '*.py')
```
Clean (no output = no compile errors), confirms `eval/validate.py` compiles.

### What failed and why (during this checkpoint, not in the final state)

`python -m eval.cli run --all` initially **crashed** (not just
skipped-and-passed) after the first draft of the 8 domain case files was
written directly into `eval/cases/`:
```
TypeError: eval.loader.EvalCase() argument after ** must be a mapping, not list
```
Root cause: `eval/loader.py::load_all_cases` globs `eval/cases/*.yaml`
(non-recursive) and calls `EvalCase(**data)` per file. This schema's case
files are each a top-level YAML **list**, not the old single-case mapping
shape `EvalCase` expects — placing them directly in `eval/cases/` broke
`--all` for `EXAMPLE-001`/`EXAMPLE-002` too, since the crash happens before
any case executes, not per-file.

Fix (file layout only, zero code changes): moved the 8 domain case files
into `eval/cases/domain/`, outside `load_all_cases`'s non-recursive glob.
`eval/loader.py`, `eval/scorer.py`, `eval/runner.py`, `eval/executor.py`,
`eval/cli.py`, `EXAMPLE-001.yaml`, `EXAMPLE-002.yaml`, and
`tests/test_eval_harness_smoke.py` remain byte-for-byte untouched from the
baseline commit. Documented explicitly in `eval/README.md`
("Why `cases/domain/` and not `cases/` directly") since it's a deviation
from the mission's literal flat `eval/cases/<category>.yaml` path — flagged
for owner awareness, not hidden.

### Scope confirmation

```
$ git diff --stat 72c1c15 -- agent mcp_server eval/loader.py eval/scorer.py \
    eval/runner.py eval/executor.py eval/cli.py eval/cases/EXAMPLE-001.yaml \
    eval/cases/EXAMPLE-002.yaml tests/test_eval_harness_smoke.py
(empty — no output)
```
Confirms none of the explicitly-protected files changed since the baseline
commit.

### Outstanding for owner review (see eval/README.md and eval/THRESHOLDS.md)

1. The 25 exemplar cases themselves — do the `expected` shapes and sample
   facts/records match what "correct" should mean per category?
2. The provisional ITSM tool contract (`itsm_search_records`,
   `itsm_create_request`) — 2-operation surface, param names. Flagged as
   input to Phase B0 (SRS-MIT/SRS-AGT), not owned by this phase.
3. Per-category thresholds in `THRESHOLDS.md`, all marked
   `PROPOSED — pending owner review`.
4. The `known-gap` tag + removal-trigger mechanism for `operational`
   model-failure cases (`OPS-004`).
5. The optional `performance_budget` schema field, marked
   `PROPOSED — pending owner review`.
6. The `eval/cases/domain/` file-layout deviation described above.

**No further case volume will be generated, and no commit beyond this
checkpoint will be made, until the owner responds.**

## Checkpoint 1 — review outcome

**Approved with conditions** (2026-08-13). All conditions applied in a
dedicated prep commit before Checkpoint 2 work began, so the git history
shows what changed in response to review separately from new volume:

1. ITSM provisional contract — approved as input to Phase B0, no changes.
2. `known-gap` mechanism — approved; added a tooling-enforcement line to
   `THRESHOLDS.md` (a surviving `known-gap` tag after Phase B closes the
   fallback path is a CI **failure**, not a warning).
3. `performance_budget` — approved as optional/informative; added a line
   to `THRESHOLDS.md` stating it never gates on its own unless explicitly
   promoted to a threshold row.
4. `cases/domain/` layout — approved; recorded in `eval/README.md` as a
   mandatory input to Phase B0/B (authoritative home: **SRS-EVH**) — a
   silent layout change in Phase B is a violation of this approval, not a
   routine refactor.
5. Thresholds — approved in structure, re-expressed as **maximum absolute
   failures allowed** (not percentages, given n=5–15 per category), with
   the original proposed percentage kept in parentheses as informative
   context only. See the rewritten table in `THRESHOLDS.md`.
6. Exemplar cases — approved as authored, no corrections.
7. This LC-04 evidence paragraph (top of this report) — added per review.
8. Report-naming convention (`reports/<branch-name>.md`) — confirmed;
   noted in `eval/README.md` for Phase B0's trace-check to rely on.

## Checkpoint 2 — full volume

Scope: extended all 8 `eval/cases/domain/*.yaml` files from the
Checkpoint-1 exemplars to the mission's full target counts, as variants of
the approved exemplar patterns. No schema, manifest, or threshold
*structure* changes beyond what Checkpoint 1's review already approved.

### Final case counts

```
$ python3 eval/validate.py
Case counts: {'knowledge_qa.yaml': 15, 'itsm_read.yaml': 8, 'tool_selection.yaml': 8,
'draft_request.yaml': 6, 'out_of_domain.yaml': 6, 'unauthorized_write.yaml': 6,
'prompt_injection.yaml': 8, 'operational.yaml': 5} total: 62
All cases valid.
```
Exit code 0 on first run against the full 62-case set — every case
validates against `schema.json`'s per-category `expected` shape, all `id`s
are globally unique, file↔category names match, and every `knowledge_qa`
`source_doc_ids` reference resolves against `corpus-manifest.yaml`
(covers 14 of the 20 manifest documents across the 15 knowledge_qa cases,
including 3 multi-document citations).

One new fixture record id, `INC-10261`, was introduced during volume
generation (for an `itsm_read` status+free-text search case) and added to
`eval/README.md`'s fixture list — the other 7 fixture ids from Checkpoint
1 needed no changes.

### Regression checks (same commands as Checkpoint 1, re-run against full volume)

```
$ python3 -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002

2/2 cases passed

$ python3 -m pytest -q
..............                                                           [100%]
14 passed in 0.64s

$ make lint
python -m py_compile $(find agent mcp_server eval -name '*.py')
(clean)

$ git diff --stat 72c1c15 -- agent mcp_server eval/loader.py eval/scorer.py \
    eval/runner.py eval/executor.py eval/cli.py eval/cases/EXAMPLE-001.yaml \
    eval/cases/EXAMPLE-002.yaml tests/test_eval_harness_smoke.py
(empty — no output)
```
All green; the explicitly-protected files remain byte-for-byte unchanged
from the baseline commit through both checkpoints.

### `operational` gate composition (per the re-expressed threshold)

5 cases total: `OPS-001` (tool_timeout), `OPS-002` (tool_error /
connection_refused), `OPS-003` (step_limit_exceeded), `OPS-005` (tool_error
/ retries_exhausted, anchored to `tool_retry_limit: 2`) count toward the
gate (n=4, max 0 fail). `OPS-004` (model_failure) is tagged `known-gap` and
excluded, per the Checkpoint-1-approved removal-trigger mechanism.

### What's next

Phase A is complete per its definition of done: schema validates all
cases, case↔corpus references resolve, owner has reviewed exemplars *and*
(pending this submission) the final set, and nothing in Phase B (`agent/`,
`mcp_server/`, `eval/loader.py`, `eval/scorer.py`, etc.) has been touched.
**Stopping here per CLAUDE.md's Phase A checkpoint — no Phase B0 or Phase B
work begins without a separate, explicit go-ahead.**
