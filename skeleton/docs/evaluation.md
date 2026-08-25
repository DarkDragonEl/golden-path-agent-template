# Evaluation

`eval/` is the CI/CD promotion gate the proposal calls for: version-
controlled cases, deterministic scoring, nonzero exit on any failure.

```sh
python -m eval.cli run --all          # every case in eval/cases/
python -m eval.cli run --case EXAMPLE-001
```

Both currently ship cases pass — confirmed by direct execution during this
scaffold's build (`2/2 cases passed`, exit code 0), not just assumed from
the code.

## Case format

A case is either single-step (top-level `input` + `assertions`) or
multi-step (`steps:`, each with its own `action: invoke|resume` and
`assertions`). Multi-step cases drive the *same* compiled graph/thread
across steps, so a `resume` step continues the exact paused execution the
preceding `invoke` step left behind — mirroring the real
`POST /approvals/{id}/resume` flow, not a separate simulation of it.

## The two placeholder cases

- **EXAMPLE-001** — single-step, read path (`write` omitted → defaults to
  `false`). Proves the graph, the MCP contract's mock tool, and the
  read-path completion all wire together, with zero domain content.
- **EXAMPLE-002** — two-step, write path (`write: true`). Step 1
  (`invoke`) asserts `pending_approval == true` and no `final_output` yet.
  Step 2 (`resume`, `decision: approve`) asserts `final_output` is now
  present. This is the human-approval gate's own regression test — the
  proposal's most demo-critical path gets dedicated coverage, not just
  incidental coverage inside EXAMPLE-001.

## Assertion types (`eval/scorer.py`)

All deterministic except one: `tool_called`, `contains`, `max_reasoning_steps`,
`latency_ms_max`, `no_unapproved_write`, `state_equals`, `no_final_output`.
`semantic_judge` (LLM-as-judge) is wired but unused by the placeholder
cases — its rubric is a generic TODO(domain) stub; replace it once real
correctness/citation-quality criteria exist.

## Determinism

`eval/cli.py` sets `AGENT_MODEL_MODE=fake` and `MCP_MODE=mock` by default
(via `os.environ.setdefault`, so an explicit live-mode override still
wins) *before* importing anything that reads `agent/config.py`. This is
why `eval run` needs no network access or credentials — verified by
running it with no `.env` file present at all.

## As a CI gate

`ci/pr-checks.yaml`'s `eval-gate` stage runs `python -m eval.cli run --all`
and the pipeline fails if it exits nonzero. Results are also written to
`eval/results/run-<timestamp>.json` (gitignored) for local inspection.

## TODO(domain)

Everything above proves the harness works, not that the agent is good at
anything. Real golden-set cases — answer correctness, retrieval relevance,
citation quality, tool-argument correctness, refusal/escalation behavior,
prompt-injection resistance — are domain content and belong in
`eval/cases/` once a use case is chosen (see `../TODO_DOMAIN.md`).
