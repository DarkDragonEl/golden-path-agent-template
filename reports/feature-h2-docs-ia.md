# Phase H2 — docs/ information architecture, naming conventions,
glossary, credentials doc

**Coordinating-session note (Phase H4b pre-task, DEC-124 follow-up):**
two independent H2 streams ran concurrently (two coordinating sessions
both executing Phase H after `DEC-114`'s announcement). This report
documents this particular stream's own experience, including the
credential-script access gap below — but the content actually merged to
`main` as `DEC-116` came from the *other* stream, which did successfully
copy and track both credential scripts (confirmed live: `git ls-files
tools/provision-demo-credentials.sh tools/get-test-user-credential.sh`
both return a match, and `docs/access-and-credentials.md` links both).
`state/README.md` was a casualty of the hybrid merge — genuinely missing
until this pre-task added it. Kept this report as-is below rather than
rewritten, since it's an accurate record of what *this* stream
experienced; just don't take its "not yet tracked" framing as current
truth for the scripts.

Worktree: `.claude/worktrees/agent-abf6d7fd7e593a530`. Branch: see
"Branch-name collision" below — could not be renamed to
`feature/h2-docs-ia` as instructed; work is committed on this worktree's
own branch instead.

## Inputs read in full before writing anything

`reports/docs-audit.md`, `reports/docs-terms-sheet.md` (both Phase H0),
the `DECISIONS.md` tail (`DEC-095` through `DEC-114`, especially `DEC-098`/
`DEC-099` the three-image split and `DEC-114` the Phase H kickoff/file-
ownership entry), `docs/architecture.md`, `docs/local-dev.md`,
`docs/security-identity.md`, `scripts/dev.sh`, `Makefile`,
`platform/bootstrap/keycloak-realm-import.yaml`,
`platform/bootstrap/provision-identity-secrets.sh`, and all 16 existing
`docs/*.md` files (at least their headers/structure) to place them
correctly in the hub.

## `docs/` tree, before → after

**Before (16 files)**: `architecture.md`, `direct-chat-walkthrough.md`,
`drafts/AGENT-UI-MAP.draft.md`, `environments.md`, `evaluation.md`,
`local-dev.md`, `owner-walkthrough.md`, `phase-c-runbook.md`,
`phase-d-runbook.md`, `phase-e-kickoff-plan.md`, `phase-f-kickoff-plan.md`,
`security-identity.md`, `showcase-access.md`,
`showcase-walkthrough-script.md`, `template-nine-output-mapping.md`,
`testing-perspectives-guide.md`.

**After (20 files)**: the same 16, unmoved, plus `README.md` (the hub),
`access-and-credentials.md`, `glossary.md`, `naming-conventions.md`.

**File moves/renames: none.** Every existing file stayed at its current
path — none of them actively misled a reader badly enough to justify a
move, per the mission's own preference for "fix links, don't rename."

## Per-directory `README.md` files added (13)

`agent/`, `approval_service/`, `ci/`, `deploy/`, `mcp_server/`,
`pipelines/`, `platform/`, `policy/`, `reports/`, `scripts/`, `srs/`,
`tests/`, `tools/`.

**Correction to the mission brief's own directory list**: `state/` does
not exist anywhere in this repository (`ls -la` at repo root confirms) —
skipped, not created. `corpus/`, `eval/`, `skeleton/`, `skeleton-tools/`
already had a `README.md` and were left untouched, confirmed before
starting (`corpus/README.md`, `eval/README.md`, `skeleton/README.md`,
`skeleton-tools/README.md` all pre-existing). Final count: 13 new READMEs,
matching the audit's own corrected count once `state/` is excluded.

Each new README is 5–15 lines (a couple run slightly longer where the
directory's real content genuinely needed a bit more, e.g. `deploy/`'s
three-way kustomize/argocd/otel split), states what lives there, who/what
consumes it (a human developer, a human operator with cluster access,
Tekton, ArgoCD, RHDH — named specifically per directory, not generically),
what builds/applies/deploys it, and links up to the documentation hub and
sideways to its closest contract docs/READMEs. All cross-references are
real markdown links, verified to resolve (see Verification below).

## `docs/README.md` hub

Diátaxis-shaped: Tutorials (3: owner walkthrough, showcase walkthrough
script, direct-chat walkthrough), How-to/runbooks (6: Phase C runbook,
Phase D runbook, access-and-credentials, local-dev, showcase-access,
testing-perspectives-guide), Reference (5: environments, evaluation,
glossary, naming-conventions, `PINS.md` pointer, template-nine-output-
mapping — six entries, one section), Explanation (2 docs + a
`DECISIONS.md` pointer: architecture, security-identity). A short
"Historical & draft records" section covers the three remaining files
that are explicitly self-marked draft/historical and don't fit the four
Diátaxis categories as current reference: Phase E kickoff plan, Phase F
kickoff plan, the approver-UI-map draft.

Verified programmatically: all 19 non-hub `docs/*.md` files (16 existing
+ 3 new, excluding the hub itself) are linked directly from
`docs/README.md` — every doc is reachable in exactly 1 click, comfortably
inside the ≤2-click requirement.

## The two stale-file fixes

**`docs/local-dev.md`** — the Quickstart section previously said
`up-offline` "builds the image once, and starts all three roles as plain
containers," and separately claimed the mock tool call "happens
in-process," with the `mcp` container existing only "for architectural
parity." Both claims are now false per `scripts/dev.sh`'s actual G2-era
behavior (`DEC-098`/`DEC-099`): it builds **three separate images**
(`Containerfile.agent`/`.mcp`/`.approval`) and forces `MCP_MODE=live`
unconditionally, offline or not — there is no in-process mock path left
in this topology at all (`Containerfile.agent` deliberately excludes
`mcp_server/server.py`, so the in-process fallback would `ImportError`).
Rewrote the section to state this accurately, including that `dev.sh`
actually starts **four** containers (agent, mcp, approval, plus a local
OTel Collector) and citing `DEC-096`'s own finding as the reason
`MCP_MODE` was changed to always-live. Also fixed a second, related stale
claim later in the same file ("Running for real" section previously said
`MCP_MODE` "can stay mock even in live-model mode" — no longer true,
`dev.sh` forces `live` regardless).

**`docs/security-identity.md`** — the Network-boundary section called the
architecture "one-image-two-roles." Replaced with the three-image split,
citing `DECISIONS.md` `DEC-098`/`DEC-099`, matching how `docs/
architecture.md` itself now describes the same change. While in this
file, also fixed an adjacent, independently-stale claim in the Workload
Identity section directly above it: it said one shared `ServiceAccount`
(`golden-path-agent`) backs "both the agent and MCP pods," but
`deploy/kustomize/base/` actually declares three distinct
`ServiceAccount`s today (`serviceaccount.yaml`, `serviceaccount-mcp.yaml`,
`serviceaccount-approval.yaml`, per `DEC-061`, which explicitly closed a
`DEC-045` finding that agent/MCP originally shared one). This wasn't
named in the mission brief's stale-file list, but it's a small, clearly-
verified factual correction directly adjacent to the required edit in the
same file, not a scope expansion.

## Credential scripts: NOT tracked — flagged, not fabricated

**`tools/provision-demo-credentials.sh` and `tools/get-test-user-
credential.sh` do not exist anywhere accessible to this worktree.**
Verified directly, not assumed: `ls tools/` lists neither file; `git log
--all -- '**/provision-demo-credentials.sh'` and the same for
`get-test-user-credential.sh` return zero hits across every local and
remote branch/ref; `git stash list` is empty. The most likely
explanation: these are untracked files sitting in the coordinating
session's own checkout (or wherever Phase H0's audit ran) — `git
worktree add` only checks out committed content, so an untracked file
never propagates into a new worktree. This is the same failure mode
already named in the mission brief for `reports/provision-demo-
credentials.md` (also untracked, also absent from this worktree,
confirming the pattern).

