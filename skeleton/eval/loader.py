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
