"""Loader for eval/cases/domain/*.yaml — distinct from eval/loader.py,
which serves the EXAMPLE-*.yaml harness-mechanics fixtures only (kept
untouched by design). Each domain file is a YAML *list* of
cases, matching eval/schema.json, not eval/loader.py's one-file-one-case
shape.
"""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

DOMAIN_CASES_DIR = Path(__file__).resolve().parent / "cases" / "domain"


class DomainEvalCase(BaseModel):
    id: str
    category: str
    input: dict
    expected: dict
    threshold_notes: str
    tags: list[str]
    version: str
    performance_budget: Optional[dict] = None


def load_domain_case_file(path: Path) -> list[DomainEvalCase]:
    data = yaml.safe_load(path.read_text())
    return [DomainEvalCase(**item) for item in data]


def load_all_domain_cases(cases_dir: Path = DOMAIN_CASES_DIR) -> list[DomainEvalCase]:
    cases: list[DomainEvalCase] = []
    for path in sorted(cases_dir.glob("*.yaml")):
        cases.extend(load_domain_case_file(path))
    return cases


def load_domain_case_by_id(case_id: str, cases_dir: Path = DOMAIN_CASES_DIR) -> DomainEvalCase:
    for case in load_all_domain_cases(cases_dir):
        if case.id == case_id:
            return case
    raise KeyError(f"no domain eval case with id {case_id!r}")