**I did not fabricate either script.** Per this mission's own contingency
plan for "a script shouldn't be tracked," I did the safe thing instead:
described the intended per-person-account and self-service-reset model in
`docs/access-and-credentials.md` in the terms the mission brief itself
gave me, stated plainly that neither script could be verified or tracked
from this worktree, and left both unlinked. **Flagging this prominently,
as instructed**: the coordinating session needs to get these two files'
actual content into whichever stream tracks them next so the anonymity
check and `git add` this mission calls for can actually happen — this
worktree cannot do either for a file it cannot see.

Separately, confirmed `reports/provision-demo-credentials.md` is not
tracked by this commit (trivially true — it doesn't exist in this
worktree at all) and is not referenced anywhere in anything I wrote.

## Other findings worth flagging (not fixed — outside this stream's ownership)

- **A real, personal (non-placeholder) GitHub account/owner name appears
  hardcoded into the `git push`/`curl` commands in
  `pipelines/tasks/open-promotion-pr.yaml`** (its `git push`/GitHub-API
  target literally embeds a specific account owner, not a generic
  placeholder). Deliberately not quoted here to avoid repeating an
  identifiable string in a file this stream authors. `pipelines/` is not
  mine to edit (only `pipelines/README.md` is), and this predates this
  stream — flagging it for the coordinating session's direct review of
  that file, given `CLAUDE.md`'s anonymity rule is repo-wide, not
  phase-scoped. Not touched.
- No `state/` directory exists (see above — the mission's own directory
  list was slightly stale here, same as the audit warned it might be).
