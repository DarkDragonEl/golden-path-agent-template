# Review Index — Unattended Iteration

Consolidated pointer, per SRS document produced during the unattended
Phase B0 continuation (`MISSION_UNATTENDED.md`), to everything a human
reviewer should check before accepting it: `PROPOSED` requirements,
`DECISIONS.md` entries made while deriving it, and the manual
traceability-verification evidence (same protocol as
`reports/feature-phase-b0-srs.md`, until `tools/trace-check` exists).

This index does not itself approve anything — it is the owner's checklist
for the review pass at the end of this iteration (or at the next natural
checkpoint).

---

## srs/SRS-AGT.md (Checkpoint B0-a continuation, unattended iteration) — RESOLVED at Checkpoint B0-b (2026-08-21)

**All 9 PROPOSED items below were reviewed and accepted as drafted by the
owner at Checkpoint B0-b.** Item 3 (SRS-AGT-F-04) was adjudicated jointly
with `srs/SRS-APR.md`'s SRS-APR-F-04 under the agent-as-invoker model —
see `DECISIONS.md` DEC-008, which also closes FIND-004 via a new, additive
`SRS-APR-IF-05`. Item 9 (SRS-AGT-SEC-03) closes FIND-003 at the SRS level;
the SyRS-level clause is explicitly deferred to a future SyRS revision,
per the owner's own instruction, not silently dropped. The list below is
kept as the historical record of what was reviewed.

Full-depth derivation, 25 requirements (F-01..09, IF-01..09, DATA-01,
SEC-01..04, PERF-01, QUAL-01). Adversarially verified by three independent
subagent reviewers (trace validity, cross-document agreement, coverage
completeness) and repaired once before this entry was written — see
`reports/feature-phase-b0-srs.md` for the manual grep-based traceability
protocol run after repair.

**9 PROPOSED items — owner must decide each:**

1. **SRS-AGT-F-01** — citation granularity: per corpus-derived claim, not
   per answer. Check: is per-claim too strict for the demo, or exactly the
   groundedness signal wanted?
2. **SRS-AGT-F-03** — exactly one output type (recommended action /
   troubleshooting plan / draft request) per conversational turn.
3. **SRS-AGT-F-04** — decision-outcome query mechanism, and that the
   *agent* (not the approval service) issues the literal
   `itsm_create_request` call on approval. **Depends on FIND-004** — this
   PROPOSED item can't be fully closed until the owner decides whether
   `SRS-APR.md` gets a new terminal-state query interface. Read FIND-004
   in `srs/FINDINGS.md` first.
4. **SRS-AGT-F-05** — escalation reference is a static, environment-
   configured contact, not a live agent-initiated handoff.
5. **SRS-AGT-F-06** — a "detected" injection attempt is defined as any
   policy-enforcement refusal, not an independent content classifier.
6. **SRS-AGT-F-07** — one "step" (for the step-limit) = one
   reasoning/tool-execution loop cycle, tool call or not.
7. **SRS-AGT-F-09** — policy bundle is read once at task start, not
   hot-reloaded mid-task.
8. **SRS-AGT-IF-04** — agent looks up SRS-MIT's tool-catalog metadata at
   runtime as the source of truth for tool identity, vs. treating the two
   tool schemas as fixed.
9. **SRS-AGT-SEC-03** — classification-ambiguous actions fail closed to
   "requires approval." **Tied to FIND-003** in `srs/FINDINGS.md` — read
   that first; this is the SRS-level fix for a gap in
   SysR-P-SEC-05/SysR-P-POL-01 the owner may also want closed at the SyRS
   level.

**Also needs owner attention (not a PROPOSED marker, but new since
Checkpoint B0-a):**

- **FIND-003, FIND-004** in `srs/FINDINGS.md` — new findings from this
  derivation. FIND-004 in particular is a gap in the already-approved
  `srs/SRS-APR.md` (no terminal-state proposal query interface), which
  this document cannot close itself since SRS-APR is frozen.
- **DEC-001, DEC-002** in `DECISIONS.md` — the SRS-AGT/SRS-RET derivation-
  order exception, and a record of why this run proceeded without an
  additional stop despite one of the adversarial verifiers flagging that
  question. Worth a skim even though neither blocks anything.
- One coverage gap noted honestly inside the document itself (not a
  PROPOSED item): no Phase A eval case exercises retrieval-authorization-
  negative behavior (SRS-AGT-F-02/IF-03) or classification-ambiguous
  actions (SRS-AGT-SEC-03) — both recommended as future eval-set additions
  in `eval/cases/domain/`.

## srs/SRS-RET.md (Checkpoint B0-a continuation, unattended iteration; Medium depth) — RESOLVED at Checkpoint B0-b (2026-08-21)

**Both PROPOSED items below were reviewed and accepted as drafted by the
owner at Checkpoint B0-b.** Item 1 (SRS-RET-DATA-02) closes FIND-005. The
list below is kept as the historical record of what was reviewed.

