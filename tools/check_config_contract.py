"""Post-Checkpoint-C backlog item 3 (DECISIONS.md DEC-035, scope extended
to placeholder detection at the Checkpoint C closure review).

Two independent checks, run together, no cluster access needed:

1. KEY COMPLETENESS. `agent/config.py` reads some env vars via a bare
   `_env(name)` call with no default argument at all -- for these, an
   absent deployment surface isn't "wrong but running," it's silently
   `None`. Extracted directly from `agent/config.py`'s own source (AST,
   not a hand-maintained list -- DEC-035's own pattern note: a
   hand-maintained list is exactly what went stale twice already), this
   check verifies every such key is either declared (as a literal, any
   value) by every deployment surface below, or named on
   `KNOWN_SECRET_SHADOWED` with a stated reason.

2. PLACEHOLDER DETECTION. `deploy/argocd/apps/*.yaml` names exactly which
   overlay paths a GitOps-synced `Application` consumes precisely as
   committed (no pipeline injection step exists for these -- DEC-042's
   `REGISTRY_PLACEHOLDER` finding). Every manifest under those overlay
   paths, plus `deploy/kustomize/base/` (which every overlay builds on),
   is scanned for placeholder-shaped values (`REPLACE_WITH_*`,
   `*_PLACEHOLDER`). Any match not named on `KNOWN_PLACEHOLDERS` with a
   stated reason is a finding.

Both allow-lists use the same named/dated/rationale-carrying convention
already established elsewhere in this repo (`eval/cli.py::KNOWN_GAP_TOLERANCES`,
this script's own sibling `tools/check_policy_sync.py`) -- an exception
is recorded, not silent.

Usage: `python tools/check_config_contract.py`. Exit 1 with the finding(s)
printed on any undocumented gap; exit 0 otherwise.
"""

import ast
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PY = REPO_ROOT / "agent" / "config.py"
ARGOCD_APPS_DIR = REPO_ROOT / "deploy" / "argocd" / "apps"
KUSTOMIZE_BASE = REPO_ROOT / "deploy" / "kustomize" / "base"
KUSTOMIZE_OVERLAYS = REPO_ROOT / "deploy" / "kustomize" / "overlays"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
DEV_SH = REPO_ROOT / "scripts" / "dev.sh"

# --- Check 1: known, documented exceptions -----------------------------
# (surface, key) -> reason. A surface is either an overlay directory name
# under deploy/kustomize/overlays/, or the literal "base".
KNOWN_SECRET_SHADOWED = {
    ("demo-prod", "MODEL_FALLBACK_API_BASE_URL"): (
        "demo-prod is ArgoCD-synced with selfHeal: true -- no apply-time "
        "injection point exists (unlike ephemeral-test's pipeline Task), "
        "so the real value comes from a third golden-path-agent-secrets "
        "copy instead, shadowing the ConfigMap via envFrom ordering. "
        "DECISIONS.md DEC-039, docs/phase-c-runbook.md section 2."
    ),
    ("demo-prod", "MODEL_FALLBACK_NAME"): (
        "Same mechanism and reason as MODEL_FALLBACK_API_BASE_URL above."
    ),
    ("demo-prod", "APPROVAL_OIDC_CLIENT_SECRET"): (
        "DECISIONS.md DEC-062: base/configmap.yaml declares a safe "
        "'not-needed' placeholder (satisfies completeness everywhere); "
        "demo-prod's real value comes from golden-path-agent-secrets "
        "instead, provisioned by pipelines/bootstrap/provision-identity-"
        "secrets.sh (DEC-059) -- same shadowing mechanism as "
        "MODEL_FALLBACK_API_BASE_URL above, documented here for the "
        "identical reason even though base's own placeholder already "
        "satisfies the completeness check on its own."
    ),
    ("demo-prod", "MCP_AUTH_TOKEN"): (
        "Same mechanism and reason as APPROVAL_OIDC_CLIENT_SECRET above."
    ),
}

# --- Check 2: known, documented placeholder exceptions -----------------
# (relative file path, matched string) -> reason.
KNOWN_PLACEHOLDERS = {
    ("deploy/kustomize/base/configmap.yaml", "placeholder-model"): (
        "MODEL_NAME's committed default -- base is consumed by demo-prod "
        "as-is (Secret-shadowed, see KNOWN_SECRET_SHADOWED's own reasoning "
        "for the sibling MODEL_FALLBACK_* keys; MODEL_NAME/MODEL_API_BASE_URL "
        "are shadowed the identical way, just not yet needing their own "
        "KNOWN_SECRET_SHADOWED entry since they always had a hardcoded "
        "default, unlike the fallback pair)."
    ),
    ("deploy/kustomize/base/configmap.yaml", "placeholder-fallback-model"): (
        "MODEL_FALLBACK_NAME's committed default -- same reasoning."
    ),
}

# Placeholder-shaped VALUE patterns. Deliberately narrow (not "localhost"
# or "example.com", which are legitimate RFC1918/RFC2606-style
# placeholders in overlays that ARE pipeline-injected, e.g.
# ephemeral-test -- see docs/environments.md's "What's still a
# placeholder" section) -- this check is specifically about the
# REGISTRY_PLACEHOLDER/REPLACE_WITH_* family: an unresolved sentinel with
# no injection mechanism at all for the environment that would consume it.
PLACEHOLDER_PATTERNS = [
    re.compile(r"REPLACE_WITH_[A-Z0-9_]+"),
    re.compile(r"\b[A-Za-z0-9][A-Za-z0-9-]*_PLACEHOLDER\b"),
    re.compile(r"\bPLACEHOLDER[A-Za-z0-9_-]*\b"),
    re.compile(r"\bplaceholder-[a-z0-9-]+\b"),
]


