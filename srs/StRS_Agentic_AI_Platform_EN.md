# Stakeholder Requirements Specification (StRS)

## Agentic AI Platform — Golden Path MVP and Pilot Agent

---

## Document Identification

| Field | Value |
|---|---|
| Document ID | StRS-AGP-001 |
| Version | 1.1 (amended baseline) |
| Status | Baseline — living working standard |
| Date | 2026-08-12 |
| Conformance | Structured per ISO/IEC/IEEE 29148, clause 9.3 (StRS information item content) |
| System of interest | The Agentic AI Platform golden path, together with one pilot agent (Platform Knowledge and Request Agent) as its first exemplar use |
| Classification | Organization-agnostic blueprint; contains no proprietary content |

### Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-12 | Account Owner / Advisor | Initial draft |
| 0.2 | 2026-08-12 | Account Owner / Advisor | Incorporated Annex A clarifications (OI-01, OI-02, OI-03); replaced schedule statements with complexity-based sizing; pilot exit redefined by evidence rather than duration |
| 0.3 | 2026-08-12 | Account Owner / Advisor | Editorial alignment with Annex A v0.3 (assumption-log model): ITSM integration restated as *adopted working assumption* (§2b); Associated Documents updated to describe the Assumption Log mechanism. No requirements changed. |
| 0.4 | 2026-08-12 | Account Owner / Advisor | Added StR-EVL-04 (domain-expert validation of ground truth — closes developer self-approval gap on the promotion gate). Extended StR-SEC-01 with model endpoint/identifier/version and routing reason code per call (model-lifecycle audit, meaningful under M-06 route changes). Extended §2 out-of-scope: closed-loop autonomous execution excluded as an explicit phase decision; portal-as-MCP-tool disambiguated as a phase-two candidate (POL-06, POL-09). Revised StR-DX-01: template also directly instantiable, de-risking the demonstration critical path without weakening portal exposure (OBJ-01/OS-01). |
| 1.0 | 2026-08-12 | Account Owner / Advisor | **Baseline.** Requirements content stable since v0.4; all pending editorial items cleared: Status field aligned to the living-working-standard model; §18.3 pilot-exit wording changed from "agreed" to "defined... proposed by the author and revisable on evidence" (no implied committee governance); STK-08 interest extended with evaluation ground-truth responsibility (consistency with StR-EVL-04). This baseline is the derivation basis for the SyRS and the evaluation set. Subsequent substantive changes proceed as change-controlled 1.x revisions; refutation of an adopted assumption that alters business scope (e.g., Annex A OI-02) would warrant a major revision. |
| 1.1 | 2026-08-28 | Account Owner / Advisor | Reference-implementation reframe (DECISIONS.md DEC-130): §19 reframed from single-engagement demonstration-milestone scope to reference-implementation delivery scope, with "MVP acceptance" retitled "reference-implementation acceptance" throughout that section. OBJ-07, STK-09, and the Blueprint glossary entry reworded from "a second team" to "an adopter," for consistency with the SyRS's SysR-P-F-13 rewording. No stakeholder requirement's substantive obligation changed — objectives are satisfied the same way, described as adopter-facing rather than engagement-facing. |

### Associated Documents

- **Annex A (StRS-AGP-001-AXA)** — Assumption Log. Informative; records the assumptions the author has adopted and works under, each with its basis, passively observed confirming/refuting evidence, and a concrete revision trigger. Maintained as a separate living document.

---

## Definitions

- **Agent**: A containerized application that combines a language model, retrieval over an approved knowledge corpus, and enterprise tool invocation to perform a bounded business task.
- **Golden path**: An opinionated, template-driven, supported route from local development through CI/CD to pilot production, with evaluation, identity, observability, and approval built in.
- **Blueprint**: The reusable set of templates, contracts, pipelines, and documentation that allows an adopter to instantiate a new agent without assistance from the original implementation team.
- **Contract**: A stable, environment-independent interface (model API, tool API, retrieval API, configuration schema, telemetry schema) that the agent depends on instead of environment-specific implementations.
- **Immutable artifact**: A single OCI image, identified by digest, promoted unchanged across all environments; environment differences are expressed only through configuration, secrets, policy bundles, model endpoint selection, and data-source bindings.
- **Evaluation set**: A version-controlled collection of task-level test cases used to validate agent behavior and gate promotion between environments.
- **Human approval boundary**: The point at which an agent-proposed action affecting an external system requires explicit human authorization before execution.
- **Pilot production**: A tightly scoped production environment with a limited user population, one data domain, one tool, one model route, and human approval for all writes.

