"""Phase F2/F3 (DECISIONS.md DEC-087 item 1, DEC-088, DEC-090). The one
rendering engine for skeleton/ -- imported by both tools/verify_skeleton.py
(F2's own internal verification) and tools/instantiate_agent_project.py
(F3's real CLI). Deliberately factored out into its own module rather than
duplicated between the two: DEC-075's own root cause was exactly two
hand-maintained copies of one constant silently drifting apart, and this
module exists so that failure shape structurally cannot repeat here.

Substitution engine: a small regex-based renderer for exactly the
'${{ values.x }}' subset the skeleton actually uses today (plain value
substitution, no loops/conditionals/filters) -- deliberately not a Jinja2
dependency, since nothing in the skeleton needs more than this yet
(DEC-088's own reasoning).
"""

import json
import re
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKELETON_DIR = REPO_ROOT / "skeleton"
SCHEMA_PATH = REPO_ROOT / "template-schema.json"

# Phase G, Stage 3 (DEC-098/DEC-099/DEC-110, G6 Path B). The two
# instantiable templates this project ships, by --template flag value --
# the one place this pairing is declared, so tools/instantiate_agent_project.py
# and tools/verify_skeleton.py (already extended at Stage 2 to check both)
# can't drift the way DEC-075's own duplicated constant did.
TEMPLATES = {
    "agent": SKELETON_DIR,
    "tools": REPO_ROOT / "skeleton-tools",
}

PLACEHOLDER_RE = re.compile(r"\$\{\{\s*values\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def schema_path_for(skeleton_dir: Path) -> Path:
    """Derives the matching template-schema*.json for a given skeleton
    directory."""
    return skeleton_dir.parent / (
        "template-schema.json" if skeleton_dir.name == "skeleton" else "template-schema-tools.json"
    )


def resolve_template(template: str) -> tuple[Path, Path]:
    """Resolves a --template flag value ('agent' or 'tools') to its
    (skeleton_dir, schema_path) pair."""
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}; choose from {sorted(TEMPLATES)}")
    skeleton_dir = TEMPLATES[template]
    return skeleton_dir, schema_path_for(skeleton_dir)


def load_schema(schema_path: Path = SCHEMA_PATH) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def resolve_values(provided: dict, schema: dict | None = None) -> dict:
    """Applies template-schema.json's declared defaults for any optional
    property not supplied, and validates required properties are present
    and 'name' matches its pattern -- the same schema both F2's
    verification and F3's CLI validate against, never two copies of the
    same rules."""
    schema = schema or load_schema()
    props = schema["properties"]
    values = dict(provided)
    for key, spec in props.items():
        if key not in values and "default" in spec:
            values[key] = spec["default"]
    missing = [r for r in schema.get("required", []) if r not in values or not values[r]]
    if missing:
        raise ValueError(f"missing required parameter(s): {', '.join(missing)}")
    name_pattern = props.get("name", {}).get("pattern")
    if name_pattern and not re.match(name_pattern, values["name"]):
        raise ValueError(
            f"'name' value {values['name']!r} does not match required pattern "
            f"{name_pattern!r}"
        )
    max_len = props.get("name", {}).get("maxLength")
    if max_len and len(values["name"]) > max_len:
        raise ValueError(
            f"'name' value {values['name']!r} exceeds maxLength={max_len} "
            f"(kept short so every derived namespace name stays under "
            f"Kubernetes' 63-char limit -- see template-schema.json)"
        )
    return values


def render_text(text: str, values: dict) -> str:
    def _sub(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(
                f"skeleton references '${{{{ values.{key} }}}}' but no such key "
                f"exists in template-schema.json / the supplied values -- schema "
                f"and skeleton have drifted apart"
            )
        return values[key]

    return PLACEHOLDER_RE.sub(_sub, text)


def render_skeleton(dest: Path, values: dict, skeleton_dir: Path = SKELETON_DIR) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    for src_path in skeleton_dir.rglob("*"):
        rel = src_path.relative_to(skeleton_dir)
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


def sweep_for_literal(root: Path, literal: str) -> list[str]:
    hits = []
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if literal in text:
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
