---
description: Bootstrap session context in one shot -- read HANDOFF.md, the last 5 DECISIONS.md entries, PINS.md, and the current phase runbook, then produce a half-page brief of where the project stands, what's queued next, which invariants are live, and which checkpoint (if any) is open.
---

# /start-step

**Classification: read-only.** This command only reads files and reports
a summary -- it never edits `HANDOFF.md`, `DECISIONS.md`, or anything
else.

**Do not trust `HANDOFF.md` alone.** It is a snapshot written at the
close of whatever session last rewrote it, and it goes stale the moment
a later session adds `DECISIONS.md` entries without also rewriting it --
this happened concretely during the `feature/workspace-tooling` mission
(HANDOFF.md said "currently through DEC-073" while the live tail had
already reached DEC-075). Always cross-check HANDOFF.md's claimed state
against the actual most recent `DECISIONS.md` entries, and if they
disagree, the DEC entries win -- say so explicitly in the brief.

## Procedure

1. Read `HANDOFF.md` in full.
2. Find the real latest `DEC-NNN` by locating every `^## DEC-` header in
   `DECISIONS.md` and reading from the 5th-most-recent header to the end
   of the file (do not read the whole file -- it grows past 5000 lines
   and most of it is settled history irrelevant to "where things stand
   right now").
3. Read `PINS.md` in full (pinned component versions -- flag if a pin
   looks stale relative to what the latest DEC entries describe running).
4. Determine the current phase from whichever is more recent -- the
   latest DEC entries or HANDOFF.md's own "where this is" section -- and
   read the matching phase artifact. **Two naming patterns exist,
   confirmed live, not just theoretical:** `docs/phase-<x>-runbook.md`
   once a phase is actually executing, but a phase that's been planned
   and is awaiting owner authorization (not yet started) instead gets
   `docs/phase-<x>-kickoff-plan.md` -- a real example: at the moment
   this note was written, Phase D had just formally closed and Phase E
   existed only as `docs/phase-e-kickoff-plan.md`, not a runbook. Check
   for both patterns (`ls docs/phase-*.md`) before concluding nothing
   exists for the current phase; only say "no artifact yet" if neither
   pattern matches.

## Output format

A half-page brief, in this order:
- **Where things stand** (1-2 sentences, sourced from the DEC entries,
  not just HANDOFF.md)
- **Discrepancy flag** (only if HANDOFF.md and the DEC tail disagree --
  state exactly what's stale)
- **Open checkpoint, if any** (name it plainly if one is mid-flight or
  awaiting owner adjudication -- this is the single most important fact
  a new session needs before touching anything)
- **What's queued next** (from HANDOFF.md's own queue, corrected against
  what the DEC tail shows has actually already happened)
- **Live invariants** (the numbered list from HANDOFF.md, only if still
  current)
- **Pins worth a second look** (only if `PINS.md` shows something
  superseded/deprecated relevant to current work)

Keep it to half a page. This command exists to save a new session from
re-reading 5000+ lines of `DECISIONS.md` cold -- if the brief itself
sprawls, it has failed at that job.