## Acronyms and Abbreviations

| Acronym | Meaning |
|---|---|
| CI/CD | Continuous Integration / Continuous Delivery |
| IDP | Internal Developer Portal |
| ITSM | IT Service Management (platform) |
| MCP | Model Context Protocol |
| OCI | Open Container Initiative |
| OIDC | OpenID Connect |
| OPA | Open Policy Agent |
| OTel | OpenTelemetry |
| RAG | Retrieval-Augmented Generation |
| SBOM | Software Bill of Materials |
| SLO | Service Level Objective |
| StRS | Stakeholder Requirements Specification |
| SyRS | System Requirements Specification |

## References

**Compliance**

- ISO/IEC/IEEE 29148 — Systems and software engineering — Life cycle processes — Requirements engineering.

**Guidance**

- Agentic AI Platform MVP Approach (project reference document; organization-agnostic).
- Enterprise container platform, AI/ML platform, CI/CD, GitOps, and policy tooling documentation as applicable to the implementing organization.

---

## 1. Business Purpose *(ISO 29148 §9.3.1)*

The organization intends to adopt agentic AI as an operational capability, not as a series of disconnected experiments. Today, teams that wish to build AI agents face inconsistent development experiences, ungoverned access to data and tools, no standard evaluation practice, unclear identity and audit posture, and no supported route to production.

The proposed system addresses this by establishing an **opinionated, repeatable golden path** for developing, evaluating, deploying, and operating enterprise agents, proven through **one useful pilot agent**. The system contributes to business objectives by:

- Demonstrating a concrete, measurable improvement to an existing operational workflow rather than only showing the "art of the possible."
- Establishing confidence that enterprise platform technologies can support a private, hybrid, and governed agent platform.
- Producing a reusable "bring your own agent" blueprint that other business units can adopt without a single centralized implementation.
- Revealing the organizational, data, security, and platform gaps that must be resolved before broader production adoption.

The deliberate strategy is to lead with a practical, opinionated implementation and avoid building a generic platform containing every possible capability before proving a valuable use case.

## 2. Business Scope *(ISO 29148 §9.3.2)*

**a) Business domain.** IT platform operations and internal developer enablement: the activities by which engineers discover platform knowledge, diagnose operational issues, and raise service requests against enterprise systems.

**b) Range of business activities in scope.**

- Answering platform, procedure, and known-issue questions from a curated, approved knowledge corpus.
- Retrieving limited, read-only records from one enterprise system (an ITSM platform is the reference integration — an *adopted working assumption*, see Annex A OI-02; it is the reference because it exercises the human approval boundary with a natural, low-risk write action. Any replacement pair must still demonstrate one curated knowledge domain, one read-only enterprise retrieval, one approved write gated by human approval, and end-to-end traceability).
- Producing recommended actions, troubleshooting plans, or draft service requests.
- Submitting agent-drafted requests to the enterprise system **only after explicit human approval**.
- Developing, evaluating, promoting, and operating the agent along the golden path.

**External entities that interact with the business activities (in scope as interfaces, not as systems to be built):** the enterprise identity provider, the ITSM platform, the Internal Developer Portal, enterprise model-serving endpoints or approved external model providers, the container platform, and enterprise observability services.

**c) Scope of the system being developed.** The system of interest comprises two inseparable parts:

