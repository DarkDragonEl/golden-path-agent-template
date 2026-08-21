# Session handoff

## Where this is

- **Branch:** `feature/phase-b-golden-path`
- **Last commit:** `d5913f1` — "Phase B4: domain harness wiring,
  DEC-009..DEC-012 investigation, decide-then-retrieve redesign (DEC-013
  candidate)"
- **Working tree:** dirty. Modified: `reports/feature-phase-b-golden-path.md`
  (this session's redesign report appended), `HANDOFF.md` (this file).
  Nothing else — the redesign itself, the B4 harness files, and the
  DEC-009..DEC-012 investigation content are all committed as of `d5913f1`.

## Phase position

**B4 (domain harness live-testing) in progress, blocked on an owner
decision — not blocked on running anything.** `DEC-012`'s frozen-config
re-baseline (evidence for the "something is broken" call) and this
session's decide-then-retrieve redesign (evidence for "here's a fix, how
far did it get") are both done and both committed. What's blocking forward
progress is the owner's read of the redesign's *partial* recovery plus one
new safety-adjacent finding — not a pending measurement. Checkpoint B2
(`make up && make eval` green across all 8 domain categories) is not
reachable until that decision lands and whatever it prescribes is
implemented and re-verified.

## This session's work: decide-then-retrieve reordering (DEC-013 candidate)

Full narrative, root cause, and the complete 3-pass evidence table are in
`reports/feature-phase-b-golden-path.md`'s "DEC-013 candidate" section —
read that before doing anything else that touches `agent/graph.py`,
`agent/nodes/decide.py`/`generate.py`, or either prompt file. Summary:

- **Step 0 forensic check** (`tools/diagnose_tool_call_raw_output.py`,
  `reports/tool-call-raw-diagnostic.json`): ruled out a vLLM/Granite
  serving-config bug (vLLM issue #11402) as the cause — 0/10 matched that
  signature, 8/10 prose narration, 2/10 no tool-call attempt. Corroborates
  `DEC-012`'s prompt-competition diagnosis. No salvage parser built.
- **The redesign**: split the single `reason_node` into `decide_node`
  (tool schemas, no retrieved context, no citation instructions) and
  `generate_node` (retrieved context + citation instructions, no tool
  schemas), with retrieval now conditional on `decide`'s "no tool needed"
  outcome instead of the graph's unconditional entry point. Verified
  against `SRS-AGT-F-03`/`SRS-RET-IF-01` before building — not a violation
  of already-approved SRS text (F-03 constrains output-type cardinality,
  not model-call cardinality, and its evidence never cites `knowledge_qa`,
  the branch the second call lives in).
- **Result (3 live passes, frozen post-redesign state, commit `d5913f1`)**:
  gate still FAILS all 3 passes, but the failure shape changed
  substantially — `operational` fully recovered (3/5 fail → 0/5),
  `itsm_read`/`draft_request`/`tool_selection`/`unauthorized_write`'s
  corroborating check all improved sharply (roughly halved or better) but
  did not clear threshold, `out_of_domain` held clean, `knowledge_qa`
  regressed slightly (2/15 → 3/15), and **`prompt_injection` regressed
  from clean (0/8, throughout the entire `DEC-012` investigation) to a
  reproducible 1/8 fail (`INJ-006`, a jailbreak-style `user_message`
  injection now gets a write action drafted — the no-bypass guarantee
  still held, `write_blocked` was 0 failures across every case in all 3
  passes, but the corroborating "no write drafted from injected content"
  check regressed)**. Full table and per-case detail in the report.
- **No `DEC-013` written.** Per this cycle's explicit boundary: report the
  evidence, do not unilaterally pick a resolution, no further prompt
  iteration, no eval-case edits, no model swaps.

## Open decision, pending owner sign-off

Whether this partial recovery plus the `INJ-006` regression is enough to
lock in the redesign as `DEC-013` and move to a narrower conversation about
what's left: the firm-ceiling cases (`ITR-001`, `ITR-007`, `KQA-002`,
`KQA-010`, `KQA-012`, `INJ-006`, `UAW-002`, `UAW-005`, `DRQ-006` — identical
across all 3 passes) as a documented known-gap for the demo milestone, a
targeted `decide_system_prompt.md` adjustment for the jailbreak-framing
case specifically, or a model swap subject to `DEC-011`'s full-5-category
rule (`granite-4-0-h-tiny` is now confirmed available on the MaaS — logged
as a future candidate, not tested this cycle). **Do not pick one of these
unilaterally** — same discipline `DEC-011`/`DEC-012` already established.

## Invariants that must survive any future session

These are load-bearing design decisions, not implementation details — do
not silently drift from them while doing other work:

1. **DEC-008 arguments-sourcing.** `human_approval_node` is the sole
   invoker of a write-classified tool, and only on `decision == "approve"`
   — it reads the arguments back from persisted graph state
   (`approval_action`), never a cached or re-derived copy. No other code
   path may call a write-classified tool. Unchanged by this session's
   redesign.
2. **DEC-009 route assertion (B4's compensating control) — now list-based.**
   Every domain-eval-run model call must assert `route=primary,
   reason_code=none`, except cases specifically designed to exercise the
   fallback path. Since a turn can now make two model calls (`decide` then
   `generate`, on the no-tool branch), this is enforced via
   `state["model_calls"]` (a list, one entry per call this turn) —
   `eval/domain_scorer.py::check_dec009_route_assertion` reads that list,
   not the single-call scalar `model_route`/`model_route_reason_code`
   fields (which are last-write-wins and would silently hide a routing
   failure on `decide` once `generate` overwrote them). Any new node that
   makes a model call must append to `model_calls`, not just set the
   scalars.
3. **The 5-category rule for model swaps (`DEC-011`).** Any future
   primary-model change must pass the full 5-category acceptance test
   (`knowledge_qa`, `out_of_domain`, `itsm_read`, `draft_request`,
   `tool_selection`) before adoption — not just the categories that
   motivated testing it.
4. **The prompt-is-instrument rule (`DEC-012`).** Both `decide_system_prompt.md`
   and `generate_system_prompt.md` (the old single `system_prompt.md` no
   longer exists) are part of the measurement instrument, on the same
   footing as model choice, retrieval code, `.env` config, and graph
   topology. Any change to either invalidates in-flight category
   comparisons and requires a fresh, frozen-state, multi-pass re-baseline
   before its results are compared against anything measured before the
   change.
5. **New this session: `decide` never sees retrieved context, `generate`
   never sees tool schemas.** This is the literal fix, not an
   implementation detail — reintroducing either (e.g. "helpfully" passing
   `retrieved_docs` into `decide`'s prompt, or adding `tools=` to
   `generate`'s call) resurrects `DEC-012`'s diagnosed failure mode.
   Regression-guarded by `tests/test_decide_node.py::test_context_never_reaches_decide_prompt`
   and `tests/test_generate_node.py::test_called_without_tools_kwarg`.

## Pointers

- `DECISIONS.md` — `DEC-001` through `DEC-012`, full rationale for every
  design/config choice through the pre-redesign investigation, in order.
  No `DEC-013` entry yet — this session's redesign is reported, not yet
  decided.
- `reports/feature-phase-b-golden-path.md` — the running work-log/test-
  report for this branch; the "DEC-013 candidate" section (this session)
  has the full redesign narrative and 3-pass evidence table.
- `reports/tool-call-raw-diagnostic.json` — Step 0's raw forensic capture.
- `~/.claude/plans/read-claude-md-handoff-md-decisions-md-vast-hare.md` —
  this session's approved implementation plan, if useful for context on
  design choices made along the way.
- `~/.claude/plans/encapsulated-wobbling-conway.md` — the accepted phased
  delivery plan (B0 → B → C → D → E) this branch is executing against.
