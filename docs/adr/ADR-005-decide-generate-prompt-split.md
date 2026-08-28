# ADR-005: Decide-Then-Retrieve Split

## Context
A single combined reasoning call retrieved corpus context unconditionally
and then decided, in that same call, whether to answer from it or call a
tool. A detailed procedure document placed in that context reliably
out-competed the tool-calling instructions for the model's attention,
causing the model to narrate a tool call in prose (or answer from
retrieved context) instead of actually invoking the tool, which
collapsed multiple eval categories at once.

## Decision
Tool-selection and knowledge-answering are split into two separate model
calls with separate prompts: a `decide` step runs first, without
retrieved context, and decides only whether to call a tool; a `generate`
step runs only on the knowledge-answering path, after retrieval, and
produces the cited final answer. On a tool-selected turn, retrieval is
never invoked at all.

## Consequences
- Tool-calling reliability improves because tool-calling instructions no
  longer share a call with a large retrieved-context block competing for
  the model's attention; previously-injected tool faults now fire and are
  handled correctly on every pass.
- Retrieval citations (`evidence_refs`) can never be populated for a
  tool-selected turn, since retrieval is skipped on that path entirely —
  an accepted simplification, not a defect to fix. Nothing downstream may
  depend on retrieved evidence being present on a write-classified turn.
- A smaller set of firm-ceiling gaps remains open after this split (e.g.
  an explicit write request still occasionally misrouted to the knowledge
  path, and a jailbreak-framed write still occasionally drafted though the
  approval gate blocks it) — real, tracked, not resolved by this decision.

## Supersedes / Superseded-by
Supersedes the earlier unconditional-retrieve-then-reason design, in which
one combined call retrieved context and reasoned over it together; that
design is the diagnosed cause of the gate failures this split fixes.

## Journal
DEC-013
