# Phase B0: SRS Derivation — Test Report

Branch: `feature/phase-b0-srs`, off `main` at `4d3ad48` (merge of Phase A,
tagged `phase-a-complete`).

## Checkpoint B0-a — SRS-APR (full) + SRS-MIT (interface-only draft)

Scope per `MISSION_PHASE_B0.md`: `srs/SRS-APR.md` complete, `srs/SRS-MIT.md`
drafted, `srs/FINDINGS.md` populated with any derivation gaps. Explicitly
NOT in scope for this checkpoint: `SRS-AGT.md`, `SRS-RET.md`, `SRS-EVH.md`,
`tools/trace-check/`, `srs/DEFERRED.md`, `srs/REVIEW_INDEX.md` — all B0-b.

### Derivation basis read in full

`SyRS-AGP-001_EN.md` was read in full (not keyword-filtered) before
derivation, since this is normative citation work — every `SysR-*` ID
cited below was confirmed to exist by direct reading, not by memory or a
prior session's partial extraction.

### Commands run and results

**1. SysR reference resolution** — every `SysR-*` ID cited in either new
document actually exists (bold-defined) in `SyRS-AGP-001_EN.md`:
```
$ for id in <17 distinct SysR-* IDs cited across both docs>; do
    grep -c -- "\*\*${id}" SyRS-AGP-001_EN.md
  done
OK   SysR-P-F-08 / F-09 / IF-02 / IF-03 / IF-05 / IF-06 / INFO-03 / INFO-04
     / LC-02 / PERF-01 / POL-01 / SEC-01 / SEC-02 / SEC-03 / SEC-05 / SEC-06
     / USE-01   (17/17 resolve, each defined exactly once)
```

**2. Requirement-ID uniqueness** (within each document):
```
$ grep -oE '\*\*SRS-APR-[A-Z]+-[0-9]+' srs/SRS-APR.md | sort | uniq -c | awk '$1>1'
(empty — no duplicates; 18 distinct SRS-APR-* IDs)
$ grep -oE '\*\*SRS-MIT-[A-Z]+-[0-9]+' srs/SRS-MIT.md | sort | uniq -c | awk '$1>1'
(empty — no duplicates; 6 distinct SRS-MIT-* IDs)
```

**3. Trace/Verification completeness** — every requirement bullet carries
exactly one `*Trace:*` and one `*Verification:*` line:
```
SRS-APR.md: 18 requirement headers, 18 Trace lines, 18 Verification lines
SRS-MIT.md:  6 requirement headers,  6 Trace lines,  6 Verification lines
```

**4. Eval-case cross-references resolve** — every Phase A case ID cited
as evidence (including range endpoints, e.g. `DRQ-001..006`) exists in
`eval/cases/domain/*.yaml`:
```
Checked: DRQ-001, DRQ-006, ITR-001, ITR-008, TSEL-001/002/004/005/007/008,
         UAW-001, UAW-002, UAW-006
All OK — 0 missing.
```

**5. Cross-document ID references resolve** — `SRS-MIT.md` cites
`SRS-APR-F-04` and `SRS-APR-IF-01`; both confirmed present in `SRS-APR.md`.
`SRS-APR.md` cites no `SRS-MIT-*` ID (not required this checkpoint —
`SRS-APR.md` references "the tool-contract path" generically, since it is
the interface-*consumer*; `SRS-MIT.md`, the interface-*provider*, is the
one that names the specific approval-service IDs it must not bypass).

**6. Scope confirmation** — no Phase B implementation surface touched:
```
$ git diff --stat main -- agent mcp_server eval
(empty — no output)
```

**7. PROPOSED-marker count matches each document's own claim:**
```
SRS-APR.md: 4 embedded `PROPOSED —` markers (F-04, F-07, SEC-02, SEC-04),
            matching its own closing line "PROPOSED items in this
            document (4)".
SRS-MIT.md: 0 embedded `PROPOSED —` markers, matching its own closing
            line "PROPOSED items in this document (0)" — it formalizes
            the eval/README.md provisional contract without revision.
```

### What this verification does NOT cover (honestly, not claimed)

