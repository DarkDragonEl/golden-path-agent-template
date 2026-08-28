"""eval/validate.py — structural validation for the domain eval set.

Standalone: imports only json/yaml/jsonschema/pathlib/sys. Does not import
or modify loader.py/scorer.py/runner.py/executor.py/cli.py, and targets an
explicit filename allowlist (never a glob), so it can't touch
eval/cases/EXAMPLE-001.yaml or EXAMPLE-002.yaml — those belong to the
separate harness-mechanics fixture documented in eval/README.md.

Domain case files live in eval/cases/domain/, not eval/cases/ directly:
eval/loader.py::load_all_cases globs eval/cases/*.yaml (non-recursive) and
calls EvalCase(**data) on each file, which crashes on a file shaped as a
YAML list (this schema's case-list-per-category shape) rather than the old
single-case-mapping shape. Nesting under domain/ keeps `python -m eval.cli
run --all` passing 2/2 against EXAMPLE-001/002 with zero changes to
loader.py, since its glob is non-recursive and never descends into
eval/cases/domain/.

Checks: every case in the 8 category files validates against schema.json,
case ids are globally unique, each file's cases have `category` matching
the filename, and knowledge_qa's `expected.source_doc_ids` resolve against
corpus-manifest.yaml.
"""
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

EVAL_DIR = Path(__file__).parent
CATEGORY_FILES = [
    "knowledge_qa.yaml",
    "itsm_read.yaml",
    "tool_selection.yaml",
    "draft_request.yaml",
    "out_of_domain.yaml",
    "unauthorized_write.yaml",
    "prompt_injection.yaml",
    "operational.yaml",
]


def main() -> int:
    schema = json.loads((EVAL_DIR / "schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    manifest = yaml.safe_load((EVAL_DIR / "corpus-manifest.yaml").read_text())
    known_doc_ids = {d["doc_id"] for d in manifest["documents"]}

    errors = []
    seen_ids = {}
    counts = {}

    for filename in CATEGORY_FILES:
        path = EVAL_DIR / "cases" / "domain" / filename
        expected_category = filename.removesuffix(".yaml")
        if not path.exists():
            errors.append(f"{filename}: file does not exist")
            counts[filename] = 0
            continue

        cases = yaml.safe_load(path.read_text()) or []
        counts[filename] = len(cases)

        for i, case in enumerate(cases):
            for err in validator.iter_errors(case):
                errors.append(f"{filename}[{i}] ({case.get('id')}): {err.message}")

            cid = case.get("id")
            if cid in seen_ids:
                errors.append(f"{filename}[{i}]: duplicate id {cid!r} (also in {seen_ids[cid]})")
            seen_ids[cid] = filename

            if case.get("category") != expected_category:
                errors.append(
                    f"{filename}[{i}]: category={case.get('category')!r} != {expected_category!r}"
                )

            if expected_category == "knowledge_qa":
                for doc_id in case.get("expected", {}).get("source_doc_ids", []):
                    if doc_id not in known_doc_ids:
                        errors.append(
                            f"{filename}[{i}] ({cid}): unknown source_doc_id {doc_id!r}"
                        )

    print("Case counts:", counts, "total:", sum(counts.values()))

    if errors:
        print(f"\n{len(errors)} validation error(s):")
        for e in errors:
            print(" -", e)
        return 1

    print("All cases valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