1. **The golden path (platform)**: agent template, local development environment, CI/CD pipeline with evaluation gates, GitOps promotion, identity integration, policy scaffolding, telemetry, and the human approval workflow. Identity and policy depth in phase one follows a three-tier framing (Annex A OI-03): *shown working* — user authentication via OIDC, a dedicated service identity per agent workload, scoped read-only tool credentials, the human approval workflow, and full audit telemetry; *shown as scaffolding* — the policy bundle structure and CI policy validation, including at least one enforced deny path (e.g., an unauthorized tool call or disallowed write) to prove the enforcement point exists; *explicitly deferred* — cryptographic workload attestation, per-agent sandbox profiles, and fleet-wide policy governance.
2. **The pilot agent (first use)**: a Platform Knowledge and Request Agent exercising the golden path end to end.

**Explicitly out of scope for the MVP** (deferred to a second phase): enterprise-wide data mesh, autonomous infrastructure remediation, general-purpose multi-agent orchestration, broad enterprise MCP enablement, model fine-tuning, new on-premises GPU infrastructure, dynamic semantic routing across every provider, an agent marketplace, organization-wide federated governance, production sandbox policy profiles for every agent type, closed-loop autonomous execution of actions without human approval (whether against IT systems or physical/industrial systems), and exposing the Internal Developer Portal's capabilities (e.g., scaffolder templates) as agent-invocable tools over MCP — the latter noted as a phase-two candidate compatible with the phase-one tool contracts (POL-06, POL-09). In phase one the portal scaffolds agents (StR-DX-01); it is not itself a tool that agents invoke.

## 3. Business Overview *(ISO 29148 §9.3.3)*

The relationships among the main elements are:

- An **agent developer** instantiates an agent project from a template exposed by the **Internal Developer Portal**, develops and evaluates locally, and pushes changes to Git.
- The **CI pipeline** builds one immutable OCI image, runs software, agent, security, and operational test categories, and publishes evaluation results as promotion evidence.
- A **GitOps controller** promotes the identical image (by digest) through ephemeral test, staging, and pilot production environments; environment differences live in configuration, secrets, policy bundles, endpoint selection, and data bindings.
- At runtime, the agent authenticates the **initiating user** via the enterprise identity provider, operates under its own **workload identity**, retrieves only authorized documents from the curated corpus, invokes the enterprise tool under contract, and routes model calls through a client abstraction with a logged reason code.
- Any **write action** is held pending until a **human approver** authorizes it; every retrieval, model call, tool call, policy decision, and approval decision is captured as telemetry and audit evidence.

## 4. Stakeholders *(ISO 29148 §9.3.4)*

| ID | Stakeholder class | Interest in the system |
|---|---|---|
| STK-01 | Business sponsor | Measurable workflow improvement; evidence supporting a production investment decision |
| STK-02 | Agent developer | Fast, consistent laptop-to-production experience; no rewrites between environments |
| STK-03 | Platform engineering team | A supportable, repeatable golden path; low operational burden per additional agent |
| STK-04 | Pilot end user (e.g., an operations engineer) | Trustworthy answers, useful drafts, no unauthorized changes to systems they own |
| STK-05 | Human approver | Sufficient context to approve or reject agent-proposed writes quickly and safely |
| STK-06 | Security and governance function | Identity attribution, least privilege, policy enforcement, complete audit trails |
| STK-07 | Enterprise tool owner (e.g., ITSM platform owner) | Controlled, attributable, rate-bounded access; no unapproved writes |
| STK-08 | Data/knowledge owner | Corpus contents are approved, classified, owned, versioned, and refreshable; evaluation ground truth is authored or explicitly validated by this class (StR-EVL-04) |
| STK-09 | Adopter | Ability to instantiate the blueprint without help from the original team |
| STK-10 | Site reliability / operations | SLOs, rollback, support procedures, actionable telemetry |

## 5. Business Environment *(ISO 29148 §9.3.5)*

The system operates in an enterprise environment characterized by: an established container platform and internal developer portal; an enterprise OIDC identity provider; regulatory and internal-policy expectations of auditability and least privilege; a hybrid posture in which large models may be served internally or consumed from approved external providers; and an organizational preference for assembling validated patterns over building bespoke systems.