def _extract_no_default_env_keys() -> set[str]:
    """AST-parse agent/config.py for every bare `_env("KEY")` call -- one
    positional arg, no default -- the class of key with no safe fallback
    at all. `_env_int`/`_env_str` always take a hard_default (3rd
    positional), so they're structurally excluded from this class."""
    tree = ast.parse(CONFIG_PY.read_text())
    keys = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "_env"):
            continue
        if len(node.args) != 1 or node.keywords:
            continue  # has a default, positional or keyword -- not this class
        (name_arg,) = node.args
        if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
            keys.add(name_arg.value)
    return keys


def _env_example_keys() -> set[str]:
    keys = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def _dev_sh_keys() -> set[str]:
    # `-e KEY="${KEY:-default}"` / `-e KEY=value` style flags only --
    # dev.sh's other -e-shaped text (comments, non-env args) won't match
    # this specific `-e IDENT=` shape.
    return set(re.findall(r'-e\s+([A-Z][A-Z0-9_]*)=', DEV_SH.read_text()))


def _configmap_generator_keys(kustomization_path: Path) -> set[str]:
    doc = yaml.safe_load(kustomization_path.read_text())
    keys = set()
    for gen in doc.get("configMapGenerator") or []:
        for literal in gen.get("literals") or []:
            keys.add(literal.split("=", 1)[0].strip())
    return keys


def check_key_completeness() -> list[str]:
    required = _extract_no_default_env_keys()
    problems = []

    base_configmap = yaml.safe_load((KUSTOMIZE_BASE / "configmap.yaml").read_text())
    base_keys = set(base_configmap["data"].keys())

    # (display name, KNOWN_SECRET_SHADOWED lookup key, declared keys) --
    # the lookup key is None for surfaces KNOWN_SECRET_SHADOWED can never
    # exempt (.env.example/scripts/dev.sh are local-dev-only, not a
    # Kustomize tree with an inheritance chain).
    surfaces = [
        (".env.example", None, _env_example_keys()),
        ("scripts/dev.sh", None, _dev_sh_keys()),
        ("base (deploy/kustomize/base/configmap.yaml)", "base", base_keys),
    ]
    for overlay_dir in sorted(p for p in KUSTOMIZE_OVERLAYS.iterdir() if p.is_dir()):
        kfile = overlay_dir / "kustomization.yaml"
        if kfile.exists():
            # An overlay's own configMapGenerator uses `behavior: merge`
            # (deploy/kustomize/base/kustomization.yaml's own comment) --
            # a key present in base and never overridden is still present
            # in what actually gets applied, with base's own value. Only
            # flag a key truly absent from BOTH -- an overlay is never
            # required to redeclare a key it has no reason to override.
            declared = base_keys | _configmap_generator_keys(kfile)
            surfaces.append((f"overlay:{overlay_dir.name}", overlay_dir.name, declared))

    for surface_name, shadow_lookup_key, declared in surfaces:
        for key in sorted(required):
            if key in declared:
                continue
            if shadow_lookup_key is not None and (shadow_lookup_key, key) in KNOWN_SECRET_SHADOWED:
                continue
            problems.append(
                f"{key!r} (no default in agent/config.py) is not declared by {surface_name} "
                f"and is not on KNOWN_SECRET_SHADOWED"
            )
    return problems


def _gitops_synced_overlay_paths() -> set[Path]:
    """Every overlay path a deploy/argocd/apps/*.yaml Application's own
    source.path actually points at -- these, plus base (every overlay
    builds on it), are consumed exactly as committed, with no pipeline
    injection step. Derived from the live Application manifests, not a
    hand-maintained list -- self-updating if a new one is added."""
    paths = {KUSTOMIZE_BASE}
    for app_file in sorted(ARGOCD_APPS_DIR.glob("*.yaml")):
        doc = yaml.safe_load(app_file.read_text())
        rel_path = doc.get("spec", {}).get("source", {}).get("path")
        if rel_path:
            paths.add(REPO_ROOT / rel_path)
    return paths


def check_placeholder_values() -> list[str]:
    problems = []
    for overlay_path in sorted(_gitops_synced_overlay_paths()):
        for manifest in sorted(overlay_path.glob("*.yaml")):
            rel = manifest.relative_to(REPO_ROOT).as_posix()
            text = manifest.read_text()
            for pattern in PLACEHOLDER_PATTERNS:
                for match in pattern.finditer(text):
                    value = match.group(0)
                    if (rel, value) in KNOWN_PLACEHOLDERS:
                        continue
                    line_no = text.count("\n", 0, match.start()) + 1
                    problems.append(
                        f"{rel}:{line_no}: unresolved placeholder-shaped value {value!r}, "
                        f"consumed as-committed by a GitOps-synced Application, "
                        f"not on KNOWN_PLACEHOLDERS"
                    )
    return problems


def main() -> int:
    key_problems = check_key_completeness()
    placeholder_problems = check_placeholder_values()
    problems = key_problems + placeholder_problems

    if problems:
        print("CONFIG-CONTRACT CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    required_count = len(_extract_no_default_env_keys())
    scanned_count = len(_gitops_synced_overlay_paths())
    print(
        f"config-contract check OK -- {required_count} no-default key(s) accounted for "
        f"across every deployment surface; {scanned_count} GitOps-synced-as-committed "
        f"path(s) scanned for unresolved placeholders, none found undocumented"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
