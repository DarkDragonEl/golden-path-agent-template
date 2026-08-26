# Phase H1 — README rewrite, provenance split, install.sh

Worktree stream. Branch: `feature/h1-readme-rewrite-2` (see the branch-name
note at the end — the literal `feature/h1-readme-rewrite` name was already
in use by a sibling worktree with zero commits ahead of `main` when this
stream started; renaming was blocked at the git level).

## What was built

1. **`README.md` rewritten in full**, in the mandated section order: What
   this is / Architecture at a glance (Mermaid) / Repo map / Quickstart A
   (laptop) / Quickstart B (fresh OpenShift cluster) / Docs index (held
   tail) / Footer.
   - Repo map now lists all 19 real top-level directories (confirmed
     against `reports/docs-audit.md` §3, not the stale 7-directory
     "Layout" section it replaces), split into **the blueprint**, **the
     build journal**, and an added **Other root files** table for
     load-bearing root files (`Makefile`, the three `Containerfile.*`,
     the three `entrypoint-*.sh`, `requirements*.txt`, the four
     `template*` files, `catalog-info.yaml`, `.env.example`,
     `pyproject.toml`, `TODO_DOMAIN.md`, `SHOWCASE_NOTES.md`) that the
     mission's own two-group enumeration didn't name but the "one line
     per top-level directory/load-bearing root file" instruction implied
     should still be covered. `ci/` and `tests/` were folded into "the
     blueprint" group (not in the mission's literal 14-item enumeration,
     but clearly blueprint-shaped: the PR-check pipeline and the test
     suite). `approval_service/` is now explicitly documented — the
     single biggest gap the H0 audit found.
   - `state/` is git-ignored and does not exist in a fresh clone; it gets
     one explanatory sentence under the blueprint table instead of a
     dead-linked row.
   - The two dangling out-of-repo references the audit flagged
     (`README.md:4`'s `../Agentic_AI_Platform_MVP_Agnostic.md`, and the
     unlinked "reuse-map artifact... parent workspace" phrase) are both
     gone from the new README text.
2. **`docs/provenance.md`** — the old Provenance section, moved verbatim
   in substance. The reuse-map reference is rewritten as an explicit,
   self-contained note that the artifact lives in the private parent
   workspace and is not part of this public repo (no path invented, none
   implied to exist here). The provenance claim itself (original work,
   patterns observed not copied, no client code/secrets/config) is
   unchanged.
3. **`scripts/install.sh`** — a pure sequencer: `scripts/bootstrap.sh
   <kubeconfig-path>` then `platform/bootstrap/provision-identity-secrets.sh`,
   in that order. Interactive "yes" confirmation (DEC-059 semantics)
   before the second call; `--yes` skips only the prompt. Either script's
   non-zero exit stops the wrapper immediately with a message naming
   which script failed. Never passes `--reenable-sync` (DEC-083) or
   `--with-rhdh` — those remain the operator's own explicit call via
   `scripts/bootstrap.sh` directly. Exports `KUBECONFIG` once (see
   finding below) so both invocations target the same cluster.
   Executable (`chmod +x`), `bash -n` clean.

## A real finding surfaced while building install.sh

**`platform/bootstrap/provision-identity-secrets.sh` takes no kubeconfig
argument of its own** — confirmed by reading the file (no `$1`/`$#`/
`usage()` anywhere in it); it just calls `oc` directly and relies on
`KUBECONFIG` already being set in its environment. `scripts/bootstrap.sh`
covers this internally via `export KUBECONFIG="$1"` at its own top, but
that export dies with that script's process — it does **not** propagate
back to `install.sh`'s shell for its own, second, explicit invocation of
the secrets script. Without an explicit `export KUBECONFIG=...` inside
`install.sh` itself, step 2 would silently target whatever kubeconfig
happens to be ambient (or none), not the cluster the operator named on
the command line. Fixed by exporting `KUBECONFIG` once near the top of
`install.sh`, before step 1. Treated as necessary wiring, not "new logic"
in the sense the mission's "pure sequencer" constraint means to forbid —
flagging it here so the coordinating session can judge that call.

