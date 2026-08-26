"""Eval-harness environment configuration.

Defines DEFAULT_LATENCY_BUDGET_MS, the default latency budget in
milliseconds, read from EVAL_DEFAULT_LATENCY_BUDGET_MS (default: 5000).
"""

import os

DEFAULT_LATENCY_BUDGET_MS = int(os.environ.get("EVAL_DEFAULT_LATENCY_BUDGET_MS", "5000"))