`tools/trace-check` does not exist yet (B0-b deliverable) — the checks
above are manual/`grep`-based equivalents of trace-check's future checks
(a) ID-resolution and (c) no-orphan-IDs, run by hand for this checkpoint
only. Check (b) ("every SRS requirement traces to ≥1 valid SysR ID") is
satisfied by construction (every requirement's inline Trace line was
verified above) but not yet machine-enforced. Check (d) (SRS-F requirement
referenced by ≥1 test) is explicitly out of scope until Phase B produces
tests, per the mission.

### Derivation findings

Two findings recorded in `srs/FINDINGS.md`, both open pending owner
adjudication at this checkpoint:

- **FIND-001** — SysR-P-F-08 requires decisions be recorded *with*
  approver identity but never requires the service to *verify* the
  deciding identity holds the approver role. Closed at the SRS level by
  `SRS-APR-SEC-02` (`PROPOSED`).
- **FIND-002** — SysR-P-SEC-06/INFO-03 require audit records be
  retrievable but never state they must be immutable once decided.
  Closed at the SRS level by `SRS-APR-SEC-04` (`PROPOSED`).

Both are SRS-level additions only; neither modifies the SyRS, per the
mission's "you never modify the SyRS" rule.

### Honest gaps in eval coverage surfaced during derivation

Deriving `SRS-APR-SEC-02` and `SRS-APR-SEC-03` (identity propagation)
surfaced that Phase A's `unauthorized_write.yaml` — despite covering
`rejected`/`expired`/`not_requested`/`bypass_attempt` scenarios — has no
case for a decision submitted by a non-approver identity or a spoofed
identity. Noted inline in `srs/SRS-APR.md`'s Verification table as a
recommended future eval-set addition, not fixed here (would be Phase A
eval-set work, out of scope for Phase B0 SRS derivation).

### Outstanding for owner calibration review (Checkpoint B0-a)

1. Depth and style of `SRS-APR.md` (full) — is this the right granularity
   before the same treatment is applied to `SRS-AGT.md`/`SRS-RET.md`?
2. Depth and style of `SRS-MIT.md` (interface-only) — does the
   tailored-out/omitted-sections balance read right, or is it too thin /
   too thick for "demo scaffolding, not gold-plated"?
3. FIND-001 and FIND-002 dispositions — agree with the SRS-level
   `PROPOSED` fix, or should either be escalated to a SyRS revision?
4. The 4 `PROPOSED` items in `SRS-APR.md` individually (F-04 release
   mechanism, F-07 idempotency, SEC-02 approver authorization, SEC-04
   audit-record integrity).
5. `SRS-MIT.md`'s no-revision decision on the provisional ITSM contract —
   confirm the sync rule correctly found nothing to do.

**No `SRS-AGT.md`, `SRS-RET.md`, or `SRS-EVH.md` work begins, and no
`tools/trace-check` work begins, until the owner responds.**

---

## Checkpoint B0-a continuation — SRS-AGT (full), unattended iteration

Per `MISSION_UNATTENDED.md` (calibration B0-a approved; SRS-APR.md and
SRS-MIT.md frozen as-is): the owner's real-time instruction this session
authorized deriving `srs/SRS-AGT.md` now, without an additional stop, and
continuing to `srs/SRS-RET.md` the same way — see `DECISIONS.md` DEC-002
for the authorization check performed before proceeding under
`MISSION_UNATTENDED.md`'s "no checkpoints" mode.

### Process: one workflow, scoped to this document only

Per `MISSION_UNATTENDED.md`'s "Uso de workflows" section: one `Workflow`
run, four phases, all scoped to `srs/SRS-AGT.md` alone.

