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

Phase G, Stage 2 (DEC-098/DEC-099): extended to verify BOTH templates --
skeleton/ (the Agent Template) and skeleton-tools/ (the new Tools
Template) -- rather than duplicating this file for the second one.
TARGETS below is the only thing that changed structurally; the
render-then-sweep logic itself is unchanged and shared via
skeleton_renderer.py, same as before.

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
    render_skeleton,
    schema_path_for,
    sweep_for_literal,
    sweep_for_unresolved_placeholders,
)

# Deliberately distinct from any real value this project's own identity
# ever used, so a false-pass (test values that happen to collide with a
# literal already in the source tree) is structurally impossible.
SOURCE_LITERAL = "golden-path-agent"

TARGETS = [
    {
        "label": "Agent Template",
        "skeleton_dir": REPO_ROOT / "skeleton",
        "scratch_dir": REPO_ROOT / ".skeleton-verify-scratch",
        "test_values": {
            "name": "widget-support-agent",
            "owner": "group:default/widget-team",
            "description": "A pilot agent for widget support ticket triage.",
            "mcpEndpoint": "http://widget-tools-mcp.widget-tools-ns.svc.cluster.local:8081",
            "mcpApiName": "widget-tools-api",
            "approvalServiceEndpoint": "http://platform-approval.platform-foundation.svc.cluster.local:8082",
            "oidcIssuerUrl": "http://platform-keycloak.platform-foundation.svc.cluster.local:8080/realms/platform",
            "modelRoute": "general-v1",
            "gitHost": "gitea.example.org",
            "repoOwner": "example-org",
            "repoName": "widget-support-agent",
        },
    },
    {
        "label": "Tools Template",
        "skeleton_dir": REPO_ROOT / "skeleton-tools",
        "scratch_dir": REPO_ROOT / ".skeleton-tools-verify-scratch",
        "test_values": {
            "name": "widget-tools",
            "owner": "group:default/widget-team",
            "description": "An MCP tool server for widget support ticket triage.",
            "allowedConsumerName": "widget-support-agent",
            "gitHost": "gitea.example.org",
            "repoOwner": "example-org",
            "repoName": "widget-tools",
        },
    },
]


def verify_one(target: dict) -> bool:
    label = target["label"]
    scratch_dir = target["scratch_dir"]
    skeleton_dir = target["skeleton_dir"]
    schema_path = schema_path_for(skeleton_dir)

    print(f"--- {label} ({skeleton_dir.relative_to(REPO_ROOT)}) ---")
    print(f"Rendering into {scratch_dir} ...")
    render_skeleton(scratch_dir, target["test_values"], skeleton_dir=skeleton_dir)

    literal_hits = sweep_for_literal(scratch_dir, SOURCE_LITERAL)
    placeholder_hits = sweep_for_unresolved_placeholders(scratch_dir)

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

    # Confirm the schema's own declared properties actually match what
    # was rendered against -- catches a schema/skeleton drift the sweep
    # above wouldn't (e.g. a property present in the schema but never
    # referenced anywhere in the skeleton).
    import json
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    unused_props = set(schema["properties"]) - set(target["test_values"])
    if unused_props:
        ok = False
        print(f"FAIL: template-schema property(ies) not exercised by this verification's "
              f"own test_values: {sorted(unused_props)}")

    file_count = sum(1 for _ in skeleton_dir.rglob("*") if _.is_file())
    import shutil
    shutil.rmtree(scratch_dir, ignore_errors=True)

    if ok:
        print(f"PASS: {label} -- {file_count} skeleton files rendered and swept.")
    print()
    return ok


def main() -> int:
    results = [verify_one(target) for target in TARGETS]
    if not all(results):
        print("FAILED: one or more targets above did not pass.")
        return 1
    print(f"All checks passed across {len(TARGETS)} template(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
