"""Loads the pre-existing harness-mechanics eval case file format
(`eval/cases/*.yaml`, e.g. `EXAMPLE-001.yaml`/`EXAMPLE-002.yaml`) into
pydantic models.

File format: an `EvalCase` is `{id, description, mode, input, assertions,
steps}` -- deliberately no `category`/`expected`/`tags`/`version`/
`threshold_notes` field (that richer shape belongs to the separate
`eval/cases/domain/*.yaml` set and `eval/domain_loader.py`, not this
module). A case with no `steps` is scored as a single implicit
`invoke`, against its top-level `assertions`; a case with `steps` is a
multi-step invoke/resume sequence (`EvalStep.action`), each step
carrying its own `assertions` and, for a `resume` step, the approver
`decision` (SRS-APR-IF-02's `"approve"|"reject"` verb) to apply.
`load_all_cases` reads every `*.yaml` file in a directory, sorted by name.
"""

from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import BaseModel


class Assertion(BaseModel):
    type: str
    field: Optional[str] = None
    value: object = None
    tool_name: Optional[str] = None


class EvalStep(BaseModel):
    action: Literal["invoke", "resume"]
    decision: Optional[str] = None  # required for action="resume"
    assertions: list[Assertion] = []


class EvalCase(BaseModel):
    id: str
    description: str
    mode: Literal["offline", "live"] = "offline"
    input: Optional[dict] = None
    assertions: list[Assertion] = []
    steps: list[EvalStep] = []


def load_case(path: Path) -> EvalCase:
    data = yaml.safe_load(path.read_text())
    return EvalCase(**data)


def load_all_cases(cases_dir: Path) -> list[EvalCase]:
    return [load_case(p) for p in sorted(cases_dir.glob("*.yaml"))]
