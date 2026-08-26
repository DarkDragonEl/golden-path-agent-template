# G6 follow-up — make rendered GitOps/promotion content Gitea-aware: session report

Branch: `feature/g6-gitops-gitea-aware` (git worktree, not merged, not
pushed). Closes `DEC-111`'s named gap: the rendered skeleton's own
GitOps/promotion content was still hardcoded to GitHub, genuinely wrong
once a real two-repo, Gitea-hosted publish exists.

## Scope found to be larger than the gap's original framing — both real, both fixed

The original framing named two problems (ArgoCD `repoURL`,
`open-promotion-pr.yaml`'s GitHub API calls). Investigation found the real
scope was bigger, all one root cause (DEC-111's two-repo split physically
relocated `deploy/` out of the source repo into a separate `<repoName>-gitops`
repo, dropping the `deploy/` prefix there):

1. **`repoURL`** (4 `Application` manifests + `project.yaml`'s `sourceRepos`)
   — pointed at the *source* repo on GitHub. Now points at
   `${{ values.gitHost }}/${{ values.repoOwner }}/${{ values.repoName }}-gitops.git`.
2. **`path:` fields in the same 4 `Application` manifests** — still carried
   the `deploy/` prefix (`deploy/argocd/apps`, `deploy/kustomize/overlays/*`)
   even though the GitOps repo drops it at its own root. Not named in the
   original framing; found live by actually reading the manifests, not
   assumed clean. Fixed: `argocd/apps`, `kustomize/overlays/*`.
3. **`open-promotion-pr.yaml`'s own working assumption was structurally
   broken, not just hostname-wrong** (both `skeleton/` and `skeleton-tools/`
   have this file, byte-identical, both fixed identically). The Task edits
   `deploy/kustomize/base/kustomization.yaml` **inside the pipeline's own
   already-checked-out source-repo workspace** — but that file doesn't
   exist there at all anymore once the two-repo split is real (it's in the
   *separate* GitOps repo). Fixed by rewriting the Task to clone the
   `<repoName>-gitops` repo into its own scratch subdirectory of the shared
   workspace, edit/commit/push there, and open the PR against Gitea's own
   API (`token` auth scheme, same request-body shape as GitHub's
   `title`/`head`/`base`/`body` — confirmed live, not assumed).
4. **`pipeline.yaml`'s own `repo-url` default** (both templates) was also
   hardcoded to `github.com` — the *source* repo's own fetch URL, a third
   spot with the identical root cause. Fixed for consistency; left
   unfixed would have been a confusing half-fix once the other two were
   Gitea-aware.
5. **A connected, pre-existing bug that would have made this fix wrong in
   the common case**: `tools/instantiate_agent_project.py --publish`
   resolved `repoOwner`/`repoName` to their real publish target *after*
   `render_skeleton()` was already called — so whenever a caller didn't
   pass `--repoOwner`/`--repoName` explicitly (the common case), the
   rendered content's own `${{ values.repoOwner }}`/`${{ values.repoName }}`
   references stayed as the literal `REPLACE_ME_*` placeholder strings,
   while the *actual* Gitea org/repo used for publish was something else
   entirely. This predates this session (present since `DEC-111`) and
   would have made every fix above silently wrong in the default,
   no-explicit-flags case. Fixed: resolution now happens before
   rendering, so the rendered content is always self-consistent with the
   real publish target.

## The real design question, resolved with cited support, not guessed

**Decision: scaffolded projects target Gitea exclusively — not
"support both GitHub and Gitea."** `DEC-098`'s own text already
distinguishes the two: "the external copy \[GitHub\] remains the public
upstream of the anonymized blueprint" — i.e. GitHub is where *this
blueprint repo itself* lives, not a legitimate publish target for a
*scaffolded child project*. The pre-Gitea GitHub hardcoding in
`argocd/*.yaml`/`open-promotion-pr.yaml`/`pipeline.yaml` predates Gitea
entirely (traces to Phase C, `DEC-025`/`DEC-037`) — it was never a
deliberate "support GitHub too" decision, just the only option that
existed at the time. Went Gitea-only rather than adding a
`gitProvider`-style conditional (GitHub vs. Gitea branches in the same
Task script) for two reasons: (a) it's the option actually supported by
a recorded decision, not invented; (b) `DEC-105`'s own reasoning against
config-gated dual-behavior (a structural default over a flag-driven
branch, for a platform whose whole posture is structural gating) applies
here too, by the same logic, even though this isn't a security surface
the way `DEC-105`'s own case was.

## New schema parameter: `gitHost`

Added to both `template-schema.json` and `template-schema-tools.json`.
Real default (this blueprint's own live Platform Foundation Gitea host),
not a `REPLACE_ME_*` placeholder — unlike `repoOwner`/`repoName`, there's
no reason to force an explicit value before this is usable, since every
scaffolded project shares the same one Platform Foundation Gitea
instance. `repoName`'s GitOps repo name is *not* an independent
parameter — always `<repoName>-gitops`, matching `tools/gitea_publish.py`'s
own already-proven convention (`DEC-111`), so the two names can never
drift apart. `instantiate_agent_project.py`'s own prior `DEFAULT_GITEA_HOST`
Python constant (and the now-redundant `--gitea-host` CLI flag) were
removed entirely once the schema had this same value with a real default
-- one source of truth, not a second copy of the same literal
(`DEC-075`'s own duplicated-constant lesson, applied again).

## Verified live, with real evidence, not just code review

1. `tools/verify_skeleton.py` (extended with `gitHost` test values for
   both targets) — clean, both templates, 179 + 38 files.
2. Full pytest suite (container, matching CI's own method): 253 passed,
   1 skipped — unchanged.
3. **Real end-to-end publish**, using the live, already-proven
   `golden-path-agent-scaffolder` credential (`DEC-100`): rendered and
   published a real test project (`g6-gitops-fix-test` +
   `-gitops`) to the real Platform Foundation Gitea instance.
4. **Fetched the published content back from Gitea's own API** (not just
   "push succeeded"): the GitOps repo's own `argocd/application-root.yaml`
   correctly self-references the GitOps repo (`.../g6-gitops-fix-test-gitops.git`,
   not GitHub, not the source repo) with path `argocd/apps` (no `deploy/`
   prefix); the GitOps repo's own root correctly has `argocd`/`kustomize`/
   `otel` directly (no `deploy/` wrapper); the source repo's own
   `pipeline.yaml` correctly points its `repo-url` default at the *source*
   repo, not GitOps.
5. **Confirmed the resolution-order fix works**: publishing without
   explicit `--repoOwner`/`--repoName` now bakes the *real* resolved
   values into the rendered content (verified: `pipeline.yaml`'s
   `repo-url` default contained the real org/repo name, not
   `REPLACE_ME_repoOwner`/`REPLACE_ME_repoName`).
6. **Real, live test of the rewritten `open-promotion-pr.yaml` logic**:
   cloned the real published GitOps repo into a scratch directory (the
   same pattern the Task itself now uses), edited
   `kustomize/base/kustomization.yaml`'s digest, committed, pushed a
   `promote/*` branch, and opened a real PR via Gitea's own API
   (`token` auth) — **PR #1 created successfully**
   (`.../g6-gitops-fix-test-gitops/pulls/1`), confirming Gitea's
   PR-creation endpoint accepts the identical request-body shape
   (`title`/`head`/`base`/`body`) as GitHub's, not assumed from Gitea's
   own "GitHub-compatible API" reputation.
7. **All test artifacts cleaned up**: both test repos (source + gitops,
   which also removes the test PR) deleted via the admin credential and
   confirmed `404`; all local scratch clones, rendered directories, and
   credential files removed.

## What was NOT attempted, per this session's own scope

- Live-cluster verification of this fix running inside an actual Tekton
  `PipelineRun` (as opposed to a direct simulation of the same git/API
  calls the Task's script performs) — the simulation exercises the exact
  same operations the Task would, but a real `PipelineRun` (with a real
  `${{ values.name }}-gitea-token` Secret provisioned into a real
  `${{ values.name }}-ci` namespace) was not run, since per-project CI
  namespace/RBAC bootstrap for a scaffolded child project doesn't exist
  as an automated mechanism yet (`DEC-111`'s own named, separate gap).
- The `feature/g6-scaffolder-plugin-spike` stream's own work (portal-wizard
  publish) — not coordinated with directly, per instruction, but this
  session's fix makes sense regardless of which publish path (CLI or a
  future portal wizard) produces the two-repo Gitea structure, since both
  would produce byte-identical repo content.
- A full `docs/*.md` consistency pass referencing the old GitHub-based
  promotion credential (`docs/phase-c-runbook.md §3`, referenced only in
  code comments here, not itself a rendered skeleton file) — out of this
  session's scope, named for a future docs-reconciliation pass.

## Drafted decision entry (numbered as a placeholder — land at the
coordinating session's own next available `DEC-NNN`)

```
## DEC-1xx — G6 follow-up: rendered GitOps/promotion content made
Gitea-aware, closing DEC-111's named gap; scaffolded projects target
Gitea exclusively (not GitHub), per DEC-098's own already-recorded
framing

**Context**: `DEC-111` (G6 Path B) found and named a real gap: the
published GitOps repo's own ArgoCD/promotion-PR references were still
hardcoded to GitHub. This entry closes it -- and found the real scope
was larger than "wrong hostname."

**What changed, all one root cause (DEC-111's two-repo split relocated
`deploy/` into a separate `<repoName>-gitops` repo, dropping the
`deploy/` prefix there)**:
1. All four `Application` manifests' `repoURL` (+ `project.yaml`'s
   `sourceRepos`) now point at the GitOps repo
   (`${{ values.gitHost }}/${{ values.repoOwner }}/${{ values.repoName }}-gitops.git`),
   not the source repo on GitHub.
2. Those same manifests' `path:` fields had their own `deploy/` prefix
   stripped (`argocd/apps`, `kustomize/overlays/*`) -- found live, not in
   the gap's original framing.
3. `open-promotion-pr.yaml` (byte-identical in `skeleton/` and
   `skeleton-tools/`, both fixed) was structurally broken, not just
   hostname-wrong: it edited `deploy/kustomize/base/kustomization.yaml`
   inside the pipeline's own already-checked-out source-repo workspace --
   that file doesn't exist there anymore once split. Rewritten to clone
   the separate GitOps repo into its own scratch subdirectory, edit/
   commit/push there, and open the PR via Gitea's own API.
4. `pipeline.yaml`'s own `repo-url` default (both templates) was also
   GitHub-hardcoded -- a third spot, same root cause, fixed for
   consistency.
5. A connected, pre-existing bug found and fixed: `--publish` resolved
   `repoOwner`/`repoName` to their real target *after* rendering, so the
   common no-explicit-flags case baked literal `REPLACE_ME_*` strings
   into rendered content while publishing somewhere else entirely.
   Resolution now happens before rendering.

**Design decision, resolved with cited support (DEC-098's own text),
not guessed**: scaffolded projects target Gitea exclusively, not "both
GitHub and Gitea" -- GitHub was always this blueprint repo's own public
upstream (DEC-098's own phrasing), never a legitimate scaffolded-child
target; the pre-Gitea hardcoding predates Gitea entirely and was never a
deliberate dual-support decision.

**New schema parameter**: `gitHost` (both `template-schema.json` and
`template-schema-tools.json`), real default (not a placeholder) since
every scaffolded project shares one Platform Foundation Gitea instance.
The GitOps repo name stays derived (`<repoName>-gitops`), not an
independent parameter, matching `tools/gitea_publish.py`'s own
convention. `instantiate_agent_project.py`'s own separate
`DEFAULT_GITEA_HOST` constant and the now-redundant `--gitea-host` flag
were removed -- one source of truth, not two copies of the same literal
(`DEC-075`'s lesson, applied again).

**Verified live, with real evidence**: `verify_skeleton.py` clean on both
templates; full suite 253/1 skipped unchanged; a real end-to-end publish
to the live Gitea instance, with published content fetched back and
confirmed correct (GitOps repo self-references itself, correct paths, no
`deploy/` prefix; source repo's own pipeline points at the source repo);
the resolution-order fix confirmed working in the no-explicit-flags case;
a real, live simulation of the rewritten `open-promotion-pr.yaml` logic
-- clone, edit, commit, push, and a genuine PR opened via Gitea's API
(PR #1, confirmed created) -- proving Gitea's PR-creation endpoint
accepts the same request shape as GitHub's, not assumed. All test
artifacts (two repos, one PR, all local scratch/credential files)
cleaned up and confirmed gone.

**Not attempted, per this session's own scope**: a real Tekton
`PipelineRun` exercising this fix end-to-end (the underlying per-project
CI namespace/RBAC bootstrap this would need doesn't exist yet, `DEC-111`'s
own separate named gap); coordination with the concurrent portal-wizard
publish spike (not needed -- this fix is publish-path-agnostic); a
`docs/*.md` consistency pass for the old GitHub-based credential
references in prose comments.

**Status**: `DEC-111`'s named gap is closed, with a larger real scope
than its own framing anticipated, all verified live.
```
