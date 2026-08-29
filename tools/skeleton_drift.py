#!/usr/bin/env python3
"""Read-only drift detector for skeleton/ and skeleton-tools/.
skeleton(-tools)/ is a hand-curated, committed directory -- nothing
regenerates it from this repo's own source, so nothing currently
guards its parity with that source after the one-time build that
created it. This script renders both templates with fixed synthetic
values, maps each rendered file to its main-tree counterpart (where
one exists), and classifies each pair.

Two modes:
- --mode text (default): raw unified-diff comparison after value
  substitution. Fast, but a file that only differs in comments/
  docstrings/prose still reports as "drifted" -- exactly the blind spot
  that once let a real bug (skeleton/agent/cli.py bypassing the
  approval service entirely) hide inside a "the diff has some vocabulary
  in it, so it's probably fine" heuristic bucket.
- --mode semantic: normalizes each side before comparing, so
  comment/docstring-only differences collapse to equivalence and only
  a REAL structural difference is reported as drifted. Python:
  docstrings stripped, compared as an AST dump (comments are already
  invisible to `ast`). YAML/JSON: parsed and compared as data, not
  text (comments are already invisible to a parser). Rego/shell/
  Makefile/Containerfile/requirements*.txt: `#`-comment lines stripped
  (shebang preserved), whitespace-normalized, then compared as text --
  no parser available for these, so this is a best-effort, not a
  structural proof the way AST/data comparison is. Markdown and other
  pure-prose files have no non-narrative content to normalize toward,
  so semantic mode leaves their text-mode verdict unchanged.

Never writes anything -- a human (or a future I7 CI gate, once this
mode has run cleanly enough to trust) acts on the report.

Usage: python3 tools/skeleton_drift.py [--mode text|semantic]
                                        [--format table|json] [--output PATH]
                                        [--only PATH [PATH ...]]
"""

import argparse
import ast
import difflib
import json
import re
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
# config now resolves it via a bootstrap-injected ${GITEA_HOST} env var,
# not a literal string, while skeleton resolves it at
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


# --- Semantic normalization -------------------------------------------------
# Each normalizer takes already value-substituted text and returns a string
# that is EQUAL for two files iff they are equivalent under that file type's
# own notion of "same content, modulo comments/docstrings/formatting". None
# of these need to be perfect -- they only need to be strict enough that two
# genuinely different implementations still compare unequal.


class _DocstringStripper(ast.NodeTransformer):
    def _strip(self, node):
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(
            body[0].value.value, str
        ):
            node.body = body[1:] or [ast.Pass()]
        self.generic_visit(node)
        return node

    visit_Module = _strip
    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip
    visit_ClassDef = _strip


def semantic_normalize_python(text: str) -> str | None:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    tree = _DocstringStripper().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.dump(tree, annotate_fields=False)


def semantic_normalize_yaml(text: str) -> str | None:
    import yaml

    try:
        docs = list(yaml.safe_load_all(text))
    except yaml.YAMLError:
        return None
    return json.dumps(docs, sort_keys=True, default=str)


def semantic_normalize_json(text: str) -> str | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return json.dumps(data, sort_keys=True)


_HASH_COMMENT_RE = re.compile(r"#.*$")  # best-effort: no string-literal awareness, matches any '#' to end of line


def semantic_normalize_hash_comment_lang(text: str) -> str:
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if i == 0 and line.startswith("#!"):
            out.append(line.strip())
            continue
        stripped = _HASH_COMMENT_RE.sub("", line).rstrip()
        if stripped.strip():
            out.append(stripped.strip())
    return "\n".join(out)


_SEMANTIC_NORMALIZERS = {
    ".py": semantic_normalize_python,
    ".yaml": semantic_normalize_yaml,
    ".yml": semantic_normalize_yaml,
    ".json": semantic_normalize_json,
    ".rego": semantic_normalize_hash_comment_lang,
    ".sh": semantic_normalize_hash_comment_lang,
    ".txt": semantic_normalize_hash_comment_lang,
}
_NAME_NORMALIZERS = {
    "Makefile": semantic_normalize_hash_comment_lang,
    "Containerfile": semantic_normalize_hash_comment_lang,
}


