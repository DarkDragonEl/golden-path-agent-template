#!/usr/bin/env python3
"""Phase F3 (DECISIONS.md DEC-090; docs/phase-f-kickoff-plan.md SS7). The
direct CLI instantiation path SysR-P-F-01(b) requires, co-equal with the
Internal Developer Portal path (F5, RHDH's own Scaffolder) -- not a
lesser fallback. Consumes the same skeleton(-tools)/ + template-schema*.json
as the Scaffolder Template(s) do (tools/skeleton_renderer.py is the one
rendering engine both share), so the two paths cannot drift the way
DEC-075's parallel-constant bug did.

Produces a complete, parameterized new project in one operation --
literally satisfying SysR-P-F-01's "produces in one operation" language.
Zero RHDH dependency for local rendering.

Phase G, Stage 3 (DEC-098/DEC-099/DEC-110, G6 Path B): --template selects
which of the two templates to render (default: agent, the pre-existing
behavior, unchanged for anyone not passing the new flag); --publish
extends rendering with a real publish to the Platform Foundation's Gitea
instance, as two repositories (source+pipeline, and a separate GitOps
repo) per the owner's own two-repo decision. See tools/gitea_publish.py
and reports/feature-g6-cli-publish.md for the publish mechanism itself
and its one significant named gap (the published GitOps repo's own
ArgoCD/promotion-PR content is not yet rewritten to be internally
consistent with the two-repo, Gitea-hosted split -- that's separate,
larger GitOps-onboarding work, not attempted here).

Usage:
    python3 tools/instantiate_agent_project.py --name my-agent \\
        --owner group:default/my-team --output /path/to/new-project

    # Or omit flags to be prompted interactively for required values:
    python3 tools/instantiate_agent_project.py --output /path/to/new-project

    # Tools Template instead of the (default) Agent Template:
    python3 tools/instantiate_agent_project.py --template tools \\
        --name my-tools --owner group:default/my-team \\
        --allowedConsumerName my-agent --output /path/to/new-tools-project

    # Render AND publish to Gitea as two repos (requires GITEA_TOKEN and
    # GITEA_USERNAME in the environment -- never passed as a bare CLI flag,
    # so the token never appears in shell history/process listings):
    GITEA_TOKEN=... GITEA_USERNAME=golden-path-agent-scaffolder \\
        python3 tools/instantiate_agent_project.py --name my-agent \\
        --owner group:default/my-team --output /path/to/new-project --publish
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skeleton_renderer import (  # noqa: E402
    load_schema,
    render_skeleton,
    resolve_template,
    resolve_values,
)

DEFAULT_GITEA_HOST = (
    "golden-path-agent-gitea-golden-path-agent-gitea.apps.cluster-hj7xp.dyn.redhatworkshops.io"
)
DEFAULT_GITEA_ORG = "golden-path-agent-projects"
PLACEHOLDER_REPO_OWNER = "REPLACE_ME_repoOwner"
PLACEHOLDER_REPO_NAME = "REPLACE_ME_repoName"


def prompt_for_missing(provided: dict, schema: dict) -> dict:
    values = dict(provided)
    for key in schema.get("required", []):
        if not values.get(key):
            title = schema["properties"][key].get("title", key)
            values[key] = input(f"{title} ({key}): ").strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instantiate a new project from a golden-path-agent template."
    )
    parser.add_argument(
        "--template", choices=["agent", "tools"], default="agent",
        help="Which template to render: 'agent' (default) or 'tools'.",
    )
    # Parse --template first, alone, so the rest of the schema-derived
    # flags below (which differ between the two templates) are built
    # against the right schema.
    template_arg, _ = parser.parse_known_args()
    skeleton_dir, schema_path = resolve_template(template_arg.template)
    schema = load_schema(schema_path)
    props = schema["properties"]

    for key, spec in props.items():
        parser.add_argument(f"--{key}", help=spec.get("description", ""))
    parser.add_argument(
        "--output", required=True, type=Path,
        help="Directory to render the new project into (created if it doesn't exist).",
    )
    parser.add_argument(
        "--publish", action="store_true",
        help=(
            "After rendering, publish to the Platform Foundation's Gitea instance as "
            "two repositories (source+pipeline, and a separate GitOps repo). Requires "
            "GITEA_TOKEN and GITEA_USERNAME in the environment."
        ),
    )
    parser.add_argument(
        "--gitea-host", default=DEFAULT_GITEA_HOST,
        help="Gitea hostname (default: this project's own Platform Foundation instance).",
    )
    parser.add_argument(
        "--gitea-org", default=DEFAULT_GITEA_ORG,
        help="Gitea org to publish into (default: this project's own scaffolded-projects org).",
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
    render_skeleton(args.output, values, skeleton_dir=skeleton_dir)
    file_count = sum(1 for _ in args.output.rglob("*") if _.is_file())
    print(f"Done. {file_count} files rendered to {args.output}.")

    if not args.publish:
        return 0

    gitea_token = os.environ.get("GITEA_TOKEN")
    gitea_username = os.environ.get("GITEA_USERNAME")
    if not gitea_token or not gitea_username:
        print(
            "FAIL: --publish requires GITEA_TOKEN and GITEA_USERNAME in the environment.",
            file=sys.stderr,
        )
        return 1

    # repoOwner/repoName default to REPLACE_ME_* placeholders in both
    # schemas (they were only ever load-bearing for this exact publish
    # step, per template-schema.json's own long-standing comment) -- fall
    # back to the org/name actually being published with, rather than
    # publishing a repo literally named "REPLACE_ME_repoName".
    repo_owner = values.get("repoOwner")
    if not repo_owner or repo_owner == PLACEHOLDER_REPO_OWNER:
        repo_owner = args.gitea_org
    repo_name = values.get("repoName")
    if not repo_name or repo_name == PLACEHOLDER_REPO_NAME:
        repo_name = values["name"]
    gitops_repo_name = f"{repo_name}-gitops"

    from gitea_publish import publish  # noqa: E402  (deferred: only needed for --publish)

    print(f"Publishing to https://{args.gitea_host}/{repo_owner} as "
          f"'{repo_name}' + '{gitops_repo_name}' ...")
    result = publish(
        args.output,
        gitea_host=args.gitea_host,
        org=repo_owner,
        token=gitea_token,
        username=gitea_username,
        repo_name=repo_name,
        gitops_repo_name=gitops_repo_name,
    )
    for label, repo in result.items():
        verb = "created" if repo["created"] else "already existed, pushed to"
        print(f"  {label}: {repo['clone_url']} ({verb})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
