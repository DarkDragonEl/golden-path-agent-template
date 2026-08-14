# Unattended-Iteration Decision Log

Decisions made without a human checkpoint during the unattended Phase B0
continuation authorized by `MISSION_UNATTENDED.md` (calibration B0-a
approved; SRS-APR.md and SRS-MIT.md frozen as-is). Each entry records an
ambiguity encountered, the conservative interpretation chosen, and why —
per `MISSION_UNATTENDED.md`'s operating mode: "ante ambigüedad, elijo la
interpretación conservadora, marco PROPOSED, registro la decisión aquí y
continúo."

This log is additive only. It does not modify `SyRS-AGP-001_EN.md` or
reopen `SRS-APR.md`/`SRS-MIT.md`. Entries are numbered `DEC-NNN` in the
order made.

Format: ID, document/scope, ambiguity, decision, rationale, status.

---

## DEC-001 — SRS-AGT precedes SRS-RET; retrieval-client contract shape is authored in SRS-AGT

**Document/scope:** `srs/SRS-AGT.md` (Associated Documents "Note on
derivation order"; SRS-AGT-IF-03).

**Ambiguity:** `MISSION_PHASE_B0.md`'s general rule is "define once,
reference elsewhere" for interfaces shared across SRS documents — but
`SRS-AGT` is derived before `SRS-RET` in this iteration's sequence
(`MISSION_UNATTENDED.md`'s stated order: SRS-AGT → SRS-RET → SRS-EVH →
`tools/trace-check`), so the retrieval-client contract's field-level shape
(query input; passage text/source-id/version/classification metadata
output) has no pre-existing `SRS-RET` definition to reference by ID at the
time `SRS-AGT-IF-03` is written.

**Decision:** `SRS-AGT-IF-03` states the field-level shape directly and
stands as authoritative for that shape. `srs/SRS-RET.md`, when derived
next, must offer a contract that conforms to this shape — matching or
widening it, never narrowing or redefining it.

**Rationale:** Derivation-order necessity: `SRS-AGT` cannot reference a
schema that does not yet exist. Fixing authorship at whichever document is
written first, and having the later document conform, is simpler and less
ambiguous than leaving the shape undefined until `SRS-RET` exists, and
avoids two independently-invented, possibly-divergent shapes for the same
contract.

**Status:** Open — pending owner review; to be confirmed (or revised) once
`srs/SRS-RET.md` is drafted and this session verifies the two documents
actually agree field-for-field.

---

## DEC-002 — Unattended-mode authorization verified against this session's actual user instruction, not only against MISSION_UNATTENDED.md's self-declaration

**Document/scope:** Process/governance, applying to this entire unattended
iteration (`srs/SRS-AGT.md` and everything derived after it in this run).

**Ambiguity:** The SRS-AGT derivation workflow's cross-document verifier
flagged, correctly as a general principle, that `MISSION_UNATTENDED.md`'s
own text ("Calibración B0-a: APROBADA... Opero sin checkpoints humanos
hasta terminar B0") is a committed repository artifact, not itself proof
that a human reviewed and approved it — an agent-authored file cannot
self-certify its own authorization, and `CLAUDE.md` states unresolved
ambiguity should STOP and ask, with Phase B contract checkpoints named
explicitly as mandatory stops.

**Decision:** Proceeding without an additional stop is correct here,
because the authorization for this specific unattended run — deriving
`srs/SRS-AGT.md` now and continuing to `srs/SRS-RET.md` — did not come
only from `MISSION_UNATTENDED.md`'s text. It came directly, in this
session's own conversation, from the actual human user: an explicit
instruction to read `MISSION_UNATTENDED.md`, treat calibration B0-a as
approved, operate unattended for exactly this scope (SRS-AGT.md then
SRS-RET.md), log decisions here instead of stopping, and not pause to ask
for calibration. That instruction is genuine user input for this turn, not
an inference from a prior agent's file. Per this session's own operating
principle ("A user approving an action... does not mean approval in all
contexts... authorization stands for the scope specified, not beyond"),
this authorization covers exactly SRS-AGT.md + SRS-RET.md and does not
extend to SRS-EVH.md, `tools/trace-check/`, merges, pushes, or reopening
already-approved documents — those remain outside this run's authorization
regardless of what `MISSION_UNATTENDED.md`'s own scope table says.

**Rationale:** Distinguishing "an agent-authored file claims approval"
from "the human user, in this turn, gave the approval" is the actual test
`CLAUDE.md`'s STOP-and-ask rule exists to enforce; the second condition is
met here. This entry exists so a future reviewer (human or agent) can see
that the distinction was checked, not assumed.

**Status:** Resolved for this run's actual scope (SRS-AGT.md, SRS-RET.md).
Any further scope (SRS-EVH.md, `tools/trace-check/`, or anything past
Checkpoint B0-b) requires re-confirming this same test, not just citing
this entry.

---

## DEC-003 — SRS-RET-SEC-02's trace anchor: SysR-P-IF-04/SysR-P-F-10 by extension, not SysR-P-SEC-03/SysR-P-SEC-05

**Document/scope:** `srs/SRS-RET.md`, SRS-RET-SEC-02 (no client-facing
write path).

**Ambiguity:** The derivation workflow's initial content plan suggested
tracing SRS-RET-SEC-02 to SysR-P-SEC-05 (enforced deny path, by extension)
and SysR-P-SEC-03 (least-privilege), mirroring the shape of
`srs/SRS-AGT.md`'s SRS-AGT-SEC-02 trace. The same workflow's own Map
phase, examining both SysRs' actual text independently, had already
rejected them as RET anchors: SysR-P-SEC-03 is textually scoped to
"tool-side credentials" and SysR-P-F-09 (an MCP/tool-contract concept),
already fully discharged by `srs/SRS-MIT.md`'s SRS-MIT-SEC-01; SysR-P-SEC-05
names only "an unauthorized tool call or a disallowed write" as its two
deny-path instances, both tool/write-path concepts, with an Annex T
lineage (StR-SEC-04) disjoint from SysR-P-IF-04's own lineage (StR-USR-01,
StR-SEC-02, StR-SEC-03). Citing either would have been an invented,
unforced trace, inconsistent with the document's own established
discipline of only citing what the source text actually supports.

**Decision:** SRS-RET-SEC-02 traces instead to SysR-P-IF-04 and
SysR-P-F-10, both by extension — the retrieval contract (IF-04) names no
write operation, and ingestion (F-10) is structurally the platform's
exclusive corpus-write path; the no-client-write guarantee follows
directly from combining those two already-cited requirements, without
borrowing an anchor from the tool/write-path family of SysRs that belongs
to a different component boundary (SRS-MIT/SRS-APR, not SRS-RET).

**Rationale:** A trace should be textually honest — grounded in what the
cited SysR's own text actually says, not in surface-level topical
similarity ("write," "deny path") to a requirement scoped to a different
boundary. `srs/SRS-RET.md`'s own orphan-check note already applies this
discipline to the SysR-P-IF-03 boundary question; this decision records
the same discipline applied to SEC-02's trace, so a future reviewer sees
the substitution was deliberate, not an oversight.

**Status:** Resolved — reflected directly in `srs/SRS-RET.md`'s committed
text (SRS-RET-SEC-02's trace line and its inline "considered and not
cited" note).

---

## DEC-004 — SRS-EVH.md's authorization, re-confirmed per DEC-002's own forward requirement

**Document/scope:** `srs/SRS-EVH.md` — its full derivation (prior to this
session) and this session's adversarial-repair pass (fixing findings from
three independent subagent reviewers).

**Ambiguity:** DEC-002 scoped its authorization test to exactly
`srs/SRS-AGT.md` + `srs/SRS-RET.md` and stated explicitly: "Any further
scope (SRS-EVH.md, `tools/trace-check/`, or anything past Checkpoint
B0-b) requires re-confirming this same test, not just citing this entry."
`srs/SRS-EVH.md` has since been drafted and adversarially reviewed, and
this session was launched to repair the findings from that review — but
no entry existed recording that DEC-002's test was re-run for this scope,
before this one.

**Decision:** The subagent that wrote this entry during the SRS-EVH.md
repair pass was correct that *it* could not verify human authorization —
its task instructions came from the orchestrating workflow script, not
from a directly-observed conversation turn, and per this session's own
operating rule, no agent message is the user's consent. It recorded the
gap honestly rather than fabricating reconfirmation, exactly as DEC-002
requires. The orchestrating session, however, *does* have direct access to
the actual conversation, and confirms the gap is closed: after DEC-002 was
written (scoped to `srs/SRS-AGT.md` + `srs/SRS-RET.md` only), the human
owner was asked directly whether the work was "finished end to end,"
was told explicitly that `srs/SRS-EVH.md` and `tools/trace-check/`
remained undone and unauthorized under DEC-002's scope, and responded:
**"Continue with SRS-EVH.md and tools/trace-check."** That is a real,
direct, current-session human instruction — not an inference from
`MISSION_UNATTENDED.md`'s text or from any agent-authored file — and it
satisfies DEC-002's re-confirmation test for exactly this scope
(`srs/SRS-EVH.md` and `tools/trace-check/`), the same way the original
user instruction satisfied it for `srs/SRS-AGT.md` + `srs/SRS-RET.md`.

**Rationale:** DEC-002's own point was that an agent-authored record
cannot self-certify its own authorization — a rule the repair subagent
correctly applied to itself. That same rule is satisfied, not violated,
by the orchestrating session recording a fact it actually observed in the
live conversation. The two halves of this entry are deliberately kept
distinct: the subagent's honest "I cannot verify this" and the
orchestrator's "I can, and here is the specific instruction" are not in
tension — they are different agents with different visibility, and both
statements were true when made.

**Status:** Resolved for `srs/SRS-EVH.md` and `tools/trace-check/` —
including `srs/DEFERRED.md`, which is not a separate ask: `tools/trace-check`'s
own check (a) requires it to exist to produce a meaningful result
(otherwise every platform-level SysR with no owning SRS document reports
as a violation), and `MISSION_PHASE_B0.md` lists it as deliverable 3
alongside trace-check as deliverable 2, both needed for deliverable 5's
"run it yourself" requirement to mean anything. As DEC-002 itself states,
any scope beyond this (merges, pushes, or anything past Checkpoint B0-b)
requires re-confirming this same test again, not just citing this entry.

---

## DEC-005 — SRS-EVH-F-03 commits to the eval/cases/domain/ layout without change

**Document/scope:** `srs/SRS-EVH.md`, SRS-EVH-F-03 (domain case-set
layout).

**Ambiguity:** `eval/README.md` explicitly mandated that SRS-EVH either
commit to the existing `eval/cases/domain/` split or propose a deliberate,
documented alternative unification with `EXAMPLE-*.yaml` — leaving open
which of the two SRS-EVH would choose, and stating plainly that a Phase B
change that quietly moved or reshaped `cases/domain/` without updating
SRS-EVH would violate Checkpoint 1's approval.

**Decision:** SRS-EVH-F-03 commits to the existing split without change:
`eval/cases/domain/` remains the authoritative domain case source scored
against category thresholds; `eval/cases/EXAMPLE-001.yaml`/`EXAMPLE-002.yaml`
remain a separate harness-mechanics smoke fixture, never treated as domain
content or scored against a category threshold.

**Rationale:** `eval/README.md`'s own stated reason for the split was
re-verified directly against `eval/loader.py` during derivation, not
assumed from the Phase A document's claim alone: `eval/loader.py::load_all_cases`
globs `eval/cases/*.yaml` non-recursively and calls `EvalCase(**data)` on
each match, which would crash on `cases/domain/*.yaml`'s list-per-file
shape if un-nested, breaking `python -m eval.cli run --all` for
`EXAMPLE-001`/`EXAMPLE-002` too (the glob's crash is per-invocation, not
per-file). This is a real implementation-crash constraint, confirmed by
direct reading, not a stylistic preference — so the existing split is the
correct choice and no alternative layout is proposed. Recorded here for
durability beyond the SRS text itself, since `eval/README.md` flagged this
specific decision as one the owner would want visibility into regardless
of which way it went.

**Status:** Resolved — reflected directly in `srs/SRS-EVH.md`'s committed
text (SRS-EVH-F-03's same-PR sync rule).

---

## DEC-006 — SRS-EVH-IF-02 results-schema extension: additive fields, not a version bump

**Document/scope:** `srs/SRS-EVH.md`, SRS-EVH-IF-02 (results record
schema).

**Ambiguity:** `SysR-P-INFO-05` requires evaluation-run records to carry
five fields (eval-set version, image digest, configuration reference,
thresholds applied, results) that `eval/results/*.json`'s current minimal
shape does not have — confirmed by direct inspection of
`eval/results/run-20260813T002957.json`: exactly `{timestamp, total,
passed, failed, cases[]}`, produced by `eval/reporter.py::write_report`.
Two ways to add the missing fields are both defensible: additive new
top-level fields on the existing shape, or an explicit schema-version bump
or restructure.

**Decision:** SRS-EVH-IF-02 proposes additive fields (`eval_set_version`,
`build_reference`, `config_reference`, `thresholds_applied`,
`gate_verdict`) layered onto the existing, unchanged `{timestamp, total,
passed, failed, cases[]}` shape, rather than a version bump — while noting
an owner-preferred explicit `schema_version` marker would be a compatible
addition, not a competing alternative.

**Rationale:** None of the existing fields are redefined, narrowed, or
removed by the extension — `total`/`passed`/`failed` remain correct
aggregate counts, `cases[]` remains valid per-case detail — so
semantic-versioning discipline (bump only on a breaking change) argues for
additive-only. This choice is already marked `PROPOSED` directly inline in
SRS-EVH-IF-02; this entry gives the reasoning a durable, cross-document
home, the same role DEC-003 plays for a decision `srs/SRS-RET.md` resolves
inline in its own text.

**Status:** Open — pending owner review (the choice itself is marked
`PROPOSED` in `srs/SRS-EVH.md`; this entry is the durable record of the
reasoning, not a claim that the design choice itself is settled).