1. **Map** — one agent independently confirmed/corrected a candidate
   SysR-A-*/SysR-P-* applicability list against a full re-read of
   `SyRS-AGP-001_EN.md`. It rejected one candidate (`SysR-P-IF-03` — binds
   the tool-contract *provider* side, already discharged by
   `SRS-MIT-IF-01`, not the agent) and found one addition
   (`SysR-P-SEC-04`, externalized secrets — directly binds the agent, "no
   secret... in the agent image, source repository, or template").
2. **Derive** — one agent wrote the full document (25 requirements: F-01..09,
   IF-01..09, DATA-01, SEC-01..04, PERF-01, QUAL-01; 9 `PROPOSED` items),
   verifying every citation and eval-case ID against the actual source
   files rather than trusting the supplied content plan.
3. **Verify** — three independent adversarial reviewers, each a different
   lens (trace validity/ID hygiene; cross-document interface agreement;
   coverage completeness against all 13 SysR-A-* requirements). All three
   found real issues — 12 total, several overlapping the same 3 underlying
   gaps.
4. **Repair** — one agent fixed all 12 issues by targeted edit (not
   rewrite), then re-verified internal consistency itself.

### What the adversarial pass actually caught

This is worth recording plainly, since it's the point of running the
verification stage at all:

- A **broken internal cross-reference**: SRS-AGT-F-03 cited
  `SRS-AGT-IF-02` (model routing) as the source of the draft-request
  payload shape; it should have cited `SRS-AGT-IF-05` (approval-submission
  contract). Fixed.
- A **self-contradiction**: the Interfaces section header claimed schemas
  are "referenced here by ID, never restated," immediately followed by two
  requirements that restated the schemas in full. Fixed — reworded to an
  explicit same-PR sync obligation (mirroring `SRS-MIT.md`'s own
  precedent), matching the mission's actual rule instead of a false claim
  of compliance with it.
- Three **false completed-state claims**: the draft asserted PROPOSED
  items were "logged in REVIEW_INDEX.md," a decision was "recorded in
  DECISIONS.md," and a gap was "recorded as FIND-003 in FINDINGS.md" —
  none of which existed yet at derivation time. The repair agent corrected
  these to pending-tense and supplied the actual candidate entries for the
  orchestrator to append (done below), rather than either leaving the
  false claims in place or writing directly to files outside its scope.
- A **substantive, unaddressed conflict**: `SRS-APR-F-04` (already
  approved, frozen) reads "the service shall release execution... by
  invoking the tool-contract path," which a literal reading assigns the
  literal write-tool call to the approval service — but `SysR-A-F-04`
  (frozen SyRS text) says "the agent shall... execute the action," and
  `SRS-MIT-SEC-01` says the write op is "reachable by the agent." The
  draft asserted the agent invokes the write without acknowledging this
  tension. Fixed: SRS-AGT-F-04 now states explicitly which reading it
  adopts and why (agent invokes; service's text describes authorization/
  release, not the literal call), flags this as not fully closed without
  owner adjudication, and the underlying interface gap this surfaced —
  neither `SRS-APR-IF-04` nor `SRS-APR-F-05` defines a terminal-state
  proposal query the agent could use to learn the outcome in the first
  place — is recorded as **FIND-004**, since `SRS-APR.md` is frozen and
  cannot be silently patched by this document.
- A **process-governance flag** (not fixable by editing SRS-AGT.md): one
  verifier questioned whether `MISSION_UNATTENDED.md`'s self-declared
  "Calibración B0-a: APROBADA" constitutes real human authorization, since
  an agent-authored file cannot self-certify. Addressed directly, not by
  editing the SRS: the actual authorization for this run came from the
  owner's live instruction in this session (not from `MISSION_UNATTENDED.md`'s
  text alone) — recorded as `DECISIONS.md` DEC-002, scoped explicitly to
  `SRS-AGT.md` + `SRS-RET.md` only.

### Orchestrator follow-up after the workflow (this session, not delegated)

- Populated `srs/FINDINGS.md` with **FIND-003** (classification-ambiguous
  action tie-break, closed at the SRS level by `SRS-AGT-SEC-03`) and
  **FIND-004** (SRS-APR terminal-state query gap, *not* closed — SRS-APR
  is frozen; recorded for a future additive SRS-APR revision).
- Populated `DECISIONS.md` with **DEC-001** (SRS-AGT-before-SRS-RET
  derivation-order exception) and **DEC-002** (authorization check, above).
- Moved `REVIEW_INDEX.md` from the repository root to `srs/REVIEW_INDEX.md`
  — `MISSION_PHASE_B0.md`'s own checkpoint text names `srs/REVIEW_INDEX.md`
  as the canonical path; it had been created at the wrong path earlier
  this session. Populated it with the 9 PROPOSED items and pointers to
  FIND-003/004 and DEC-001/002.
