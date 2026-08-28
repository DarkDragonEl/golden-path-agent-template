# ADR-002: Route Assertion via Recorded Call List

## Context
Fallback model selection needed to reject the only candidates that met a
size-below-primary safety criterion, because none of them called tools
reliably; the strongest available candidate is far larger than the
primary. That criterion existed to guarantee that a routing bug silently
defaulting to the fallback route couldn't hide behind improved output
quality, so waiving it left that risk uncovered unless something else
closed it.

## Decision
Every model call the routed client makes records its own route
(`primary`/`fallback`) and reason code. The eval promotion gate asserts,
per case, over the full recorded list of calls a run made — not just its
final output — that ordinary cases used `route=primary, reason_code=none`
and that cases specifically designed to exercise the fallback path show
the reverse.

## Consequences
- A routing bug that silently defaults to the fallback route fails CI
  immediately, regardless of whether the fallback's output happens to look
  acceptable.
- This assertion is a fixed obligation on the eval harness, independent of
  which physical model occupies the primary or fallback role — it must
  survive any future primary/fallback reassignment unchanged.
- Do not treat output quality as evidence that routing worked correctly;
  route and reason code must be checked directly from the call record.
- Non-fallback-exercising cases that show any fallback route/reason code
  are a gate failure, not a benign variance to tolerate.

## Supersedes / Superseded-by
None.

## Journal
DEC-009
