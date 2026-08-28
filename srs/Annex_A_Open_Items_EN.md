# Annex A — Assumption Log

**Document ID:** StRS-AGP-001-AXA · **Version:** 1.1 · **Status:** Living working document
**Applies to:** StRS-AGP-001 v1.1
**Purpose:** This StRS is maintained as a personal working standard — a systematic, ISO 29148-structured way of approaching the project — not as a committee-governed artifact. There is no review board and no formal ratification session. Accordingly, this annex does not track open items awaiting external decisions. It records **assumptions the author adopts and works under**, each with a stated basis, the passively observed evidence that would confirm or refute it, and the concrete trigger that forces a revision. Rigor is preserved; blocking dependencies on other people are removed. This annex is informative; it introduces no new requirements.

### Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-08-12 | Initial draft (open-items model), written against StRS v0.1 |
| 0.2 | 2026-08-12 | Aligned with StRS v0.2; OI-01 reframed as scope-based; OI-01/OI-03 marked incorporated |
| 0.3 | 2026-08-12 | Mechanism changed from open-items / resolution-tracking model to **assumption-log model**, reflecting that the StRS is a personal working standard with no committee governance. OI-02 (ITSM scenario) and OI-03 (three-tier identity/policy framing) changed from pending to **adopted**; OI-01 closed as resolved in StRS v0.2 §19. IDs retained for traceability with v0.2. |
| 0.4 | 2026-08-12 | Applies-to updated to StRS v0.3; OI-02 editorial alignment marked completed (StRS §2b now reads "adopted working assumption"). |
| 0.5 | 2026-08-12 | Applies-to updated to StRS v0.4. Added OI-04: portal integration achievable with bounded effort in phase one, with a defined demotion path for the demonstration milestone (direct template instantiation per revised StR-DX-01) while full portal exposure remains required for MVP acceptance (OBJ-01). Note: the requesting edit specification assumed the annex was at v0.3; it was already at v0.4, so this revision is numbered v0.5. |
| 1.0 | 2026-08-12 | **Baseline**, paired with StRS v1.0. No assumption content changed: OI-01 remains Closed; OI-02, OI-03, OI-04 remain Adopted with their triggers active. The baseline does not freeze this log — it remains living; assumption changes after baseline are recorded here first, and trigger StRS revisions only when a refutation alters requirements. |
| 1.1 | 2026-08-28 | Paired with StRS v1.1 (reference-implementation reframe, DECISIONS.md DEC-130). **OI-04 closed** — not refuted, moot by completion: SysR-P-F-01 ships both the portal path and the direct-CLI path as permanent, delivered, adopter-facing capabilities (DEC-091/DEC-098), so the fallback scenario OI-04 hedged against no longer has a case to trigger. OI-01's own resolution (§19 defines scope, not date) still holds under the reframe; noted here since §19 was further revised. |

---

## OI-01 — Demonstration milestone vs. MVP acceptance

**Status: CLOSED** — fully resolved in StRS v0.2 (§19, "Milestones"). Retained in this log for traceability only.

The StRS body now defines the demonstration milestone by scope (delivery Steps 1–3, enterprise integration in read-only or mocked form, approval workflow demonstrated against a test system) and defines MVP acceptance exclusively by the §6 objectives (OBJ-01 through OBJ-08), with pilot exit evidence-based rather than duration-based (§18.3). No assumption remains to manage.

---

## OI-02 — Data-source + tool pair

**Assumption adopted:** The ITSM scenario — a Platform Knowledge and Request Agent with the ITSM platform as the single enterprise integration — is the working data-source + tool pair, and delivery Step 1 (the evaluation set) proceeds on this basis.

**Basis:** Among the candidate scenarios, the ITSM pair is the only one that exercises the human approval boundary (POL-02) with a natural, low-risk write action (drafting and submitting a service request). Alternatives considered (e.g., a technical-document search domain with a different read-only integration) demonstrate retrieval but not the approval boundary, which is a defining platform outcome of the MVP (OBJ-05). Any compliant pair must in every case demonstrate: one curated knowledge domain, one read-only enterprise retrieval, one approved write action gated by human approval, and end-to-end traceability (OBJ-03, OBJ-04, OBJ-05).

**Confirming / refuting evidence (passively observed):**
- *Confirming:* team discussions and delivery activity continue to reference the ITSM scenario; the evaluation set and demonstration narrative built on it are used without objection.
- *Refuting:* the delivery team converges on a different data/tool pair in its own discussions, or the ITSM integration proves unavailable to the delivery environment.

**Revision trigger:** A different data/tool pair emerges as the working direction in team discussion, or an access/availability constraint on the ITSM platform is identified.

