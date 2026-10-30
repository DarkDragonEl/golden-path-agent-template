"""DEC-147: every kustomize tree must build -- the blueprint's own
(deploy/, adapters/, platform/) and every rendered template's (skeleton/,
skeleton-tools/). A skeleton overlay that only breaks after rendering
(the old demo-prod approval-config merge) is invisible to every other
check, so this renders each template exactly as tools/verify_skeleton.py
does and builds every overlay it contains.

Needs a `kustomize` binary (or $KUSTOMIZE). Without one the test skips,
unless REQUIRE_KUSTOMIZE=1 -- the unit-tests Task sets that, so CI fails
rather than silently skipping. Never shells out to oc/kubectl.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools"))

from skeleton_renderer import render_skeleton  # noqa: E402
from verify_skeleton import TARGETS  # noqa: E402

BLUEPRINT_TREES = ("deploy", "adapters", "platform")


def _kustomize() -> str:
    binary = os.environ.get("KUSTOMIZE") or shutil.which("kustomize")
    if not binary:
        if os.environ.get("REQUIRE_KUSTOMIZE") == "1":
            pytest.fail("REQUIRE_KUSTOMIZE=1 but no kustomize binary found (set $KUSTOMIZE or put it on PATH)")
        pytest.skip("no kustomize binary on PATH (set REQUIRE_KUSTOMIZE=1 to make this a failure)")
    return binary


def _buildable_dirs(root: Path) -> list[Path]:
    """Every directory under root holding a Kustomization -- Components are
    excluded, since they only build as part of a parent."""
    dirs = []
    for kfile in sorted(root.rglob("kustomization.yaml")):
        doc = yaml.safe_load(kfile.read_text(encoding="utf-8")) or {}
        if doc.get("kind") == "Component":
            continue
        dirs.append(kfile.parent)
    return dirs


def _build(kustomize: str, overlay: Path) -> list[dict]:
    result = subprocess.run([kustomize, "build", str(overlay)], capture_output=True, text=True)
    assert result.returncode == 0, f"kustomize build {overlay} failed:\n{result.stderr}"
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    assert docs, f"kustomize build {overlay} rendered no objects"
    return docs


def test_blueprint_overlays_build():
    kustomize = _kustomize()
    dirs = [d for tree in BLUEPRINT_TREES for d in _buildable_dirs(REPO_ROOT / tree)]
    assert dirs, "found no kustomizations to build"
    for overlay in dirs:
        _build(kustomize, overlay)


@pytest.mark.parametrize("target", TARGETS, ids=[t["label"] for t in TARGETS])
def test_rendered_template_overlays_build(target, tmp_path):
    kustomize = _kustomize()
    rendered = tmp_path / "rendered"
    render_skeleton(rendered, target["test_values"], skeleton_dir=target["skeleton_dir"])
    dirs = _buildable_dirs(rendered)
    assert any("deploy" in d.relative_to(rendered).parts for d in dirs), \
        f"{target['label']}: rendered output has no kustomizations under deploy/"
    for overlay in dirs:
        _build(kustomize, overlay)
