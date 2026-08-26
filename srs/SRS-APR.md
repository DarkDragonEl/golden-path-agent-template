# Software Requirements Specification (SRS)

## Approval Service — Blueprint Component

| Field | Value |
|---|---|
| Document ID | SRS-APR |
| Version | 0.3 (Draft, amended) |
| Conformance | ISO/IEC/IEEE 29148 §9.5 (SRS content), tailored per §0.1 |
| Derivation basis | SyRS-AGP-001 v0.1 (frozen) — SysR-P-F-08, SysR-P-F-09, SysR-P-USE-01, SysR-P-IF-05/06, SysR-P-SEC-01/02/03/05/06, SysR-P-INFO-03, SysR-P-POL-01 |
| Classification | Organization-agnostic blueprint; no proprietary content; no product names in normative text |
| Depth | Full (per `MISSION_PHASE_B0.md`) |

### Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-13 | Delivery agent (Phase B0) | Initial derivation from SyRS-AGP-001 v0.1, following the skeleton pattern at `SRS-APR_skeleton.md`. Submitted at Checkpoint B0-a. |
| 0.2 | 2026-08-21 | Owner review, Checkpoint B0-b | All 4 PROPOSED items resolved (F-04 jointly with `srs/SRS-AGT.md`'s F-04, F-07, SEC-02, SEC-04); SRS-APR-IF-05 (terminal-state proposal query) added, closing FIND-004. See `DECISIONS.md` DEC-008. |
| 0.3 | 2026-08-26 | Phase G kickoff (G0) | Added SRS-APR-QUAL-02 (held, never auto-approved, on shared-service unavailability), extending SRS-APR-SEC-01's fail-closed guarantee to the shared-approval-service consumption boundary introduced by DECISIONS.md DEC-098. Purely additive; no existing requirement text changed. |

### Associated Documents

- **SyRS-AGP-001 v0.1 (frozen)** — derivation basis. Never modified by this document; gaps found during derivation are recorded in `srs/FINDINGS.md`, not applied here.
- **`eval/` (Phase A, signed, `phase-a-complete`)** — verification evidence. `eval/cases/domain/draft_request.yaml` (DRQ-001..006) and `eval/cases/domain/unauthorized_write.yaml` (UAW-001..006) are the closest existing Phase A cases; where cited below, they provide end-to-end, agent-observable evidence, not component-level test evidence of this service in isolation — the distinction is noted per requirement.
- **`SRS-APR_skeleton.md`** — pattern document for this derivation; its four worked exemplars (F-01..F-04) are carried into this document unchanged as style anchors.
- **ISO/IEC/IEEE 29148:2011** — requirements engineering (compliance reference).

### 0.1 Tailoring declaration

Per the working standard: sections of ISO 29148 §9.5 with no content for a blueprint demo component are marked *Not applicable — tailored out* with a one-line reason, never silently omitted. Verification methods: I (inspection), A (analysis), D (demonstration), T (test) — same conventions as the SyRS. Where two methods are listed, the first is primary.

### 0.2 Purpose and scope of the software item

The approval service is the platform component that receives every agent-proposed external write action, presents it to a human approver with full decision context, records the decision, and releases execution — only on approval, only through the tool-contract path. It is the enforcement point for the MVP's defining objective (human approval for every external write, OBJ-05).

Out of scope for this item: the agent's drafting logic (SRS-AGT), the write executor itself (tool contract, SRS-MIT for the demo), user authentication (platform identity interface, SysR-P-IF-05 — this service *consumes* that interface's output, it does not implement it), notification delivery mechanisms beyond the demo surface (SRS-APR-F-06's pull-based query surface is the demo surface; push notification is not built).

---

## 1. Functional Requirements (SRS-APR-F-*)

- **SRS-APR-F-01 — Proposal intake.** The service shall accept a proposed action only as a structured proposal containing: action type, target system identifier, complete action arguments, evidence references (retrieval citations and tool-call record IDs from the initiating run), initiating user identity, agent workload identity, and originating session/request ID. Proposals missing any required field shall be rejected with a machine-readable error and shall create no pending approval.
  *Trace:* SysR-P-F-08. *Verification:* T (schema-reject cases). No Phase A eval case directly verifies service-level field-validation rejection — `eval/cases/domain/draft_request.yaml` (DRQ-001..006) verify that the *agent* supplies complete fields, which is necessary but not sufficient evidence for this requirement; a dedicated Phase B test is needed.

- **SRS-APR-F-02 — Single-decision lifecycle.** Each proposal shall exist in exactly one state from {pending, approved, rejected, expired} and shall transition at most once, atomically, from pending to a terminal state. Duplicate or late decisions against a non-pending proposal shall be refused and audit-logged as refused attempts.
  *Trace:* SysR-P-F-08. *Verification:* T (race: two concurrent decisions → one wins, one refused). No Phase A eval case exercises concurrent decisions — out of scope for black-box agent evaluation; a Phase B integration test is needed.

- **SRS-APR-F-03 — Expiry without execution.** A proposal not decided within the configured time limit shall transition to expired, shall never execute, and shall be indistinguishable from a rejection with respect to execution side effects. The time limit shall be environment configuration, not code.
  *Trace:* SysR-P-F-08 (expiry clause). *Verification:* T (expiry path; demo scenario 3 in Phase D). Evidence: `eval/cases/domain/unauthorized_write.yaml` UAW-002 (`approval_scenario: expired`) — agent-observable evidence that expiry produces `write_blocked: true` / `final_state: no_execution`, consistent with but not a substitute for a service-level expiry-timer test.

- **SRS-APR-F-04 — Execution release, not execution.** On approval, the service shall release execution — an atomic transition of the proposal to `approved` plus making the approved proposal, including its *unmodified* `action_arguments`, queryable (SRS-APR-IF-05) — with the *unmodified* approved arguments; the service itself shall contain no target-system client logic and shall not itself issue the literal tool-contract invocation. `Resolved at Checkpoint B0-b — adjudicated jointly with SRS-AGT-F-04, agent-as-invoker model (see DECISIONS.md DEC-008):` "release execution... by invoking the tool-contract path" is read as the service's atomic state transition plus queryable-approved-proposal guarantee described above, not a literal tool-contract call performed by the service; the agent is the component that issues that literal call, per SRS-AGT-F-04 and SRS-MIT-SEC-01's "reachable by the agent" language, which the frozen SysR-A-F-04 also requires ("the agent shall... execute the action"). This resolves the release-mechanism question this requirement originally posed (synchronous invoke-and-record vs. an execution-authorized event) as neither literally: release is the atomic approve-and-expose step; execution is a separate, agent-side act, sourced from this service's query surface rather than a client-cached copy — closing FIND-004 via the new SRS-APR-IF-05 below. Rationale: this keeps SRS-APR-F-04 consistent with the frozen SyRS text it derives from (SysR-P-F-09 does not itself assign the literal invocation to this service) while still satisfying "unmodified approved arguments" end to end, since SRS-AGT-F-04's added condition requires the agent to execute exactly the arguments this service's query surface returns.
  *Trace:* SysR-P-F-09. *Verification:* I (no target-system dependencies in the component), T (argument-equality assertion), D. Evidence: `eval/cases/domain/draft_request.yaml` DRQ-001..006 (`write_executed_before_approval: false`) and `eval/cases/domain/unauthorized_write.yaml` UAW-001..006 (`tool_result_in_final_output: false`) — both agent-observable, both consistent with this requirement's outcome.

- **SRS-APR-F-05 — Decision-context availability.** For every pending proposal, the service shall make available, on query, the complete decision context: the proposed action and its arguments, the evidence references supplied at intake, and the initiating user's identity — sufficient to satisfy SRS-APR-QUAL-01's single-view presentation without a separate query to any other system.
  *Trace:* SysR-P-F-08, SysR-P-USE-01. *Verification:* T (context-completeness assertion against a submitted proposal). No Phase A eval case; Phase A tested the agent's behavior, not a standalone service query surface.

- **SRS-APR-F-06 — Pending-proposal query surface.** The service shall support listing all proposals currently in the `pending` state, filterable at minimum by originating session/request ID, such that an approver or an operator can discover work awaiting decision without prior knowledge of a specific proposal identifier.
  *Trace:* SysR-P-F-08, SysR-P-USE-01. *Verification:* T (list reflects true pending set across intake/decision transitions). No Phase A eval case.

- **SRS-APR-F-07 — Idempotent proposal submission.** `Resolved at Checkpoint B0-b (accepted as drafted):` a proposal submission carrying a client-supplied idempotency key already seen for the same originating session/request ID shall return the existing proposal's current state rather than creating a duplicate pending approval. Rationale: SysR-P-F-08 does not address retry behavior on the intake path; without this, a network retry after a successful intake could create two pending approvals for one intended action. Alternative considered: leave de-duplication to the caller (agent-side retry safety) — rejected because it would require every future agent implementation to reimplement the same safeguard the service can provide once.
  *Trace:* SysR-P-F-08 (intake reliability, by extension). *Verification:* T (duplicate submission with the same idempotency key resolves to one proposal). No Phase A eval case.

## 2. Interfaces (SRS-APR-IF-*)

<!-- This section IS the former "B1 contract" for this component. Schemas are
     defined once, here; SRS-AGT references them by ID rather than restating them. -->

- **SRS-APR-IF-01 — Proposal API.** The service shall expose a submission operation accepting a structured proposal — `action_type`, `target_system_id`, `action_arguments` (complete, as intended for execution), `evidence_refs` (retrieval citation IDs and/or tool-call record IDs from the initiating run), `initiating_user_id`, `agent_workload_id`, `originating_session_id`, `originating_request_id`, and, where SRS-APR-F-07 is adopted, an optional `idempotency_key` — and returning a `proposal_id` and initial `state: pending` on success (SRS-APR-F-01), or a machine-readable validation error and no created proposal on failure. This is the single source schema for SRS-AGT's approval-client requirement.
  *Trace:* SysR-P-F-08. *Verification:* I (schema inspection), T (schema-reject cases).

- **SRS-APR-IF-02 — Decision surface.** The service shall expose a decision operation accepting `proposal_id`, `decision` (`approve` \| `reject`), and the deciding approver's identity as established by SRS-APR-SEC-03 (never a client-supplied claim), transitioning the named proposal per SRS-APR-F-02 and returning the updated state and recorded decision metadata (approver identity, timestamp, outcome) on success, or a refusal carrying the proposal's actual current state if it is not `pending`. This is the approver-facing API consumed by the demo UI.
  *Trace:* SysR-P-F-08, SysR-P-USE-01. *Verification:* I (schema inspection), T (approve / reject / refused-duplicate-decision cases).

- **SRS-APR-IF-03 — Audit/telemetry emission.** Every state transition shall emit a telemetry event correlated to the originating session/request ID, on the platform telemetry interface.
  *Trace:* SysR-P-IF-06. *Verification:* T (trace continuity asserted end-to-end; Phase D dashboard).

- **SRS-APR-IF-04 — Pending-proposal query interface.** The service shall expose a query operation implementing SRS-APR-F-06, accepting an optional `originating_session_id` or `originating_request_id` filter and returning the matching set of pending proposals with the same decision-context fields as SRS-APR-IF-01/F-05.
  *Trace:* SysR-P-F-08, SysR-P-USE-01. *Verification:* I (schema inspection), T.

- **SRS-APR-IF-05 — Terminal-state proposal query.** *Added at Checkpoint B0-b, adopted per `DECISIONS.md` DEC-008, closing FIND-004 — purely additive, does not modify SRS-APR-IF-01..04.* The service shall expose a query operation accepting `proposal_id` and returning that proposal's current state and, once it has left `pending`, its terminal-state record in full: the decision outcome (`approved`/`rejected`/`expired`), the approver identity and decision timestamp (SRS-APR-DATA-01), and, for an `approved` proposal, the *unmodified* `action_arguments` accepted at intake (SRS-APR-IF-01) — the exact arguments SRS-AGT-F-04's agent-as-invoker execution step must use. This is the mechanism SRS-AGT-F-04 depends on to learn a decided proposal's outcome and to source the arguments it executes; SRS-APR-IF-04/F-06 remain scoped to `pending` proposals only and are not widened by this addition. **Realization note:** Phase B realizes this requirement's functional intent through an interim, explicitly-labeled mechanism (the agent's own in-process interrupt/resume, plus a `GET /approvals/{session_id}` read endpoint on the agent itself, per `srs/SRS-AGT.md`'s SRS-AGT-F-04 resolution) rather than a standalone service query, since no standalone approval service exists until Phase D; Phase D's standalone `approval_service` component is where this interface is actually implemented as specified.
  *Trace:* SysR-P-F-08, SysR-A-F-04 (referenced — the agent-side obligation this interface exists to satisfy). *Verification:* I (schema inspection), T (a terminal-state query returns the correct outcome and, for `approved`, arguments identical to those accepted at intake). No Phase A eval evidence; a Phase D integration test is needed once the standalone service exists — Phase B's interim mechanism is verified instead via SRS-AGT-F-04's added arguments-equality test.

## 3. Data Requirements (SRS-APR-DATA-*)

- **SRS-APR-DATA-01 — Proposal/decision record content.** Each proposal record shall persist, for its full lifecycle: all fields accepted at intake (SRS-APR-IF-01); the sequence of state transitions with timestamps; and, once decided, the approver identity, decision outcome, and decision timestamp (SRS-APR-F-02). This is the persistence *requirement* — what must survive a restart; the store realizing it is a realization choice (SysR-P-LC-02) recorded outside this document, not here.
  *Trace:* SysR-P-F-08, SysR-P-SEC-01. *Verification:* I (record-schema inspection), T (record survives a service restart).

- **SRS-APR-DATA-02 — Retention and retrievability.** Proposal and decision records shall be retained per the configured retention policy and shall remain retrievable on demand as audit evidence for the duration of the pilot; retention duration is environment configuration, not a value fixed by this document.
  *Trace:* SysR-P-SEC-06, SysR-P-INFO-03. *Verification:* I (retention configuration), D (audit retrieval exercise).

## 4. Security Requirements (SRS-APR-SEC-*)

- **SRS-APR-SEC-01 — Fail closed.** Any internal error, dependency failure, or undecidable state shall result in no execution release. There shall be no code path from an error condition to an executed write.
  *Trace:* SysR-P-SEC-05 (deny-path principle). *Verification:* T (fault injection on every dependency), I. Evidence: `eval/cases/domain/unauthorized_write.yaml` UAW-001..006 provide end-to-end, agent-observable evidence that the wider system's outcome is consistent with this requirement across the `rejected`/`expired`/`not_requested`/`bypass_attempt` scenarios — they exercise the agent's policy layer together with the approval path, not this service in isolation.

- **SRS-APR-SEC-02 — Approver authorization.** `Resolved at Checkpoint B0-b (accepted as drafted, closes FIND-001):` a decision (SRS-APR-IF-02) shall be accepted only from an identity holding the approver role for the proposal's scope; a decision from an identity not so authorized shall be refused and audit-logged as a refused attempt, identically to SRS-APR-F-02's duplicate-decision handling. Rationale: this closes a gap identified during derivation — see `srs/FINDINGS.md` FIND-001. The SyRS records that decisions carry approver identity (SysR-P-F-08) and StRS defines the approver as a distinct stakeholder role (STK-05), but no SysR requires the service to verify the deciding identity actually holds that role. Alternative considered: rely on the demo UI being reachable only by designated approvers, with no service-side check — rejected as inconsistent with the fail-closed/least-privilege posture applied everywhere else in this document (SRS-APR-SEC-01, SysR-P-SEC-03). **Owner known-limitation note (Checkpoint B0-b, not a change to the requirement):** as drafted, this requirement does not forbid an initiator who also holds the approver role from approving their own proposal — acceptable at demo tier; four-eyes / initiator≠approver separation is a staging/phase-two concern and is not built now.
  *Trace:* SysR-P-F-08 (approver identity recording, by extension), StRS STK-05. *Verification:* T (a decision attempt from a non-approver identity is refused). No Phase A eval case exercises this dimension — recommend it as a future addition to `eval/cases/domain/unauthorized_write.yaml` (e.g., "decision submitted by an identity without the approver role").

- **SRS-APR-SEC-03 — Identity propagation.** The initiating user identity (SRS-APR-IF-01) and the approver identity (SRS-APR-IF-02) shall each be established from the enterprise identity provider's authenticated session (SysR-P-IF-05), never accepted as a client-supplied field; the service shall not use a broadly shared credential to represent either identity (SysR-P-SEC-02).
  *Trace:* SysR-P-IF-05, SysR-P-SEC-02. *Verification:* I (identity-source inspection), T (a request asserting an identity different from its authenticated session is rejected). No Phase A eval case exercises identity-spoofing on the approval path.

- **SRS-APR-SEC-04 — Audit-record integrity.** `Resolved at Checkpoint B0-b (accepted as drafted, closes FIND-002):` once a proposal reaches a terminal state (`approved`, `rejected`, `expired`), its decision record shall be immutable — no operation exposed by this service shall update or delete a terminal-state record's action, arguments, approver identity, decision, or timestamp. Rationale: StR-APR-03 requires decision records be retrievable "as audit evidence," which implies the evidence is trustworthy; the SyRS states no explicit immutability mechanism, so this document proposes one. Alternative considered: allow corrections via a compensating new record referencing the original (append-only correction) — reasonable if a real correction workflow is ever needed; rejected for the demo tier as unnecessary complexity.
  *Trace:* SysR-P-SEC-06, SysR-P-SEC-01. *Verification:* I (no update/delete operation in the service's exposed interface), T (attempted mutation of a terminal record fails).

## 5. Quality Requirements (SRS-APR-QUAL-*)

- **SRS-APR-QUAL-01 — Non-developer approver usability.** A pilot approver with no software-development background shall be able to complete an approve-or-reject decision using only the decision surface (SRS-APR-IF-02) and the decision context it presents (SRS-APR-F-05), without consulting any system outside the approval interface and the audit record, and without prior training beyond a single walkthrough.
  *Trace:* SysR-P-USE-01. *Verification:* D (approver walkthrough in staging, per SysR-P-USE-01).

- **SRS-APR-QUAL-02 — Held, never auto-approved, when the shared service is unreachable.** When any consumer (an agent workload or another platform component) cannot reach the approval service, or receives no response within its own configured request timeout, that consumer shall treat the affected action as held: it shall not synthesize a locally-assumed `approved` decision, shall not reuse a prior decision for a different proposal, and shall not release execution by any path that bypasses SRS-APR-IF-02's decision surface. This is a consumer-side extension of SRS-APR-SEC-01's fail-closed guarantee to the shared-service boundary introduced once the approval service is consumed by more than one agent/tool workload (`DECISIONS.md` DEC-098) rather than co-located with a single agent's own deployment; it composes with, and does not replace, the independent per-agent write kill switch already required by SysR-P-OPS-03 — together the two form a two-level fail-safe: SysR-P-OPS-03's operator-triggered, per-agent switch, and this requirement's automatic, consumer-side default the moment the shared gate itself is unreachable, requiring no operator action for that specific case.
  *Trace:* SysR-P-SEC-05, SysR-P-OPS-03 (by extension — the independent-kill-switch principle this requirement's second level composes with). *Verification:* T (fault injection: block network access from ≥2 distinct consumer workloads to the approval service; confirm zero execution release from either, and confirm SysR-P-OPS-03's own kill switch is not required to achieve that outcome), D.

- **Performance.** *Not applicable — tailored out.* No component-specific latency or throughput target is set for this blueprint's demo tier; the only platform-level performance requirement bearing on this component is the one-hour local-start budget (SysR-P-PERF-01), which is a whole-golden-path measure, not an approval-service-specific one.

## 6. Verification *(consolidated)*

| Requirement | Method | Evidence |
|---|---|---|
| SRS-APR-F-01 | T | Phase B schema-reject test (needed); DRQ-001..006 (agent-side, partial) |
| SRS-APR-F-02 | T | Phase B concurrency test (needed) |
| SRS-APR-F-03 | T | UAW-002 (agent-observable); Phase B expiry-timer test (needed) |
| SRS-APR-F-04 | I, T, D | DRQ-001..006, UAW-001..006 (agent-observable) |
| SRS-APR-F-05 | T | Phase B context-completeness test (needed) |
| SRS-APR-F-06 | T | Phase B list-query test (needed) |
| SRS-APR-F-07 | T | Phase B idempotency test (needed) |
| SRS-APR-IF-01 | I, T | Phase B schema conformance test (needed) |
| SRS-APR-IF-02 | I, T | Phase B schema conformance test (needed) |
| SRS-APR-IF-03 | T | Phase D dashboard trace-continuity check |
| SRS-APR-IF-04 | I, T | Phase B schema conformance test (needed) |
| SRS-APR-IF-05 | I, T | Phase D standalone-service integration test (needed); Phase B verified instead via SRS-AGT-F-04's arguments-equality test on the interim mechanism |
| SRS-APR-DATA-01 | I, T | Phase B restart-persistence test (needed) |
| SRS-APR-DATA-02 | I, D | Phase D audit-retrieval exercise |
| SRS-APR-SEC-01 | T, I | UAW-001..006 (agent-observable); Phase B fault-injection test (needed) |
| SRS-APR-SEC-02 | T | Phase B non-approver-decision test (needed); recommend eval-set addition |
| SRS-APR-SEC-03 | I, T | Phase B identity-spoofing test (needed) |
| SRS-APR-SEC-04 | I, T | Phase B immutability test (needed) |
| SRS-APR-QUAL-01 | D | Phase D approver walkthrough |
| SRS-APR-QUAL-02 | T, D | Phase G consumer-side fault-injection test (needed; executable once a second consumer exists, G3+) |

"Needed" marks a Phase B verification artifact that does not yet exist — listed for `tools/trace-check`'s check (d), which activates once Phase B produces tests.

## 7. Traceability

| SRS-APR requirement | Traces to | Verification |
|---|---|---|
| SRS-APR-F-01 | SysR-P-F-08 | T |
| SRS-APR-F-02 | SysR-P-F-08 | T |
| SRS-APR-F-03 | SysR-P-F-08 | T |
| SRS-APR-F-04 | SysR-P-F-09 | I, T, D |
| SRS-APR-F-05 | SysR-P-F-08, SysR-P-USE-01 | T |
| SRS-APR-F-06 | SysR-P-F-08, SysR-P-USE-01 | T |
| SRS-APR-F-07 | SysR-P-F-08 | T |
| SRS-APR-IF-01 | SysR-P-F-08 | I, T |
| SRS-APR-IF-02 | SysR-P-F-08, SysR-P-USE-01 | I, T |
| SRS-APR-IF-03 | SysR-P-IF-06 | T |
| SRS-APR-IF-04 | SysR-P-F-08, SysR-P-USE-01 | I, T |
| SRS-APR-IF-05 | SysR-P-F-08, SysR-A-F-04 (ref.) | I, T |
| SRS-APR-DATA-01 | SysR-P-F-08, SysR-P-SEC-01 | I, T |
| SRS-APR-DATA-02 | SysR-P-SEC-06, SysR-P-INFO-03 | I, D |
| SRS-APR-SEC-01 | SysR-P-SEC-05 | T, I |
| SRS-APR-SEC-02 | SysR-P-F-08 (StRS STK-05) | T |
| SRS-APR-SEC-03 | SysR-P-IF-05, SysR-P-SEC-02 | I, T |
| SRS-APR-SEC-04 | SysR-P-SEC-06, SysR-P-SEC-01 | I, T |
| SRS-APR-QUAL-01 | SysR-P-USE-01 | D |
| SRS-APR-QUAL-02 | SysR-P-SEC-05, SysR-P-OPS-03 (ref.) | T, D |

**SysR coverage.** SRS-APR requirements trace to: SysR-P-F-08, SysR-P-F-09, SysR-P-USE-01, SysR-P-IF-05, SysR-P-IF-06, SysR-P-SEC-01, SysR-P-SEC-02, SysR-P-SEC-05, SysR-P-SEC-06, SysR-P-INFO-03, SysR-P-OPS-03. This is informative; `tools/trace-check` (Phase B0, check (b)) is the authoritative validator once built.

**Orphan check (manual, this checkpoint).** Every SysR ID cited above was confirmed present in `SyRS-AGP-001_EN.md` §4.1/§5/§7/§12/§13 by direct reading during derivation (see `reports/feature-phase-b0-srs.md`).

---

*Requirements marked PROPOSED are not signed. Originally submitted at Checkpoint B0-a with 4 PROPOSED items; all 4 were resolved at Checkpoint B0-b, and SRS-APR-IF-05 was added at that same checkpoint (purely additive) to close FIND-004.*

**All 4 PROPOSED items in this document were resolved at Checkpoint B0-b:** SRS-APR-F-04 (release mechanism — resolved jointly with SRS-AGT-F-04 as the agent-as-invoker model, see `DECISIONS.md` DEC-008), SRS-APR-F-07 (idempotent submission, accepted as drafted), SRS-APR-SEC-02 (approver authorization, accepted as drafted, closes FIND-001 — with an owner-noted known limitation on initiator-as-approver, see inline note), SRS-APR-SEC-04 (audit-record integrity, accepted as drafted, closes FIND-002). **SRS-APR-IF-05** (terminal-state proposal query) was added at this checkpoint, not carried as a PROPOSED item — it is new, additive content adopted directly per DEC-008, closing FIND-004.