- No OpenShift `ImageStream` objects exist anywhere in this repo — images
  are referenced directly by registry path + digest. Documented as a
  "known deviation from a common assumption" in `docs/naming-
  conventions.md` rather than silently assumed.
- Two old `promote/<sha>`-shaped remote branches (no `<component>`
  segment) predate the G2 three-image split's `promote/<component>/<sha>`
  convention and haven't been cleaned up — documented as a known,
  historical deviation, not a live inconsistency, in `docs/naming-
  conventions.md`.

## Branch-name collision (blocked the first instruction)

`git branch -m feature/h2-docs-ia` failed: that branch name is already
checked out (locked) in a different worktree,
`.claude/worktrees/agent-a3e7afd924033f04a`, sitting at the same commit
as `main` (`f8b1e79`) with zero additional commits — it looks like a
stale/orphaned worktree from an earlier, incomplete attempt at this same
task. This worktree's own sandbox explicitly refuses any git operation
that targets another worktree (`cd`, `git -C <path>`, and `git branch -M`
all errored with an explicit refusal), so I could not inspect or clean up
that other worktree myself. **All work in this report is committed on
this worktree's own original branch, not `feature/h2-docs-ia`.** The
coordinating session should either remove the stale empty worktree/branch
and re-run the rename here, or otherwise merge this stream's work under
the intended branch name itself.

## Verification performed

- **Anonymity sweep**: grepped every touched/added file for known-
  sensitive strings (the repo owner's OS username/GitHub handle, the
  user's email domain, generic email/hostname/URL patterns, IPv4
  literals). Zero hits except one legitimate external link
  (`https://diataxis.fr/`, the public naming-methodology site the hub
  cites by design — explicitly allowed, external `http(s)` links are
  fine).
- **Link check**: wrote a small script that extracts every `[text](path)`
  markdown link from all 19 touched/added files and resolves each
  relative path against the filesystem (skipping `http(s)` links). Result:
  all links resolve. Separately confirmed all 19 non-hub `docs/*.md`
  files are reachable directly from `docs/README.md` (1 click each).
- **Diff scope check**: `git status --porcelain` shows exactly 19 changed
  paths — 2 modified (`docs/local-dev.md`, `docs/security-identity.md`)
  and 17 new (4 new `docs/*.md` files + 13 new per-directory `README.md`
  files). No `README.md`, no Python file, no `DECISIONS.md`/`HANDOFF.md`/
  `PINS.md`, and no `docs/provenance.md` touched.
- **Untracked-report check**: `reports/provision-demo-credentials.md`
  does not exist in this worktree (confirmed via direct search), so it
  cannot have been accidentally staged — trivially satisfies "stays
  untracked."

## Drafted DEC-entry fragment (provisional — re-check the real tail before commit)

```
## DEC-NNN (provisional — re-check tail before commit) — Phase H2: docs/ information architecture, naming conventions, glossary, credentials doc

**Ambiguity:** Phase H2's brief assumed two credential scripts
(`tools/provision-demo-credentials.sh`, `tools/get-test-user-credential.sh`)
and a directory named `state/` already existed in the repo, ready to be
read/tracked/documented from this worktree.

**Finding:** Neither credential script exists anywhere accessible to this
worktree — not in the working tree, not in git history across every
branch/ref, not stashed. Most likely cause: they are untracked files in
another checkout (the coordinating session's own, or wherever Phase H0's
audit ran), and `git worktree add` never copies untracked content into a
new worktree. `state/` does not exist anywhere in this repository at all
(`ls -la` at repo root). Separately, `git branch -m feature/h2-docs-ia`
failed: that branch name was already checked out, locked, in a different,
apparently-orphaned worktree at the same commit as `main` with no extra
work — this worktree's sandbox refuses cross-worktree git operations, so
it could not be cleaned up from here.

**Decision:** Did not fabricate the two missing scripts and did not
invent a `state/README.md`. Documented the intended credential model in
`docs/access-and-credentials.md` using only the description already given
in the mission brief, explicitly marked both scripts as unverified/
untracked, and left them unlinked. Built all other Phase H2 deliverables
(the docs hub, naming conventions, glossary, the two stale-file fixes,
13 per-directory READMEs) against the repository's real, verified state.
Committed all work on this worktree's own branch rather than the intended
`feature/h2-docs-ia` name, since that name was unavailable and unfixable
from inside this worktree's sandbox.

**Evidence:** `reports/feature-h2-docs-ia.md` (this file) — full before/
after doc tree, all fixes, link-check and anonymity-sweep results, and
the exact commands run to confirm both the missing scripts and the
missing `state/` directory.

**Status:** Phase H2 deliverables complete and committed locally, except
the two credential scripts (blocked, flagged for the coordinating
session) and the branch rename (blocked, flagged for the coordinating
session). Nothing pushed, nothing merged to `main`.
```
