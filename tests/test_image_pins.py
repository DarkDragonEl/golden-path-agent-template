"""DEC-146 (M21): one image, one digest. The approval image is pinned in
both deploy/kustomize/base/ and overlays/approval-platform/ (the shared
service's standalone overlay); a promotion that updated only one of them
let the shared service run a stale image unnoticed. Every kustomization
under deploy/ and adapters/ that pins a given image name must agree."""

from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pins():
    pins = defaultdict(dict)
    for tree in ("deploy", "adapters"):
        for kfile in sorted((REPO_ROOT / tree).rglob("kustomization.yaml")):
            doc = yaml.safe_load(kfile.read_text(encoding="utf-8")) or {}
            for image in doc.get("images") or []:
                if "digest" in image:
                    pins[image["name"]][str(kfile.relative_to(REPO_ROOT))] = (image.get("newName"), image["digest"])
    return pins


def test_every_image_pin_agrees_across_kustomizations():
    pins = _pins()
    assert pins, "no digest pins found"
    drift = {name: files for name, files in pins.items() if len(set(files.values())) > 1}
    assert not drift, f"same image pinned differently: {drift}"


def test_approval_image_is_pinned_where_open_promotion_pr_looks():
    files = set(_pins()["golden-path-agent-approval"])
    assert files == {
        "deploy/kustomize/base/kustomization.yaml",
        "deploy/kustomize/overlays/approval-platform/kustomization.yaml",
    }, files
