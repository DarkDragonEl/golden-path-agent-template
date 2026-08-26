# G5 — Catalog model design: test report

Branch: `feature/g5-catalog-model` (git worktree, not merged, not pushed).
Scope: `DEC-098`/`DEC-099`, Stage 2 / G5 — local catalog entity design
only, not live RHDH registration (deliberately deferred, see below).

## What was built

Three new files under `platform/catalog/` (new directory, does not touch
`platform/bootstrap/` — that stays G1's territory):

- `system.yaml` — `System` entity `golden-path-agent-platform-foundation`,
  the grouping node for platform → tools → agents.
- `approval-service.yaml` — `Component` `golden-path-agent-approval-service`
  (the approval service as a shared Platform Foundation singleton, per
  `DEC-098`) + `API` `golden-path-agent-approval-api`, an OpenAPI 3.0.3
  definition covering all four real routes (`POST /proposals`,
  `GET /proposals`, `GET /proposals/{proposal_id}`,
  `POST /proposals/{proposal_id}/decision`) plus `/healthz`.
- `model-routes.yaml` — one shared `API`
  `golden-path-agent-model-route-api` (the OpenAI-compatible
  chat-completions contract) plus two `Resource` entities, `...-primary`
  and `...-fallback`, both providing that API.

## Sources used (not invented)

- Route/reason-code shape: `agent/model_client.py` (`RoutedModelClient`,
  `_classify_primary_failure`) and `agent/config.py`
  (`MODEL_API_BASE_URL`/`MODEL_NAME`/`MODEL_FALLBACK_API_BASE_URL`/
  `MODEL_FALLBACK_NAME`) — the real closed reason-code set is `none`,
  `primary_timeout`, `primary_429`, `primary_5xx`, `primary_unreachable`.
  `srs/SRS-AGT.md`'s `SRS-AGT-IF-02` lists a *different*, illustrative
  example set (`primary-selected`, `fallback-on-error`, `forced-route`,
  prefixed "e.g.") — the catalog entity documents the real, implemented
  set and notes the SRS's own set is non-literal, so a future reader
  doesn't treat the SRS text as the actual enum.
- Approval API shape: `srs/SRS-APR.md` (`SRS-APR-IF-01/02/04/05`,
  `SRS-APR-SEC-01`, `SRS-APR-QUAL-02`) for the normative contract, cross-
  checked against `approval_service/api.py`'s real route decorators
  (`grep '@app\.\(get\|post\)'`) to confirm the OpenAPI paths match what's
  actually implemented, not just what the SRS describes.
- Ownership convention: this repo's own `catalog-info.yaml` (single
  existing owner, `group:default/golden-path-agent-team`) — reused
  verbatim across every new entity, since no second team/owner
  distinction exists anywhere in this project yet. **Judgment call,
  named rather than silently assumed**: the task brief asked for
  "platform-owned vs. tool-owned vs. agent-owned" ownership, but that
  distinction has no real referent until G7's multi-team scenario
  introduces actual separate teams — inventing a second team name now
  (e.g. a fictitious "platform-team") would be exactly the kind of
  unfounded invention this project's own discipline warns against.
  Deferred: G7 is where distinct ownership becomes meaningful, not
  before.

## Model-name-hardcoding avoidance (deliberate design choice)

The two model-route `Resource` entities do **not** name a specific model
(no `granite-3-2-8b-instruct`, no `llama-scout-17b` in the entity itself)
— `SRS-AGT-IF-01` explicitly forbids hardcoding an endpoint or model
identifier in agent source, and the same principle is applied here: the
*route* (primary/fallback role) is the stable catalog identity; the model
behind it is injected configuration (`DEC-009`'s `llama-scout-17b` choice
is noted in prose as a realization fact, not encoded as a spec field).

## What's explicitly deferred, and why

Per the task brief's own exclusion (multiple concurrent Stage-2 streams
might all want to touch RHDH's live catalog config at once):

- **Not registered in RHDH's live `catalog.locations`.** These are local
  YAML files only. Registering them means editing
  `deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml` — the
  exact file G1's tail may also need to touch for its own ArgoCD/GitOps
  work, and a concurrent G3+G4 stream may also want to touch for the new
  Tools/Agent Template entities. The coordinating session should sequence
  that single shared edit once all three Stage-2 streams report back,
  rather than each stream racing to it independently (the class of
  mistake `DEC-101` already recorded once this stage).