**Second finding, surfaced but not changed:** `scripts/bootstrap.sh`'s own
step 5/9 already calls `platform/bootstrap/provision-identity-secrets.sh`
once, non-interactively, as part of its own unattended sequence. The
mission's explicit two-script sequencing means `install.sh` calls the
same secrets script a **second time**, right after, gated behind the
interactive confirmation. Net effect: a full `install.sh` run rotates
identity secrets twice in immediate succession. This is harmless by
DEC-059's own design (idempotent by regeneration, safe to re-run), and it
does guarantee the human operator sees the rotation warning at least once
on the one-button path — but it is a real, visible redundancy, not an
oversight I introduced. Implemented literally per the mission's explicit,
repeated spec rather than silently deviating; documented in `install.sh`'s
own header comment and flagged here for the coordinating session.

## Verification actually executed (not claimed)

Ran directly in this worktree, `podman` + `pytest` both available locally:

```
$ python3 -m pytest -q      # via `make test`
253 passed, 1 skipped, 243 warnings in 5.11s

$ make eval-fast
AGENT_MODEL_MODE=fake python -m eval.cli run --all
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002
2/2 cases passed

$ cp .env.example .env && make up-offline
# built/ran all three containers (golden-path-agent-dev,
# golden-path-agent-mcp-dev, golden-path-agent-approval-dev,
# golden-path-otel-collector-dev); base images already cached locally,
# so this ran with no network access.

$ curl -sf http://localhost:18080/healthz   -> 200
$ curl -sf http://localhost:18082/healthz   -> 200
$ curl -s  http://localhost:18081/records?record_type=request
  -> real seeded ITSM records (REQ-30021, ...)

$ curl -sS -X POST http://localhost:18080/invoke \
    -d '{"query": "What is the current status of incident INC-10255?", "write": false}'
  -> pending_approval:false, tool_calls[0].classification:"read"

$ curl -sS -X POST http://localhost:18080/invoke \
    -d '{"query": "Draft an access request for the staging namespace.", "write": true, "session_id": "h1-verify-write"}'
  -> pending_approval:true, final_output:null, tool_calls[0].result:null,
     classification:"write"   # confirms the approval gate: drafted, not executed

$ make down    # clean teardown, no golden-path containers remained
```

This is real end-to-end confirmation of the human-approval gate described
in the README's "What this is" and architecture diagram: a write drafts
and pauses; it does not execute without a human decision.

`install.sh` was verified functionally against stub replacements of both
target scripts (not the real cluster scripts — no live OpenShift cluster
in this environment) in a scratch directory outside the repo:
- `--yes` + both stubs succeed → both run in order, correct exit 0.
- No `--yes`, answer `yes` at the prompt → both run, exit 0.
- No `--yes`, answer `no` → stops before step 2, exit 1, clear message.
- Stub `bootstrap.sh` exits 1 → `install.sh` stops immediately, names
  `scripts/bootstrap.sh` as the failure, never calls step 2, exit 1.
- Stub `provision-identity-secrets.sh` exits 1 → `install.sh` reports it
  by name, exit 1.
- No args → usage/exit 1. An unrecognized flag (tried `--reenable-sync`
  directly against `install.sh`) is rejected with a usage error, not
  silently forwarded — confirms `install.sh` has no path that lets
  `--reenable-sync` reach `scripts/bootstrap.sh`.
- `KUBECONFIG` was observed correctly exported and visible to both stub
  invocations.

`bash -n scripts/install.sh` — clean.

## Reader test

Spawned a fresh, context-free subagent with only the final rendered
README text (no other repo access) and asked the four mandated
questions. Outcome: all four answered correctly using only the given
text, including correctly citing `DEC-083`/`DEC-059` by number for the
decision-provenance question (zero ambiguity flagged there). Two minor
precision gaps it flagged were fixed in the README before finalizing:
- "MCP" was unexplained on first use → expanded to
  "MCP (Model Context Protocol) tool contract."
- The live-model quickstart named "the fallback route" without naming
  the env vars → added `MODEL_FALLBACK_API_BASE_URL`/`MODEL_FALLBACK_NAME`
  explicitly (verified against `.env.example`).
No other ambiguity, missing information, or contradiction was flagged
against the four required questions after those two fixes.

## Anonymity sweep

Grepped `README.md`, `docs/provenance.md`, and `scripts/install.sh` for
real names/emails/hostnames (user email/username, common corp-domain
patterns) — no matches. Product/tool names used throughout (OpenShift,
Keycloak, ArgoCD, Tekton, Gitea, RHDH, MCP, LangGraph) are the same
already-established real open-source/vendor technology names used
extensively elsewhere in this repo's own `DECISIONS.md`/`docs/` — not
client-identifying, consistent with the existing convention, not a new
exposure.

