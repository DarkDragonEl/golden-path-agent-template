"""Step 4c copies the blueprint's `main` into the in-cluster Gitea.

Gitea refuses a push from a shallow clone ("shallow update not allowed"),
so the clone that feeds that push must carry full history. This runs the
script's own clone line against a local source repository, adds the
allowedHosts-style commit the script adds, and pushes to a default bare
repository -- real git, no cluster, no network.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO_ROOT / "scripts" / "bootstrap.sh"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.test"]


def _clone_line() -> str:
    match = re.search(r'^\s*(git clone [^\n]*"\$BLUEPRINT_REPO_URL"[^\n]*)$', BOOTSTRAP.read_text(), re.M)
    assert match, "the mirror clone line is not in scripts/bootstrap.sh"
    return match.group(1)


def _git(cwd, *args):
    return subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True, text=True)


def test_mirror_clone_can_be_pushed_to_a_server_that_refuses_shallow_updates(tmp_path):
    src = tmp_path / "upstream"
    src.mkdir()
    _git(src, "init", "-q", "-b", "main")
    for i in range(3):
        (src / "template.yaml").write_text(f"allowedHosts:\n  - gitea.example.com\n# {i}\n")
        _git(src, "add", "template.yaml")
        _git(src, "commit", "-q", "-m", f"c{i}")
    dest = tmp_path / "gitea.git"
    _git(tmp_path, "init", "-q", "--bare", str(dest))

    mirror = tmp_path / "mirror"
    mirror.mkdir()
    subprocess.run(
        ["bash", "-c", _clone_line()],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "BLUEPRINT_REPO_URL": f"file://{src}",
            "MIRROR_DIR": str(mirror),
            "HOME": str(tmp_path),
        },
        check=True,
        capture_output=True,
    )
    work = mirror / "src"
    (work / "template.yaml").write_text("allowedHosts:\n  - gitea.cluster.test\n")
    _git(work, "commit", "-q", "-am", "allowedHosts")

    push = subprocess.run(
        [*GIT, "push", "-q", "--force", str(dest), "HEAD:main"],
        cwd=work,
        capture_output=True,
        text=True,
    )
    assert push.returncode == 0, push.stderr
    assert _git(dest, "rev-list", "--count", "main").stdout.strip() == "4"