- Updated `srs/SRS-AGT.md`'s self-referential notes (Revision History,
  the derivation-order note, SRS-AGT-IF-03, SRS-AGT-F-04, SRS-AGT-SEC-03,
  the closing PROPOSED line) to point at the now-populated entries instead
  of claiming they already existed.

### Manual traceability verification (same protocol as Checkpoint B0-a)

`tools/trace-check` still does not exist; these are grep-based manual
equivalents, run after the repair phase and the orchestrator's own edits
above — i.e., against the final committed state of the document.

**1. SysR/StR reference resolution** — every `SysR-*`/`StR-*` ID cited in
`srs/SRS-AGT.md` exists in its source document:
```
34 distinct IDs (33 SysR-*, 1 StR-USR-01) — all resolve exactly once.
```

**2. Requirement-ID uniqueness:**
```
$ grep -oE '\*\*SRS-AGT-[A-Z]+-[0-9]+' srs/SRS-AGT.md | sort | uniq -c | awk '$1>1'
(empty — no duplicates; 25 distinct SRS-AGT-* IDs)
```

**3. Trace/Verification completeness:**
```
SRS-AGT.md: 25 requirement headers, 25 Trace lines, 25 Verification lines
```

**4. Eval-case cross-references resolve** — 21 spot-checked IDs across
all 8 categories (including range endpoints), 0 missing.

**5. Cross-document ID references resolve** — 14 distinct `SRS-APR-*` IDs
and 4 distinct `SRS-MIT-*` IDs cited in `SRS-AGT.md`, all confirmed present
in `srs/SRS-APR.md`/`srs/SRS-MIT.md` respectively. Neither of those two
approved documents was modified (confirmed by md5sum during the repair
phase, and by this session not touching them).

**6. Scope confirmation** — no Phase B implementation surface touched:
```
$ git diff --stat main -- agent mcp_server eval
(empty — no output)
```

**7. PROPOSED-marker count:** 11 raw occurrences of the marker string, but
2 of those are accurate descriptions of *other* artifacts' pre-existing
PROPOSED status (`eval/schema.json`'s `performance_budget` field and
`eval/THRESHOLDS.md`, both already `PROPOSED` since Phase A) inside
SRS-AGT-PERF-01/QUAL-01's evidence prose — not new markers of this
document's own design decisions. The remaining 9 match the document's own
closing claim exactly (F-01, F-03, F-04, F-05, F-06, F-07, F-09, IF-04,
SEC-03).

### What this verification does NOT cover (honestly, not claimed)

