"""DEC-147: every kustomize tree must build -- the blueprint's own
(deploy/, adapters/, platform/) and every rendered template's (skeleton/,
skeleton-tools/). A skeleton overlay that only breaks after rendering
(the old demo-prod approval-config merge) is invisible to every other
check, so this renders each template exactly as tools/verify_skeleton.py
does and builds every overlay it contains.

Needs a `kustomize` binary (or $KUSTOMIZE). Without one the test skips,
unless REQUIRE_KUSTOMIZE=1 -- the unit-tests Task sets that, so CI fails
rather than silently skipping. Never shells out to oc/kubectl.

Three kustomizations pull a remote GitHub base (the upstream Gitea and
Keycloak operator installs, and the skeleton's copy), which kustomize
fetches with `git`. The unit-tests Task's image has no git, so those
builds are skipped there, with a warning naming each one -- but only when
git really is absent AND kustomize's error is exactly the missing-git one.
Any other build error still fails.
"""

import os
import shutil
import warnings
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


MISSING_GIT_ERROR = "no 'git' program on path"


def _build(kustomize: str, overlay: Path, env: dict | None = None) -> list[dict] | None:
    """Builds one overlay. Returns None (not built) only for a remote base
    on a machine without git; every other failure is an assertion."""
    result = subprocess.run([kustomize, "build", str(overlay)], capture_output=True, text=True, env=env)
    if result.returncode != 0:
        path = (env or os.environ).get("PATH")
        if MISSING_GIT_ERROR in result.stderr and shutil.which("git", path=path) is None:
            return None
        raise AssertionError(f"kustomize build {overlay} failed:\n{result.stderr}")
    docs = [d for d in yaml.safe_load_all(result.stdout) if d]
    assert docs, f"kustomize build {overlay} rendered no objects"
    return docs


def _build_all(kustomize: str, dirs: list[Path], label: str) -> None:
    not_built = [d for d in dirs if _build(kustomize, d) is None]
    if not_built:
        warnings.warn(f"{label}: no git on PATH, remote base not built: {[str(d) for d in not_built]}")
    assert len(not_built) < len(dirs), f"{label}: nothing was built"


def test_blueprint_overlays_build():
    kustomize = _kustomize()
    dirs = [d for tree in BLUEPRINT_TREES for d in _buildable_dirs(REPO_ROOT / tree)]
    assert dirs, "found no kustomizations to build"
    _build_all(kustomize, dirs, "blueprint")


@pytest.mark.parametrize("target", TARGETS, ids=[t["label"] for t in TARGETS])
def test_rendered_template_overlays_build(target, tmp_path):
    kustomize = _kustomize()
    rendered = tmp_path / "rendered"
    render_skeleton(rendered, target["test_values"], skeleton_dir=target["skeleton_dir"])
    dirs = _buildable_dirs(rendered)
    assert any("deploy" in d.relative_to(rendered).parts for d in dirs), \
        f"{target['label']}: rendered output has no kustomizations under deploy/"
    _build_all(kustomize, dirs, target["label"])


def _no_git_env(tmp_path: Path, kustomize: str) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "kustomize").symlink_to(Path(shutil.which(kustomize) or kustomize).resolve())
    return {**os.environ, "PATH": str(bindir)}


def test_remote_base_without_git_is_not_built(tmp_path):
    kustomize = _kustomize()
    overlay = tmp_path / "remote"
    overlay.mkdir()
    (overlay / "kustomization.yaml").write_text(
        "resources:\n  - github.com/keycloak/keycloak-k8s-resources/kubernetes?ref=26.7.2\n"
    )
    assert _build(kustomize, overlay, env=_no_git_env(tmp_path, kustomize)) is None


def test_other_build_errors_still_fail_without_git(tmp_path):
    kustomize = _kustomize()
    overlay = tmp_path / "broken"
    overlay.mkdir()
    (overlay / "kustomization.yaml").write_text("resources:\n  - does-not-exist.yaml\n")
    with pytest.raises(AssertionError, match="kustomize build"):
        _build(kustomize, overlay, env=_no_git_env(tmp_path, kustomize))
