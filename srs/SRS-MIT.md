# Software Requirements Specification (SRS)

## Mock ITSM (MCP Server) — Blueprint Component

| Field | Value |
|---|---|
| Document ID | SRS-MIT |
| Version | 0.2 |
| Conformance | ISO/IEC/IEEE 29148 §9.5 (SRS content), tailored per §0.1 |
| Derivation basis | SyRS-AGP-001 v0.3 — SysR-P-IF-02, SysR-P-IF-03; SysR-P-SEC-03 for the write-path boundary |
| Classification | Organization-agnostic blueprint; no proprietary content; no product names in normative text |
| Depth | **Interface-only** — no functional, data, quality, or performance requirements. Demo scaffolding; not gold-plated. |

### Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-13 | Delivery agent (Phase B0) | Initial interface-only derivation, formalizing the provisional ITSM tool contract already established in `eval/README.md` at Phase A Checkpoint 1 (approved as Phase B0 input). |
| 0.2 | 2026-08-28 | Delivery agent | Derivation-basis line corrected to the current SyRS version, dropping the stale prior-version tag; session/checkpoint vocabulary removed; delivery-phase verification-timing labels renamed to verification-mechanism names (docs/testing-perspectives-guide.md). Reference-implementation reframe, DECISIONS.md DEC-130. No requirement text otherwise changed. |

### Associated Documents

- **SyRS-AGP-001 v0.3** — derivation basis.
- **`eval/README.md`** — the provisional contract this document formalizes. **No revision**: field names, operation names, and shapes below are unchanged from the eval-set version. Because nothing changed, the "same-PR sync rule" (tool-name strings in `eval/cases/domain/*.yaml` must be updated in the same PR as any SRS-MIT revision) does not trigger this time — noted here as the first live check of that rule, which found nothing to do.
- **`eval/cases/domain/itsm_read.yaml`, `draft_request.yaml`, `tool_selection.yaml`, `unauthorized_write.yaml`, `prompt_injection.yaml`** — domain-eval-suite cases that already exercise these tool names and argument shapes end-to-end (agent-observable evidence; see `srs/SRS-APR.md`'s evidence-precision convention, which applies here identically).
- **`srs/SRS-APR.md`** — SRS-APR-F-04/IF-02 define the approval-release path; SRS-MIT-SEC-01 below references it.
- **ISO/IEC/IEEE 29148:2011** — requirements engineering (compliance reference).

### 0.1 Tailoring declaration

Per the working standard: sections of ISO 29148 §9.5 with no content for a blueprint demo component are marked *Not applicable — tailored out* with a one-line reason, never silently omitted. This document is **interface-only** by mission directive: Functional (§1), Data (§3), Quality, Verification, and Traceability sections are tailored out or omitted per the rules below — this is a scope decision, not a gap this document is silently absorbing. Verification methods: I (inspection), A (analysis), D (demonstration), T (test).

### 0.2 Purpose and scope of the software item

The mock ITSM is the MCP-contract realization of the platform's one enterprise-tool integration (CLAUDE.md scope guard: "one tool (mock ITSM with persistent state)") for the demo milestone. It exposes exactly two MCP tools — one read-only, one write (approval-gated by the agent's policy layer and the approval service, not by this component) — and, for demo/test purposes only, a REST introspection surface to observe and reset its state without going through the agent.

This document specifies **interface requirements only**: MCP tool schemas, the REST introspection surface, and state-visibility guarantees. It does not specify: the mock's internal matching/search logic (unit/integration-tests implementation detail), its persistence design — which store, if any (unit/integration-tests implementation detail; only the *externally observable* persistence guarantee is specified, at MIT-IF-05), performance targets, or usability/quality criteria. This is demo scaffolding standing in for a real enterprise ITSM system; SysR-P-IF-02's REST/OpenAPI-to-MCP bridge clause becomes relevant only if this mock is later replaced by a real ITSM integration that does not natively support MCP — not built here.

Out of scope for this item: the agent's tool-selection and drafting logic (SRS-AGT), the approval workflow itself (SRS-APR), retrieval/corpus content (SRS-RET), evaluation scoring (SRS-EVH).

---

## 1. Functional Requirements

*Not applicable — tailored out.* Interface-only depth; the mock's request-handling behavior (how a query matches records, how state is seeded/reset internally) is a unit/integration-tests implementation concern, not an interface contract.

## 2. Interfaces (SRS-MIT-IF-*)

- **SRS-MIT-IF-01 — Tool contract metadata.** Each of the two MCP tools below shall carry machine-readable metadata comprising at minimum: tool name, semantic version, and certification status (a demo-tier value, e.g. `blueprint-demo`, not a production certification), sufficient for registration in a tool catalog/registry without contract change.
  *Trace:* SysR-P-IF-03. *Verification:* I (schema inspection).