**Sections affected if refuted:** §2 (business scope), BP-02, OS-04/OS-05, STK-07; the evaluation set (StR-EVL-*) must be rebuilt for the new domain. The complexity envelope (§18.1) is unaffected: any compliant replacement preserves the declared bounds (1 data domain, 1 tool, 1 write-action type). Note that the cost of refutation grows with work invested on this assumption; the trigger deserves particular attention during early team discussions, when changing course is cheapest.

**Editorial alignment (completed in StRS v0.3):** §2b now reads "an *adopted working assumption*, see Annex A OI-02". No further alignment pending.

---

## OI-03 — Depth of identity and policy enforcement in phase one

**Assumption adopted:** The three-tier framing stated in StRS v0.2 §2c — *shown working* (OIDC user authentication, dedicated service identity per agent workload, scoped read-only tool credentials, human approval workflow, full audit telemetry), *shown as scaffolding* (policy bundle structure and CI policy validation, with at least one enforced deny path), *explicitly deferred* (cryptographic workload attestation, per-agent sandbox profiles, fleet-wide policy governance) — correctly represents the phase-one depth intended by the approach document.

**Basis:** The framing is a conservative reading of the approach document, which commits to identity, least privilege, and policy scaffolding in phase one while explicitly deferring hardened sandboxing and attestation to phase two. The three tiers prevent both over-commitment ("full zero-trust in phase one") and under-representation ("no enforcement at all").

**Confirming / refuting evidence (passively observed):** The framing is being left as a review comment on the approach document — the author explicitly requested comments, so this is already-owed review work, not a new question posed to anyone. Tacit non-objection to the comment confirms the assumption; an objection or correction from the author refutes it.

**Revision trigger:** The approach document's author objects to or corrects the review comment, or a later revision of the approach document states a different phase-one depth.

**Sections affected if refuted:** §2c (three-tier framing) and the demonstration narrative derived from it.

---

## OI-04 — Internal Developer Portal integration effort

**Closed 2026-08-28 — resolved by completion, under the reference-implementation reframe (`DECISIONS.md` DEC-130).** Both instantiation paths of `SysR-P-F-01` — portal-driven (a) and direct CLI (b) — ship as permanent, delivered, adopter-facing capabilities (`DEC-091`, `DEC-098`). The fallback scenario this item hedged against (portal-integration effort proving too costly, forcing a demotion to CLI-only) no longer has a case to trigger: there is no single milestone left to endanger, and CLI-first instantiation was never a contingency to begin with — it is simply one of two equally supported, equally documented adoption paths. Retained below for its historical basis, not as an active assumption.

**Assumption adopted (historical, prior to closure):** Integration of the agent template with the Internal Developer Portal is achievable with bounded effort within phase one.

**Basis:** The template is a thin wrapper over a directly instantiable repository (see revised StR-DX-01, which requires direct instantiation — e.g., via a command-line interface against the template repository — independently of the portal). Portal work is therefore additive, not foundational: the golden path's substance (template contents, contracts, local environment, evaluation project) exists and is exercisable with or without the portal layer.

**Confirming / refuting evidence (passively observed):** Effort consumed by portal integration relative to the local golden path as a whole. Proportionate, bounded effort confirms; portal integration consuming a disproportionate share of phase-one effort, or accumulating blockers unrelated to the template itself, refutes.

**Revision trigger (historical, moot since closure):** Portal integration effort demonstrably endangers the demonstration milestone. On trigger: the portal exposure is reclassified from *shown working* to *shown as scaffolding* for that milestone, and direct instantiation satisfies StR-DX-01 for the demonstration. Full portal exposure remains required for MVP acceptance (OBJ-01) — the trigger demotes the milestone presentation, never the acceptance criterion. Retained for historical context; both paths are delivered, so this trigger has nothing left to arm.

**Sections affected if refuted:** The demonstration narrative (OS-01 as demonstrated at the milestone); no StRS requirement changes, since StR-DX-01 already admits both instantiation paths and OBJ-01 is untouched.

---

## Assumption status

| ID | Assumption | Status | Revision trigger |
|---|---|---|---|
| OI-01 | Demonstration milestone defined by scope (Steps 1–3), distinct from MVP acceptance (OBJ-01..08) | **Closed** (resolved in StRS v0.2 §19) | — (reopens only if §19 is revised) |
| OI-02 | ITSM scenario is the working data-source + tool pair; Step 1 proceeds on this basis | **Adopted** | A different pair emerges in team discussion, or an ITSM access/availability constraint is identified |
| OI-03 | Three-tier identity/policy framing represents the intended phase-one depth | **Adopted** | The approach document's author objects to the review comment, or a document revision states otherwise |
| OI-04 | Portal integration and direct CLI instantiation are both delivered, adopter-facing paths (SysR-P-F-01(a)/(b)) | **Closed — resolved by completion** | — (reopens only if SysR-P-F-01's dual-path delivery is reduced to one path) |

*End of Annex A (v1.0).*
