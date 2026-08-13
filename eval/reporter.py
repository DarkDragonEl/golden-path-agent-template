import json
import time
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def write_report(run_results: list[dict], timestamp: str | None = None) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = timestamp or time.strftime("%Y%m%dT%H%M%S")
    path = RESULTS_DIR / f"run-{ts}.json"
    summary = {
        "timestamp": ts,
        "total": len(run_results),
        "passed": sum(1 for r in run_results if r["passed"]),
        "failed": sum(1 for r in run_results if not r["passed"]),
        "cases": run_results,
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
