# Evaluation Set (Delivery Step 1)

This is the version-controlled evaluation set for the pilot agent (the
**Platform Knowledge and Request Agent**, ITSM scenario per Annex A OI-02),
covering the nine dimensions StR-EVL-01 / SysR-A-EVL-01 require: answer
correctness, retrieval relevance, citation quality, tool selection,
tool-argument correctness, refusal and escalation behavior, resistance to
prompt injection, policy compliance, and latency/token consumption.

It exists **before** the complete agent implementation, per StR-EVL-03 /
SysR-P-LC-04 — verified by repository-history inspection: this content is
committed on `feature/phase-a-eval-set`, ahead of any ITSM tool, corpus, or
domain-prompt implementation. Ground-truth validation (StR-EVL-04 /
SysR-P-INFO-02) happens as the two review checkpoints below, each a
separate, dated commit — see the Review Log.

## This is not the existing eval harness

`eval/loader.py`, `eval/scorer.py`, `eval/runner.py`, `eval/executor.py`,
`eval/cli.py`, `eval/cases/EXAMPLE-001.yaml`, `eval/cases/EXAMPLE-002.yaml`,
and `tests/test_eval_harness_smoke.py` are a **separate, pre-existing
fixture** proving the LangGraph plumbing runs end-to-end (invoke/resume,
the human-approval interrupt, mock MCP mode) with zero domain content. They
are unaffected by this work and still pass (`python -m eval.cli run
--all` → 2/2). The files documented here (`schema.json`, `cases/domain/*.yaml`,
`corpus-manifest.yaml`, `THRESHOLDS.md`, `validate.py`) are the actual
domain evaluation set and are not yet wired into that harness — see
"The harness needs extending to run these cases" below.

## Directory structure

```
eval/
├── schema.json                # JSON Schema every case in cases/domain/ validates against
├── corpus-manifest.yaml       # identity of ~20 synthetic corpus documents
├── THRESHOLDS.md               # proposed per-category promotion-gate thresholds
├── validate.py                 # standalone structural validator (see below)
└── cases/
    ├── EXAMPLE-001.yaml        # pre-existing harness-mechanics fixture, untouched
    ├── EXAMPLE-002.yaml        # pre-existing harness-mechanics fixture, untouched
    └── domain/                 # this eval set
        ├── knowledge_qa.yaml
        ├── itsm_read.yaml
        ├── tool_selection.yaml
        ├── draft_request.yaml
        ├── out_of_domain.yaml
        ├── unauthorized_write.yaml
        ├── prompt_injection.yaml
        └── operational.yaml
```

**Why `cases/domain/` and not `cases/` directly:** `eval/loader.py::
load_all_cases` globs `eval/cases/*.yaml` (non-recursive) and calls
`EvalCase(**data)` on every match. This schema's files are each a YAML
**list** of cases, which crashes that call if placed directly in
`eval/cases/` — it would break `python -m eval.cli run --all` for
`EXAMPLE-001`/`EXAMPLE-002` too, not just silently skip the new files,
since the glob's crash is per-`--all`-invocation, not per-file. Nesting
under `domain/` keeps that command passing 2/2 with zero changes to
`loader.py`, since the glob never descends into subdirectories. This is a
file-layout choice, not a schema change — noted here for visibility since
it's a deviation from a literal flat `eval/cases/<category>.yaml` layout.

**This is a mandatory input to the next implementation work, not a
detail that work is free to silently redo.** The
authoritative home for the extended evaluation harness is **SRS-EVH**, to
be drafted alongside SRS-MIT/SRS-AGT. SRS-EVH must explicitly specify that
the harness reads cases from `eval/cases/domain/` — or, if that work
decides to unify the layout with `EXAMPLE-*.yaml` some other way, that
unification must be a deliberate, documented SRS-EVH decision. A later
change that quietly moves or reshapes `cases/domain/` without updating
SRS-EVH is a violation of this checkpoint's approval, not a routine
refactor.

## Case format

Each `eval/cases/domain/<category>.yaml` file is a top-level **YAML
list** of cases belonging to that category — a different convention from
`EXAMPLE-*.yaml`'s one-file-one-case shape, since these are separate
systems with separate schemas.

Every case object has the required top-level fields defined in
`schema.json`:

| Field | Meaning |
|---|---|
| `id` | Globally unique. Category-prefixed: `KQA-*`, `ITR-*`, `TSEL-*`, `DRQ-*`, `OOD-*`, `UAW-*`, `INJ-*`, `OPS-*`. |
| `category` | One of the 8 categories below; must match the file it lives in. |
| `input` | What's presented to the agent — always at least `query`; some categories require extra fields (an injection payload, a fault type, an approval scenario). |
| `expected` | Structured, mechanically checkable ground truth — never prose. Shape is category-specific; see `schema.json`. |
| `threshold_notes` | One-line note on how this case counts toward its category's gate (see `THRESHOLDS.md`) — e.g. `known-gap: excluded pending model-failure fallback implementation`. |
| `tags` | Free-form labels — see Tag conventions below. |
| `version` | Content version of this case, e.g. `"0.1.0"`. Bumped on material change; git history is the authoritative record. |

One optional field, `performance_budget` (`max_latency_ms`, `max_tokens`),
is **`PROPOSED — pending owner review`** — see `THRESHOLDS.md`.

### The 8 categories

| Category | File | Target volume | `expected` captures |
|---|---|---|---|
| Knowledge QA | `knowledge_qa.yaml` | 15 | must-contain facts, source doc IDs, groundedness |
| Read-only retrieval | `itsm_read.yaml` | 8 | correct tool selected, correct query params, no write attempted |
| Tool selection | `tool_selection.yaml` | 8 | which tool (or none) for ambiguous asks |
| Draft request | `draft_request.yaml` | 6 | draft produced, required fields present, approval explicitly requested |
| Out-of-domain | `out_of_domain.yaml` | 6 | polite refusal, no tool call, no hallucinated answer |
| Unauthorized write | `unauthorized_write.yaml` | 6 | write is BLOCKED, approval path invoked, denial logged |
| Prompt injection | `prompt_injection.yaml` | 8 | injected instruction ignored, no tool misuse, no data exfil |
| Operational | `operational.yaml` | 5 | behavior on tool timeout, model failure, fallback route with reason code |

Full nine-dimension-to-category mapping and gate thresholds are in
`THRESHOLDS.md`, not duplicated here.

## The ITSM tool contract these cases assume — PROVISIONAL

No ITSM tool exists in this codebase yet (`mcp_server/` today ships a
single generic `placeholder_lookup(query, write: bool)`; `TODO_DOMAIN.md`
explicitly defers the real tool's fields to whoever picks the domain
tools). The categories above need concrete tool/operation names to write
mechanically checkable `expected` blocks against, so this eval set
provisionally names them:

- **`itsm_search_records`** (read-only, always).
  Input: `record_type` (`incident|request|known_error`, required), `query`
  (optional free-text), `record_id` (optional — returns one record instead
  of a list), `status` (optional filter), `limit` (default 10).
  Output: `records[]` (`record_id, record_type, status,
  short_description, opened_at, updated_at, owner_team`), `count`,
  `source: "mock-itsm"`.
- **`itsm_create_request`** (write, always approval-gated).
  Input: `short_description`, `description`, `category`
  (`access|provisioning|break_fix|information`), `requested_for`,
  `related_record_id` (optional).
  Output (post-approval only): `record_id` (e.g. `REQ-30099`),
  `status: "submitted"`, `source: "mock-itsm"`.

Read vs. write is signaled by **which operation is called**, not by a
`write` argument flag — an improvement over today's `placeholder_lookup`
pattern.

**This contract is provisional, not authoritative.** Its authoritative
home is **SRS-MIT** (the MCP tool interface requirement) and **SRS-AGT**
(the `agent/policy.py::classify_action` requirement — which will need to
move from `arguments.get("write")` to a tool-name check), both to be
drafted as part of contract definition (per CLAUDE.md's contract-review
checkpoint). That work may revise this contract freely. Eval
cases in this set reference the operation **names**
(`itsm_search_records`, `itsm_create_request`) only — never an
implementation, and this README is not the place two sources of truth for
the same contract should live once SRS-MIT/SRS-AGT actually exist.

**Mock fixture record IDs** these cases reference (seed data the
persistent mock-ITSM state should provide): `INC-10234`, `INC-10240`,
`INC-10255`, `INC-10261`, `REQ-30021`, `REQ-30052`, `KE-50007`, `KE-50012`.
`INC-10261` was added for `itsm_read`
coverage of a status+free-text search — same provisional-contract caveat
as the rest of this list.

## Corpus references

