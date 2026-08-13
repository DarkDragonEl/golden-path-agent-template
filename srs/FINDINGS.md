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

## Findings not raised (considered and set aside)

For transparency: two other candidate gaps were considered during
SRS-APR derivation and *not* raised as findings, because they read as
ordinary implementation detail below the SyRS's level of abstraction
rather than a requirements-level gap needing owner disposition —
`SRS-APR-F-07` (idempotent proposal submission) and the release-mechanism
choice inside `SRS-APR-F-04` (synchronous vs. event-style execution
release). Both are handled as inline `PROPOSED` design decisions within
`srs/SRS-APR.md` itself, not as findings here.
