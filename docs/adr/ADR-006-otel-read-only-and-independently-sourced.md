# ADR-006: OpenTelemetry Instrumentation Is Read-Only and Independently Sourced

## Context
Adding tracing to a model-calling agent pipeline risks the instrumentation
code itself altering the model calls it is meant to observe, which would
silently invalidate eval baselines. Separately, the agent and its approval
service are independently deployed and communicate across a human-latency
approval gap, so correlating a request across both needs a decision between
full distributed trace-context propagation and a simpler join key.

## Decision
OTel spans and span events are populated strictly from already-computed
state after a model or tool call completes; no telemetry code changes
prompt text or the arguments passed to the model client. The agent and
approval service each maintain independent span trees, correlated by
explicit `session.id`/`proposal.id` attributes on both sides rather than
shared W3C trace-context propagation across the async approval wait.

## Consequences
- Extending telemetry never requires, and must never trigger, an eval
  re-baseline: the model call's actual arguments (model, messages, tools,
  temperature, seed) stay byte-for-byte unchanged by telemetry work — only
  observation of already-computed state changes.
- A route with more than one model call (e.g. a fallback after a primary
  failure) gets one span event per call, not just last-write-wins scalar
  fields, so per-route data is never silently overwritten.
- `proposal.id` is emitted as an empty string, never omitted, when no
  proposal exists yet in a turn, so a trace store can query consistently.
- There is no single trace spanning both services; correlation is a manual
  join on `session.id`/`proposal.id` via query tooling, not a live trace
  UI — adopters wanting a unified view must build that join, not expect an
  off-the-shelf trace backend to show one tree.
- A new span attribute must be sourced from state already computed for
  another purpose, not by adding a new field to the model-call path.

## Supersedes / Superseded-by
None.

## Journal
DEC-020, DEC-071
