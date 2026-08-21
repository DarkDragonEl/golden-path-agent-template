# Session handoff

## Where this is

- **Branch:** `feature/phase-b-golden-path`
- **Last commit:** `2f430fc` — "fix: restore citation-format instructions
  lost in the tokenizer-bug bisection"
- **Working tree:** dirty. Modified: `.env.example`, `DECISIONS.md`,
  `Makefile`, `agent/config.py`, `agent/nodes/reason.py`,
  `agent/retrieval_client.py`, `eval/cli.py`, `eval/reporter.py`,
  `reports/feature-phase-b-golden-path.md`,
  `reports/phase-b-tool-calling-spike-raw.json`. Untracked (new B4
  harness files, functional, not yet committed): `eval/domain_executor.py`,
  `eval/domain_loader.py`, `eval/domain_scorer.py`, `eval/thresholds.yaml`.
  `agent/prompts/system_prompt.md` is clean — its restoration is already
  committed (`2f430fc`).

## Phase position

**B4 (domain harness live-testing) in progress, blocked on an owner
decision — not blocked on running anything.** The frozen-config,
multi-pass re-baseline this block was waiting on is already done
(`DECISIONS.md` `DEC-012`); what's blocking forward progress is the
owner's call on how to respond to what it found, not a pending
measurement. Checkpoint B2 (`make up && make eval` green across all 8
domain categories, broken-primary fallback demo, updated report) is not
reachable until that decision lands and whatever it prescribes is
implemented and re-verified.

## The frozen-config definition (`DEC-012`'s re-baseline)

This is the exact, reproducible configuration the current open decision
is about — reproduce it exactly before trusting any comparison against
it:

- `.env`: `MODEL_NAME=granite-3-2-8b-instruct` (primary),
  `MODEL_FALLBACK_NAME=llama-scout-17b` (fallback) — `DEC-009`'s original
  arrangement, restored after `DEC-010`'s swap was reverted (`DEC-011`).
- `agent/config.py`: `REASONING_CONTEXT_TOP_K` / `REASONING_EXCERPT_CHARS`
  at their code defaults, 3 / 400 — no env override.
- `agent/retrieval_client.py`: tokenizer fix (`len(w) > 1` filter) and
  `MIN_OVERLAP=2` — both in code, not env-toggled, unchanged since B4.
- `agent/prompts/system_prompt.md`: citation-format instructions restored
  verbatim from commit `ca8702f` (Phase B3.5, pre-bisection), committed
  in `2f430fc`. Diffed against `ca8702f` to confirm nothing else was
  silently lost — the only remaining delta is the procedure-document
  clarification paragraph, a separate deliberate fix from earlier in B4.

Result on this exact configuration, 3 live passes against the real MaaS,
near-identical failure sets each pass (a firm ceiling, not noise):
`itsm_read` 8/8 fail, `draft_request` 6/6 fail, `tool_selection` 6/8,
`unauthorized_write` 6/6 (all on the corroborating `approval_path_invoked`
check — the store-verified `write_blocked` safety property held 18/18),
`operational` 3/5, `knowledge_qa` 2/15, `out_of_domain` 0–1/6,
`prompt_injection` 0/8 (clean). Root cause diagnosed directly from raw
model output: granite narrates tool calls in prose/fenced-JSON instead of
emitting real `tool_calls`, triggered by the restored citation
instruction competing with tool-calling instructions whenever `retrieve`
(which runs unconditionally for every query, by design) returns any
topically-plausible context — even for tool-oriented queries. Full
detail: `DECISIONS.md` `DEC-012`.

## Open decision, pending owner sign-off

No model tested this session clears all 8 domain categories on this MaaS
(granite, scout, qwen3-14b measured in full; gpt-oss-20b disqualified on
transport reliability before an accuracy run). The frozen-config
re-baseline above is the evidence table. The owner is choosing between:
restructuring retrieval so it doesn't run (or is gated/ignored) for
tool-oriented queries; reverting the citation restoration and accepting
the smaller, better-understood pre-restoration gap instead; trying a
different mitigation for the prose-narrated-tool-call behavior; testing a
model not yet tried; or accepting a documented known-gap on specific
categories for the demo milestone. **Do not pick one of these
unilaterally — this is explicitly an owner call**, per `DEC-011`/`DEC-012`.

## Invariants that must survive any future session

These are load-bearing design decisions, not implementation details — do
not silently drift from them while doing other work:

1. **DEC-008 arguments-sourcing.** `human_approval_node` is the sole
   invoker of a write-classified tool, and only on `decision == "approve"`
   — it reads the arguments back from persisted graph state
   (`approval_action`), never a cached or re-derived copy. No other code
   path may call a write-classified tool.
2. **DEC-009 route assertion (B4's compensating control).** Every
   domain-eval-run model call must assert `route=primary,
   reason_code=none`, except cases specifically designed to exercise the
   fallback path (which assert the reverse). This is what makes it safe
   that the fallback model doesn't have to match the primary's domain
   quality — without this assertion in the gate, a routing bug silently
   defaulting to fallback could hide behind good-looking output instead
   of failing CI.
3. **The 5-category rule for model swaps (`DEC-011`).** Any future
   primary-model change must pass the full 5-category acceptance test
   (`knowledge_qa`, `out_of_domain`, `itsm_read`, `draft_request`,
   `tool_selection`) before adoption — not just the categories that
   motivated testing it. `DEC-010`'s swap only checked the two categories
   it was trying to fix and missed a severe regression in the other
   three; this rule exists specifically because of that miss.
4. **The prompt-is-instrument rule (`DEC-012`).** `system_prompt.md` is
   part of the measurement instrument, on the same footing as model
   choice, retrieval code, and `.env` config. Any change to it invalidates
   in-flight category comparisons and requires a fresh, frozen-state,
   multi-pass re-baseline before its results are compared against
   anything measured before the change.

## Pointers

- `DECISIONS.md` — `DEC-001` through `DEC-012`, full rationale for every
  design/config choice this session, in order. Read `DEC-009` → `DEC-010`
  → `DEC-011` → `DEC-012` in sequence for the full model-routing
  investigation; the others cover B0–B3.5 governance decisions.
- `~/.claude/plans/encapsulated-wobbling-conway.md` — the accepted
  phased delivery plan (B0 → B → C → D → E) this branch is executing
  against.
- `reports/feature-phase-b-golden-path.md` — the running work-log/test-
  report for this branch; B4's section has the full crisis narrative,
  the measurement matrices (including the struck pre-restoration one and
  `DEC-012`'s frozen re-baseline table), and the open-items list mirrored
  from `DECISIONS.md`.
