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