def semantic_normalizer_for(path: Path):
    if path.name in _NAME_NORMALIZERS:
        return _NAME_NORMALIZERS[path.name]
    if path.name.startswith("Containerfile"):
        return semantic_normalize_hash_comment_lang
    return _SEMANTIC_NORMALIZERS.get(path.suffix)


def semantic_classify(
    main_text: str, rendered_text: str, synthetic: dict, path: Path
) -> tuple[str, str | None, str | None]:
    """Returns (verdict, diff, note). verdict adds 'semantically-equivalent'
    to classify()'s vocabulary; note explains what normalizer ran, or why
    none did (no normalizer for this file type -- falls back to classify())."""
    text_verdict, diff = classify(main_text, rendered_text, synthetic)
    if text_verdict in ("identical", "differs-by-placeholder-only"):
        return text_verdict, diff, None

    normalizer = semantic_normalizer_for(path)
    if normalizer is None:
        return text_verdict, diff, "no semantic normalizer for this file type -- text-mode verdict stands"

    main_sub = normalize(main_text, synthetic)
    rend_sub = normalize(rendered_text, synthetic)
    main_norm = normalizer(main_sub)
    rend_norm = normalizer(rend_sub)
    if main_norm is None or rend_norm is None:
        return text_verdict, diff, "normalizer failed to parse one side (syntax error?) -- text-mode verdict stands"
    if main_norm == rend_norm:
        return "semantically-equivalent", diff, f"{normalizer.__name__} normalized both sides equal"
    return "drifted", diff, f"{normalizer.__name__} normalized both sides -- still differ"


def main_tree_path(rel: Path, template: str) -> Path:
    parts = rel.parts
    if len(parts) == 1 and parts[0] in ROOT_ALIASES[template]:
        return REPO_ROOT / ROOT_ALIASES[template][parts[0]]
    return REPO_ROOT / rel


def run_template(template: str, mode: str, only: set[str] | None) -> dict:
    skeleton_dir, schema_path = resolve_template(template)
    schema = load_schema(schema_path)
    synthetic = SYNTHETIC_VALUES[template]
    values = resolve_values(synthetic, schema)

    results = {
        "identical": [],
        "differs-by-placeholder-only": [],
        "semantically-equivalent": [],
        "drifted": [],
        "skeleton-only": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / f"render-{template}"
        render_skeleton(out_dir, values, skeleton_dir=skeleton_dir)
        for f in sorted(out_dir.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(out_dir)
            if only is not None and str(rel) not in only:
                continue
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
            if mode == "semantic":
                verdict, diff, note = semantic_classify(main_text, rendered_text, synthetic, rel)
            else:
                verdict, diff = classify(main_text, rendered_text, synthetic)
                note = None
            if verdict == "identical":
                results["identical"].append(str(rel))
            else:
                row = {"path": str(rel), "main_tree_path": str(mt_path.relative_to(REPO_ROOT)), "diff": diff}
                if note:
                    row["note"] = note
                results[verdict].append(row)
    return results


def print_table(all_results: dict) -> None:
    for template, results in all_results.items():
        print(f"\n=== {template} ===")
        for bucket in results:
            print(f"{bucket}: {len(results[bucket])}")
        for item in results["drifted"]:
            print(f"\n--- DRIFTED: {item['path']} (main-tree: {item['main_tree_path']}) ---")
            if item.get("note"):
                print(f"[{item['note']}]")
            print(item["diff"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["text", "semantic"], default="text")
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        help="restrict to these rendered-relative paths only (e.g. for re-triaging a specific bucket)",
    )
    args = parser.parse_args()
    only = set(args.only) if args.only else None

    all_results = {template: run_template(template, args.mode, only) for template in ("agent", "tools")}

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
