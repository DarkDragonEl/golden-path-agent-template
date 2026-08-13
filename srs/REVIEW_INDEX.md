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

## srs/SRS-AGT.md (Checkpoint B0-a continuation, unattended iteration)

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

## srs/SRS-RET.md (Checkpoint B0-a continuation, unattended iteration; Medium depth)

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
