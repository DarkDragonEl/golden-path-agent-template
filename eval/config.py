"""Eval-harness-wide configuration, distinct from `agent/config.py`
(the agent's own runtime config) -- this module holds settings the eval
gate itself needs, not settings of the agent under test.

Environment variables: `EVAL_DEFAULT_LATENCY_BUDGET_MS` (default 5000)
-- a default latency budget in milliseconds, held here for the
`performance_budget`/`max_latency_ms` per-case field `eval/schema.json`
proposes (SRS-EVH-F-05); today every `latency_ms_max` assertion
(`eval/scorer.py`) still supplies its own explicit threshold value, so
this constant is not yet consumed elsewhere.
"""

import os

DEFAULT_LATENCY_BUDGET_MS = int(os.environ.get("EVAL_DEFAULT_LATENCY_BUDGET_MS", "5000"))
