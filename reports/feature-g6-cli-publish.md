# G6 (Stage 3), Path B — CLI-first Gitea publish: session report

Branch: `feature/g6-cli-publish` (git worktree, not merged, not pushed). Per
`DEC-099`'s single-governance-owner rule, this branch does **not** touch
`DECISIONS.md`/`HANDOFF.md`/`PINS.md` — the drafted decision entry is at the
bottom of this report for the coordinating session to land at merge.

## Status against this session's scope

| Item | Status |
|---|---|
| Extend the CLI to publish to Gitea as two repos (source+pipeline, GitOps) | **DONE, verified live** |
| Handle the Tools Template gap named in `DEC-104` (`instantiate_agent_project.py` was hardcoded to the Agent Template) | **DONE** — `--template {agent,tools}` added; both templates render and publish |
| Real end-to-end instantiation + publish, verified against actual Gitea content | **DONE, twice** — once for each template |
| Idempotent re-run behavior | **DONE, verified live** (a second `create_repo` call against an existing repo returns `created=False` and the same `clone_url`, not an error) |
| Test repo cleanup | **DONE** — all four test repos (agent + gitops, tools + gitops) confirmed `404` after deletion |
| Full pipeline/ArgoCD auto-onboarding | **NOT attempted, per explicit scope instruction** |
| Rewriting the published content's own ArgoCD/promotion-PR references to be internally consistent with the two-repo, Gitea-hosted split | **NOT attempted — a real, significant, named gap, see below** |
| Live RHDH catalog registration of a published project's `Component` | **NOT attempted** — this session's own directive listed it as optional; kept out of scope to stay focused on the core publish mechanism |

## What was built

- **`tools/gitea_publish.py`** (new): `create_repo`/`delete_repo`/`push_directory`/`split_rendered_tree`/`publish`. Stdlib-only (`urllib.request`, `subprocess`), matching this project's own existing `tools/` convention (`diagnose_tool_call_raw_output.py`, `query_traces.py` — not the two files that already have an undeclared `requests` dependency, pre-existing tech debt not touched here) rather than adding a new HTTP library dependency.
- **`tools/skeleton_renderer.py`**: added `TEMPLATES` (the `agent`/`tools` → skeleton-dir mapping), `schema_path_for()`, and `resolve_template()` — factored out of `tools/verify_skeleton.py`'s own inline derivation (which already existed from G3+G4's Stage-2 work) so `instantiate_agent_project.py` and `verify_skeleton.py` share one definition of the schema/skeleton pairing, not two copies that could drift the way `DEC-075`'s own bug did. `load_schema()` now takes an optional `schema_path` argument (defaults unchanged, so nothing else calling it with zero args breaks).
- **`tools/verify_skeleton.py`**: one-line change, now calls `schema_path_for(skeleton_dir)` instead of its own inline derivation. Re-ran after the change: still `PASS` on both templates, byte-identical output to before.
- **`tools/instantiate_agent_project.py`**: added `--template {agent,tools}` (default `agent`, so existing invocations without the flag are unaffected) and `--publish` (plus `--gitea-host`/`--gitea-org`, defaulted to this project's own live Platform Foundation instance/org). The Gitea token/username are read from `GITEA_TOKEN`/`GITEA_USERNAME` environment variables only, never accepted as a bare CLI flag — keeps the credential out of shell history and `ps` output, the same reasoning this project has applied to every other credential-handling step this phase.

## The two-repo split — design and reasoning

`deploy/` (kustomize + argocd + otel manifests) goes to a new `<name>-gitops`
repo; everything else (source, pipelines, tests, docs, catalog-info.yaml,
...) stays in the `<name>` repo. This is the owner's own binding two-repo
decision from earlier this phase, matching the verified
`redhat-ai-dev/ai-lab-template` reference pattern.

**Judgment call, made this session, not backed by a prior decision**: the
GitOps repo's own top-level structure drops the redundant `deploy/` prefix
— its content is `kustomize/`, `argocd/`, `otel/` directly at the repo
root, not `deploy/kustomize/` etc. Reasoning: a repo whose entire purpose
is deployment manifests doesn't need a directory literally named "deploy"
inside it. Verified live (see below) that this renders correctly and the
resulting `kustomization.yaml` resource lists are internally consistent
with the new flat layout.

`repoOwner`/`repoName` default to `REPLACE_ME_*` placeholders in both
schemas (unchanged, pre-existing) — the publish path falls back to the
Gitea org (`--gitea-org`) and the project's own `name` value respectively
when those placeholders are still present, rather than literally
publishing a repo named `REPLACE_ME_repoName`. This fallback lives only in
the `--publish` code path in `instantiate_agent_project.py`, not in
`resolve_values()` itself — deliberately narrow blast radius, since
`resolve_values()` is also used by the (not-yet-existing) RHDH Scaffolder
publish path and by `verify_skeleton.py`'s own test-values, neither of
which should have this fallback silently applied to them.

## Live verification (commands run, actual outcomes)

1. **Smoke tests, non-publish path unaffected**: rendered both templates
   via the CLI with the new `--template` flag (`agent` explicit and
   `tools`), confirmed file counts match `verify_skeleton.py`'s own
   expectations (179 and 38 respectively) and exit code 0.
2. **`tools/verify_skeleton.py` re-run after the refactor**: still `PASS`
   on both templates, identical output.
3. **Full test suite, container-based**: `253 passed, 1 skipped` —
   unchanged from before this session's edits.
4. **Real Gitea credentials confirmed live** before writing any publish
   code: the scaffolder token's org lookup succeeded; a bare `/api/v1/user`
   call correctly `401`'d with `required=[read:user]` (the token
   deliberately lacks that scope, per `DEC-100`'s own minimal-scoping
   design — expected, not a bug). The admin user/password (Basic auth)
   confirmed `is_admin: true`.
