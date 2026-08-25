#!/usr/bin/env python3
"""Phase F3 (DECISIONS.md DEC-090; docs/phase-f-kickoff-plan.md SS7). The
direct CLI instantiation path SysR-P-F-01(b) requires, co-equal with the
Internal Developer Portal path (F5, not yet built) -- not a lesser
fallback. Consumes the same skeleton/ + template-schema.json as F5's
eventual Scaffolder Template will (tools/skeleton_renderer.py is the one
rendering engine both share), so the two paths cannot drift the way
DEC-075's parallel-constant bug did.

Produces a complete, parameterized new agent project in one operation --
literally satisfying SysR-P-F-01's "produces in one operation" language.
Zero RHDH dependency.

Usage:
    python3 tools/instantiate_agent_project.py --name my-agent \\
        --owner group:default/my-team --output /path/to/new-project

    # Or omit flags to be prompted interactively for required values:
    python3 tools/instantiate_agent_project.py --output /path/to/new-project
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skeleton_renderer import (  # noqa: E402
    load_schema,
    render_skeleton,
    resolve_values,
)


def prompt_for_missing(provided: dict, schema: dict) -> dict:
    values = dict(provided)
    for key in schema.get("required", []):
        if not values.get(key):
            title = schema["properties"][key].get("title", key)
            values[key] = input(f"{title} ({key}): ").strip()
    return values


def main() -> int:
    schema = load_schema()
    props = schema["properties"]

    parser = argparse.ArgumentParser(
        description="Instantiate a new agent project from the golden-path-agent skeleton."
    )
    for key, spec in props.items():
        parser.add_argument(f"--{key}", help=spec.get("description", ""))
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Directory to render the new project into (created if it doesn't exist).",
    )
    args = parser.parse_args()

    provided = {k: getattr(args, k) for k in props if getattr(args, k, None)}

    if sys.stdin.isatty():
        provided = prompt_for_missing(provided, schema)

    try:
        values = resolve_values(provided, schema)
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"Rendering into {args.output} with: {values}")
    render_skeleton(args.output, values)
    file_count = sum(1 for _ in args.output.rglob("*") if _.is_file())
    print(f"Done. {file_count} files rendered to {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