11 requirements (F-01..04, IF-01..03, DATA-01..02, SEC-01..02). Same
adversarial-verify-then-repair process as SRS-AGT.md; 5 issues found (all
minor: a stale requirement-count comparison, an under-disclosed scaffold
divergence, a trace-table/prose mismatch, and an unmarked design decision)
and fixed. Notably: this document is the retrieval-service *provider* side
of the contract `srs/SRS-AGT.md`'s SRS-AGT-IF-03 already states as the
*consumer's* requirement — SRS-RET-IF-01 was checked field-for-field
against SRS-AGT-IF-03 and confirmed to satisfy and widen it, never narrow
it (see `DECISIONS.md` DEC-001).

**2 PROPOSED items — owner must decide each:**

1. **SRS-RET-DATA-02** — a superseded corpus document version remains
   retrievable (by explicit version, via SRS-RET-IF-02) after a refresh,
   rather than being deleted. **Tied to FIND-005** in `srs/FINDINGS.md` —
   read that first: this closes a real gap where an approval proposal's
   `evidence_refs` (in the already-approved `srs/SRS-APR.md`) could cite a
   corpus version that later becomes unverifiable if superseded versions
   aren't retained.
2. **SRS-RET-IF-01** — the `top_k` result-count default, when omitted by
   the caller, is sourced from deployment configuration rather than a
   fixed/hardcoded value (the existing `agent/retrieval_client.py` scaffold
   hardcodes `top_k: int = 5`, but that scaffold is a pre-existing
   `TODO(domain)` placeholder, not a normative source).

**Also needs owner attention:**

- **FIND-005** in `srs/FINDINGS.md` — new finding from this derivation,
  see above.
- **DEC-003** in `DECISIONS.md` — records why SRS-RET-SEC-02 (no
  client-facing write path) traces to SysR-P-IF-04/SysR-P-F-10 rather than
  the SysR-P-SEC-03/SysR-P-SEC-05 anchors a naive pattern-match to
  SRS-AGT-SEC-02 would have suggested; worth a skim to confirm the
  reasoning holds.
- Two things the derivation flagged as *pre-existing scaffold divergence*,
  not SRS defects, but worth the owner's awareness before Phase B starts:
  `agent/retrieval_client.py`'s `RetrievedChunk` dataclass uses different
  field names (`snippet`, `source_uri`, no `owner_role`/`effective_date`)
  than SRS-RET-IF-01's authoritative naming (`passage_text`, `source`,
  `owner_role`, `effective_date`) — both are `TODO(domain)` placeholders
  Phase B will need to update to match this SRS, not the reverse.
- One coverage gap already noted at `srs/SRS-AGT.md`'s SRS-AGT-F-02,
  restated here from the provider side (SRS-RET-F-03/IF-01): no Phase A
  eval case exercises retrieval-authorization-negative behavior. Same
  future eval-set addition would close both.

## srs/SRS-EVH.md (Checkpoint B0-a continuation; Medium depth) — RESOLVED at Checkpoint B0-b (2026-08-21)

**Both PROPOSED items below were reviewed and resolved by the owner at
Checkpoint B0-b**, after being held out of the initial closure pass
pending direct review of their exact text. SRS-EVH-F-04 was resolved as a
declarative signal (the `known-gap` tag itself, read from the
version-controlled thresholds file) rather than static code inspection —
self-verifying, since a dishonestly-removed tag fails the gate unless the
fallback actually works. SRS-EVH-IF-02 was accepted with one added
condition: a `build_reference_type` companion field, closing FIND-006 and
`DECISIONS.md` DEC-006. The list below is kept as the historical record of
what was reviewed.

13 requirements (F-01..06, IF-01..02, DATA-01..04, QUAL-01). Same
adversarial-verify-then-repair process as its siblings; 8 issues found (2
major, 6 minor) and fixed. This document resolves two decisions Phase A's
`eval/README.md` and `eval/THRESHOLDS.md` explicitly deferred to it: the
`eval/cases/domain/` layout (committed to, unchanged — DEC-005) and the
`known-gap` tag lifecycle governance rule (SRS-EVH-F-04, mechanism forward-
referenced to `tools/trace-check`, built next).

**Process note the owner should know about:** during the Derive phase, the
subagent ran two read-only git commands (`git log --oneline --all`,
`git branch -a`) despite an explicit "do not run any git command"
instruction, to confirm commit ordering for SRS-EVH-DATA-04's evidence. It
self-flagged this violation transparently rather than omitting it. No
state was changed, nothing was committed or pushed — but it's a real
deviation from instructions, not a hypothetical one, and is recorded here
for visibility. Separately, the Repair phase subagent wrote directly to
`DECISIONS.md` (creating DEC-004) to flag an authorization gap it correctly
couldn't resolve itself — see DEC-004's own text; the orchestrator has
since resolved it with the actual authorization fact, but the fact that a
subagent wrote to a shared coordination file outside its assigned
document is itself a process note worth the owner's awareness (harmless
here, but a numbering collision risk in general).

**2 PROPOSED items — owner must decide each:**

