#!/usr/bin/env python3
"""Phase F2 (DECISIONS.md DEC-087 item 1; docs/phase-f-kickoff-plan.md SS6,
item 6). This is F2's OWN internal verification tool -- NOT F3's CLI
renderer (that's tools/instantiate_agent_project.py). This script exists
only to prove the skeleton itself is correct before F3/F5 are built
against it: render once with test parameters into a scratch directory,
then sweep the result for (a) zero surviving source-repo literals and
(b) zero unresolved template placeholders. Both checks matter -- (a)
proves nothing project-specific leaked through, (b) proves every
placeholder in the skeleton has a matching parameter in
template-schema.json, catching typos/drift between the two before F3/F5
ever get built on top of a broken pairing.

Rendering logic lives in tools/skeleton_renderer.py, shared with F3's CLI
-- DEC-090's own reasoning for why this file no longer defines its own
copy (it used to; DEC-075's precedent is exactly the failure this refactor
avoids repeating).

Usage:
    python3 tools/verify_skeleton.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skeleton_renderer import (  # noqa: E402
    REPO_ROOT,
    SKELETON_DIR,
    render_skeleton,
    sweep_for_literal,
    sweep_for_unresolved_placeholders,
)

# Deliberately distinct from any real value this project's own identity
# ever used, so a false-pass (test values that happen to collide with a
# literal already in the source tree) is structurally impossible.
TEST_VALUES = {
    "name": "widget-support-agent",
    "owner": "group:default/widget-team",
    "description": "A pilot agent for widget support ticket triage.",
    "repoOwner": "example-org",
    "repoName": "widget-support-agent",
}

SOURCE_LITERAL = "golden-path-agent"


def main() -> int:
    rendered_dir = REPO_ROOT / ".skeleton-verify-scratch"
    print(f"Rendering skeleton/ with test values into {rendered_dir} ...")
    render_skeleton(rendered_dir, TEST_VALUES)

    literal_hits = sweep_for_literal(rendered_dir, SOURCE_LITERAL)
    placeholder_hits = sweep_for_unresolved_placeholders(rendered_dir)

    ok = True
    if literal_hits:
        ok = False
        print(f"FAIL: {len(literal_hits)} file(s) still contain the source literal "
              f"'{SOURCE_LITERAL}':")
        for h in literal_hits:
            print(f"  - {h}")
    else:
        print(f"PASS: zero surviving '{SOURCE_LITERAL}' occurrences in the rendered output")

    if placeholder_hits:
        ok = False
        print(f"FAIL: {len(placeholder_hits)} file(s) still contain an unresolved "
              f"'${{{{ values.x }}}}' placeholder:")
        for h in placeholder_hits:
            print(f"  - {h}")
    else:
        print("PASS: zero unresolved template placeholders in the rendered output")

    file_count = sum(1 for _ in SKELETON_DIR.rglob("*") if _.is_file())
    import shutil
    shutil.rmtree(rendered_dir, ignore_errors=True)

    if not ok:
        return 1
    print(f"\nAll checks passed. ({file_count} skeleton files rendered and swept.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
