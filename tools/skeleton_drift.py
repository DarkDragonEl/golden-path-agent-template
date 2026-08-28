#!/usr/bin/env python3
"""Read-only drift detector for skeleton/ and skeleton-tools/ (I4,
DEC-132's STOP 2 follow-up). skeleton(-tools)/ is a hand-curated,
committed directory -- nothing regenerates it from this repo's own
source, so nothing currently guards its parity with that source after
the one-time build that created it. This script renders both templates
with fixed synthetic values, maps each rendered file to its main-tree
counterpart (where one exists), and reports identical /
differs-by-placeholder-only / drifted, with a unified diff for drifted
files. Never writes anything -- a human (or a future I7 CI gate) acts
on the report.

Usage: python3 tools/skeleton_drift.py [--format table|json] [--output PATH]
"""

import argparse
import difflib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from skeleton_renderer import (  # noqa: E402
    load_schema,
    render_skeleton,
    resolve_template,
    resolve_values,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Same fixed values the I3/I4 scratch baseline used for the agent
# template render, reused here for reproducibility. No prior baseline
# render existed for the tools template; chosen to be internally
# consistent with the agent template's own synthetic name (as its
# allowedConsumerName).
SYNTHETIC_VALUES = {
    "agent": {
        "name": "i3-baseline-check",
        "owner": "group:default/baseline-team",
        "mcpEndpoint": "https://mcp-tool.example.com",
        "approvalServiceEndpoint": "https://approval.example.com",
    },
    "tools": {
        "name": "baseline-tools-check",
        "owner": "group:default/baseline-team",
        "allowedConsumerName": "i3-baseline-check",
    },
}

# This blueprint's own real identity -- what the schema fields above
# are standing in for. Only fields with an actual literal-text
# counterpart in the main tree belong here. mcpEndpoint/
# approvalServiceEndpoint/mcpApiName/oidcIssuerUrl/modelRoute have no
# main-tree analog at all (they describe OTHER projects' endpoints, not
# this repo's own); gitHost is deliberately excluded too -- main's own
# config now resolves it via a bootstrap-injected ${GITEA_HOST} env var
# (DEC-131), not a literal string, while skeleton resolves it at
# Scaffolder render time -- different mechanisms for different
# deployment models, not something a text substitution can compare.
REAL_VALUES = {
    "name": "golden-path-agent",
    "owner": "group:default/golden-path-agent-team",
    "repoOwner": "DarkDragonEl",
    "repoName": "golden-path-agent-template",
}

# Root-level files skeleton(-tools)/ names generically (one Containerfile,
# one entrypoint.sh, one requirements.txt) that this repo's own three-image
# split names per-component. Every other path maps identically.
ROOT_ALIASES = {
    "agent": {
        "Containerfile": "Containerfile.agent",
        "entrypoint.sh": "entrypoint-agent.sh",
        "requirements.txt": "requirements-agent.txt",
    },
    "tools": {
        "Containerfile": "Containerfile.mcp",
        "entrypoint.sh": "entrypoint-mcp.sh",
        "requirements.txt": "requirements-mcp.txt",
    },
}

PLACEHOLDER = "‹{}›"


def normalize(text: str, synthetic: dict) -> str:
    out = text
    for key, real in REAL_VALUES.items():
        out = out.replace(real, PLACEHOLDER.format(key))
        synth = synthetic.get(key)
        if synth:
            out = out.replace(synth, PLACEHOLDER.format(key))
    return out


def classify(main_text: str, rendered_text: str, synthetic: dict) -> tuple[str, str | None]:
    if main_text == rendered_text:
        return "identical", None
    main_lines = main_text.splitlines()
    rend_lines = rendered_text.splitlines()
    diff = "\n".join(
        difflib.unified_diff(main_lines, rend_lines, fromfile="main-tree", tofile="rendered", lineterm="")
    )
    sm = difflib.SequenceMatcher(None, main_lines, rend_lines)
    only_placeholder = True
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        a = normalize("\n".join(main_lines[i1:i2]), synthetic)
        b = normalize("\n".join(rend_lines[j1:j2]), synthetic)
        if a != b:
            only_placeholder = False
            break
    return ("differs-by-placeholder-only" if only_placeholder else "drifted"), diff


def main_tree_path(rel: Path, template: str) -> Path:
    parts = rel.parts
    if len(parts) == 1 and parts[0] in ROOT_ALIASES[template]:
        return REPO_ROOT / ROOT_ALIASES[template][parts[0]]
    return REPO_ROOT / rel


def run_template(template: str) -> dict:
    skeleton_dir, schema_path = resolve_template(template)
    schema = load_schema(schema_path)
    synthetic = SYNTHETIC_VALUES[template]
    values = resolve_values(synthetic, schema)

    results = {"identical": [], "differs-by-placeholder-only": [], "drifted": [], "skeleton-only": []}
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / f"render-{template}"
        render_skeleton(out_dir, values, skeleton_dir=skeleton_dir)
        for f in sorted(out_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(out_dir)
            mt_path = main_tree_path(rel, template)
            if not mt_path.exists():
                results["skeleton-only"].append(str(rel))
                continue
            try:
                rendered_text = f.read_text(encoding="utf-8")
                main_text = mt_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                results["skeleton-only"].append(f"{rel} (binary, skipped)")
                continue
            verdict, diff = classify(main_text, rendered_text, synthetic)
            if verdict == "identical":
                results["identical"].append(str(rel))
            else:
                results[verdict].append(
                    {"path": str(rel), "main_tree_path": str(mt_path.relative_to(REPO_ROOT)), "diff": diff}
                )
    return results


def print_table(all_results: dict) -> None:
    for template, results in all_results.items():
        print(f"\n=== {template} ===")
        for bucket in ("identical", "differs-by-placeholder-only", "drifted", "skeleton-only"):
            items = results[bucket]
            print(f"{bucket}: {len(items)}")
        for item in results["drifted"]:
            print(f"\n--- DRIFTED: {item['path']} (main-tree: {item['main_tree_path']}) ---")
            print(item["diff"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    all_results = {template: run_template(template) for template in ("agent", "tools")}

    if args.format == "json":
        text = json.dumps(all_results, indent=2)
        if args.output:
            args.output.write_text(text)
        else:
            print(text)
    else:
        print_table(all_results)
        if args.output:
            import contextlib
            import io

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                print_table(all_results)
            args.output.write_text(buf.getvalue())

    total_drifted = sum(len(r["drifted"]) for r in all_results.values())
    return 1 if total_drifted else 0


if __name__ == "__main__":
    sys.exit(main())
