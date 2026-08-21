# Phase B: Local Golden Path — Test Report

Branch: `feature/phase-b-golden-path`, off `main` at `cc56013` (Checkpoint B0-b closed).

## Task 0 — baseline (2026-08-21)

Sandbox had neither `make` nor `pytest`/`pip` installed. Bootstrapped a
real environment: `python3 -m venv .venv`, `pip install -r
requirements-dev.txt` (pytest 9.1.1, mcp 1.29.0, fastapi 0.141.1, and the
rest of `requirements.txt`'s pins, all within their declared ranges).

```
$ .venv/bin/python -m pytest -q
1 failed, 55 passed
FAILED tests/test_trace_check.py::test_real_srs_documents_parse_without_error_and_match_known_counts
  AssertionError: SRS-APR.md: expected 18 requirements, got 19
```

Red on the first run — a real harness bug, not an environment problem: the
test hardcoded SRS-APR.md's requirement count from before Checkpoint B0-b
added `SRS-APR-IF-05` (`DECISIONS.md` DEC-008). Fixed the stale count
(18→19, total 73→74) per the Task 0 rule ("if red, fix the environment/
harness first"). Commit `ec1be3d`.

```
$ .venv/bin/python -m pytest -q
56 passed
$ .venv/bin/python -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002
2/2 cases passed
```

Baseline green. Task 0 done.

## Task 1 — tool-calling spike + fallback selection (2026-08-21)

Full method, results, and decision point in
`reports/phase-b-tool-calling-spike.md` (commit `ba127da`). Summary:
primary (`granite-3-2-8b-instruct`) passes cleanly; all three
originally-shortlisted fallback candidates fail (one hard backend error,
two silently never call a tool). A diagnostic probe of 4 more models found
`llama-scout-17b` calling tools correctly and faster than primary, but
exceeding the size≤primary criterion. Resolved as `DECISIONS.md` DEC-009
(commit `89ae565`): fallback = `llama-scout-17b`, size≤primary criterion
explicitly waived with a required compensating control landing in Phase
B4 (a route/reason-code assertion in the eval gate). `.env`/`.env.example`
and the plan document updated to match. Task 1 done.

## B1 — Mock ITSM MCP server (2026-08-21)

### SDK spike (prerequisite, done before writing server.py's tool registrations)

Per `docs/architecture.md`'s own recorded breaking-change scare with the
`mcp` package, verified both open questions empirically against the
pinned version actually installed (`mcp` 1.29.0), not assumed:

1. **Tool-catalog metadata (SRS-MIT-IF-01).** `FastMCP.tool()` accepts a
   `meta: dict[str, Any]` kwarg. Confirmed it propagates into the real
   `list_tools()` MCP-protocol response (not just stored inertly) via a
   direct probe. Used as `@mcp.tool(meta={"semver": ..., "certification_status":
   "blueprint-demo"})`.
2. **REST/MCP coexistence.** Confirmed `FastMCP.streamable_http_app()`
   returns a `Starlette` ASGI app that mounts cleanly under a parent
   FastAPI app on one port, provided the parent's lifespan explicitly
   enters the sub-app's lifespan context (`AsyncExitStack` +
   `mcp_asgi_app.router.lifespan_context(...)`) — otherwise the MCP
   session manager never starts. Verified via `TestClient`: the REST route
   returned 200, and the mounted `/mcp` route was genuinely reachable (a
   421 from MCP's own Host-header DNS-rebinding protection against the
   test client's fake host — not a mounting failure). One port, no
   second-port fallback needed.

**A second, more consequential API constraint surfaced while writing
tests against the built app** (not caught by the single-call spike
above): `FastMCP` lazily creates and **caches** its
`StreamableHTTPSessionManager` on the `FastMCP` instance itself; that
session manager's `.run()` (entered via the app's lifespan) can only be
called **once per instance's lifetime** — calling `build_app()` fresh
per test raised `RuntimeError: StreamableHTTPSessionManager .run() can
only be called once per instance`. Fixed on the test side (a
module-scoped `TestClient` fixture, reused across all REST tests in the
file, matching how `main()` calls `build_app()` exactly once in
production) and documented directly in `build_app()`'s docstring so a
future reader doesn't reintroduce the bug.

### Implementation

- `mcp_server/itsm_store.py` (new) — in-process, thread-safe store.
  Entity model and field shapes transcribed directly from `srs/SRS-MIT.md`
  SRS-MIT-IF-02/IF-03 (the approved contract, not `eval/README.md`'s
  provisional version — though they agree). Seed data: exactly the eight
  contractual IDs from `eval/README.md`
  (`INC-10234/10240/10255/10261`, `REQ-30021/30052`, `KE-50007/50012`),
  field values cross-checked against every assertion in
  `eval/cases/domain/itsm_read.yaml` that touches them. New requests mint
  sequentially from `REQ-30100`. `_simulate_error` fault-injection hook on
  both `search()` and `create_request()`, test-only.
- `mcp_server/schemas.py` — added `ItsmSearchRecordsInput/Output`,
  `ItsmCreateRequestInput/Output`, field-for-field per SRS-MIT-IF-02/IF-03.
  `PlaceholderLookupInput/Output` left untouched.
- `mcp_server/server.py` — added `itsm_search_records` and
  `itsm_create_request` tools alongside (not replacing) `placeholder_lookup`
  — see "What was deliberately not done" below — plus the REST
  introspection app (`GET /records`, `GET /records/{id}`, `POST /reset`)
  mounted via `build_app()`. `main()` now runs the combined app via
  `uvicorn` instead of `mcp.run()`.
- `itsm_create_request`'s docstring carries the required interim-gap
  label: this tool is directly callable with no approval check in front
  of it in B1 — expected and correct for this phase, since
  `SRS-MIT-SEC-01`'s no-bypass guarantee is enforced by the agent's
  policy layer plus the approval flow (Phase B2), never by this MCP tool
  interface itself. Not the intended end state; closes in B2.

### What was deliberately not done

`placeholder_lookup`, `PlaceholderLookupInput/Output`, and
`agent/policy.py::classify_action()`'s write-flag check were left
untouched. Removing/replacing them now would have broken
`eval/cases/EXAMPLE-001.yaml` (asserts `tool_called: placeholder_lookup`
— an SRS-EVH-F-03-protected harness-mechanics fixture, never to be
treated as domain content), `tests/test_mcp_contract.py`, and
`tests/test_policy_limits.py` (which tests the *old* write-flag
classification — replacing it is explicitly Phase B2's write-gating
restructure, not B1's). B1 adds the two new tools alongside the old one;
retiring `placeholder_lookup` from the agent's active path is B2 work.

### B1 exit criteria — evidence

| Criterion | Evidence |
|---|---|
| Both MCP tools callable, schemas field-for-field per IF-02/IF-03 | `tests/test_itsm_mcp_server.py::test_itsm_search_records_signature_matches_srs_mit_if_02`, `::test_itsm_create_request_signature_matches_srs_mit_if_03`; `tests/test_itsm_store.py::test_search_result_fields_match_srs_mit_if_02`, `::test_create_request_output_shape_matches_srs_mit_if_03` |
| Write-then-read round trip (IF-05) | `test_itsm_store.py::test_write_then_read_round_trip_within_one_instance`, `test_itsm_mcp_server.py::test_itsm_create_request_then_search_round_trip` |
| REST introspection up (`GET /records`, `GET /records/{id}`, `POST /reset`), REST state matches MCP state (IF-04) | `test_itsm_mcp_server.py::test_rest_get_records_lists_seed_set`, `::test_rest_get_single_record_found_and_not_found`, `::test_rest_reset_restores_seed_set_after_a_write`, `::test_rest_state_matches_mcp_tool_state_for_the_same_record` |
| `_simulate_error` reachable only via the executor's `fault_params`, never through a real agent call | `test_itsm_mcp_server.py::test_simulate_error_not_reachable_through_the_public_tool_functions` (asserts `TypeError` when passed to the public tool wrapper functions — it's a store-level-only kwarg) |
| Existing 56 tests still green + new unit tests | see below |

```
$ .venv/bin/python -m pytest -q
92 passed
  (56 pre-existing + 20 in tests/test_itsm_store.py + 16 in tests/test_itsm_mcp_server.py)
$ .venv/bin/python tools/trace-check/trace_check.py --docs-only
(a)/(b)/(c) PASS, 0 violations — unaffected by B1 (no srs/ changes this pass)
```

Tool-catalog metadata (SRS-MIT-IF-01) confirmed present on the real
`list_tools()` response for both new tools (`semver`, `certification_status`).

### Files changed

New: `mcp_server/itsm_store.py`, `tests/test_itsm_store.py`,
`tests/test_itsm_mcp_server.py`. Modified: `mcp_server/schemas.py`,
`mcp_server/server.py`.

## B2 — Write-gating restructure (2026-08-21)

### Design point 1: DEC-008, translated to the Phase B interim mechanism

Phase B has no standalone approval service — the "service" is the graph's
own checkpointed state (LangGraph `MemorySaver`, resumed via
`POST /approvals/{id}/resume`). Implemented exactly as specified:

- `agent/nodes/tool_invoke.py` — a write-classified action is drafted
  only: a `tool_calls` entry with `result: None, error: None` is appended,
  and `approval_action={tool_name, arguments}` is persisted into state.
  The tool is never invoked here.
- `agent/nodes/human_approval.py` — on `approve`, reads `tool_name`/
  `arguments` back from the persisted `approval_action` (never from a
  node-scope variable, never re-derived) and is now the sole invoker.
- `tests/test_write_gating.py::test_approve_invokes_with_exactly_the_persisted_approval_action_arguments`
  and `::test_approve_reads_arguments_from_persisted_state_not_a_stale_local_copy`
  assert `arguments_executed == arguments_approved` by comparing the mock
  ITSM's created record (fetched via REST, full field set) against
  `approval_action`'s arguments — not by trusting the node's return value.

When Phase D swaps in the standalone `approval_service`, only the
read-back *source* changes (a terminal-state query, `SRS-APR-IF-05`,
instead of graph-checkpointed state) — the invariant and this same test
shape carry over unchanged, which is the point of landing it now.

### Design point 2: fail-closed default + explicit `placeholder_lookup` classification

`policy/approval_rules.yaml`: `itsm_search_records → read`,
`itsm_create_request → write`, `placeholder_lookup → read` (explicit, with
an inline comment — harness fixture per `eval/README.md`/`DECISIONS.md`
DEC-005, not domain content), `default_classification: write`
(SRS-AGT-SEC-03).

One real wrinkle found while implementing this: `eval/cases/EXAMPLE-002.yaml`
(pinned, harness-mechanics, untouchable) signals its write-classified case
via a legacy `write: true` *argument* flag on `placeholder_lookup` — not
by naming a different tool. A pure name-based taxonomy would classify
every `placeholder_lookup` call as `read` unconditionally, silently
breaking EXAMPLE-002 (its whole point is to pause for approval). Resolved
with a narrow, explicitly-commented carve-out in
`agent/policy.py::classify_action()` (`_LEGACY_WRITE_FLAG_TOOLS`): only
for `placeholder_lookup`, an explicit `write: true` argument still
overrides its taxonomy default — every other tool, including
`placeholder_lookup`'s own baseline, is classified purely by name. This
is scoped to keep one pinned fixture green, not a general mechanism.

The inverse test, per the kickoff ask, exists in two places:
`tests/test_policy_limits.py::test_unknown_tool_fails_closed_to_write`
(unit-level: `classify_action`/`requires_approval` on an unlisted name)
and `tests/test_write_gating.py::test_unrecognized_tool_classifies_as_write_and_would_pause`
(same assertion, phrased against the exact predicate `tool_invoke_node`'s
read/write branch depends on, so it's equivalent to "would pause," not
just a classification-in-isolation check). `srs/SRS-AGT.md`'s own Verification
table already flags this as a gap the Phase A eval set doesn't cover.

### Design point 3: reject/expiry/no-resume verified at the store

`tests/test_write_gating.py`'s reject, synthetic-`expired`, and no-resume
(`bypass_attempt`/`not_requested`) tests each assert a `GET /records` diff
on `record_type=request` shows **zero new records** — the mock ITSM's own
state, via the same REST surface a demo operator or CI pipeline test would
use — with the agent's own `pending_approval`/`fallback_reason` checked
first as corroborating evidence only, never the primary check. This is
only possible now that B1's REST introspection surface exists. The
no-resume test drives the real `tool_invoke_node` write branch (today
reachable through the legacy `placeholder_lookup` path) rather than a
hand-built state, so it exercises the actual drafting code.

### What was deliberately not done

`agent/nodes/tool_invoke.py` still hardcodes `tool_name = "placeholder_lookup"`
— it does not dynamically dispatch to `itsm_create_request` in the
production graph path. Wiring real tool selection (the model choosing
between `itsm_search_records`/`itsm_create_request` via OpenAI-style
`tools=`) is Phase B3's job, not B2's; changing tool_invoke_node's
dispatch now would have broken `EXAMPLE-002.yaml`'s pinned assertion that
the write path's `final_output` contains `PLACEHOLDER_TOOL_RESPONSE_MARKER`.
The DEC-008 tests above exercise the real `itsm_create_request` tool by
constructing `approval_action` directly and calling `human_approval_node`
in isolation — a legitimate test of the actual invoker logic, independent
of upstream tool selection.

`mcp_server/client.py::call_tool` was extended (mock mode) to dispatch to
`itsm_search_records`/`itsm_create_request`, not just `placeholder_lookup`
— required for `human_approval_node` to be able to invoke the new tools at
all; without it every DEC-008 test above would fail with "unknown tool."

A known, unfixed gap for B3: `human_approval_node`'s `final_output`
formatting (`result.get("result", "")`) matches `placeholder_lookup`'s
output shape but not `itsm_create_request`'s (`{record_id, status,
source}`, no `"result"` key) — a real approval today would produce an
empty `final_output` string. Left alone deliberately: composing a good
confirmation message depends on knowing which tool ran, which is B3's
response-composition territory, not B2's write-gating mechanism. Design
point 3 already treats `final_output` as corroborating evidence, not the
primary check, so this doesn't undermine B2's own tests — but note it.

### B2 exit criteria — evidence

| Criterion | Evidence |
|---|---|
| Pre-existing policy tests replaced, not silently deleted | `tests/test_policy_limits.py`: `test_read_action_not_classified_as_write` → renamed `test_placeholder_lookup_without_write_flag_classified_as_read`; `test_write_flag_classified_as_write` → renamed `test_placeholder_lookup_write_flag_legacy_carveout_classified_as_write` (module docstring explains why: they now test a narrow legacy carve-out, not the general mechanism) |
| New classification tests | `test_itsm_search_records_classified_as_read`, `test_itsm_create_request_classified_as_write`, `test_unknown_tool_fails_closed_to_write`, `test_only_a_recognized_write_flag_absent_placeholder_call_is_read_only_by_default` (`test_policy_limits.py`) + `test_unrecognized_tool_classifies_as_write_and_would_pause` (`test_write_gating.py`) |
| Pause/invoke/reject/expiry/round-trip tests | `tests/test_write_gating.py` (6 tests, listed above) |
| EXAMPLE-001/002 still green | `python -m eval.cli run --all` → `[PASS] EXAMPLE-001`, `[PASS] EXAMPLE-002`, 2/2 |
| trace-check unaffected | `python tools/trace-check/trace_check.py --docs-only` → checks (a)/(b)/(c) PASS, 74 SRS requirements (unchanged — no `srs/` edits this pass) |
| Report updated | this section |

```
$ .venv/bin/python -m pytest -q
102 passed   (92 pre-B2 + 6 in test_write_gating.py + 4 net-new in test_policy_limits.py)
$ .venv/bin/python -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002
2/2 cases passed
$ .venv/bin/python eval/validate.py
All cases valid. (62 cases, unchanged)
```

### Files changed

New: `tests/test_write_gating.py`, `tests/conftest.py` (session-scoped
`rest_client` fixture, shared with `tests/test_itsm_mcp_server.py` — the
process-wide session-manager singleton found in B1 means only one
`build_app()`/`TestClient` cycle can ever run per test process, not one
per module; refactored `test_itsm_mcp_server.py` to use the shared
fixture too). Modified: `policy/approval_rules.yaml`, `agent/config.py`,
`agent/policy.py`, `agent/nodes/tool_invoke.py`,
`agent/nodes/human_approval.py`, `mcp_server/client.py`,
`tests/test_policy_limits.py`.

## B3 — Model routing/fallback + real tool selection (2026-08-21)

`agent/model_client.py`: `RoutedModelClient` (primary + one fallback, both
OpenAI-compatible) tries primary, retries once against fallback on any
exception, classifies via `_classify_primary_failure` into the closed
4-code enum (`primary_timeout`/`primary_429`/`primary_5xx`/`primary_unreachable`;
non-429 `APIStatusError` folds into `primary_5xx`, a simplification of the
given enum, noted inline). `agent/nodes/reason.py`: wrapped in try/except,
total failure sets `fallback_reason="model_failure:<exception-class>"` and
`agent/routers.py::decide_after_reason` now checks it before the
step-limit check. `agent/tool_schemas.py` (new): OpenAI-style schemas
mirroring `mcp_server/schemas.py`, same shape already verified in the
kickoff spike.

`tool_invoke_node`'s hardcoded dispatch is genuinely retired — it now
reads `state["selected_tool"]` exclusively. `reason_node` owns the
mode-branching: live mode uses the model's real `tool_calls`; fake mode
reproduces the pre-B3 legacy dispatch exactly (so `EXAMPLE-*.yaml` keeps
passing unchanged) — this is the "judge on the spot" call on where the
carve-out's hardcoding lives now. The `write:true` carve-out in
`agent/policy.py` itself is unchanged code but got the requested
retirement-trigger comment: it dies once `EXAMPLE-*` fixtures can be
migrated off it per `DECISIONS.md` DEC-005's own terms, or Phase C at the
latest — not yet, since `EXAMPLE-002.yaml`'s own pinned input still
depends on it regardless of where the dispatch hardcoding lives.

**Two real gaps found and fixed via live testing against the actual MaaS**
(not just offline/fake-mode tests, which couldn't have caught either):

1. `human_approval_node`/`tool_invoke_node`'s `final_output` formatting
   (`result.get("result", "")`) only ever matched `placeholder_lookup`'s
   shape — a live `itsm_search_records`/`itsm_create_request` call
   produced an empty string. Fixed with `agent/tool_result_format.py`
   (deterministic templating, not a second model call — SRS-AGT-F-03
   stays one model call per turn). A real approval now surfaces the
   minted `REQ-` ID, e.g. `"Request REQ-30100 has been submitted (status:
   submitted)."`
