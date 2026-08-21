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

## Pausing for B2 confirmation

Per the kickoff instructions: B1 is done, evidence above. B2 (the
write-gating restructure — `policy/approval_rules.yaml`'s taxonomy,
`agent/policy.py::classify_action()`, splitting `tool_invoke.py`'s eager
write into a draft-only path, and `human_approval.py` becoming the actual
invoker on approval) is where the `DECISIONS.md` DEC-008 arguments-sourcing
condition lands — pausing here for review before implementing it.