- **SRS-MIT-IF-02 — `itsm_search_records` (read-only).** The service shall expose an MCP tool named `itsm_search_records` accepting: `record_type` (`incident` \| `request` \| `known_error`, required), `query` (free-text, optional), `record_id` (optional — when present, returns that one record instead of a list), `status` (optional filter), `limit` (optional, default `10`); and returning `records` (array of `{record_id, record_type, status, short_description, opened_at, updated_at, owner_team}`), `count` (integer), and `source` (constant `"mock-itsm"`). This operation shall never create, modify, or delete state.
  *Trace:* SysR-P-IF-02. *Verification:* I (schema inspection), D (mock behind the identical MCP contract a real integration would present). Evidence: `eval/cases/domain/itsm_read.yaml` (ITR-001..008), `eval/cases/domain/tool_selection.yaml` (TSEL-001, TSEL-004, TSEL-007) exercise this schema end-to-end at the agent level.

- **SRS-MIT-IF-03 — `itsm_create_request` (write).** The service shall expose an MCP tool named `itsm_create_request` accepting: `short_description` (required), `description` (required), `category` (`access` \| `provisioning` \| `break_fix` \| `information`, required), `requested_for` (required), `related_record_id` (optional); and, only once execution has been released per SRS-APR-F-04, returning `record_id` (newly minted, format `REQ-NNNNN`), `status` (constant `"submitted"`), and `source` (constant `"mock-itsm"`). Read vs. write is signaled by which operation is called, never by an argument flag.
  *Trace:* SysR-P-IF-02. *Verification:* I (schema inspection), D. Evidence: `eval/cases/domain/draft_request.yaml` (DRQ-001..006), `eval/cases/domain/tool_selection.yaml` (TSEL-002, TSEL-005, TSEL-008) exercise this schema end-to-end at the agent level; `eval/cases/domain/unauthorized_write.yaml` (UAW-001..006) exercise the negative path (this operation's output never appears in `final_output` absent an `approve` decision).

- **SRS-MIT-IF-04 — REST introspection surface (demo/test-support only).** The service shall additionally expose a REST surface — `GET /records` (list, filterable by `record_type`/`status`), `GET /records/{record_id}` (single record), `POST /reset` (restore seed state) — for demo and test use, never called by the agent and never part of its tool contract. This is the mechanism by which a demo operator or a unit/integration test verifies mock state directly, without going through the agent or the MCP contract.
  *Trace:* SysR-P-IF-02 (informative — this surface exists alongside, not instead of, the MCP contract; it is not the bridge clause, since the agent never uses it). *Verification:* I (schema inspection), T (state visible via REST matches state returned via MCP).

- **SRS-MIT-IF-05 — Persistent-state guarantee.** Within one running instance of the service, a record created by `itsm_create_request` shall subsequently be visible to `itsm_search_records` and to the REST introspection surface (SRS-MIT-IF-04) — state persists across calls within the instance's lifetime, satisfying CLAUDE.md's "mock ITSM with persistent state" scope guard. This is a behavioral guarantee only; the storage mechanism realizing it (in-memory, file-backed, database-backed) is a unit/integration-tests realization choice, out of scope for this interface-only document.
  *Trace:* SysR-P-IF-02 (implicit — a tool contract that cannot round-trip its own writes is not a credible stand-in for a real enterprise system). *Verification:* T (write-then-read round trip within one instance).

## 3. Data Requirements

*Not applicable — tailored out.* Interface-only depth; persistence design is out of scope (SRS-MIT-IF-05 states the observable guarantee without prescribing a store). One pointer, not a requirement of this document: per SysR-P-INFO-04, any seed/fixture state used to exercise this interface shall be synthetic — enforcement belongs to whichever component owns that seed data (the domain eval suite's `eval/README.md` fixture list and the mock-state seeding used in unit/integration tests are both already synthetic per CLAUDE.md; this document does not restate that requirement, only notes it applies).

## 4. Security Requirements (SRS-MIT-SEC-*)

- **SRS-MIT-SEC-01 — No approval-bypass path.** `itsm_create_request` (SRS-MIT-IF-03) shall be reachable by the agent only through the sequence: draft → approval service (SRS-APR-IF-01/IF-02) → execution release (SRS-APR-F-04). This tool interface itself shall expose no alternate invocation path, flag, or parameter that causes the write to execute without a prior `approve` decision recorded by the approval service.
  *Trace:* SysR-P-SEC-03 (write-capable scope reachable only through the approval-gated execution path), SysR-P-POL-01. *Verification:* I (interface inspection — no bypass parameter exists), T. Evidence: `eval/cases/domain/unauthorized_write.yaml` (UAW-001..006) exercise this at the agent-observable level.

---

*(Sections 5–7 — Quality, Verification, Traceability — are omitted entirely for this document, per the skeleton note that SRS-MIT omits §§5–7 structurally, since this is interface-only depth and every requirement above already carries its own inline Trace/Verification line.)*

*Requirements marked PROPOSED are not signed. This document has none — it formalizes an already-approved provisional contract without revision, so no new design decision required a PROPOSED marker.*

**PROPOSED items in this document (0).**