2. The live model (`granite-3-2-8b-instruct`) doesn't reliably pass a
   named record ID as `record_id` vs. `query` even with explicit prompt
   guidance (tried and reverted a more directive prompt — it regressed
   the model into narrating tool calls in prose instead of emitting real
   `tool_calls`). Fixed at the store level instead:
   `itsm_store.search()` now also matches an exact record-ID string
   passed as `query`, case-insensitive — a deterministic fix, not a
   prompt-engineering bet.

`agent/prompts/system_prompt.md` replaced (was a `TODO(domain)`
placeholder with no domain/tool guidance at all). Also found and fixed:
the model had no way to know *who* was asking (no identity in the message
sent to it), so it hesitated to draft `itsm_create_request` without a
`requested_for` value — `reason_node` now appends `(Requested by:
<user_id>)` to the message.

**Live-verified against the real MaaS, both routes** (not just unit
tests): record-ID read lookup (correct tool + arguments, real answer);
free-text write-shaped request → drafts → pauses → approves → real
`REQ-30100` created with correctly-inferred fields, `final_output`
surfaces the ID; broken-primary run → falls back to `llama-scout-17b` with
`reason_code="primary_5xx"`, still answers correctly; broken-primary+
broken-fallback run → `fallback_reason="model_failure:AuthenticationError"`,
clean escalation message; out-of-domain refusal (no tool call); prompt
injection (no real tool call executed — `unauthorized_tool_calls: []`
holds structurally, though the model's own text sometimes narrates
engaging with the injected framing rather than cleanly ignoring it,
flagged for B4's scorer design: check `tool_calls`/`approval_action`
state, not fuzzy text matching, for this dimension); a purely conceptual
question (no tool needed). **One anomaly observed once, not reproduced on
retry**: a single live call produced a wildly off-topic hallucinated
response (unrelated "StickShift" system-administration content) on a
conceptual question; a clean retry of the identical query succeeded.
Noted as a reliability risk to watch during B4's full domain-eval run, not
chased further now (single non-reproducing occurrence across ~8 live
calls).