5. **Real, full Agent Template publish**: `golden-path-agent-cli-publish-test`
   (source) + `-gitops` (GitOps), both created, both pushed. Verified via
   real Gitea API content fetches, not just "push succeeded": source
   repo's file listing matches the expected split (`agent/`, `pipelines/`,
   `tests/`, no `deploy/`); `catalog-info.yaml`'s `metadata.name` correctly
   shows the real substituted project name; GitOps repo's file listing is
   `argocd/`, `kustomize/`, `otel/` (flat, no `deploy/` wrapper); its
   `kustomize/base/kustomization.yaml` resource list renders correctly
   relative to the new flat layout.
6. **Real, full Tools Template publish**: `golden-path-agent-cli-publish-test-tools`
   + `-gitops`, same verification depth — source repo has `mcp_server/`,
   no `deploy/`; both repos' content fetched and confirmed real.
7. **Idempotent re-run, isolated test**: called `create_repo` twice against
   the same new repo name (`idempotency-probe`) — first call `created=True`,
   second `created=False`, both returning the identical `clone_url`, not an
   error. Matches the documented design.
8. **Minimum-scoping re-confirmed**: attempted to `DELETE` a repo with the
   scaffolder token directly — `403`, as `DEC-100` already established.
   Cleanup used the admin credential instead, as designed.
9. **All test repos deleted and confirmed gone**: all four repos from
   steps 5/6 plus the idempotency probe from step 7 — each independently
   re-fetched after deletion and confirmed `404`. No test debris left in
   the shared Gitea instance. All local scratch directories and
   credential files (`/tmp/gt.txt`, `/tmp/gu.txt`, `/tmp/gap.txt`, and
   the two rendered-project scratch trees) removed after use.

## What did NOT get resolved — named, not silently absorbed

**The published GitOps repo's own content is not internally consistent
with the two-repo, Gitea-hosted reality it was just published into.**
Specifically:

- `deploy/argocd/*.yaml` (now living at the GitOps repo's own
  `argocd/*.yaml`) still has `spec.source.repoURL: https://github.com/${{
  values.repoOwner }}/${{ values.repoName }}.git` — pointing at GitHub, at
  the *source* repo's own name, not at the GitOps repo this content now
  actually lives in. This is pre-existing skeleton content (present since
  before this session, `github.com` hardcoded throughout, never adapted
  for Gitea at all) — not introduced by this session's specific split, but
  now genuinely wrong in a new way once the split is real.
- `pipelines/tasks/open-promotion-pr.yaml` (staying in the source repo)
  hardcodes `api.github.com`/`github.com` REST calls for opening the
  promotion PR — this needs to target the *GitOps* repo (where the
  promoted digest file now lives) via *Gitea's* API, not GitHub's. A
  materially different task than the publish mechanism this session
  built: this needs a Gitea-native promotion-PR action, the same shape of
  problem `DEC-110`'s own feasibility investigation named for the
  portal-publish side (Path A), just on the CI/promotion side instead.

**Recommendation**: treat this as its own explicitly-scoped follow-up —
"make the rendered pipeline/GitOps content Gitea-aware," not squeezed into
either this session or a future session's margins. It's real work
(a new schema parameter for the GitOps repo's own owner/name, rewriting
every `github.com`-hardcoded reference across `deploy/argocd/*.yaml` and
`open-promotion-pr.yaml` to be provider-configurable or Gitea-native), not
a quick fix — consistent with how `DEC-110` already sequenced the
portal-publish plugin work (Path A) as a separate slice rather than
attempting everything in one pass.

**Also not attempted, by this session's own explicit scope instruction**:
per-project CI namespace/RBAC bootstrap for a newly-published project,
Tekton webhook/EventListener wiring, and onboarding the new project into
the platform's own ArgoCD app-of-apps. All three remain real, separate
follow-up work.

