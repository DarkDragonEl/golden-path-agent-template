# Phase B0 Derivation Findings

Findings recorded during SRS derivation from `SyRS-AGP-001_EN.md` v0.1
(frozen — never modified by this log). Each finding records a gap,
ambiguity, or conflict discovered while deriving an SRS document; the
owner adjudicates disposition. Where derivation continued past a finding,
it did so with an explicitly marked `PROPOSED` assumption in the affected
SRS document, cross-referenced below.

Format: ID, affected SysR/StR, description, proposed disposition, status.

---

## FIND-001 — No enforcement requirement that a decision come from an authorized approver

**Affected:** SysR-P-F-08 (Human approval workflow); StRS STK-05 (Human
approver, stakeholder role definition); StR-APR-01/02.

**Description:** SysR-P-F-08 requires that every decision be recorded
*with* approver identity, timestamp, and outcome. StRS defines "Human
approver" (STK-05) as a distinct stakeholder role — "sufficient context to
approve or reject agent-proposed writes quickly and safely." Neither
document states a requirement that the **system verify** the identity
rendering a decision actually holds the approver role for that proposal.
As derived, an approval workflow satisfying SysR-P-F-08's literal text
could accept a decision from *any* authenticated identity, including the
proposal's own initiating user — which would be difficult to reconcile
with OBJ-05 ("zero unapproved writes"), read as "zero writes approved by
someone other than a legitimate approver," rather than the weaker "zero
writes with no decision record at all."

**Proposed disposition:** Add `SRS-APR-SEC-02 — Approver authorization`
(done, marked `PROPOSED — pending owner review` in `srs/SRS-APR.md`):
the service refuses and audit-logs a decision from an identity not
holding the approver role for the proposal's scope. This is an addition
to SRS-APR, not a change to the SyRS — SysR-P-F-08's text is unmodified;
this finding and its disposition exist so the owner can decide whether the
gap should *also* be closed at the SyRS level in a future revision (out of
scope for this document to decide).

**Status:** Open — pending owner adjudication at Checkpoint B0-a.

---

## FIND-002 — No audit-record integrity/immutability requirement

**Affected:** SysR-P-SEC-06 (Audit evidence on demand); SysR-P-INFO-03
(Retention and retrievability); StR-APR-03.

**Description:** StR-APR-03 requires decision records be "retrievable as
audit evidence." SysR-P-SEC-06 and SysR-P-INFO-03 require retrievability
and retention but neither states that a terminal decision record, once
written, cannot subsequently be altered or deleted. "Audit evidence"
conventionally implies tamper-resistance, but the SyRS does not say so
explicitly, and a service satisfying the literal retrievability/retention
text could still expose an update or delete operation on a decided
proposal without violating any stated SysR.

**Proposed disposition:** Add `SRS-APR-SEC-04 — Audit-record integrity`
(done, marked `PROPOSED — pending owner review` in `srs/SRS-APR.md`):
no operation exposed by the service updates or deletes a terminal-state
record. As with FIND-001, this is an SRS-level addition; the owner may
choose to fold an explicit immutability clause into a future SyRS
revision instead of (or in addition to) carrying it only at the SRS
level.

**Status:** Open — pending owner adjudication at Checkpoint B0-a.

---

## FIND-003 — No explicit tie-breaking rule for a classification-ambiguous proposed action

**Affected:** SysR-P-SEC-05 (Enforced deny path); SysR-P-POL-01 (Read-only
default posture).

**Description:** SysR-P-SEC-05 requires at least one policy deny path
enforced at runtime; SysR-P-POL-01 requires the default policy bundle to
grant no write-capable tool operations. Neither states what the system
should do when the loaded policy's classification rules cannot determine
whether a specific proposed action is read-only or write-capable (an
unrecognized or ambiguous action type). As derived, a policy engine
satisfying both requirements' literal text could plausibly default a
classification-ambiguous action to read-only/directly-executable (since
only recognized write-capable operations are enumerated as requiring
gating), which would be difficult to reconcile with the fail-closed
posture applied everywhere else in the platform.

**Proposed disposition:** Add `SRS-AGT-SEC-03 — Fail closed on ambiguous
action classification` (done, marked `PROPOSED — pending owner review` in
`srs/SRS-AGT.md`): a classification-ambiguous action is always treated as
write-capable and routed to approval, never executed directly or treated
as read-only. This is an addition to SRS-AGT, not a change to the SyRS;
the owner may decide whether the gap should also be closed at the SyRS
level in a future revision.

**Status:** Open — pending owner adjudication at Checkpoint B0-a.

---

## FIND-004 — No terminal-state query interface for a decided proposal

**Affected:** SysR-P-F-08 (Human approval workflow); SysR-A-F-04 (Draft,
approve, execute).