## 6. Goals and Objectives — MVP Success Measures *(ISO 29148 §9.3.6)*

The MVP is accepted when the following measurable objectives are met:

| ID | Objective |
|---|---|
| OBJ-01 | A developer can instantiate the template and run the agent locally in under one hour. |
| OBJ-02 | The identical OCI image digest built in CI is the digest running in pilot production. |
| OBJ-03 | Exactly one curated data source and one enterprise tool are integrated. |
| OBJ-04 | All tool calls, model calls, retrieval events, and approval decisions are traced end to end. |
| OBJ-05 | Zero write operations occur without prior human approval. |
| OBJ-06 | The agent meets the agreed task-success threshold against the version-controlled evaluation set. |
| OBJ-07 | An adopter instantiates the blueprint without assistance from the original implementation team. |
| OBJ-08 | The pilot demonstrates a measurable improvement to the selected workflow against its baseline. |

## 7. Business Model *(ISO 29148 §9.3.7)*

The system creates value as an internal platform capability: each additional agent built on the golden path amortizes the platform investment, reduces time-to-first-agent for adopting teams, and inherits governance rather than re-implementing it. The pilot agent creates direct value by reducing time spent searching platform knowledge and drafting service requests, and indirect value as the proof required for the phase-two investment decision.

## 8. Information Environment *(ISO 29148 §9.3.8)*

- **Knowledge corpus**: tens to hundreds of approved documents (platform documentation, operating procedures, architecture standards, known issues). Each document has an owner, a classification, a version or effective date, an access policy, source metadata, and a documented refresh process.
- **Enterprise records**: read-only records retrieved from one enterprise system under the initiating user's authorization.
- **Configuration and policy**: environment-injected configuration, externally managed secrets, versioned policy bundles, versioned prompts and tool schemas — all under version control.
- **Telemetry and evidence**: distributed traces, metrics, application and audit logs, evaluation results, and experiment tracking records.
- No proprietary content is embedded in the blueprint itself; seeded local corpora use synthetic or public sample data.

## 9. Business Processes *(ISO 29148 §9.3.9)*

| ID | Process | Description | Scenarios |
|---|---|---|---|
| BP-01 | Knowledge inquiry | A user asks a platform question; the agent answers with citations from the approved corpus. | OS-03 |
| BP-02 | Assisted request drafting | The agent retrieves read-only enterprise records, drafts a service request, and submits it after human approval. | OS-04, OS-05 |
| BP-03 | Agent development | A developer scaffolds, develops, and evaluates an agent locally against the same contracts used in production. | OS-01 |
| BP-04 | Promotion | CI builds the immutable artifact; evaluation gates and GitOps promote it through environments. | OS-02 |
| BP-05 | Corpus curation | A knowledge owner adds, updates, classifies, or retires corpus documents through a documented refresh process. | OS-06 |
| BP-06 | Operation and audit | Operators monitor SLOs, respond to incidents, roll back, and produce audit evidence on demand. | OS-07, OS-08 |

## 10. Operational Policies and Rules *(ISO 29148 §9.3.10 / part of §9.3.16a)*

- **POL-01 — One immutable artifact.** One OCI image is promoted unchanged from CI through pilot production; production images are never rebuilt from a separate branch or alternate source tree.
- **POL-02 — Human approval for writes.** Every agent action that creates or modifies state in an external system requires explicit prior human approval.
- **POL-03 — Read-only by default.** The agent's default posture toward enterprise systems is read-only.
- **POL-04 — Least privilege and attribution.** The agent operates under a distinct workload identity, acts on behalf of an authenticated initiating user, and never uses broadly shared credentials.
- **POL-05 — Evaluation as a gate.** Evaluation results gate promotion between environments; they are not a one-time demonstration.
- **POL-06 — Contract-driven design.** The agent depends only on stable contracts (model API, tool contracts, retrieval contract, injected configuration, standard telemetry); proposals that couple the agent to a specific provider or environment are rejected.
- **POL-07 — Deliberate constraint.** The MVP agent has one business role, one knowledge domain, one primary tool, a limited action set, explicit timeouts and retry limits, a maximum number of reasoning/tool steps, and a deterministic fallback when it cannot proceed safely.
- **POL-08 — Anonymized, reusable blueprint.** All blueprint deliverables are organization-agnostic and use synthetic or public sample data only.
- **POL-09 — Phase-two readiness without phase-two scope.** Phase-one contracts are designed so that data mesh, model routing, sandboxing, and memory tiers can attach later without rework — and none of them is built now.

