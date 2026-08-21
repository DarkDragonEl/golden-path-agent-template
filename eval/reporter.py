import json
import subprocess
import time
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _default_build_reference() -> tuple[str, str]:
    """(build_reference, build_reference_type) per the resolved
    SRS-EVH-IF-02: a real image digest once one exists (Phase C), a git
    commit hash for a clean pre-build local run, or the explicit
    "local-dev-uncommitted" sentinel for a dirty worktree -- self-
    describing via the type field so a downstream consumer (the Phase C
    MLflow record) can never mistake a commit hash for a real digest.
    """
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        if status.stdout.strip():
            return "local-dev-uncommitted", "local_dev_uncommitted"
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        )
        return commit.stdout.strip(), "git_commit"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "local-dev-uncommitted", "local_dev_uncommitted"


def write_report(
    run_results: list[dict],
    timestamp: str | None = None,
    eval_set_version: str | None = None,
    build_reference: str | None = None,
    build_reference_type: str | None = None,
    config_reference: str | None = None,
    thresholds_applied: dict | None = None,
    gate_verdict: str | None = None,
) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = timestamp or time.strftime("%Y%m%dT%H%M%S")
    path = RESULTS_DIR / f"run-{ts}.json"

    if build_reference is None or build_reference_type is None:
        build_reference, build_reference_type = _default_build_reference()

    summary = {
        "timestamp": ts,
        "total": len(run_results),
        "passed": sum(1 for r in run_results if r["passed"]),
        "failed": sum(1 for r in run_results if not r["passed"]),
        "cases": run_results,
        # SRS-EVH-IF-02 (resolved at Checkpoint B0-b) -- additive fields.
        "eval_set_version": eval_set_version,
        "build_reference": build_reference,
        "build_reference_type": build_reference_type,
        "config_reference": config_reference,
        "thresholds_applied": thresholds_applied,
        "gate_verdict": gate_verdict,
    }
    path.write_text(json.dumps(summary, indent=2))
    return path


def print_summary(run_results: list[dict]) -> None:
    for r in run_results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"[{status}] {r['case_id']}")
        if not r["passed"]:
            for a in r["results"]:
                if not a["passed"]:
                    print(f"    - {a.get('step', '')} {a['assertion']}: {a['detail']}")
    total = len(run_results)
    passed = sum(1 for r in run_results if r["passed"])
    print(f"\n{passed}/{total} cases passed")
