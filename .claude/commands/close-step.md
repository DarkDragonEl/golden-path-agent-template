---
description: Scaffold (never commit) a DEC-entry draft in the standing ambiguity -> finding -> decision -> evidence -> status shape, plus a reports/ skeleton, from the current session's work. The human reviews, edits, and commits both -- this command only drafts.
argument-hint: <short-feature-name>
---

# /close-step <short-feature-name>

**Classification: draft-only, never state-changing on its own.** This
command writes its output to the conversation (or, if asked, to a
scratch/draft location the human names) -- it **never appends to
`DECISIONS.md`** and never runs `git commit`. Per this project's
governance rule, only a human deliberately reviewing and committing the
draft turns it into a real decision.

## The DEC number this command produces is provisional -- always

`DECISIONS.md` is append-only and can have more than one active writer
across sessions (this was observed directly: the `feature/workspace-
tooling` mission found `DEC-075` mid-draft, uncommitted, in a *different*
session's working tree, while this repo's committed tail still read
`DEC-074`). A number computed from the committed tail at the moment this
command runs can be stale by the time a human actually commits it.

**Every number this command emits must be labeled exactly:**
```
DEC-NNN (provisional -- re-check tail before commit)
```
Never emit a bare `DEC-NNN`. The human re-checking the real tail (`grep
'^## DEC-' DECISIONS.md | tail -5`) immediately before committing is not
optional -- state that explicitly in the command's output, every time.

## Procedure

1. Run `grep -n '^## DEC-' DECISIONS.md | tail -1` to get the current
   highest committed number; the draft's number is that value + 1,
   labeled provisional as above.
2. Draft the entry in this shape (adjust subheading wording to match
   whatever the 2-3 most recent real entries in `DECISIONS.md` actually
   use at draft time -- re-read them, don't assume this template is
   byte-exact forever):

   ```markdown
   ## DEC-NNN (provisional -- re-check tail before commit) -- <short title>

   **Ambiguity:** <what was unclear or undecided going in>

   **Finding:** <what was discovered while doing the work>

   **Decision:** <what was decided/done, and why this option over the
   alternatives>

   **Evidence:** <commands run, test/eval output, file paths, report
   reference>

   **Status:** <e.g. "Implemented, verified live" / "Held for owner
   review" / "Superseded by DEC-xxx">
   ```
3. Draft `reports/feature-<short-feature-name>.md` skeleton: what was
   attempted, commands run and their real output (not paraphrased),
   what passed/failed, what's left open.
4. Present both drafts in the conversation for the human to
   review/edit/commit. Do not write either file yourself unless the
   human explicitly says to save the draft to disk -- and even then,
   never to `DECISIONS.md` directly; only to the standalone
   `reports/*.md` file or a scratch location.

## Output format

Two clearly-labeled markdown blocks -- the DEC draft first, the report
skeleton second -- each prefixed with a one-line reminder that both are
drafts pending human review, and that the DEC number specifically needs
a fresh tail-check before it's committed.
