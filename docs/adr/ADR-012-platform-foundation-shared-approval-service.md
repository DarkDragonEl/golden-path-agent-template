# ADR-012: Approval Service as a Shared Platform Foundation Component

## Context
Human approval for every external write is this platform's defining
objective. When the approval service is bundled per agent instance, each
scaffolded project runs its own independent approval workflow — once more
than one instance exists, this yields inconsistent, per-instance behavior
rather than one consistent enforcement point.

## Decision
The approval service is extracted out of the Agent Template and becomes a
singleton component of the shared Platform Foundation (alongside identity,
telemetry, Git hosting, model routes, and GitOps machinery), serving every
Agent Template instance, with its own namespace, image, and lifecycle
independent of any single agent's deployment.

## Consequences
- Sharing the service introduces a new failure class beyond its own internal
  fail-closed behavior: a consumer unable to reach the now-out-of-process
  service at all. Consumers must hold the action in that case, never
  synthesize or reuse a decision (see Requirement).
- This composes with, not replaces, the existing per-agent write kill switch:
  operator-triggered per-agent disable is level one; the automatic
  consumer-side hold above is level two, needing no operator action.
- Any future NetworkPolicy/RBAC change to the approval service must preserve
  reachability for every agent consumer, not just the one in hand.

## Supersedes / Superseded-by
Supersedes the per-agent-bundled approval service (one Containerfile
dispatching agent/mcp/approval roles from a single image).

## Requirement
Cites SRS-APR-QUAL-02 (`srs/SRS-APR.md` v0.4): a consumer that cannot reach
or get a decision from the shared service within its own timeout must hold
the action — never synthesize or reuse an approval, never bypass the decision
surface. Verification: fault injection blocking ≥2 distinct consumer
workloads from the service, confirming zero execution release from either.

## Journal
DEC-098, DEC-103