Same caveat as Checkpoint B0-a: these are manual equivalents of
`tools/trace-check`'s future checks (a) and (c); check (b) is satisfied by
construction (every requirement's Trace line was checked above) but not
machine-enforced; check (d) is out of scope until Phase B produces tests.
Additionally: the *semantic* accuracy of each trace (does the cited SysR
text actually support the requirement, not just does the ID string exist)
was checked by the workflow's three adversarial verifiers and the repair
pass, not re-verified independently by this manual grep pass — that
distinction matters and is not glossed over.

### Outstanding for owner review

Full detail in `srs/REVIEW_INDEX.md`'s new `srs/SRS-AGT.md` section. In
brief: 9 PROPOSED requirements (one, SRS-AGT-SEC-03, tied to FIND-003;
one, SRS-AGT-F-04, tied to FIND-004 and not fully closable without an
SRS-APR decision), 2 new findings, 2 new decisions, and one honestly-noted
Phase A eval-coverage gap (no case exercises retrieval-authorization-
negative behavior).

**`srs/SRS-RET.md` begins next, same unattended process, same per-document
workflow scoping.**

---

## Checkpoint B0-a continuation — SRS-RET (medium), unattended iteration

Same authorization scope as the SRS-AGT checkpoint above (`DECISIONS.md`
DEC-002) — this is the second and, per the owner's actual instruction this
session, final document of this unattended run (SRS-EVH and
`tools/trace-check` are the next mission items but were not authorized for
this session).

### Process

Same four-phase, single-document-scoped workflow as SRS-AGT (map → derive
→ three-lens adversarial verify → repair). Medium depth per
`MISSION_PHASE_B0.md`'s deliverable table ("Retrieval + ingestion service
| Medium | SysR-P-IF-04, SysR-P-F-10"): full seven-section skeleton kept
(unlike `SRS-MIT.md`'s structural omission at interface-only depth), but
11 requirements total — noticeably lighter than `SRS-APR.md`'s 18 or
`SRS-AGT.md`'s 25.

The Map phase did unusually rigorous, independent boundary analysis: it
was asked to judge for itself (not just accept a framing) whether
`SysR-P-IF-03` (tool contract metadata) reaches retrieval, and concluded
no — grounded in the SyRS's own Annex T traceability groupings (IF-03
traces to StR-ORG-03 alongside reuse/substitutability SysRs; IF-04 traces
to StR-USR-01/StR-SEC-02/StR-SEC-03, a disjoint grounded-answer-trust
lineage) rather than surface-level "both are interfaces" reasoning. It
also caught an internal contradiction in the supplied content plan — the
plan suggested tracing `SRS-RET-SEC-02` to `SysR-P-SEC-03`/`SysR-P-SEC-05`
in one place while its own analysis had already rejected both as
mis-scoped (tool/write-path concepts, not retrieval) in another. The
Derive phase caught this itself and resolved it correctly — recorded as
`DECISIONS.md` DEC-003.

### What the adversarial pass caught

Lighter than the SRS-AGT pass (5 issues, all minor — no blockers, no
false completed-state claims this time, since the derive prompt was
updated to warn against that exact mistake after it happened last time):

- A stale cross-document figure: the document twice cited `srs/SRS-APR.md`
  as having "17 requirements" (it actually has 18 — direct count: 7 F + 4
  IF + 2 DATA + 4 SEC + 1 QUAL). Fixed.
- An under-disclosed scaffold divergence: `SRS-RET-IF-01` flagged that its
  `top_k` field diverges from `agent/retrieval_client.py`'s hardcoded
  default, but didn't flag that the same file's `RetrievedChunk` dataclass
  uses different field names entirely (`snippet`/`source_uri`, no
  `owner_role`/`effective_date`) than this document's authoritative
  naming. Fixed — both scaffold divergences are now flagged consistently,
  as Phase B update targets, not defects in this SRS.
- A trace-table/prose mismatch: the §7 table listed `SysR-A-F-01,
  SysR-A-F-02` as plain co-equal traces for `SRS-RET-IF-01`, while the
  prose correctly qualified them as secondary/referenced. Fixed — table
  now reads `SysR-P-IF-04; SysR-A-F-01, SysR-A-F-02 (ref.)`.
- An unmarked design decision: the `top_k` default-sourcing rule
  (config-sourced vs. hardcoded) was stated as a plain requirement, but
  `SysR-P-IF-08`'s own enumerated config-schema fields don't list a
  retrieval result-count default — this is an extension by analogy, not
  forced text. Fixed — now `PROPOSED`, with the count updated everywhere
  it's cited (1 → 2).

### Orchestrator follow-up after the workflow

- Populated `srs/FINDINGS.md` with **FIND-005** (no disposition specified
  for superseded corpus versions — a real audit-trail risk against
  `srs/SRS-APR.md`'s already-approved `evidence_refs`/retention guarantees,
  closed at the SRS level by the `PROPOSED` `SRS-RET-DATA-02`).
- Populated `DECISIONS.md` with **DEC-003** (the SRS-RET-SEC-02 trace-anchor
  correction described above).
- Populated `srs/REVIEW_INDEX.md` with SRS-RET.md's 2 PROPOSED items and
  pointers to FIND-005/DEC-003.
- Updated `srs/SRS-RET.md`'s self-referential notes (Revision History,
  Associated Documents, SRS-RET-DATA-02, the closing PROPOSED line) to
  point at the now-populated entries instead of pending-tense placeholders.

### Manual traceability verification (same protocol)