- **No relations to Tools/Agent Template entities yet** (e.g. an agent's
  `consumesApis` pointing at an MCP tool's `API`, or `dependsOn` a model
  route). The concurrent G3+G4 stream owns the Tools/Agent Template
  skeleton and hasn't landed yet. **Assumption documented for that stream
  to confirm or correct**: a scaffolded agent instance would declare
  `spec.consumesApis: [golden-path-agent-model-route-api, <the-mcp-
  instance's-own-tool-api-name>]` and `spec.dependsOn: [resource:golden-
  path-agent-model-route-primary]`, following this project's own existing
  naming pattern (`golden-path-agent`, `golden-path-agent-mcp`,
  `golden-path-agent-approval` — a `<project-name>[-component]` scheme).
  Not verified against G3/G4's actual output, since that work is
  concurrent and uncommitted.

## Validation performed (schema-shape, not live RHDH — per scope)

1. Parsed all three files as multi-document YAML; confirmed every
   document has `apiVersion`/`kind`/`metadata.name`, and every kind's
   Backstage-required `spec` fields are present (`System`: `owner`;
   `Component`: `type`/`lifecycle`/`owner`; `API`: `type`/`lifecycle`/
   `owner`/`definition`; `Resource`: `type`/`owner`) — 6/6 entities pass.
2. Cross-reference check: every `providesApis`/`consumesApis`/`system`
   reference across the three files resolves to a name actually defined
   in this set — 0 dangling references.
3. Both embedded `spec.definition` blocks parse as valid OpenAPI 3.x
   (`openapi: 3.0.3`, non-empty `paths`) — 4 paths (approval API), 1 path
   (model-route API).
4. Did **not** run this against a live RHDH instance or the actual
   Backstage catalog-model JSON Schema package (no JS toolchain in this
   Python-based repo) — this is schema-*shape* validation against
   Backstage's documented required-field rules and this repo's own
   working `catalog-info.yaml` example, not a guarantee RHDH's own
   stricter validator would accept every field with zero complaint. Real
   RHDH-side validation is exactly the live-registration step deferred
   above.

## Drafted decision entry (numbered as a placeholder — land at the
coordinating session's own next available `DEC-NNN`)

```
## DEC-1xx — G5: catalog model designed locally (System, approval-service
Component+API, model-route Resources+API) -- not yet registered in
RHDH's live catalog, by deliberate scope choice

**Context**: DEC-099's Stage 2, third parallel stream (alongside G1's
held tail and a G3+G4 template-split stream). Ran in worktree branch
`feature/g5-catalog-model`; this coordinating session lands this entry,
the worktree stream never touched DECISIONS.md/HANDOFF.md/PINS.md
directly, and never merged or pushed anything itself.

**What was built**: three new files under platform/catalog/ (new
directory; platform/bootstrap/ untouched) -- a System entity for the
Platform Foundation; a Component + OpenAPI API for the approval service
(sourced from srs/SRS-APR.md's real IF-01/02/04/05 contract, cross-
checked against approval_service/api.py's actual route decorators, not
invented); a shared OpenAI-compatible API plus two Resource entities
(primary/fallback) for the model routes (sourced from agent/
model_client.py's real RoutedModelClient and its actual closed reason-
code set -- none/primary_timeout/primary_429/primary_5xx/
primary_unreachable -- which differs from srs/SRS-AGT.md's own
illustrative example set, noted so a future reader doesn't mistake the
SRS's "e.g." list for the literal enum).

**Deliberate design choice**: neither model-route Resource names a
specific model -- SRS-AGT-IF-01 forbids hardcoding a model identifier in
agent source, and the same principle is applied to the catalog entity:
route identity (primary/fallback) is stable, the model behind it is
injected configuration.

**Deliberately deferred, not an oversight**: (1) live RHDH registration
(editing deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml) --
deferred because a concurrent G1-tail stream and a concurrent G3+G4
stream may also need to touch that same file; the coordinating session
sequences that single shared edit once all Stage-2 streams report back,
rather than repeating DEC-101's governance/collision lesson. (2)
Relations to Tools/Agent Template entities (consumesApis/dependsOn) --
the concurrent G3+G4 stream owns that skeleton and hasn't landed; this
entry documents an assumed naming convention
(golden-path-agent-model-route-api, <project-name>[-component]) for that
stream to confirm or correct, not a verified integration.

**Ownership judgment call**: reused the repo's single existing owner
(group:default/golden-path-agent-team) across every new entity rather
than inventing a "platform team" vs. "agent team" distinction that has
no real referent in this project yet -- distinct ownership becomes
meaningful at G7's multi-team scenario, not before.

**Validation performed**: schema-shape only (required-field presence per
Backstage's documented kind rules, dangling-reference check, OpenAPI 3.x
parse check on both embedded definitions) -- not live RHDH validation,
which is part of the deferred registration step above.

**Status**: Design complete, locally validated, not yet live. Next: the
coordinating session sequences the shared RHDH catalog-config edit once
G1's tail and the G3+G4 stream both report their own catalog-relevant
output.
```