1. **SRS-EVH-F-04** — the mechanical signal `tools/trace-check` uses to
   detect that the model-failure fallback gap has closed (static
   inspection of `agent/nodes/reason.py` vs. an explicit sentinel/manifest
   flag).
2. **SRS-EVH-IF-02** — two sub-choices: (a) results-schema extension is
   additive fields, not a version bump (durable rationale at DEC-006); (b)
   a build-reference sentinel (e.g. git commit hash, or an explicit
   `"local-dev-uncommitted"` marker) stands in for "image digest" on local
   runs that precede any image build. **Tied to FIND-006** in
   `srs/FINDINGS.md` — read that first.

**Also needs owner attention:**

- **FIND-006** in `srs/FINDINGS.md` — new finding: no disposition
  specified for evaluation-run records preceding an image build, closed
  at the SRS level by SRS-EVH-IF-02's build-reference-sentinel proposal.
- **DEC-004** in `DECISIONS.md` — records that this session's own
  authorization for `srs/SRS-EVH.md` + `tools/trace-check/` traces to a
  direct instruction from you this session, not from `MISSION_UNATTENDED.md`'s
  text alone. Worth a skim to confirm the record is accurate.
- **DEC-005, DEC-006** — the domain-layout commitment and the
  results-schema extension choice, given durable homes beyond the SRS
  text itself.
- Two honestly-flagged implementation gaps between this spec and today's
  scaffold, not SRS defects but useful context before Phase B starts:
  `eval/cli.py`'s `--case <id>` resolution is filename-keyed and only
  resolves the 2 `EXAMPLE-*` fixtures, not any of the 62 domain cases
  (SRS-EVH-F-01); its exit code is currently all-pass, not
  category-threshold-aware (SRS-EVH-IF-01).

## tools/trace-check/ and srs/DEFERRED.md (Checkpoint B0-a continuation)

Not an SRS document — the executable traceability CLI `MISSION_PHASE_B0.md`
deliverable 2 requires, plus `srs/DEFERRED.md` (deliverable 3, populated
from the tool's own real output). No PROPOSED items (this is code, not a
requirements document), but several things worth the owner's attention.

**What it does:** parses StR/SysR/SRS IDs and inline Trace lines from
`StRS_Agentic_AI_Platform_EN.md`, `SyRS-AGP-001_EN.md`, and all five
`srs/SRS-*.md` files; parses eval case IDs from `eval/cases/`; implements
checks (a) SysR→SRS coverage, (b) SRS→SysR trace validity, (c) no
broken/orphan IDs, (d) SRS-F→test/eval coverage (skipped in `--docs-only`
mode, since Phase B has no tests yet); emits a human-readable report and
`reports/trace-check.json`; exits non-zero on any active-check violation.
`make trace` runs it. 56 tests pass (`make test`), including 42 dedicated
to this tool.

**Current real state (dogfooded, not just built):** checks (a)/(b)/(c) all
**PASS** — 44/63 SysRs traced by the five SRS documents, 19/19 remaining
correctly listed in `srs/DEFERRED.md` with individual reasons, 0 broken
IDs, 0 trace-validity violations. Check (d) is SKIPPED as designed. Exit
code 0.

**Adversarial verification caught two real bugs before this was trustworthy
— worth knowing about, not just "it was reviewed":**
1. A **blocker-severity false negative**: the tool's own test fixture data
   (containing text shaped like `# verifies: SRS-APR-F-03`) was being
   picked up by its own naive text scan when it swept its own test file —
   meaning check (d), once Phase B exists, would have silently under-
   reported real violations because its own tests looked like coverage
   evidence. Fixed by switching to Python's `tokenize` module so text
   inside string literals can never be mistaken for a real comment; a
   second blocker-severity false negative (a wholly fabricated eval-case
   citation like `FAKE-001..999` was never even recognized as a
   reference, since the scan only matched already-known prefixes) was
   also found and fixed. Both are exactly the "tool wrongly says PASS"
   failure mode that matters most for a tool whose entire job is catching
   violations — see `tools/trace-check/README.md` and the source
   comments for full detail.
2. A **major false positive**: a known eval-case prefix ('OPS', from
   `operational.yaml`) matched as a bare substring inside the unrelated,
   valid SysR id `SysR-P-OPS-02`, which would have flagged a correct
   citation as broken the moment any SRS document wrote one. Fixed with a
   negative-lookbehind guard.

Both fixes have dedicated regression tests. Worth the owner's spot-check
given how easy this class of self-referential bug is to miss.

**One SysR resolved differently than the other 19:** `SysR-P-OPS-03` was
not deferred — `tools/trace-check` surfaced it as untraced, but on
inspection it was already substantively covered by `SRS-AGT-F-09`, just
never traced there. Fixed with an added trace, not a deferral — see
`DECISIONS.md` DEC-007. This is the one place this checkpoint reached back
into an earlier document (`srs/SRS-AGT.md`, still an open draft, not
frozen) rather than only writing new files.
