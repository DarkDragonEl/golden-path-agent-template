import os

os.environ.setdefault("AGENT_MODEL_MODE", "fake")
os.environ.setdefault("MCP_MODE", "mock")

from pathlib import Path  # noqa: E402

from eval.loader import load_case  # noqa: E402
from eval.runner import run_case  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent.parent / "eval" / "cases"


def test_example_001_passes():
    case = load_case(CASES_DIR / "EXAMPLE-001.yaml")
    result = run_case(case)
    assert result["passed"], result["results"]


def test_example_002_passes():
    case = load_case(CASES_DIR / "EXAMPLE-002.yaml")
    result = run_case(case)
    assert result["passed"], result["results"]
