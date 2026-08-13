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