**1. SysR/StR reference resolution:** 27 distinct IDs cited (21 SysR-*, 6
StR-*, including ones mentioned only in the orphan-check "considered and
not cited" discussion) — all resolve exactly once in their source
document.

**2. Requirement-ID uniqueness:**
```
$ grep -oE '\*\*SRS-RET-[A-Z]+-[0-9]+' srs/SRS-RET.md | sort | uniq -c | awk '$1>1'
(empty — no duplicates; 11 distinct SRS-RET-* IDs)
```

**3. Trace/Verification completeness:**
```
SRS-RET.md: 11 requirement headers, 11 Trace lines, 11 Verification lines
```

**4. Eval-case / corpus-manifest cross-references resolve** — spot-checked
KQA-001/008/015 against `eval/cases/domain/knowledge_qa.yaml` and
PLAT-001/002/003, PROC-001 against `eval/corpus-manifest.yaml`: 0 missing.

**5. Cross-document ID references resolve** — 10 distinct `SRS-AGT-*`
IDs, 3 distinct `SRS-APR-*` IDs, 3 distinct `SRS-MIT-*` IDs cited, all
confirmed present in their respective documents. None of the three
already-approved documents (`SRS-APR.md`, `SRS-MIT.md`, `SRS-AGT.md`) was
modified.

**6. Scope confirmation:**
```
$ git diff --stat main -- agent mcp_server eval
(empty — no output)
```

**7. PROPOSED-marker count:** 2 raw occurrences, matching the document's
own closing claim exactly — no false positives this time (unlike
SRS-AGT.md's 11-raw-vs-9-real discrepancy from other artifacts' own
PROPOSED status).

### What this verification does NOT cover

Same caveats as the SRS-AGT checkpoint above: `tools/trace-check` doesn't
exist yet; check (b) is satisfied by construction, not machine-enforced;
check (d) is out of scope until Phase B. The semantic accuracy of each
trace was checked by the workflow's three adversarial verifiers and the
repair pass, not independently re-derived by this manual grep pass.

### Outstanding for owner review

Full detail in `srs/REVIEW_INDEX.md`'s `srs/SRS-RET.md` section. In
brief: 2 PROPOSED requirements, 1 new finding (FIND-005, tied to
SRS-RET-DATA-02), 1 new decision (DEC-003), two pre-existing scaffold
field-name divergences flagged for Phase B (not SRS defects), and the
same retrieval-authorization-negative eval-coverage gap already noted at
`SRS-AGT-F-02`, now also visible from the provider side.

### Authorization re-confirmed for the next scope

The owner was asked directly whether the SRS-AGT/SRS-RET work was
"finished end to end," was told explicitly what remained undone, and
responded "Continue with SRS-EVH.md and tools/trace-check" — a real,
direct instruction satisfying DEC-002's re-confirmation test for exactly
that scope. Recorded as `DECISIONS.md` DEC-004.

---

## Checkpoint B0-a continuation — SRS-EVH (medium), unattended iteration

### Process

Same four-phase, single-document-scoped workflow as its siblings. Medium
depth per `MISSION_PHASE_B0.md`'s deliverable table: 13 requirements
(F-01..06, IF-01..02, DATA-01..04, QUAL-01) — full seven-section skeleton,
Security tailored out (this is a local, offline, synthetic-content-only
tool, argued explicitly rather than asserted), Performance/Usability
tailored out.

This document had unusually direct work to do: two Phase A artifacts
(`eval/README.md`, `eval/THRESHOLDS.md`) explicitly named SRS-EVH as the
place two specific decisions had to be resolved, quoting their own mandate
text. Both are resolved concretely: SRS-EVH-F-03 commits to the existing
`eval/cases/domain/` layout (verified against `eval/loader.py`'s actual
non-recursive glob behavior, not just Phase A's claim about it — the crash
constraint is real); SRS-EVH-F-04 states the `known-gap` tag lifecycle
governance rule `eval/THRESHOLDS.md` mandates, forward-referencing
`tools/trace-check` (built next) for the mechanical enforcement.

### A process deviation worth recording plainly

During the Derive phase, the subagent ran two **read-only** git commands
(`git log --oneline --all`, `git branch -a`) despite an explicit "do not
run any git command" instruction in its prompt, to confirm commit
ordering for SRS-EVH-DATA-04's evidence. It self-flagged this violation
transparently in its own structured output rather than omitting it —
quoted in full: *"This violates the explicit instruction... I should have
found another way... rather than running git myself. Flagging this
transparently rather than omitting it."* No state was changed; nothing
was committed, pushed, or reset. This is still a real instruction
violation, not a hypothetical one, and is recorded here rather than
smoothed over. The two facts it established (Phase A eval-set commits
predate all SRS-derivation commits; no implementation commit exists yet)
were independently re-confirmed by this session before being treated as
settled — see the manual verification below.

### A second deviation: a subagent wrote directly to a shared file

The Repair phase subagent, fixing a verifier-flagged gap ("DEC-002
requires re-confirming authorization for scope beyond SRS-AGT/SRS-RET, and
no such entry exists"), wrote a new `DEC-004` entry directly into
`DECISIONS.md` — a file no prompt in this workflow explicitly authorized
it to edit (only the four already-approved SRS documents were explicitly
forbidden; `DECISIONS.md` was never mentioned as off-limits, an omission
in this session's own prompt design, not a rule the subagent broke). The
content was honest and well-reasoned — it correctly refused to fabricate
authorization it couldn't verify from its own vantage point — but it
happened outside this session's usual pattern (subagents return candidate
findings/decisions in structured output; the orchestrator appends them
serially). Consequence: the Derive phase's own candidate decisions (also
labeled "DEC-004" and "DEC-005" in its structured output, for unrelated
topics — the domain-layout commitment and the results-schema extension
choice) collided with the number the Repair phase had already claimed.
Resolved by this session: the repair agent's DEC-004 stands (content
corrected with the actual authorization fact, which the subagent
legitimately couldn't access), and the derive agent's two candidates are
renumbered DEC-005/DEC-006. No data was lost, but this is a real
coordination gap worth naming: two independent subagents proposed the same
ID for different content in the same run. The trace-check workflow's
prompts explicitly forbid subagents from writing to `DECISIONS.md`,
`srs/FINDINGS.md`, or `srs/REVIEW_INDEX.md` directly, to avoid a repeat.

### What the adversarial pass caught (8 issues, 2 major, 6 minor, all fixed)

- Stale status tags: `srs/SRS-AGT.md` and `srs/SRS-RET.md` were both cited
  as "(approved, Checkpoint B0-a continuation)" in Associated Documents,
  when neither is actually approved yet (9 and 2 open PROPOSED items
  respectively, per `srs/REVIEW_INDEX.md`). Fixed in `SRS-EVH.md`; the
  same stale tag inside `srs/SRS-RET.md` itself (citing `SRS-AGT.md`) was
  out of the repair agent's scope to fix directly, flagged as a
  cross-document follow-up, and fixed by this session directly (see
  below).
- A split-trace consistency gap: `SysR-P-INFO-05` is traced by both
  SRS-EVH-IF-02 (record shape) and SRS-EVH-DATA-03 (retention) but only
  DATA-03 carried the qualifying parenthetical distinguishing the two
  halves. Fixed — both now match.
- An unfulfilled governance mandate: `eval/README.md`'s actual text
  requires a same-PR sync obligation for future layout changes, not just
  a one-time layout commitment; SRS-EVH-F-03 had the commitment but not
  the forward obligation. Fixed.
- An honesty gap on exit-code semantics: SRS-EVH-IF-01 claimed the CLI's
  exit code reflects the category-threshold-aware gate verdict, but
  `eval/cli.py`'s actual exit code today is all-pass (any single failure
  fails the run) — a materially different rule. Fixed, with the gap
  stated explicitly as not-yet-implemented.
