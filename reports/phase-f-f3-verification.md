# Phase F3 — CLI-instantiation parity, execution-based verification

Definition of Done per owner's authorization: execution, not diff. Render
a test project with distinct parameters, run the literal-sweep against
it (zero hits), then run the rendered project's own offline test suite
and fake-mode `make eval` — both green, **untouched after rendering**.
The diff against the source repo is supporting evidence only.

**A real defect was found and fixed** during this verification, exactly
the outcome the mission's own hard rules predicted ("every claim of
'works' must come from a command you ran... expect one \[real defect\]").

## 1. `tools/instantiate_agent_project.py` — F3's CLI, built

Consumes the same `skeleton/` + `template-schema.json` as F2's own
verification tool — `tools/skeleton_renderer.py` is now the one shared
rendering engine both import, refactored out of `tools/verify_skeleton.py`
specifically to avoid a `DEC-075`-style parallel-constant split between
F2's verification and F3's real CLI.

## 2. First render attempt — a real defect found

```
$ python3 tools/instantiate_agent_project.py --name acme-hr-helper \
    --owner "group:default/acme-hr-team" \
    --description "A pilot agent for HR helpdesk ticket triage." \
    --repoOwner acme-corp --repoName acme-hr-helper \
    --output .../rendered-acme-hr-helper
Rendering into .../rendered-acme-hr-helper with: {'name': 'acme-hr-helper', ...}
Done. 210 files rendered to .../rendered-acme-hr-helper.
```

Literal-sweep and placeholder-sweep both passed clean on this first
render. But running the rendered project's own test suite (untouched)
surfaced a real failure:

```
$ pytest -q
...
FAILED tests/test_trace_check.py::test_real_srs_documents_parse_without_error_and_match_known_counts
1 failed, 250 passed, 1 skipped, 1 warning in 29.80s
```

**Root cause**: `tests/test_trace_check.py` has one test (of 42 in that
file) that reads real files under `srs/` — a directory F2 had already,
correctly, excluded from the skeleton (`docs/template-nine-output-
mapping.md`'s own reasoning: this project's own decision/session
history). The other 41 tests in that file are self-contained unit tests
against synthetic fixture strings and would have passed regardless — only
this one test's dependency on real `srs/` files was missed when the
skeleton was built. A diff against the source repo would never have
caught this (the test file is byte-identical between source and
skeleton); only actually running it surfaced the missing dependency.

## 3. Fix applied

- Removed `tools/trace-check/` and `tests/test_trace_check.py` from
  `skeleton/` entirely (not just the one failing test) — the whole tool
  validates this project's own formal SyRS→StRS→SRS traceability
  methodology, which a scaffolded child project isn't assumed to adopt;
  consistent with `srs/`'s own exclusion, not a new scoping principle.
- Removed the now-dead `trace` target from `skeleton/Makefile` (and its
  `.PHONY` entry) — it referenced the now-removed tool.
- `docs/template-nine-output-mapping.md` updated to document this
  exclusion and its reasoning, including the honest note that a handful
  of cosmetic prose mentions of `trace-check` survive in
  `eval/THRESHOLDS.md`/`eval/README.md` (documentation text, not a
  functional dependency — left as a known minor rough edge, not silently
  hidden).
- `tools/verify_skeleton.py` re-run after the fix: still clean (207
  files now, down from 210 — matches the 3 removed files exactly).

## 4. Second render — clean, fresh directory, full execution

```
$ python3 tools/instantiate_agent_project.py --name acme-hr-helper \
    --owner "group:default/acme-hr-team" \
    --description "A pilot agent for HR helpdesk ticket triage." \
    --repoOwner acme-corp --repoName acme-hr-helper \
    --output .../rendered-acme-hr-helper
Rendering into .../rendered-acme-hr-helper with: {...}
Done. 207 files rendered to .../rendered-acme-hr-helper.
```

**Literal sweep** (zero hits):
```
$ grep -rn "golden-path-agent" .../rendered-acme-hr-helper --include="*" | grep -v '${{ values'
PASS: zero survivors
$ grep -rEln '\$\{\{\s*values\.' .../rendered-acme-hr-helper --include="*"
PASS: zero unresolved
```

**Sample rendered content**, confirming real substitution under the new
identity (not the same values as F2's own `widget-support-agent` test —
a genuinely distinct parameter set, per the DoD requirement):
```
mcp_server/auth.py:29:MCP_AUDIENCE = "acme-hr-helper-mcp"
agent/config.py:156:OTEL_SERVICE_NAME = _env("OTEL_SERVICE_NAME", "acme-hr-helper")
agent/config.py:162:AGENT_WORKLOAD_ID = _env("AGENT_WORKLOAD_ID", "acme-hr-helper")
pyproject.toml: name = "acme-hr-helper"
```

**Rendered project's own offline test suite, untouched after rendering**
(fresh `python:3.12-slim` container, `pip install -r requirements.txt -r
requirements-dev.txt`, no manual fixes applied to the rendered output):
```
$ pytest -q
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
210 passed, 1 warning in 27.16s
```
210 = 252 (source baseline) − 42 (the removed `test_trace_check.py`'s
own test count) — reconciles exactly, confirming no other regression.

**Rendered project's own fake-mode `make eval`, via the actual Makefile,
untouched**:
```
$ make eval-fast
AGENT_MODEL_MODE=fake python -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002

2/2 cases passed
```
`make test` also re-run for completeness via the real Makefile target
(not just the raw `pytest -q` invocation above): same 210 passed.

## 5. Diff against source — supporting evidence only, not the proof

```
$ diff -rq skeleton/ rendered-acme-hr-helper/ | grep -c "differ$"
82
```
82 — matching F2's own inventory count (`DEC-088`) exactly. The
remaining diff-tool output (not counted above) is `eval/results/*.json`
(two real eval-run records) and transient `.pytest_cache`/`state/`
directories — artifacts of actually *running* the rendered project, not
just rendering it. Removed after this evidence was captured.

## Summary

| Check | Result |
|---|---|
| First render, literal/placeholder sweep | Clean |
| First render, own test suite | **1 failed** (real defect: `srs/` dependency) |
| Fix applied | `tools/trace-check/`, `tests/test_trace_check.py`, Makefile `trace` target removed from skeleton |
| F2 re-verification post-fix | Clean (207 files) |
| Second render, literal/placeholder sweep | Clean |
| Second render, own test suite | 210 passed |
| Second render, own `make eval-fast` | 2/2 passed |
| Diff vs. skeleton (supporting only) | 82 files, matches F2's inventory exactly |

`SysR-P-F-01`(b) is satisfied, proven by execution under a distinct
parameter set, with a real defect found and fixed along the way — not
claimed from a diff read.
