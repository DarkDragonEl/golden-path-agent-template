# Phase C, Step C1d — negative proof #1 (seeded bad change), evidence report

**Run:** `PipelineRun/golden-path-agent-ci-c1d-pg8xq`, namespace
`golden-path-agent-ci`, triggered against branch
`test/c1d-seeded-eval-failure` (commit `809bb48`), via the same
`Pipeline` object as every other run this phase, overriding only the
`revision` param — no special-casing.

**Seed:** `policy/approval_rules.yaml`, one line —
`placeholder_write_action`'s classification flipped from `write` to
`read`. A write-classified action silently skipping the human-approval
gate: a genuine, plausible behavioral regression, not a build break.
Never merged to `main`; see `DECISIONS.md` `DEC-038` for the full design
rationale (why offline/`fake`-mode rather than live, to avoid `DEC-022`'s
documented drift class).

## 1. Per-stage results

| Stage | Result |
|---|---|
| `fetch-source` | Succeeded |
| `unit-tests` | **Failed** (4 tests, all traced to the seeded root cause) |
| `eval-gate-offline` | **Failed** (the targeted proof) |
| `policy-validate` | **Failed** (`policy-sync-check` sub-step; `opa-test` itself stayed green) |
| `container-build` | Never ran (skipped — upstream failure) |
| `digest-capture` | Never ran (skipped) |
| `sbom-generate` | Never ran (skipped) |
| `deploy-ephemeral` | Never ran (skipped) |
| `eval-gate-live` | Never ran (skipped) |
| `security-tests` | Never ran (skipped) |
| `operational-tests` | Never ran (skipped) |
| `open-promotion-pr` | Never ran (skipped) — **no promotion PR opened** |
| `destroy-ephemeral` | Succeeded (`finally:`, correctly ran anyway) |

## 2. `eval-gate-offline` — the targeted proof (verbatim `oc logs`)

```
[PASS] EXAMPLE-001
[FAIL] EXAMPLE-002
    - invoke state_equals: expected 'pending_approval'==True, got False
    - invoke no_final_output: expected no final_output yet, got 'PLACEHOLDER_TOOL_RESPONSE_MARKER'

1/2 cases passed
```

Matches the local pre-push verification exactly (`AGENT_MODEL_MODE=fake
python -m eval.cli run --all`, exit code 1) — fully deterministic, no
live-model dependency.

## 3. Two more gates independently caught the same regression

**`unit-tests`** (verbatim tail):
```
FAILED tests/test_eval_harness_smoke.py::test_example_002_passes - AssertionE...
FAILED tests/test_graph_shell.py::test_write_path_pauses_for_approval - asser...
FAILED tests/test_graph_shell.py::test_resume_after_rejection_falls_back - Ke...
FAILED tests/test_policy_limits.py::test_placeholder_write_action_classified_as_write_via_taxonomy
4 failed, 157 passed, 1 skipped, 2 warnings in 0.99s
```

**`policy-validate`**'s `policy-sync-check` step (verbatim):
```
POLICY SYNC CHECK FAILED -- policy/approval_rules.yaml and
policy/opa/approval_policy.rego have drifted:
  - 'placeholder_write_action': policy/approval_rules.yaml='read' vs policy/opa/approval_policy.rego='write'
```

The same Task's `opa-test` step stayed green (`PASS: 11/11`) — correctly
isolating that the rego bundle's own internal logic is undisturbed (it
was never touched); only the YAML/rego sync is broken, exactly the class
of drift `tools/check_policy_sync.py` exists to catch.

This is a stronger negative proof than a single isolated gate failure:
three structurally different mechanisms (Python unit assertions,
declarative-policy drift detection, behavioral eval harness) each
independently caught the same one-line regression.

## 4. No promotion PR opened — verified against GitHub directly

`open-promotion-pr` never appears in the `TaskRun` list (skipped, not
failed — normal Tekton DAG semantics for a task depending on failed
upstream stages). Verified independently against the actual GitHub API,
not inferred from pipeline status alone:

```
GET https://api.github.com/repos/DarkDragonEl/golden-path-agent-template/pulls?state=all
-> 0 PRs, any state
```

## 5. `destroy-ephemeral` still ran (verbatim `oc logs`)

```
No rendered-ephemeral.yaml on the workspace (deploy-ephemeral likely never ran) -- nothing to delete.
```

A genuine, honestly-reported no-op — nothing was ever deployed this run
(the failure occurred before `deploy-ephemeral`), so there was nothing to
clean up. The `finally:` task still executed unconditionally, proving the
always-run semantics hold even with nothing to do.

## 6. Conclusion

Negative proof #1 (`DEC-021`'s Phase C kickoff requirement) is
demonstrated: a genuine behavioral regression fails the eval gate with a
specific, legible assertion mismatch; no promotion PR opens; cleanup
still runs unconditionally. The seeded change lives only on
`test/c1d-seeded-eval-failure`; `main` was never touched.

**Not part of this evidence:** the promotion-PR path itself (`DEC-036`/
`DEC-037` fixed two real pipeline bugs there; blocked separately on a
GitHub-side fine-grained PAT permission gap, holding for the owner).
Negative proof #2 (digest equality across `ephemeral-test`/`demo-prod`)
is a C3/C4 item, once real promotion is possible.