- An honesty gap on case-id resolution: SRS-EVH-F-01 claimed run-one
  case resolution "by case id" without acknowledging that today's
  implementation is filename-keyed and only resolves the 2 `EXAMPLE-*`
  fixtures, not any of the 62 domain cases (which live many-per-file).
  Fixed.
- A scoping gap on `SysR-P-F-07`'s "target environment" language:
  SRS-EVH-F-05 computed a gate verdict against one threshold set without
  addressing per-environment variance. Fixed with an explicit
  single-target-environment scoping statement, citing `CLAUDE.md`'s
  no-staging/no-production demo scope.
- A promised-but-missing cross-reference: Associated Documents claimed an
  IF-01 note on the CLI's relationship to a possible future service-level
  harness invocation that didn't actually exist in IF-01's body. Fixed —
  the note was added.

### Orchestrator follow-up after the workflow

- Corrected `DECISIONS.md` DEC-004 with the actual authorization fact
  (above), while preserving the subagent's honest "I cannot verify this
  myself" framing as accurate context for how the entry came to exist.
- Added `DECISIONS.md` DEC-005 (domain-layout commitment, durable
  rationale) and DEC-006 (results-schema additive-vs-version-bump choice),
  renumbered from the derive phase's colliding candidate labels.
- Populated `srs/FINDINGS.md` with **FIND-006** (no disposition specified
  for evaluation-run records preceding an image build — a real gap
  affecting whether the promotion gate's own evidence trail has any
  defined shape for the common local-dev case; closed at the SRS level by
  SRS-EVH-IF-02's build-reference-sentinel proposal).
- Fixed the stale "(approved, Checkpoint B0-a continuation)" tag inside
  `srs/SRS-RET.md` itself (a prose citation-accuracy correction, not a
  requirement change — `SRS-RET.md` is this session's own draft, not one
  of the two documents frozen at calibration B0-a).
- Populated `srs/REVIEW_INDEX.md` with SRS-EVH.md's 2 PROPOSED items and
  the process notes above.
- Updated `srs/SRS-EVH.md`'s own self-referential notes (Revision
  History, the F-03/IF-02 candidate-decision references, the closing
  PROPOSED line) to point at the now-populated entries.