**Also not attempted** (listed as optional in this session's own
directive): live RHDH catalog registration of a published project's
`Component` entity. `DEC-110`'s own named open question (whether
Backstage's entity-merging behavior causes confusion for a genuinely
Gitea-only project, unlike this repo's own byte-identical GitHub/Gitea
mirror situation) remains unanswered — still worth a real live check once
catalog registration is actually attempted, not assumed clean by analogy.

## Drafted decision entry (numbered as a placeholder — land at the
coordinating session's own next available `DEC-NNN`)

```
## DEC-1xx — G6 Path B implemented: CLI-first Gitea publish, two
repositories per project, verified live for both templates; the
published GitOps content's own ArgoCD/promotion-PR references are not
yet Gitea-aware -- a real, separate, named follow-up

**Context**: `DEC-110` chose Path B (CLI-first publish) as G6's first
implementation slice. This entry records that work as done and verified
live, not just attempted.

**What changed**: `tools/gitea_publish.py` (new) implements repo
create/push/delete against the Platform Foundation's Gitea instance
(`DEC-100`), using the scoped `golden-path-agent-scaffolder` machine
account for create/push and the admin credential only for this session's
own test cleanup. `tools/instantiate_agent_project.py` gained `--template
{agent,tools}` (closing `DEC-104`'s own named gap -- the CLI was
previously hardcoded to the Agent Template only) and `--publish`
(credential via `GITEA_TOKEN`/`GITEA_USERNAME` environment variables
only, never a bare CLI flag). `tools/skeleton_renderer.py` gained a
shared `resolve_template()`/`schema_path_for()` pair, refactored out of
`tools/verify_skeleton.py`'s own pre-existing inline derivation so the
schema/skeleton pairing is declared once, not twice (`DEC-075`'s own
duplicated-constant lesson, applied proactively rather than after a
second drift incident).

**Two-repo split**: `deploy/` (kustomize + argocd + otel) goes to a new
`<name>-gitops` repo, everything else stays in `<name>` -- the owner's
own binding decision, matching the verified `redhat-ai-dev/ai-lab-template`
pattern. Judgment call made this session: the GitOps repo drops the
redundant `deploy/` prefix at its own root (`kustomize/`, `argocd/`,
`otel/` directly), not backed by a prior decision but reasoned in the
report.

**Verified live, twice (once per template), with real Gitea API content
fetches, not just "push succeeded"**: both templates publish correctly as
two real repos each; file-level split matches expectations (no `deploy/`
in the source repo, no non-deploy content in the GitOps repo);
`catalog-info.yaml`'s substituted project name confirmed correct in the
published content; idempotent re-run confirmed (a second create call
against an existing repo returns the existing repo, not an error);
minimum-scoping re-confirmed (the scaffolder token still cannot delete a
repo it created, `403`, matching `DEC-100`); all test repos and local
credential files cleaned up and confirmed gone after verification.

**SIGNIFICANT, NAMED GAP -- not resolved this session**: the published
GitOps repo's own `argocd/*.yaml` content still has `spec.source.repoURL`
pointing at `github.com/${{ values.repoOwner }}/${{ values.repoName }}`
-- the *source* repo, on GitHub, by hardcoded hostname -- not the actual
GitOps repo just published to Gitea. `pipelines/tasks/open-promotion-pr.yaml`
(staying in the source repo) is similarly hardcoded to GitHub's REST API
for opening promotion PRs, needing a Gitea-native equivalent targeting
the GitOps repo instead. This is pre-existing skeleton content (hardcoded
to GitHub since before this session, across every template render, not
introduced by the two-repo split specifically) now genuinely broken in a
new way once a real two-repo Gitea publish exists. Recommend sequencing
this as its own explicitly-scoped follow-up -- "make the rendered
pipeline/GitOps content Gitea-aware" -- the promotion-side counterpart to
`DEC-110`'s own Path A (portal-publish-side) follow-up, not squeezed into
a future session's margins.

**Also not attempted, per this session's own explicit scope**: per-project
CI namespace/RBAC bootstrap, Tekton webhook/EventListener wiring, ArgoCD
app-of-apps onboarding for newly-published projects, and live RHDH
catalog registration of a published project's own `Component` entity
(listed as optional this session, not attempted to stay focused on the
core publish mechanism). `DEC-110`'s own named open question about
Backstage's entity-merging behavior for a genuinely Gitea-only project
remains unanswered.

**Status**: G6's core CLI-first publish mechanism is complete and
verified live for both templates. The rendered content's own
GitOps/promotion internal consistency, and full pipeline/ArgoCD
auto-onboarding, remain real, separately-scoped follow-up work -- named
explicitly, not silently assumed done.
```
