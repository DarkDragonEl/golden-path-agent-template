# Phase H3a — module docstrings for agent/eval/mcp_server

Worktree stream (per DEC-114 / `reports/docs-terms-sheet.md`): adds a
module-level docstring to the 13 Python files H0's audit
(`reports/docs-audit.md` section 5) confirmed lack one. Docstring-only —
no comment edits, no logic changes, no behavior changes. Verified before
starting (re-checked each file still lacked a module docstring; all 13
did) and after finishing (see Verification below).

Branch note: the exact name `feature/h3a-python-docstrings` from DEC-114
was already held by another locked worktree sitting untouched at the same
base commit (a prior/parallel attempt at this same task). Following this
repo's own precedent for that situation (`feature/h1-readme-rewrite` /
`feature/h1-readme-rewrite-2`), this stream's branch is
`feature/h3a-python-docstrings-2` instead, without disturbing the other
worktree.

## Files and what each docstring says

1. **`agent/api.py`** — FastAPI HTTP surface for the golden-path agent:
   documents the four routes (`/invoke`, `/approvals/{session_id}/resume`,
   `/healthz`, `/ui`+`/ui/config`), their request/response contracts, the
   `AUTO_APPROVE_IN_DEV` dev-only bypass, the Layer 1/Layer 2 resume split
   (DEC-008/DEC-045/DEC-049), and the two `config`-sourced env-var inputs
   it depends on (`AUTO_APPROVE_IN_DEV`, `OIDC_ISSUER_URL`).
2. **`agent/graph.py`** — one-paragraph pointer: assembles the compiled
   LangGraph state graph from `agent/nodes/*.py` and `agent/routers.py`,
   keyed on `AgentState`; defers node-topology detail to `build_graph`'s
   own existing docstring rather than duplicating it.
3. **`agent/nodes/decide.py`** — the sole tool-vs-no-tool decision node:
   states its state-contract (reads `input_query`/`user_id`/
   `reasoning_steps`, returns a partial-state update or `fallback_reason`),
   cites the DEC-013-candidate decide-then-retrieve reordering and
   DEC-012's diagnosed root cause, and documents the `AGENT_MODEL_MODE`
   fake-mode dispatch tied to DEC-023.
4. **`agent/nodes/generate.py`** — the second, context-grounded model-call
   node: state contract, the `REASONING_CONTEXT_TOP_K`/
   `REASONING_EXCERPT_CHARS` context cap, and the SRS-AGT-F-01 citation
   requirement driving it.
5. **`agent/nodes/retrieve.py`** — short docstring: runs only on decide's
   "no tool needed" branch (DEC-013 candidate), state contract
   (`retrieved_docs`/`retrieval_unavailable`), `RETRIEVAL_TOP_K` env input,
   and the catch-and-flag-not-raise behavior.
6. **`agent/nodes/tool_invoke.py`** — read-vs-write execution node: state
   contract for both branches, the DEC-008/DEC-049 approval-submission
   path, and the `TOOL_TIMEOUT_SECONDS`/`AGENT_WORKLOAD_ID`/
   `APPROVAL_RULES_REF` env inputs it reads via `agent/config.py`.
7. **`agent/routers.py`** — one paragraph per router function
   (`decide_after_decide/_retrieve/_generate/_tool/_approval`), each
   function's routing contract (state in, next-node-name string out).
8. **`agent/state.py`** — overview of `AgentState`'s `total=False`
   partial-update contract and the `ToolCallRecord`/`ModelCallRecord`
   telemetry shapes, pointing to DEC-008/DEC-009/DEC-020/DEC-049 for the
   field-level detail already carried in inline comments.
9. **`eval/config.py`** — one-sentence docstring (file is 3 lines):
   documents the one constant, `DEFAULT_LATENCY_BUDGET_MS`, and its
   `EVAL_DEFAULT_LATENCY_BUDGET_MS` env-var source.
10. **`eval/loader.py`** — documents the harness-mechanics
    `eval/cases/*.yaml` loader and cites DEC-005, which is why this stays
    a separate, non-recursive loader from `eval/domain_loader.py`'s
    nested-list `eval/cases/domain/` layout.
11. **`eval/reporter.py`** — documents `write_report`'s JSON summary shape
    (SRS-EVH-IF-02 fields), the git-derived `build_reference` fallback,
    `tolerated_known_gaps`'s DEC-016/DEC-017 provenance, and
    `print_summary`'s separate stdout-only role.
12. **`eval/runner.py`** — documents `run_case`'s contract: drives
    `execute_case` then `score_assertion`, the steps-vs-no-steps branching,
    and the `{case_id, passed, results}` return shape consumed by
    `eval/reporter.py`.
13. **`mcp_server/schemas.py`** — documents the four schema families
    (`ItsmSearchRecords*`/SRS-MIT-IF-02, `ItsmCreateRequest*`/
    SRS-MIT-IF-03, `PlaceholderLookup*`, `PlaceholderWriteActionInput`),
    their srs/SRS-MIT.md and DEC-023 provenance, and how
    `mcp_server/server.py` and `agent/tool_schemas.py` each relate to them.

