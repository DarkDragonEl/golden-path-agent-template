"""Phase G, Stage 3 (DECISIONS.md DEC-098/DEC-099/DEC-110, G6 Path B).
Publishes a locally-rendered scaffolded project to Gitea as two
repositories -- a source+pipeline repo and a separate GitOps repo -- per
the owner's own two-repo decision (DEC-098/DEC-099), matching the
verified redhat-ai-dev/ai-lab-template reference pattern.

Uses the Platform Foundation's own Gitea instance (G1, DEC-100) and its
scoped `golden-path-agent-scaffolder` machine account for create/push --
never the admin account. Repo deletion (this module's own test cleanup,
never a normal publish operation) requires the admin credential, since
the scoped account cannot delete repos it does not own (DEC-100's own
live-proven finding, not re-derived here).

Deliberately stdlib-only (urllib.request, subprocess), matching this
project's own tools/ convention (tools/diagnose_tool_call_raw_output.py,
tools/query_traces.py) rather than adding a new HTTP dependency for a
handful of REST calls.

KNOWN, NAMED GAP (see reports/feature-g6-cli-publish.md for the full
account): splitting `deploy/` out into its own repo makes the *rendered
skeleton's own* `deploy/argocd/*.yaml` (repoURL/path) and
`pipelines/tasks/open-promotion-pr.yaml` (hardcoded `github.com` API
calls) internally inconsistent with the two-repo, Gitea-hosted reality
this module actually publishes. Fixing that is real GitOps/pipeline
onboarding work, out of this session's explicit scope -- this module
only performs the split and publish; it does not rewrite the published
content to be self-consistent.
"""

import base64
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

GITOPS_SUBDIR = "deploy"


def _api_request(method: str, url: str, token: str | None = None,
                  basic_auth: tuple[str, str] | None = None,
                  json_body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(json_body).encode() if json_body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"token {token}")
    elif basic_auth:
        user, pw = basic_auth
        creds = base64.b64encode(f"{user}:{pw}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"raw": body.decode(errors="replace")}
        return exc.code, parsed


def create_repo(gitea_host: str, org: str, token: str, repo_name: str) -> tuple[bool, str]:
    """Creates a new, empty (auto_init=False) repo in the given org.
    Returns (created, clone_url) -- created=False if the repo already
    existed (idempotent re-run, this module's own explicit design choice:
    a re-run of a publish for the same project name should not fail
    outright, since the common case is a developer retrying after fixing
    an unrelated error)."""
    status, body = _api_request(
        "POST", f"https://{gitea_host}/api/v1/orgs/{org}/repos", token=token,
        json_body={"name": repo_name, "private": False, "auto_init": False},
    )
    if status == 201:
        return True, body["clone_url"]
    if status == 409:
        status2, body2 = _api_request(
            "GET", f"https://{gitea_host}/api/v1/repos/{org}/{repo_name}", token=token,
        )
        if status2 == 200:
            return False, body2["clone_url"]
        raise RuntimeError(
            f"repo {org}/{repo_name} already exists but could not be read back: {status2} {body2}"
        )
    raise RuntimeError(f"failed to create repo {org}/{repo_name}: {status} {body}")


def delete_repo(gitea_host: str, org: str, repo_name: str, admin_user: str, admin_password: str) -> None:
    """Deletes a repo. Requires the ADMIN credential -- test-cleanup only,
    never part of a normal publish flow."""
    status, body = _api_request(
        "DELETE", f"https://{gitea_host}/api/v1/repos/{org}/{repo_name}",
        basic_auth=(admin_user, admin_password),
    )
    if status not in (204, 404):
        raise RuntimeError(f"failed to delete repo {org}/{repo_name}: {status} {body}")


def push_directory(local_dir: Path, clone_url: str, token: str, username: str) -> None:
    """git-inits and pushes the given directory's current contents to the
    repo's main branch. The token is embedded in the remote URL only for
    the duration of this call -- the .git directory (which would carry
    that URL in its config) is deleted immediately after, so no
    credential-bearing artifact survives this function."""
    authed_url = clone_url.replace("https://", f"https://{username}:{token}@", 1)

    def run(*args: str) -> None:
        subprocess.run(args, cwd=local_dir, check=True, capture_output=True, text=True)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.name", "golden-path-agent-scaffolder")
    run("git", "config", "user.email", "golden-path-agent-scaffolder@example.com")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "Initial scaffold")
    run("git", "push", "-q", authed_url, "main:main")
    shutil.rmtree(local_dir / ".git")


def split_rendered_tree(rendered_dir: Path, gitops_subdir: str = GITOPS_SUBDIR) -> tuple[Path, Path]:
    """Splits one rendered project directory into two new scratch trees:
    (source_dir, gitops_dir). Copies rather than moves -- rendered_dir
    itself is left untouched for the caller to inspect afterward.

    The GitOps repo's own top-level directory structure drops the
    redundant `deploy/` prefix (its content becomes kustomize/, argocd/,
    otel/ directly at the repo root) -- a repo whose entire purpose is
    deployment manifests doesn't need a directory named "deploy" inside
    it. Judgment call, not backed by a prior decision; documented here so
    it's visible, not just implied by the code."""
    source_dir = Path(tempfile.mkdtemp(prefix="gitea-publish-source-"))
    gitops_dir = Path(tempfile.mkdtemp(prefix="gitea-publish-gitops-"))
    gitops_src = rendered_dir / gitops_subdir

    for item in rendered_dir.iterdir():
        if item.name == gitops_subdir:
            continue
        dest = source_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    if gitops_src.exists():
        for item in gitops_src.iterdir():
            dest = gitops_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

    return source_dir, gitops_dir


def publish(rendered_dir: Path, *, gitea_host: str, org: str, token: str, username: str,
            repo_name: str, gitops_repo_name: str) -> dict:
    """End-to-end: split the rendered tree, create both repos (idempotent),
    push both. Returns a small result dict for the caller to report/verify
    against, rather than just printing -- keeps this function testable
    without scraping stdout."""
    source_dir, gitops_dir = split_rendered_tree(rendered_dir)
    try:
        source_created, source_clone_url = create_repo(gitea_host, org, token, repo_name)
        push_directory(source_dir, source_clone_url, token, username)

        gitops_created, gitops_clone_url = create_repo(gitea_host, org, token, gitops_repo_name)
        push_directory(gitops_dir, gitops_clone_url, token, username)
    finally:
        shutil.rmtree(source_dir, ignore_errors=True)
        shutil.rmtree(gitops_dir, ignore_errors=True)

    return {
        "source_repo": {"name": repo_name, "created": source_created, "clone_url": source_clone_url},
        "gitops_repo": {"name": gitops_repo_name, "created": gitops_created, "clone_url": gitops_clone_url},
    }
