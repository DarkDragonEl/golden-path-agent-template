#!/usr/bin/env python3
"""Phase F2 (DECISIONS.md DEC-087 item 1; docs/phase-f-kickoff-plan.md SS6,
item 6). This is F2's OWN internal verification tool -- NOT F3's CLI
renderer. F3 (the real instantiate-a-new-project CLI, with argument
parsing/prompts/a proper UX) is a separate, not-yet-authorized deliverable
(kickoff plan STOP 3 gates it). This script exists only to prove the
skeleton itself is correct before F3/F5 are built against it: render once
with test parameters into a scratch directory, then sweep the result for
(a) zero surviving source-repo literals and (b) zero unresolved template
placeholders. Both checks matter -- (a) proves nothing project-specific
leaked through, (b) proves every placeholder in the skeleton has a
matching parameter in template-schema.json, catching typos/drift between
the two before F3/F5 ever get built on top of a broken pairing.

Substitution engine: a small regex-based renderer for exactly the
'${{ values.x }}' subset the skeleton actually uses today (plain value
substitution, no loops/conditionals/filters) -- deliberately not a Jinja2
dependency, since nothing in the skeleton needs more than this yet.
Decision 1 (DEC-087) chose Backstage-native nunjucks syntax as the single
source of truth precisely so this stays swappable for a fuller nunjucks-
compatible engine later without touching skeleton/ itself, if a future
skeleton addition ever needs loops/conditionals this regex can't express.

Usage:
    python3 tools/verify_skeleton.py
"""

import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKELETON_DIR = REPO_ROOT / "skeleton"

PLACEHOLDER_RE = re.compile(r"\$\{\{\s*values\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

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


def render_text(text: str, values: dict) -> str:
    def _sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(
                f"skeleton references '${{{{ values.{key} }}}}' but no such key "
                f"exists in template-schema.json / TEST_VALUES -- schema and "
                f"skeleton have drifted apart"
            )
        return values[key]

    return PLACEHOLDER_RE.sub(_sub, text)


def render_skeleton(dest: Path, values: dict) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    for src_path in SKELETON_DIR.rglob("*"):
        rel = src_path.relative_to(SKELETON_DIR)
        dest_path = dest / rel
        if src_path.is_dir():
            dest_path.mkdir(parents=True, exist_ok=True)
            continue
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = src_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # No binary files are expected in the skeleton today -- fail
            # loudly rather than silently byte-copying something a real
            # render would also need to handle specially.
            raise RuntimeError(f"unexpected binary file in skeleton/: {rel}")
        dest_path.write_text(render_text(text, values), encoding="utf-8")
        shutil.copymode(src_path, dest_path)


def sweep_for_source_literal(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if SOURCE_LITERAL in text:
            hits.append(str(path.relative_to(root)))
    return hits


def sweep_for_unresolved_placeholders(root: Path) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER_RE.search(text):
            hits.append(str(path.relative_to(root)))
    return hits


def main() -> int:
    rendered_dir = REPO_ROOT / ".skeleton-verify-scratch"
    print(f"Rendering skeleton/ with test values into {rendered_dir} ...")
    render_skeleton(rendered_dir, TEST_VALUES)

    literal_hits = sweep_for_source_literal(rendered_dir)
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

    shutil.rmtree(rendered_dir, ignore_errors=True)

    if not ok:
        return 1
    print(f"\nAll checks passed. ({sum(1 for _ in SKELETON_DIR.rglob('*') if _.is_file())} "
          f"skeleton files rendered and swept.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