## Verification

### `git diff --stat` — docstring-only, exactly these 13 files

```
 agent/api.py               | 26 ++++++++++++++++++++++++++
 agent/graph.py             | 10 ++++++++++
 agent/nodes/decide.py      | 20 ++++++++++++++++++++
 agent/nodes/generate.py    | 20 ++++++++++++++++++++
 agent/nodes/retrieve.py    | 11 +++++++++++
 agent/nodes/tool_invoke.py | 21 +++++++++++++++++++++
 agent/routers.py           | 17 +++++++++++++++++
 agent/state.py             | 15 +++++++++++++++
 eval/config.py             |  6 ++++++
 eval/loader.py             | 11 +++++++++++
 eval/reporter.py           | 20 ++++++++++++++++++++
 eval/runner.py             | 12 ++++++++++++
 mcp_server/schemas.py      | 20 ++++++++++++++++++++
 13 files changed, 209 insertions(+)
```

209 insertions, 0 deletions. `git diff | grep '^-' ` (excluding the `---`
file headers) across these 13 files returns nothing — every hunk is a pure
addition of a `"""..."""` docstring block immediately before the file's
first existing statement. `git status --porcelain` shows exactly these 13
paths modified and nothing else.

### `make test` (`pytest -q`) — before/after, identical pass count

No project virtualenv existed in this worktree and the system Python had
neither `pip` nor `pytest`; bootstrapped a user-level install
(`python3 -m ensurepip --user`, then
`python3 -m pip install --user -r requirements.txt -r requirements-dev.txt`)
to actually execute the suite rather than only compiling it.

- **Before** (docstring changes stashed via `git stash`): `253 passed, 1
  skipped, 243 warnings`.
- **After** (`git stash pop`, changes restored — `git diff --stat`
  reconfirmed identical to the pre-stash diff): `253 passed, 1 skipped,
  243 warnings`.

Exact same pass/skip count both times; all warnings are pre-existing
`langgraph`/`asyncio` deprecation notices, unrelated to this change.

### `make lint` (`python -m py_compile` over `agent mcp_server eval`)

Ran clean (exit 0, no output) both before and after. Additionally ran
`python -m py_compile` individually on all 13 target files after editing:
succeeded for all.

### Anonymity sweep

Read the full diff of new docstring text (all 13 hunks). No real
organization, employee, or hostname appears anywhere — every reference is
either a generic term ("the mock ITSM tool", "the approval service") or an
internal identifier already used throughout this codebase (module paths,
`DEC-NNN`, `SysR-*`/`SRS-*`/`StR-*` IDs, env-var names). Clean.

## Draft DEC-entry fragment (for the coordinating session)

```
## DEC-NNN (provisional — re-check tail before commit) — Phase H3a: module docstrings for agent/eval/mcp_server

**Ambiguity:** H0's audit (`reports/docs-audit.md`) confirmed 13 Python
files across `agent/`, `eval/`, and `mcp_server/` have no module-level
docstring, but left open exactly what content each one should carry and
which existing DEC numbers its behavior actually traces to.

**Finding:** Each file already carries function-level docstrings and/or
inline `DEC-NNN`/`SRS-*` comments describing its own contract in detail
(e.g. `agent/nodes/decide.py`'s DEC-013-candidate reordering rationale,
`agent/nodes/tool_invoke.py`'s DEC-008/DEC-049 approval-submission path,
`eval/loader.py`'s DEC-005 split from `eval/domain_loader.py`). A module
docstring's job is to summarize that existing narrative at the top of the
file in the format already established by `agent/nodes/human_approval.py`
and `agent/config.py`, not to invent new decisions.

**Decision:** Added exactly one module-level docstring (a triple-quoted
string as the file's first statement) to each of the 13 files named in
DEC-114, covering purpose, the node/route/schema contract, any
`agent/config.py`/`eval/config.py`-sourced env-var inputs, and a brief DEC
pointer where one applies. No comment, logic, or behavior changes; only
these 13 files touched. Full docstring text: see
`reports/feature-h3a-python-docstrings.md`.

**Evidence:** `git diff --stat` shows 209 insertions / 0 deletions across
exactly these 13 files; `make test`/`pytest -q` stayed at 253 passed, 1
skipped before and after; `make lint`/`py_compile` clean on all 13 files;
anonymity sweep of the new text found no real org/employee/hostname
references. Full command output and per-file docstring summaries in
`reports/feature-h3a-python-docstrings.md`.

**Status:** Done in worktree stream `feature/h3a-python-docstrings-2`
(exact `feature/h3a-python-docstrings` name already held by another
worktree at the same base commit — see that report's branch note).
Committed locally, not pushed, not merged — awaiting the coordinating
session's review and merge to `main`.
```