## 11. Operational Constraints *(ISO 29148 §9.3.11)*

- The system deploys on the organization's existing container platform; no new GPU infrastructure is procured for the MVP.
- Authentication uses the existing enterprise OIDC identity provider.
- Secrets are held in the existing enterprise secret management service.
- Large models run on shared development/enterprise endpoints; developer laptops interact with the model contract, never with a locally hosted production-scale model.
- Pilot production is bounded to one cluster and namespace, one pilot user group, one data domain, one tool, and one approved model route with a defined fallback.

## 12. Operational Modes *(ISO 29148 §9.3.12 / §9.3.16c)*

| Mode | Description |
|---|---|
| M-01 Local development | Agent and supporting services run on a developer workstation with a seeded corpus, mock tool server, shared development model endpoint, and a local evaluation CLI. |
| M-02 CI validation | Pull-request pipeline: software, agent, security, and operational test categories; container build; SBOM generation. |
| M-03 Ephemeral test | The built image deploys into a temporary namespace with test identity, development model endpoint, and synthetic data; the automated evaluation suite runs as a gate. |
| M-04 Staging | Real identity provider, approved staging data, read-only enterprise integration, complete telemetry, load and failure testing. |
| M-05 Pilot production | GitOps-promoted image, limited user population, human approval for writes, SLOs, audit trails, rollback procedures. |
| M-06 Degraded / fallback | On model or tool failure or step-limit exhaustion, the agent falls back deterministically: it reports its state, escalates to a human, and takes no unapproved action. |

## 13. Operational Quality *(ISO 29148 §9.3.13)*

Stakeholders prioritize, in order: (1) **safety and auditability** of agent actions, (2) **trustworthiness** of answers (grounding and citation), (3) **repeatability** of the developer experience, (4) **latency and cost** within agreed budgets per interaction. Speed is never bought at the expense of the approval boundary or audit completeness.

## 14. Business Structure *(ISO 29148 §9.3.14)*

The system aligns to a federated structure: a platform engineering function owns the golden path and its contracts; business/domain teams own their agents, corpora, and evaluation sets; the security and governance function owns policy content; enterprise tool owners own tool-side authorization. The blueprint must not assume a single centralized implementation team.

## 15. User Requirements *(ISO 29148 §9.3.15)*

Requirements use "shall" and are intended to be verifiable. Each requirement will be traced to system requirements in the SyRS.

### 15.1 Developer experience (STK-02, STK-09)

- **StR-DX-01.** An agent developer shall be able to instantiate a complete agent project (source, container build, deployment manifests, GitOps configuration, tool skeleton, evaluation project, telemetry, policy scaffolding, documentation) from a template exposed through the Internal Developer Portal. The template shall also be instantiable directly (e.g., via a command-line interface against the template repository), so that portal integration is not a prerequisite for local development or for the demonstration milestone.
- **StR-DX-02.** An agent developer shall be able to run and interact with the agent on a local workstation, using a seeded knowledge corpus and a mock enterprise tool, within one hour of instantiating the template.
- **StR-DX-03.** An agent developer shall be able to execute any individual evaluation case, or the complete evaluation suite, locally via a command-line interface.
- **StR-DX-04.** An agent developer shall use the same tool schemas, prompt formats, policy formats, and configuration contracts locally as are used in all deployed environments.
- **StR-DX-05.** An agent developer shall not need to modify agent source code to move the agent between environments or to change the model provider.
- **StR-DX-06.** A second, independent team shall be able to instantiate and deploy a new agent from the blueprint using only the blueprint's documentation.