**Description:** SysR-A-F-04 requires the agent to "execute the action
only upon recorded approval" and, on rejection or expiry, to "inform the
user" — both presuppose the agent has a way to learn a submitted
proposal's decided outcome. SysR-P-F-08 requires the approval workflow to
record each decision but does not require it to expose that decision back
to the proposal's originator through a queryable interface once the
proposal leaves the `pending` state. As derived in `srs/SRS-APR.md`
(already approved, Checkpoint B0-a), the two existing query surfaces —
SRS-APR-IF-04 (pending-proposal query) and SRS-APR-F-05 (decision-context
availability) — are both explicitly scoped to proposals in the `pending`
state; neither defines a query for a proposal's terminal state
(`approved`/`rejected`/`expired`) by `proposal_id`. This gap was surfaced
while deriving `srs/SRS-AGT.md`'s SRS-AGT-F-04 (draft, approve, execute),
which must assume some mechanism for the agent to obtain the decision
outcome and currently cannot cite one.

**Proposed disposition:** Not closed by this document. `srs/SRS-APR.md`
is already approved and frozen (additive-only per
`MISSION_UNATTENDED.md`'s hard rules); this finding is recorded for the
owner to decide whether to add a new, purely additive `SRS-APR-IF-05 —
Terminal-state proposal query` requirement in a future revision of
`srs/SRS-APR.md`, or an equivalent push/notification mechanism.
`srs/SRS-AGT.md`'s SRS-AGT-F-04 states the agent's dependency on this
mechanism honestly as an open, `PROPOSED` item pending this finding's
resolution, rather than assuming an interface that does not yet exist.

**Status:** Open — pending owner adjudication; blocks closing
SRS-AGT-F-04's PROPOSED marker with full confidence until SRS-APR's
query-interface coverage is resolved.

---

## FIND-005 — No disposition specified for superseded corpus document versions

**Affected:** SysR-P-F-10 (Corpus management); SysR-P-SEC-06 (Audit evidence
on demand), SysR-P-INFO-03 (Retention and retrievability), by analogy.

**Description:** SysR-P-F-10 requires a documented refresh process such
that an updated document version is cited by subsequent answers, but says
nothing about what happens to the version a refresh supersedes — retained,
archived, or deleted. This matters beyond the corpus itself:
`srs/SRS-APR.md`'s already-approved `SRS-APR-IF-01` proposal schema
requires `evidence_refs` (retrieval citation IDs) at intake, and
`SRS-APR-DATA-02` requires those decision records remain retrievable as
audit evidence for the pilot's duration. If a corpus document a past
proposal's `evidence_refs` cited is later superseded and the superseded
version is not retained, that evidence reference becomes permanently
unverifiable — a citation trail severed by an unrelated document refresh.
As derived, a corpus-management implementation satisfying SysR-P-F-10's
literal text could plausibly delete or overwrite a superseded version,
which would be difficult to reconcile with the audit-evidence retention
posture the platform applies elsewhere (SysR-P-SEC-06, SysR-P-INFO-03 —
for approval/audit records specifically, not corpus content, so the
connection is by analogy, not a direct SyRS requirement).

**Proposed disposition:** Add `SRS-RET-DATA-02 — Superseded-version
retrievability` (done, marked `PROPOSED — pending owner review` in
`srs/SRS-RET.md`): a superseded version remains retrievable by explicit
version (not as current) rather than being deleted. This is an addition
to SRS-RET, not a change to the SyRS; the owner may decide whether
corpus-version retention should also be stated explicitly at the SyRS
level in a future revision, the same open question FIND-001/FIND-002 left
for SysR-P-F-08/SEC-06 respectively.

**Status:** Open — pending owner adjudication at Checkpoint B0-a.

---

## Findings not raised (considered and set aside)

For transparency: two other candidate gaps were considered during
SRS-APR derivation and *not* raised as findings, because they read as
ordinary implementation detail below the SyRS's level of abstraction
rather than a requirements-level gap needing owner disposition —
`SRS-APR-F-07` (idempotent proposal submission) and the release-mechanism
choice inside `SRS-APR-F-04` (synchronous vs. event-style execution
release). Both are handled as inline `PROPOSED` design decisions within
`srs/SRS-APR.md` itself, not as findings here.

Similarly, during SRS-AGT derivation, seven further candidate gaps were
considered and set aside the same way — citation granularity
(SRS-AGT-F-01), single-output-per-turn (SRS-AGT-F-03), the escalation
mechanism (SRS-AGT-F-05), the injection-detection-for-logging mechanism
(SRS-AGT-F-06), the step-counting definition (SRS-AGT-F-07), the
policy-bundle reload cadence (SRS-AGT-F-09), and runtime tool-catalog
metadata lookup (SRS-AGT-IF-04) — each handled as an inline `PROPOSED`
design decision with rationale and an alternative considered, within
`srs/SRS-AGT.md` itself, not as findings here. Only the two gaps above
(FIND-003, FIND-004) read as carrying enough risk (an unauthorized-write
adjacency, and a cross-document interface hole affecting an already-frozen
document) to warrant owner adjudication above the SRS-level `PROPOSED`
mechanism.

During SRS-RET derivation, one further candidate gap was considered and
set aside the same way — the `top_k` result-count default's
configuration-sourced-vs-hardcoded question (SRS-RET-IF-01) — handled as
an inline `PROPOSED` design decision, not a finding, since it is an
ordinary interface-default choice with no audit or security-adjacent
risk. FIND-005 (above), by contrast, was raised because a superseded
corpus version's disposition has a real downstream implication for
`srs/SRS-APR.md`'s already-approved audit-evidence guarantees, the same
risk-bearing threshold FIND-001/002/003 apply.