## Link check

Every relative link added to `README.md` was checked against the real
filesystem (`ls -d` per path) and resolves, except the one
self-referential link to this report file
(`reports/feature-h1-readme-rewrite.md`), which resolves now that this
file exists, and the intentionally-flagged Docs-index held-tail links,
which point at real, existing `docs/*.md` files (not invented paths) per
the mission's own instruction.

## Diff scope

```
$ git status --porcelain
 M README.md
?? docs/provenance.md
?? scripts/install.sh
```

Only the three owned files touched. No Python files, no other `docs/*`
files, no manifests, no Tekton tasks.

## Branch-name collision (please reconcile)

The task instructed renaming this worktree's branch to
`feature/h1-readme-rewrite`. That name was already checked out by another
live worktree (`.claude/worktrees/agent-a48f3ed2fa3520db4`) at the moment
this stream started, sitting at the exact same commit as `main`
(`f8b1e79`, zero commits ahead — `git diff main..feature/h1-readme-rewrite
--stat` was empty). `git branch -M` refused with "cannot force update the
branch ... used by worktree at ...". This stream proceeded on
`feature/h1-readme-rewrite-2` instead, since a hard git-level conflict
outside this stream's control shouldn't block Wave-β from producing this
work. **The coordinating session should reconcile the two
`feature/h1-*` worktrees/branches** — the other one appears to be an
empty/stale duplicate (no commits, no diff from `main`), but that should
be confirmed rather than assumed before either is discarded.

## Provisional DEC entry (for the coordinating session)

```
## DEC-NNN (provisional — re-check tail before commit) — Phase H1: README rewrite, provenance split, install.sh

**Ambiguity:** The mission's repo-map instruction said both "one line per
top-level directory/load-bearing root file" (broad) and gave a literal,
closed 14+6-item two-group enumeration (narrow) for "the blueprint" /
"the build journal." The literal enumeration omits `ci/`, `tests/`,
`state/`, and every load-bearing root file (Makefile, Containerfiles,
entrypoints, requirements, template*, catalog-info.yaml, etc.). Separately,
`scripts/install.sh`'s two-script sequencing (call `scripts/bootstrap.sh`,
then separately call `platform/bootstrap/provision-identity-secrets.sh`)
was specified explicitly and repeatedly, despite `bootstrap.sh`'s own
step 5/9 already calling the identity-secrets script once internally.

**Finding:** Read literally, the two-group enumeration is a minimum
membership guarantee, not a maximum — the repo genuinely has 19
directories plus load-bearing root files, and a repo map omitting `ci/`,
`tests/`, and the Containerfiles/Makefile/template files would misstate
the "one line per ... root file" instruction's own intent. Separately,
`provision-identity-secrets.sh` takes no kubeconfig argument of its own
(confirmed: no `$1`/`$#`/`usage()` in the file) — it depends on ambient
`KUBECONFIG`, which `bootstrap.sh` sets via its own `export` but which
does not survive back into a wrapper script's shell across a subprocess
boundary.

**Decision:** Kept the mission's two named groups (blueprint, build
journal) exactly as enumerated, and added a third "Other root files"
table for everything else load-bearing that fell outside both — folding
`ci/`/`tests/` into "the blueprint" table since they're clearly
blueprint-shaped, not journal-shaped. Built `install.sh` to call both
scripts exactly as specified (not "fixing" the apparent double-rotation
by deviating from the explicit spec), but added one line exporting
`KUBECONFIG` before either call, since without it the second,
explicit invocation would silently target the wrong (or no) cluster --
treated as required wiring for the specified sequencing to function
correctly, not as new decision logic. Documented the double-rotation
resulting from the literal two-call spec directly in `install.sh`'s own
header comment rather than hiding it.

**Evidence:** `reports/feature-h1-readme-rewrite.md` (this stream's own
report) — full verification transcript (`make test`, `make eval-fast`,
`make up-offline` end-to-end including a real write pausing for approval),
stub-based functional test of every `install.sh` branch (success,
decline, `--yes`, each script's failure path, argument rejection),
reader-test transcript, anonymity sweep, link check.

**Status:** Held tail (Docs index section) pending H2's merge. Also
flagging the `feature/h1-readme-rewrite` / `feature/h1-readme-rewrite-2`
branch-name collision (see this report's own section above) for the
coordinating session to reconcile before merge.
```