### 15.2 Pilot end use (STK-04)

- **StR-USR-01.** A pilot user shall be able to ask platform, procedure, and known-issue questions and receive answers grounded in the approved corpus, with citations identifying the source documents.
- **StR-USR-02.** A pilot user shall be able to request retrieval of read-only information from the integrated enterprise system, limited to records that user is authorized to view.
- **StR-USR-03.** A pilot user shall receive a recommended action, troubleshooting plan, or draft request as the agent's output for actionable inquiries.
- **StR-USR-04.** A pilot user shall be informed explicitly when the agent cannot answer safely or exceeds its operating limits, together with an escalation path to a human.

### 15.3 Approval and control (STK-05, STK-06, STK-07)

- **StR-APR-01.** A human approver shall review and explicitly approve or reject every agent-proposed action that would create or modify state in an external system, before the action executes.
- **StR-APR-02.** A human approver shall be presented, at decision time, with the proposed action, its arguments, the evidence the agent used, and the initiating user's identity.
- **StR-APR-03.** An approval decision shall be recorded with approver identity, timestamp, and outcome, and shall be retrievable as audit evidence.
- **StR-APR-04.** A pending approval that is not decided within a defined time limit shall expire without executing the action.

### 15.4 Security, identity, and audit (STK-06, STK-07, STK-08)

- **StR-SEC-01.** The organization shall be able to determine, for every agent interaction: the initiating user, the agent workload identity, the data retrieved and its authorization basis, the tool operations invoked, the model endpoint and model identifier/version used for each model call together with the routing reason code, whether approval was required and granted, and the credential or workload identity used.
- **StR-SEC-02.** The agent shall access the enterprise tool and the knowledge corpus only under authorization derived from the initiating user's identity and the agent's workload identity, never through broadly shared credentials.
- **StR-SEC-03.** The knowledge owner shall be able to establish, for every corpus document: owner, classification, version or effective date, access policy, source metadata, and refresh process.
- **StR-SEC-04.** The security function shall be able to express and update agent operating policy (permitted tools, action limits, approval rules) as versioned policy content, without rebuilding the agent image.

### 15.5 Quality and evaluation (STK-01, STK-03)

- **StR-EVL-01.** The organization shall maintain a version-controlled evaluation set covering at minimum: answer correctness, retrieval relevance, citation quality, tool selection, tool-argument correctness, refusal and escalation behavior, resistance to prompt injection, policy compliance, and latency and token consumption.
- **StR-EVL-02.** Promotion of the agent between environments shall be gated on evaluation results meeting agreed thresholds.
- **StR-EVL-03.** The evaluation set for the pilot workflow shall exist before the complete agent implementation is built.
- **StR-EVL-04.** The expected outcomes (ground truth) of the evaluation set shall be authored or explicitly validated by the data/knowledge owner (STK-08) or a designated domain subject-matter expert, and that validation shall be recorded as part of the evaluation set's version history.

### 15.6 Operations (STK-10)

- **StR-OPS-01.** Operators shall be able to observe agent SLOs, traces, metrics, and logs through the organization's standard observability services.
- **StR-OPS-02.** Operators shall be able to roll back the pilot deployment to the previously approved image digest through the GitOps mechanism.
- **StR-OPS-03.** Operators shall be able to disable the agent's write pathway independently of its read/answer pathway.

### 15.7 Organizational requirements (STK-01, STK-03)

- **StR-ORG-01.** The organization shall promote exactly one immutable OCI image (identified by digest) from CI through pilot production, with environment differences expressed only in configuration, secrets, policy bundles, model endpoint selection, and data-source bindings.
- **StR-ORG-02.** The blueprint and all its deliverables shall be organization-agnostic, using synthetic or public sample data only.
- **StR-ORG-03.** Phase-one contracts (model client abstraction, tool contracts, retrieval contract, policy format, telemetry) shall be designed so that phase-two capabilities (data mesh, model routing, agent sandbox, memory tiers) can integrate without reworking the agent.
- **StR-ORG-04.** The MVP shall integrate exactly one agent, one data domain, one enterprise tool, and one approved model route with a defined fallback; expansion beyond these bounds shall require an explicit scope decision.