`eval/cases/domain/operational.yaml` OPS-004: `known-gap` tag removed
(version bumped 0.1.0→0.2.0), `threshold_notes` updated. `eval/THRESHOLDS.md`'s
exclusion section rewritten to record closure, with the live verification
above cited as evidence (the trace-check mechanical enforcement of this
removal trigger, SRS-EVH-F-04, isn't built yet — noted honestly as
separate, still-open tooling work, not silently assumed done).

**New unit tests**: `tests/test_model_client.py` (11 — routing,
classification, fallback behavior, no real network calls),
`tests/test_tool_result_format.py` (6), `tests/test_tool_invoke_dispatch.py`
(4, covering all three `selected_tool` shapes). **123 tests pass** (102 +
21 new). `EXAMPLE-001`/`EXAMPLE-002` still green via the real eval CLI.
`eval/validate.py` still green (62 cases). `trace-check --docs-only`
unaffected.

### Files changed

New: `agent/tool_schemas.py`, `agent/tool_result_format.py`,
`tests/test_model_client.py`, `tests/test_tool_result_format.py`,
`tests/test_tool_invoke_dispatch.py`. Modified: `agent/model_client.py`,
`agent/config.py`, `agent/nodes/reason.py`, `agent/nodes/tool_invoke.py`,
`agent/nodes/human_approval.py`, `agent/routers.py`, `agent/telemetry.py`,
`agent/state.py`, `agent/policy.py` (comment only),
`agent/prompts/system_prompt.md`, `mcp_server/itsm_store.py`,
`eval/cases/domain/operational.yaml`, `eval/THRESHOLDS.md`,
`tests/test_write_gating.py` (one test updated for the new
`selected_tool`-driven contract).

## Pausing briefly before B3.5 (corpus + retrieval)

Per the kickoff instructions, continuing straight to B3.5 (not a full
stop) — evidence above is the checkpoint. B3.5 is scoped narrowly:
~20 synthetic corpus documents + minimal lexical retrieval, per the plan
document's itemized insertion.
