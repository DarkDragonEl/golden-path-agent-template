# H4b — comment slimming: scripts/ and pipelines/

Worktree: `feature/h4b-scripts-pipelines-comments` (not baked into any
image — per `CLAUDE.md`'s docs/non-image-tooling exception, committed
directly, no PR needed). Scope: every category-(b)/(c) `DEC-`-citing
comment block in `scripts/bootstrap.sh`, `scripts/dev.sh`, and 18 files
under `pipelines/`, per `docs/code-comment-policy.md` and the full
per-item classification from the `phase-h0-comment-census` workflow +
`reports/docs-audit.md`'s H4a mapping table.

## What changed

20 files, 214 insertions / 544 deletions. Every block condensed to a
≤3–4 line current-fact-or-contract statement + `DEC-NNN` pointer,
cutting the historical narrative (what was tried, why, exact prior error
text) while keeping the operationally load-bearing fact (a field name, a
precondition, a gotcha). Pointer citations corrected to the migrated
content's real new home per H4a's mapping table in three places where
the original comment cited the wrong number:
- `pipelines/pipeline-mcp.yaml` header → now cites `DEC-099` (was
  `DEC-098/DEC-099`, framing corrected to match what's actually there).
- `pipelines/bootstrap/rbac.yaml`'s approval-namespace-move subject entry
  → now cites `DEC-103` (was `DEC-098/DEC-099/DEC-101`).
- `pipelines/tasks/operational-tests.yaml`'s two label-merge-bug blocks →
  now cite `DEC-101` explicitly (were bare `DEC-098/DEC-099`).

Left untouched: every category-(a) comment (the mission's own named
examples — the `DEC-083` guard text and rotation warnings in
`scripts/bootstrap.sh` stayed verbatim, operator-facing and prominent, on
purpose); comments with no `DEC-` citation at all (out of this pass's
scope even where adjacent); already-minimal one-liners.

## Verification (real output)

**`git diff main --stat`**: 20 files, 214(+)/544(-), see commit `15081e4`.

**Structural safety — the real check, not just "diff looks small"**:
every touched YAML file's pre/post content was parsed with PyYAML and
compared as data structures. 14 of 20 files matched immediately —
comments there are true YAML comments, invisible to the parser. 6 files
(`deploy-ephemeral.yaml`, `eval-gate-live.yaml`, `open-promotion-pr.yaml`,
`operational-tests.yaml`, `security-tests.yaml`, `unit-tests.yaml`)
showed a structural diff at first pass — expected, since their edited
comments live *inside* a `script: |` literal block, which YAML treats as
an opaque string, not comments. For each: confirmed every non-`script`
field byte-identical, then diffed the `script` string itself and asserted
every changed line is a `#`-comment or blank — i.e. the *shell*
interpreter also sees zero behavioral change. All 6 passed clean (17, 12,
14, 35+23, 19, and 13 changed lines respectively, all comment/blank).

Representative output (all 6 files passed identically):
```
=== pipelines/tasks/operational-tests.yaml ===  non-script-fields-equal=True  script-count old/new=2/2
  OK: script at [0, 'spec', 'steps', 0, 'script'] differs only in comment/blank lines (35 changed lines)
  OK: script at [0, 'spec', 'steps', 1, 'script'] differs only in comment/blank lines (23 changed lines)
```

**`bash -n`**: both `scripts/bootstrap.sh` and `scripts/dev.sh` — clean.

**`make test`**: `253 passed, 1 skipped, 244 warnings in 10.23s` —
identical to the pre-existing baseline (`DEC-112`/H3a's own confirmed
count).

## Drafted DEC entry (provisional — re-check the real tail before commit)

**DEC-NNN (provisional — re-check the real tail before commit) — H4b:
category-(b)/(c) comments slimmed in `scripts/` and `pipelines/`,
structural equivalence verified two ways**

Applied `docs/code-comment-policy.md` to every `DEC-`-citing comment
block across `scripts/bootstrap.sh`, `scripts/dev.sh`, and 18
`pipelines/` manifests (the two non-image-baked directories in H4b's
scope handled by this stream) — 20 files, 214 insertions / 544 deletions.
Every block reduced to a short current-fact statement plus its `DEC-NNN`
pointer; three pointers corrected to the migrated content's real home
per H4a's mapping table (`pipeline-mcp.yaml` → `DEC-099`,
`bootstrap/rbac.yaml`'s approval-namespace entry → `DEC-103`,
`operational-tests.yaml`'s two label-merge blocks → `DEC-101`).
Category-(a) comments (including the mission's own named examples, the
`DEC-083` guard and rotation warnings in `bootstrap.sh`) and already-
minimal one-liners were left untouched.

**Verified two ways, not one**: PyYAML structural-equality diffing caught
that 6 files' edits live inside a `script: |` string (invisible to a
YAML-level comment check) and were separately verified by diffing the
script string itself and confirming every changed line is a shell
comment or blank — the interpreter, not just the YAML parser, sees zero
behavioral change. `bash -n` clean on both shell scripts. `make test`:
253 passed / 1 skipped, unchanged from baseline.

**Status**: Committed locally on `feature/h4b-scripts-pipelines-comments`
(`15081e4`), not pushed, not merged — non-image-baked, so per `CLAUDE.md`'s
exception this may commit directly to `main` (no PR) once the
coordinating session re-checks the tail and lands this entry.