## 16. Operational Concept *(ISO 29148 §9.3.16)*

**a) Operational policies and constraints.** See sections 10 and 11.

**b) Description of the proposed system.** A template-driven golden path produces containerized agents that depend only on stable contracts: a standardized (OpenAI-compatible or equivalent) model API behind a client abstraction with rules-based routing and logged reason codes; MCP or REST contracts for enterprise tools; a retrieval contract with consistent metadata and authorization behavior; environment-injected configuration; and OpenTelemetry telemetry. The pilot agent answers curated platform knowledge questions, retrieves read-only enterprise records, drafts requests, and executes writes only after human approval. The agent is treated as a distributed application, not an unrestricted chatbot.

**c) Modes of operation.** See section 12.

**d) User classes and other involved personnel.** See section 4 (stakeholders STK-02, STK-04, STK-05, STK-08, STK-10 interact directly with the system; STK-01, STK-03, STK-06, STK-07, STK-09 govern, own, or adopt it).

**e) Support environment.** The organization's container platform, Internal Developer Portal, CI/CD and GitOps services, identity provider, secret management, observability stack, model-serving endpoints, and evaluation/experiment tracking services.

## 17. Operational Scenarios *(ISO 29148 §9.3.17)*

- **OS-01 — Local first run (BP-03).** A developer instantiates the template from the Internal Developer Portal, starts the local environment (agent, seeded corpus, mock tool, development model endpoint), asks a sample question, receives a cited answer, and runs the evaluation suite locally — all within one hour.
- **OS-02 — Gated promotion (BP-04).** A developer opens a pull request. CI runs the four test categories, builds the image, generates the SBOM, deploys to an ephemeral namespace, and runs the evaluation suite. The evaluation gate passes; GitOps promotes the identical digest to staging.
- **OS-03 — Knowledge inquiry (BP-01).** A pilot user asks about a known platform issue. The agent retrieves authorized corpus documents, answers with citations, and records retrieval identifiers, model selection, and telemetry for the run.
- **OS-04 — Approved write (BP-02).** A pilot user asks the agent to raise a service request. The agent retrieves read-only context from the enterprise system, drafts the request, and submits it for approval. An approver reviews the draft, evidence, and initiating identity, and approves. The agent executes the write; the full chain is auditable.
- **OS-05 — Rejected or expired write (BP-02).** As OS-04, but the approver rejects the draft, or the approval window expires. No write occurs; the user is informed; the decision is recorded.
- **OS-06 — Corpus refresh (BP-05).** A knowledge owner updates a procedure document with a new version and effective date through the documented refresh process; subsequent answers cite the new version.
- **OS-07 — Fallback under failure (BP-06).** The primary model endpoint fails mid-task. The client abstraction routes to the fallback model and logs a reason code; if the agent still cannot proceed safely, it stops deterministically and escalates to a human.
- **OS-08 — Rollback (BP-06).** A defect is detected in pilot production. Operations reverts the GitOps state to the previous image digest; the prior version is serving within the agreed rollback objective.
- **OS-09 — Adopter bootstrap (validates OBJ-07).** An adopter uninvolved in this reference implementation's own construction, following only `docs/cluster-profile.md` and `docs/adopting-this-blueprint.md`, instantiates the blueprint from documentation alone and reaches a locally running, evaluated agent without assistance. Verified by the Refresh #2 acceptance test (a second from-scratch bootstrap on a fresh cluster).
- **OS-10 — Injection resistance (evaluation scenario).** A retrieved document or user input contains instructions attempting to induce an unauthorized tool call. The agent does not execute the call; the attempt is logged; the corresponding evaluation cases pass.

## 18. Project Constraints *(ISO 29148 §9.3.18)*

This specification deliberately states **no schedule or duration estimates**. Duration depends on organizational factors outside this document's control (approval velocity, access provisioning, team availability) and belongs in the delivery plan, where it can be estimated formally against known resources and dependencies. What this specification does bound is **complexity**, which is a declared property of the system:

