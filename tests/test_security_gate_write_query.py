"""security-tests' REST zero-mutation check needs the agent to draft a
write first. Its query is the eval set's own draft-request case DRQ-001, so
the precondition rests on behaviour the domain gate already requires."""

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_gate_write_query_is_eval_case_drq_001():
    cases = yaml.safe_load((REPO_ROOT / "eval/cases/domain/draft_request.yaml").read_text())
    drq_001 = next(c for c in cases if c["id"] == "DRQ-001")
    assert drq_001["expected"]["approval_requested"] is True
    task = (REPO_ROOT / "pipelines/tasks/security-tests.yaml").read_text()
    queries = re.findall(r'"query": "([^"]+)",\n\s+"write": True', task)
    assert queries == [drq_001["input"]["query"]]