`knowledge_qa` cases cite `expected.source_doc_ids`, which must resolve
against `doc_id` entries in `corpus-manifest.yaml` — `validate.py` checks
this. The manifest fixes 20 synthetic document identities (title, owner
role, classification, version, effective date, access policy, source,
refresh process); the documents' actual content comes from
`corpus/ingest.py` + `corpus/seed/`, per `corpus/README.md`, not from this
eval set.

## How to run today

Nothing here executes against the agent yet — these are static,
version-controlled artifacts, not yet wired into a runnable harness.

```sh
python eval/validate.py        # or: make validate-eval-set
```

`validate.py` is a **structural** check only: every case in `cases/domain/`
validates against `schema.json`, case `id`s are globally unique, each
file's cases have `category` matching the filename, and `knowledge_qa`'s
`source_doc_ids` resolve against `corpus-manifest.yaml`. It does not run
the agent and asserts nothing about agent behavior.

Contrast with `python -m eval.cli run --all`, the existing harness command
— it still only knows about `EXAMPLE-001`/`EXAMPLE-002` (see "This is not
the existing eval harness" above); it does not read anything in this
document yet.

## The harness needs extending to run these cases

Today's `eval/loader.py::EvalCase` model is `{id, description, mode,
input, assertions, steps}` — no `category`, `expected`, `tags`, `version`,
or `threshold_notes`. To actually execute the cases in `cases/domain/*.yaml`
against the agent, this harness needs to either extend `EvalCase` (or add a
parallel loader) to parse this schema, and extend `eval/scorer.py` with
category-aware scoring logic that consumes each category's structured
`expected` shape — the shapes were designed to be deterministically
checkable (substring/tool-name/policy-state assertions), so no
`semantic_judge` rubric work is required to start. This is explicitly out
of scope for this evaluation-set deliverable; nothing in `eval/loader.py`
or its consumers has been modified.

## Known, deliberate gap: `operational` / model failure

`agent/nodes/reason.py`'s model call is currently unguarded — there's no
model-failure fallback path in the graph yet, only tool-error/step-limit/
approval-rejection routes. The `operational` category's model-failure
cases are authored anyway, per SysR-A-F-05/SysR-P-F-12 (the eval set
specifies behavior ahead of implementation — that's StR-EVL-03's whole
point), tagged `known-gap`, and excluded from the promotion gate.

**Removal trigger** (full text in `THRESHOLDS.md`): the `known-gap` tag
comes off, and the cases enter the gate, the moment that fallback path is
implemented. A `known-gap` tag still present after that lands is a CI
failure, not a standing exemption.

## Tag conventions

- The category name (e.g. `knowledge_qa`) — always present.
- `read-only` | `write` — which side of the approval boundary a case
  exercises.
- `security` — for `unauthorized_write` and `prompt_injection` cases.
- `known-gap` — case is specified ahead of an implementation gap (see
  above); excluded from its category's gate until the gap closes.
- `fail-closed` — case asserts a deny-by-default / no-partial-credit
  outcome.
- `req:<id>` — optional requirement-trace tag, e.g. `req:SysR-A-F-06`, for
  greppable traceability back to the SyRS.

## Report naming convention

Test reports for this work live at `reports/<branch-name>.md` — here,
`reports/feature-phase-a-eval-set.md` — not the literal
`reports/<branch>.md` shorthand in the mission text (that shorthand is
superseded by this concrete convention). **Confirmed**: the
trace-check tooling consumes reports by this convention, so later
work should keep naming its reports `reports/<branch-name>.md` rather
than inventing a different scheme per branch.

## Review Log

Human-readable pointer to the git-history sign-off evidence StR-EVL-04 /
SysR-P-INFO-02 require. Each row corresponds to a commit on
`feature/phase-a-eval-set`.

| Date | Reviewer | Checkpoint | Outcome |
|---|---|---|---|
| 2026-08-13 | Owner | 1 — exemplars (25 cases across 8 categories, schema, manifest, thresholds draft) | **Approved with conditions**: ITSM contract approved as trace-check input; known-gap mechanism approved + tooling-enforcement line added; performance_budget approved as informative-only; cases/domain/ layout approved as mandatory SRS-EVH input; thresholds re-expressed as max absolute failures; exemplars approved as authored; report-naming convention confirmed. See `reports/feature-phase-a-eval-set.md`. |
| 2026-08-13 | Owner | 2 — full set (62 cases across 8 categories, approved-pattern variants) | _submitted; pending owner review_. Conditions from review round 1 applied in a dedicated prep commit first. See `reports/feature-phase-a-eval-set.md`. |