### 18.1 Complexity envelope (declared, verifiable)

| Dimension | Bound |
|---|---|
| Integrated enterprise entities | 1 data domain, 1 enterprise tool, 1 model route (+1 defined fallback) |
| Agents | 1 |
| Environments / operational modes | 6 (M-01 through M-06) |
| Contracts the agent depends on | 5 (model API, tool contract, retrieval contract, injected configuration, telemetry) |
| Stakeholder classes served | 10 (STK-01 through STK-10) |
| Write-action types requiring approval | 1 (draft-request submission) |
| Organizational dependency classes | 5 (identity provider access, tool-side credentials, staging data approval, pilot user group nomination, approver designation) |

Any increase to a bound in this table constitutes a scope change requiring an explicit decision (StR-ORG-04).

### 18.2 Relative build complexity by delivery step *(informative)*

| Delivery step | Dominant complexity driver | Relative complexity |
|---|---|---|
| 1. Discovery and evaluation set | Decision-making and domain capture, not code | Low technical / high organizational |
| 2. Local golden path | Template and contract design; highly automatable | Medium technical / low organizational |
| 3. CI and ephemeral testing | Pipeline and gate assembly from validated patterns | Medium technical / low organizational |
| 4. Staging integration | Real identity, credentials, and tool-side coordination | Medium technical / high organizational |
| 5. Controlled pilot | Operation, evidence capture, and human workflows | Low technical / high organizational |
| 6. Production architecture decision | Analysis of pilot evidence | Low technical / medium organizational |

### 18.3 Other constraints

- Reuse validated patterns, quickstarts, and reference repositories before writing new code; pin versions and commits.
- No procurement of new inference infrastructure within the MVP.
- Pilot exit is **evidence-based, not duration-based**: the pilot concludes when it has produced sufficient operational evidence for the phase-two decision — at minimum, a defined count of completed user interactions, a defined count of full approval cycles (including at least one rejection and one expiry), at least one exercised fallback (M-06), and at least one exercised rollback (OS-08), with thresholds proposed by the author during discovery and revisable on evidence.

## 19. Preliminary Life Cycle Concept — Delivery Alignment *(informative)*

The stakeholder requirements above are realized across the agreed six-step delivery sequence: (1) discovery and use-case definition, including the evaluation set (StR-EVL-03); (2) local golden path (StR-DX-*); (3) CI and ephemeral testing (StR-EVL-02, StR-ORG-01); (4) staging with real enterprise services (StR-SEC-*); (5) controlled pilot (StR-USR-*, StR-APR-*, StR-OPS-*, OBJ-08); (6) production architecture decision informed by pilot evidence (POL-09, StR-ORG-03). The detailed delivery plan is maintained as a separate project document and traced against this StRS and the derived SyRS.

**Reference-implementation scope (Annex A OI-01).** This project delivers a general-purpose reference implementation covering delivery Steps 1–3: an evaluation set, a local golden path, and CI with evaluation gates promoting an immutable artifact, with enterprise integration realized through a mocked, contract-conformant example tool and the approval workflow demonstrated against a test system. This scope is defined for any adopter, not for a specific engagement or date. Steps 4–6 — staging with an adopter's own real enterprise services, a controlled pilot, and a production-architecture decision — are the adopter's own extension path once they have cloned and bootstrapped the reference implementation in their own environment; this StRS documents them for traceability, not as work this delivery still owes to a specific stakeholder. Reference-implementation acceptance is defined exclusively by the objectives in §6 (OBJ-01 through OBJ-08); objectives presupposing Steps 4–6 (OBJ-03, OBJ-04, OBJ-05, and the production-facing portion of OBJ-08) are satisfied by an adopter completing those steps in their own environment, not by this reference delivery.

---

*End of Stakeholder Requirements Specification (Baseline 1.0). Next artifact in the requirements chain: System Requirements Specification (SyRS), deriving verifiable technical requirements from the stakeholder requirements herein.*
