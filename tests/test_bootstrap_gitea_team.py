"""Step 4c's Gitea team for the portal's scaffolder account. The portal's
publish step creates two repos in the projects org as that account, so the
team must be allowed to create org repos and write to every repo there.
The spec is applied on create and again on every run (an existing team is
brought up to date), and the step fails closed if Gitea does not report
both settings back."""

import json
import re
from pathlib import Path

BOOTSTRAP = (Path(__file__).resolve().parent.parent / "scripts" / "bootstrap.sh").read_text()


def _team_spec() -> dict:
    match = re.search(r"^\s*GITEA_TEAM_SPEC='(\{.*\})'$", BOOTSTRAP, re.M)
    assert match, "GITEA_TEAM_SPEC is not defined in scripts/bootstrap.sh"
    return json.loads(match.group(1))


def test_team_can_create_and_write_org_repos():
    spec = _team_spec()
    assert spec["can_create_org_repo"] is True
    assert spec["includes_all_repositories"] is True
    assert spec["permission"] == "write"
    assert spec["units_map"] == {"repo.code": "write", "repo.pulls": "write"}


def test_spec_is_applied_on_create_and_on_every_run():
    create = BOOTSTRAP.index('gitea_api POST "/api/v1/orgs/${GITEA_ORG}/teams" "$GITEA_TEAM_SPEC"')
    patch = BOOTSTRAP.index('gitea_api PATCH "/api/v1/teams/${GITEA_TEAM_ID}" "$GITEA_TEAM_SPEC"')
    member = BOOTSTRAP.index('gitea_api PUT "/api/v1/teams/${GITEA_TEAM_ID}/members/${GITEA_SCAFFOLDER_USER}"')
    assert create < patch < member


def test_step_fails_closed_if_gitea_does_not_confirm():
    check = re.search(
        r"jq -e '\.can_create_org_repo == true and \.includes_all_repositories == true'.*?\n(.*?)\n\s*fi",
        BOOTSTRAP,
        re.S,
    )
    assert check, "no read-back check of the team settings"
    assert "exit 1" in check.group(1)