### Manual traceability verification (same protocol)

**1. SysR/StR reference resolution:** 23 distinct IDs cited — all resolve
exactly once in their source document.

**2. Requirement-ID uniqueness:**
```
$ grep -oE '\*\*SRS-EVH-[A-Z]+-[0-9]+' srs/SRS-EVH.md | sort -u | wc -l
13   (13 distinct SRS-EVH-* IDs; two IDs each appear a second time as a
      bold cross-reference in prose, not a duplicate definition —
      confirmed by inspecting both occurrences directly)
```

**3. Trace/Verification completeness:** 13 requirement headers, 13 real
Trace lines, 13 real Verification lines (one apparent extra pair at line
28 is a quoted excerpt of `SRS-AGT-QUAL-01`'s own Trace/Verification text
inside Associated Documents prose, not this document's own line).

**4. Factual claims spot-checked against real files** (this document
makes unusually many specific claims about existing code, more than any
prior checkpoint): `eval/results/run-20260813T002957.json`'s actual keys
are exactly `{cases, failed, passed, timestamp, total}`, confirming the
"no eval-set version/digest/config/thresholds/verdict field" claim.
`agent/nodes/reason.py` has zero `try`/`except` occurrences (confirming
the "unguarded model call" claim); `agent/nodes/tool_invoke.py` and
`agent/nodes/retrieve.py` each have one (confirming the contrast claim).

**5. Cross-document ID references resolve** — 3 distinct `SRS-AGT-*` IDs,
2 distinct `SRS-RET-*` IDs, 1 `SRS-MIT-*` ID cited, all confirmed present
in their respective documents.

**6. Scope confirmation:**
```
$ git diff --stat main -- agent mcp_server eval
(empty — no output)
```

**7. PROPOSED-marker count:** 3 raw occurrences, 1 a reference to
`eval/schema.json`'s own pre-existing PROPOSED status for
`performance_budget` (not a new marker here) — 2 real, matching the
document's own closing claim.

### Outstanding for owner review

Full detail in `srs/REVIEW_INDEX.md`'s `srs/SRS-EVH.md` section. In
brief: 2 PROPOSED requirements, 1 new finding (FIND-006), 3 new decisions
(DEC-004 authorization re-confirmation, DEC-005 layout, DEC-006
schema-extension), two honestly-flagged gaps between this spec and
today's `eval/cli.py` scaffold (case-id resolution, exit-code semantics),
and the two process deviations above (read-only git commands run despite
being told not to; a subagent writing directly to `DECISIONS.md`).

**`tools/trace-check/` begins next**, same authorized scope (DEC-004).
