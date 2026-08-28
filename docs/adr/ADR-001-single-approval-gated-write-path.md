# ADR-001: Single Approval-Gated Write Path

## Context
The write-capable tool contract states the tool is reachable by the agent,
while an early approval-service requirement read as if the approval service
itself invoked the tool on release. Both cannot be true, and neither of the
approval service's query interfaces was scoped to let the agent learn a
decided proposal's outcome, leaving no defined way to close the loop.

## Decision
The agent is the sole invoker of every write-capable tool call. The
approval service's "release" is an atomic state transition to `approved`
plus exposing the approved proposal — including its unmodified
`action_arguments` — via a dedicated terminal-state query. On `approved`,
the agent executes the arguments exactly as returned by that query, never
a locally cached copy retained from drafting time.

## Consequences
- Enforce this structurally, not by convention: keep the drafted value and
  the approved value in separate state fields, only the latter reaching
  tool execution, and assert `arguments_executed == arguments_approved`
  for every completed write.
- Do not give the approval service its own path to call the write tool —
  that would duplicate the tool-reachability contract and reopen the
  conflict this decision resolves.
- A proposal-submission failure routes to the model fallback path with its
  own distinct reason code, never conflated with a model-call failure.
- Any interim, in-process substitute for a not-yet-deployed approval
  service must be labeled "interim" wherever described, never presented
  as the persistent service.

## Supersedes / Superseded-by
None.

## Requirement
SRS-APR-F-04, SRS-AGT-F-04, SRS-APR-IF-05 (srs/SRS-APR.md v0.4,
srs/SRS-AGT.md v0.3).

## Journal
DEC-008, DEC-049
