# System Requirements Specification (SyRS)

## Agentic AI Platform — Golden Path MVP and Pilot Agent

---

## Document Identification

| Field | Value |
|---|---|
| Document ID | SyRS-AGP-001 |
| Version | 0.3 (Draft, amended) |
| Status | Draft — derived for review under the personal working standard |
| Date | 2026-08-28 |
| Conformance | Structured per ISO/IEC/IEEE 29148, clause 9.4 (SyRS information item content), with declared tailoring (§0.3) |
| Derivation basis | StRS-AGP-001 v1.0 (Baseline) — frozen for this derivation; no StR is modified by this document |
| System of interest | The Agentic AI Platform golden path (platform) together with one pilot agent (Platform Knowledge and Request Agent) |
| Classification | Organization-agnostic blueprint; contains no proprietary content |
| Language | English (canonical); Spanish literal translation maintained in parallel (SyRS-AGP-001 ES) |

### Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-12 | Account Owner / Advisor | Initial draft derived from StRS-AGP-001 v1.0. 63 system requirements in two groups (SysR-P-\*, platform; SysR-A-\*, pilot agent); traceability matrix (Annex T); informative Red Hat realization table maintained as a separate companion document (SyRS-AGP-001-RRT). |
| 0.2 | 2026-08-26 | Account Owner / Advisor | SysR-P-F-01 amended per DECISIONS.md DEC-098: template instantiation split into an agent template and a separate tools template producing an independent MCP-server artifact (Phase G platform decomposition). No other SysR text changed. |
| 0.3 | 2026-08-28 | Account Owner / Advisor | Reference-implementation reframe (DECISIONS.md DEC-130): SysR-P-F-13 reworded from "a second, independent team" to "an adopter, per docs/adopting-this-blueprint.md"; §0.1's introductory "a second adopting team"/"a second team's agent"/"a blueprint a second team can adopt unassisted" phrasing reworded to "an adopter" throughout, for consistency with the reworded acceptance requirement. No requirement's substantive obligation changed. |

### Associated Documents

- **StRS-AGP-001 v1.0 (Baseline)** — Stakeholder Requirements Specification. The frozen derivation basis for this SyRS. Findings that would require changing an StR are reported in the findings report, never applied here.
- **StRS-AGP-001-AXA (Annex A — Assumption Log)** — living informative log of adopted assumptions. A new entry (OI-05, agentic-runtime realization support) is *proposed* alongside this SyRS; adoption is the author's decision.
- **SyRS-AGP-001-RRT — Red Hat Realization Table** — separate, **informative, non-normative** companion document mapping each protocol surface and capability in this SyRS to a concrete Red Hat realization with pinned version and verified support level. No normative requirement in this SyRS names a product.
- **Agentic AI Platform MVP Approach** — organization-agnostic guidance document.
- **ISO/IEC/IEEE 29148:2011** — requirements engineering (compliance reference).

### 0.1 Requirement grouping and identification

Requirements are stated in two groups, reflecting that an adopter inherits the platform but writes its own agent:

- **SysR-P-\*** — requirements on the **platform** (golden path): template, contracts, pipeline, promotion, identity, policy, approval workflow, observability, documentation. These are inherited unchanged by every adopting team.
- **SysR-A-\*** — requirements on the **pilot agent** (first exemplar). An adopter's agent must satisfy the SysR-A architectural and behavioral pattern for its own domain, but the concrete knowledge domain, tool, and evaluation content are adopter-specific.

Identifier scheme: `SysR-<group>-<category>-<nn>` with categories: F (functional), IF (interface), SEC (security), PERF (performance), USE (usability), MODE (modes/states), INFO (information management), POL (policies), LC (life cycle), OPS (operations), PKG (packaging), ARC (architecture constraint), EVL (evaluation), TEL (telemetry).

Each requirement carries: a verifiable **shall** statement; a **trace** to at least one StR of the baseline; and an assigned **verification method** — Inspection (I), Analysis (A), Demonstration (D), or Test (T). Where two methods are listed, the first is primary.

### 0.2 Requirement expression rules (normative for this document)

1. Requirements name **protocol surfaces and capabilities**, never products: OpenAI-compatible APIs (chat completions and, where noted, responses), MCP for tools, OCI for artifacts, OpenTelemetry (OTLP) for telemetry, OIDC for identity, declarative GitOps for promotion.
2. Products appear **only** in the separate informative realization table (SyRS-AGP-001-RRT), which records component, pinned version, support level (GA / Technology Preview / Developer Preview / community), and substitution path.
3. Realization assignment rule (see SysR-P-LC-03): GA productized with an Operator is preferred; Technology Preview only behind a contract with a documented swap path; Developer Preview only in local/demo modes, never in staging or pilot; upstream community only with an explicitly recorded justification.
4. No requirement or table in this document states schedule or duration estimates. Complexity is declared (StRS §18.1); calendar belongs to the delivery plan.

### 0.3 Tailoring statement (ISO 29148 §9.4)

All information items of clause 9.4 are addressed. The following are tailored for a software-only, container-deployed system: §9.4.10.1 (physical requirements) and §9.4.16 (packaging, handling, shipping and transportation) are interpreted as OCI artifact packaging and promotion; §9.4.11 (environmental conditions) is interpreted as the enterprise container-platform operating environment. §9.4.10.2 (adaptability) is used normatively for the phase-two integration seams.

---

## Definitions

Definitions from StRS-AGP-001 §Definitions apply. Additional terms:

- **Loop-in-pod**: the hosting pattern in which the agentic control loop (reasoning/tool-execution cycle) executes inside the agent's own immutable OCI image, invoking the model over an OpenAI-compatible API and tools over MCP. The agent process owns its loop; no shared agentic runtime is on the execution path.
- **Agent-as-a-Service (AaaS)**: the alternative hosting pattern in which the loop executes in a shared orchestration runtime exposed behind an OpenAI-compatible responses-style API, and the agent submits goals/turns rather than running the loop itself. Admitted as a future realization swap only (SysR-P-IF-09); not built in phase one.
- **Orchestrator adapter**: the internal interface (seam) between the agent's business logic and the loop implementation, designed so that the loop-in-pod realization can be replaced by an AaaS realization without changing business logic, tool contracts, or evaluation sets.
- **Protocol surface**: an interface defined by an open protocol or API convention (OpenAI-compatible API, MCP, OCI, OTLP, OIDC) rather than by a product.
- **Realization**: the concrete product/component selected to implement a protocol surface or capability; recorded only in the informative realization table.
- **Policy bundle**: versioned policy content (permitted tools, action limits, approval rules) loaded by the system at deployment/runtime without rebuilding the agent image.
- **Deny path**: a policy decision that blocks a requested action (e.g., an unauthorized tool call or a disallowed write) and is observable in telemetry.

## Acronyms and Abbreviations

The StRS acronym table applies, plus:

| Acronym | Meaning |
|---|---|
| AaaS | Agent-as-a-Service (hosting pattern) |
| I / A / D / T | Inspection / Analysis / Demonstration / Test (verification methods) |
| OTLP | OpenTelemetry Protocol |
| SysR | System Requirement |

---

## 1. System Purpose *(ISO 29148 §9.4.1)*

The system exists to convert the stakeholder needs of StRS-AGP-001 into an operating capability: an opinionated, repeatable golden path for developing, evaluating, deploying, and operating enterprise agents, proven end to end by one deliberately constrained pilot agent. The system's purpose is realized when a developer can go from template to a locally running, evaluated agent; when one immutable artifact is promoted through evaluation gates into a governed pilot; and when every retrieval, model call, tool call, policy decision, and human approval is attributable and auditable (StRS §1, §6).

## 2. System Scope *(ISO 29148 §9.4.2)*

**a) System name.** Agentic AI Platform — Golden Path MVP and Pilot Agent (system of interest as defined in StRS §2c).

**b) Needs baseline.** The finalized needs analysis is StRS-AGP-001 v1.0: users need trustworthy, cited answers from an approved corpus; read-only enterprise retrieval; drafted actions executed only after human approval; developers need laptop-to-production parity without rewrites; the organization needs attribution, least privilege, evaluation-gated promotion, and a blueprint an adopter can adopt unassisted. The system will do exactly this and will not deliver the deferred phase-two capabilities (StRS §2c "explicitly out of scope").

**c) Application, benefits, objectives.** Acceptance is defined exclusively by StRS §6 (OBJ-01 through OBJ-08). This SyRS derives the verifiable technical requirements whose satisfaction makes those objectives achievable, within the complexity envelope of StRS §18.1: 1 agent, 1 data domain, 1 enterprise tool, 1 model route (+1 defined fallback), 6 operational modes, 5 agent-facing contracts, 1 approval-gated write-action type. **No requirement in this SyRS increases any bound of that envelope**; a proposal that would do so is scope creep and requires an explicit decision (SysR-P-POL-02, StR-ORG-04).

## 3. System Overview *(ISO 29148 §9.4.3)*

### 3.1 System context *(§9.4.3.1)*

The system sits between five external entity classes (StRS §2b): the enterprise OIDC identity provider; one enterprise system reached through the tool contract (an ITSM platform is the adopted working assumption, Annex A OI-02); the Internal Developer Portal (template exposure); model-serving endpoints (internal or approved external) behind the OpenAI-compatible surface; and the organization's container platform, secret management, and observability services. Interfaces crossing the boundary are specified in §7. Human elements: agent developer, pilot user, human approver, knowledge owner, operator (StRS §4).

Context (logical):

```
 Developer ──template──▶ [IDP / template repo] ──scaffold──▶ [Agent project (Git)]
 Agent project ──PR──▶ [CI: 4 test categories + build + SBOM + eval gate]
        └──▶ one OCI image (digest) ──declarative GitOps──▶ M-03 ▶ M-04 ▶ M-05
 Pilot user ──OIDC──▶ [Agent pod: loop-in-pod]
        ├── OpenAI-compatible API ──▶ model route (+ fallback, reason code)
        ├── Retrieval contract ──▶ curated corpus (authz-filtered)
        ├── MCP ──▶ enterprise tool (read-only; writes held for approval)
        └── OTLP ──▶ traces / metrics / logs / audit evidence
 Human approver ──▶ [Approval workflow] ──approve/reject/expire──▶ write execution via tool contract
```

### 3.2 System functions *(§9.4.3.2)*

Major capabilities, conditions, constraints: template-driven scaffolding; local development parity (seeded corpus, mock tool, dev model endpoint, local eval CLI); CI with four validation categories and an evaluation promotion gate; single-digest GitOps promotion; grounded question answering with citations; read-only enterprise retrieval; draft-and-approve write execution; rules-based model routing with reason codes; policy bundles with at least one enforced deny path; end-to-end attribution telemetry; rollback and write-path kill switch. Conditions and constraints: the complexity envelope (StRS §18.1), the operational policies POL-01..POL-09 (StRS §10), and the three-tier identity/policy depth (StRS §2c, Annex A OI-03).

### 3.3 User characteristics *(§9.4.3.3)*

Per StRS §4: STK-02 agent developers and STK-09 adopting teams (build/instantiate); STK-04 pilot users, a limited nominated population (ask/receive/request); STK-05 approvers (decide on writes); STK-08 knowledge owners (curate corpus, validate ground truth); STK-10 operators (observe, roll back, disable writes); STK-01/03/06/07 govern and own. Device/location: standard enterprise workstation and browser; no special device classes.

---

## 4. Functional Requirements *(ISO 29148 §9.4.4)*

### 4.1 Platform — golden path (SysR-P-F)

- **SysR-P-F-01 — Template instantiation.** The platform shall provide (i) an agent project template that is instantiable (a) through the Internal Developer Portal and (b) directly via a command-line interface against the template repository, and that produces in one operation: agent source scaffold, container build configuration, deployment manifests, GitOps configuration, evaluation project, telemetry configuration, policy scaffolding, and developer documentation; and (ii) a separate, independently instantiable tools template, instantiable through the same two paths, that produces an MCP tool server's own container build configuration, deployment manifests, and GitOps configuration. An agent project consumes a tool server's published contract (endpoint and schema) as configuration; it shall not bundle tool-server source. An agent project likewise consumes the platform approval service through its published contract (SRS-APR-IF-01..05); it shall not bundle an approval-service implementation.
  *Trace:* StR-DX-01. *Verification:* D (OS-01; both instantiation paths exercised for each template).

- **SysR-P-F-02 — Local development environment.** The template shall include a local launch configuration that starts, on a developer workstation using a local container runtime, the agent, a seeded synthetic knowledge corpus, a local retrieval service, and a mock MCP tool server, with configuration pointing at a shared development model endpoint that exposes the same OpenAI-compatible contract as deployed environments.
  *Trace:* StR-DX-02, StR-DX-04. *Verification:* D (OS-01).

- **SysR-P-F-03 — Local evaluation CLI.** The platform shall provide a command-line interface that executes any single named evaluation case or the complete evaluation suite on the developer workstation, producing machine-readable results in the same schema as CI evaluation results.
  *Trace:* StR-DX-03. *Verification:* T.

- **SysR-P-F-04 — Contract parity across environments.** The platform shall use identical tool schemas, prompt-template formats, policy-bundle formats, and configuration schemas in local development and in every deployed environment, with environment differences expressed only through injected configuration, secrets, policy bundles, model endpoint selection, and data-source bindings.
  *Trace:* StR-DX-04, StR-ORG-01. *Verification:* I (schema/format diff across environment definitions).

- **SysR-P-F-05 — CI validation pipeline.** The continuous-integration pipeline shall execute, on every change set: (1) software tests (unit, integration, schema, dependency, container); (2) agent tests (retrieval, tool selection, response quality, multi-step completion); (3) security tests (prompt injection, unauthorized tool calls, secret exposure, disallowed network access); (4) operational tests (timeout, model failure, tool failure, retry, fallback); and shall build the container image, generate an SBOM, and publish evaluation results as promotion evidence.
  *Trace:* StR-EVL-01, StR-EVL-02, StR-ORG-01. *Verification:* D (OS-02), T (category presence asserted in pipeline definition tests).

- **SysR-P-F-06 — Single immutable artifact promotion.** The system shall build exactly one OCI image per approved change set, identified by digest, and shall promote that identical digest through ephemeral test, staging, and pilot production exclusively via declarative GitOps state; rebuilding for a target environment or building from an alternate branch or source tree shall not occur.
  *Trace:* StR-ORG-01. *Verification:* T (digest equality across environment records), I (pipeline definition).

- **SysR-P-F-07 — Evaluation promotion gate.** The system shall block promotion of the agent between environments unless the evaluation suite results meet the version-controlled thresholds defined for the target environment.
  *Trace:* StR-EVL-02. *Verification:* T (negative case: sub-threshold run is not promoted).

- **SysR-P-F-08 — Human approval workflow.** The platform shall provide an approval workflow that: receives every agent-proposed action that would create or modify state in an external system; presents to the approver, at decision time, the proposed action, its arguments, the evidence the agent used, and the initiating user's identity; records each decision with approver identity, timestamp, and outcome; and expires undecided approvals after a configured time limit without executing the action.
  *Trace:* StR-APR-01, StR-APR-02, StR-APR-03, StR-APR-04. *Verification:* T (approve, reject, expiry paths; OS-04/OS-05).

- **SysR-P-F-09 — Write execution behind the tool contract.** The system shall execute approved write actions exclusively through the tool-contract invocation path, such that the engine that performs the write is a replaceable realization: substituting the executor shall require no change to agent code, approval workflow contract, or evaluation sets.
  *Trace:* StR-APR-01, StR-ORG-03. *Verification:* I (interface analysis), D.

- **SysR-P-F-10 — Corpus management.** The platform shall provide an ingestion process that attaches to every corpus document: owner, classification, version or effective date, access policy, and source metadata; and shall support a documented refresh process such that an updated document version is cited by subsequent answers.
  *Trace:* StR-SEC-03. *Verification:* D (OS-06), I (metadata schema).

- **SysR-P-F-11 — Externalized, validated policy.** Agent operating policy (permitted tools, action limits, approval rules) shall be expressed as versioned policy bundles loadable without rebuilding the agent image; the CI pipeline shall validate policy bundles; and the policy scaffolding shall include at least one enforced deny path.
  *Trace:* StR-SEC-04. *Verification:* T (policy update without rebuild; CI validation; deny path per SysR-P-SEC-05).

- **SysR-P-F-12 — Model routing with reason codes.** The model-client abstraction shall implement rules-based routing over exactly one approved model route plus one defined fallback route, shall support a forced-route rule, and shall log a reason code for every routing decision, associated with the model endpoint and model identifier/version used for the call.
  *Trace:* StR-SEC-01, StR-ORG-04. *Verification:* T (OS-07: fallback exercised; reason codes asserted in telemetry).

- **SysR-P-F-13 — Blueprint documentation.** The platform shall include documentation sufficient for an adopter, per `docs/adopting-this-blueprint.md`, to instantiate, run locally, evaluate, and deploy a new agent from the blueprint without assistance from the original implementation team.
  *Trace:* StR-DX-06. *Verification:* D (OS-09: unassisted second-team instantiation).

### 4.2 Pilot agent (SysR-A-F)

- **SysR-A-F-01 — Grounded, cited answers.** The agent shall answer platform, procedure, and known-issue questions using only retrieval from the approved corpus, and every answer derived from the corpus shall include citations identifying the source document identifiers and versions.
  *Trace:* StR-USR-01. *Verification:* T (evaluation cases: correctness, retrieval relevance, citation quality).

- **SysR-A-F-02 — Authorized read-only retrieval.** The agent shall retrieve enterprise records exclusively in read-only mode and exclusively limited to records the initiating user is authorized to view, as determined through the retrieval and tool authorization interfaces.
  *Trace:* StR-USR-02. *Verification:* T (positive and negative authorization cases).

- **SysR-A-F-03 — Actionable output.** For actionable inquiries, the agent shall produce a recommended action, a troubleshooting plan, or a draft request as its output.
  *Trace:* StR-USR-03. *Verification:* T (evaluation cases per output type).

- **SysR-A-F-04 — Draft, approve, execute.** For any action that would create or modify state in an external system, the agent shall submit a draft to the approval workflow and shall execute the action only upon recorded approval; upon rejection or expiry the agent shall not execute, shall inform the user, and the decision shall be recorded.
  *Trace:* StR-APR-01, StR-APR-04. *Verification:* T (OS-04, OS-05; OBJ-05 zero-unapproved-writes assertion).

- **SysR-A-F-05 — Safe stop and escalation.** When the agent cannot answer safely, cannot proceed, or exceeds an operating limit, it shall stop deterministically, inform the user explicitly of the condition, and provide an escalation path to a human, taking no unapproved action (mode M-06).
  *Trace:* StR-USR-04. *Verification:* T (refusal/escalation evaluation cases; OS-07).

- **SysR-A-F-06 — Injection resistance.** Instructions embedded in retrieved documents or user input shall not cause the agent to invoke tools or perform actions outside its policy; each detected attempt shall be logged.
  *Trace:* StR-EVL-01 (injection dimension), StR-SEC-04. *Verification:* T (OS-10 evaluation cases).

- **SysR-A-F-07 — Bounded operation.** The agent shall enforce configured limits on: per-call and per-task timeouts, retry counts, and the maximum number of reasoning/tool-execution steps; on exhaustion it shall transition to M-06 behavior (SysR-A-F-05).
  *Trace:* StR-USR-04, StR-ORG-04. *Verification:* T (limit-exhaustion operational tests).

### 4.3 Pilot agent — architecture constraints (SysR-A-ARC)

- **SysR-A-ARC-01 — Client-only runtime dependencies.** The agent source code shall import, for model and tool interaction, only an OpenAI-compatible API client and an MCP client; it shall not import native SDKs, server-side libraries, or provider-specific frameworks of any agentic runtime or orchestrator product. Substituting the agentic runtime shall therefore be an edit to the realization table (SysR-P-LC-02), not a requirements or code change.
  *Trace:* StR-DX-05. *Verification:* I (static dependency inspection, enforceable as a CI check).

- **SysR-A-ARC-02 — Loop-in-pod hosting.** The agentic control loop shall execute within the agent's own immutable OCI image (in-pod), invoking the model via the OpenAI-compatible interface (SysR-P-IF-01) and tools via MCP (SysR-P-IF-02); no shared agentic runtime shall be on the execution path in phase one.
  *Trace:* StR-ORG-01, StR-DX-04. *Verification:* I (image and deployment inspection), D.

- **SysR-A-ARC-03 — Adapter-mediated loop access.** The agent's business logic shall invoke the loop exclusively through the orchestrator adapter defined by SysR-P-IF-09, and shall contain no code paths that bypass the adapter to reach the model or tool clients directly.
  *Trace:* StR-ORG-03. *Verification:* I (code-structure inspection).

- **SysR-A-ARC-04 — Configuration-only mobility.** Moving the agent between environments or changing the model provider shall require no modification to agent source code; the identical image digest with different injected configuration shall exhibit the environment-appropriate behavior.
  *Trace:* StR-DX-05. *Verification:* T (same digest deployed against two configurations).

### 4.4 Pilot agent — evaluation and telemetry (SysR-A-EVL, SysR-A-TEL)

- **SysR-A-EVL-01 — Threshold attainment.** The agent shall meet the defined thresholds of the version-controlled evaluation set across all nine dimensions: answer correctness, retrieval relevance, citation quality, tool selection, tool-argument correctness, refusal and escalation behavior, resistance to prompt injection, policy compliance, and latency and token consumption.
  *Trace:* StR-EVL-01. *Verification:* T (evaluation suite execution; gate per SysR-P-F-07).

- **SysR-A-TEL-01 — Per-run telemetry emission.** The agent shall emit, for every run, via the telemetry interface (SysR-P-IF-06): request and session identifiers; initiating user and workload identity; prompt-template version; retrieved document identifiers; model and endpoint selected with the routing reason code; tool calls and their arguments; policy and approval decisions; latency, token consumption, and errors; and the final result reference.
  *Trace:* StR-SEC-01, StR-OPS-01. *Verification:* T (telemetry-completeness assertions).

---

## 5. Usability Requirements *(ISO 29148 §9.4.5)*

- **SysR-P-USE-01 — Approver decision context.** The approval interface shall present the proposed action, its arguments, the supporting evidence, and the initiating user's identity together in a single view, such that an approver can decide without consulting systems outside the approval interface and the audit record.
  *Trace:* StR-APR-02. *Verification:* D (approver walkthrough in staging).

*(Effectiveness/efficiency criteria for developer usability are stated as measurable performance requirements: SysR-P-PERF-01. Adopter adoptability is verified under SysR-P-F-13 / OS-09.)*

## 6. Performance Requirements *(ISO 29148 §9.4.6)*

- **SysR-P-PERF-01 — One-hour local start.** The elapsed time from template instantiation to a locally running agent that answers a sample question with citations and can execute the local evaluation suite shall not exceed one hour on a standard developer workstation.
  *Trace:* StR-DX-02 (OBJ-01). *Verification:* D (timed OS-01 run).

- **SysR-P-PERF-02 — Latency and token accounting against budgets.** The system shall record, for every interaction, end-to-end latency and token consumption, and the evaluation suite shall assess both against the configured per-interaction budgets defined during discovery.
  *Trace:* StR-EVL-01 (latency/token dimension), StR-SEC-01. *Verification:* T.

- **SysR-P-PERF-03 — Rollback objective.** Following a rollback command, the previously approved image digest shall be serving within the rollback time objective defined in the pilot runbook. *(The objective's value is an operational parameter set at discovery; this document states no duration estimate.)*
  *Trace:* StR-OPS-02 (OS-08). *Verification:* D (timed rollback exercise).

---

## 7. System Interfaces *(ISO 29148 §9.4.7)*

- **SysR-P-IF-01 — Model interface.** The agent shall access all language-model capability exclusively through an OpenAI-compatible API (chat-completions surface; a responses-style surface is admitted at the orchestrator adapter seam per SysR-P-IF-09), with endpoint, model identifiers, and routing rules supplied by injected configuration.
  *Trace:* StR-DX-04, StR-DX-05. *Verification:* I (dependency and configuration inspection), T.

- **SysR-P-IF-02 — Tool interface (MCP).** The agent-facing contract for the enterprise tool shall be MCP. Where the target enterprise system does not natively support MCP, a system-side adapter shall bridge its REST/OpenAPI interface and expose it to the agent as MCP; the agent shall remain unaware of the bridge.
  *Trace:* StR-DX-04, StR-SEC-02. *Verification:* I, D (mock and real tool behind identical MCP contract).

- **SysR-P-IF-03 — Tool contract metadata.** Every tool contract shall carry machine-readable metadata comprising at minimum: tool name, semantic version, and certification status, sufficient for registration in a tool catalog/registry without contract change.
  *Trace:* StR-ORG-03. *Verification:* I (schema inspection).

- **SysR-P-IF-04 — Retrieval interface.** The retrieval contract shall return passages with source-document identifiers and metadata (owner, classification, version/effective date) and shall filter results by the initiating user's authorization before returning them to the agent.
  *Trace:* StR-USR-01, StR-SEC-02, StR-SEC-03. *Verification:* T (authorization-filtered retrieval cases).

- **SysR-P-IF-05 — Identity interface.** User authentication shall use the enterprise OIDC identity provider. Each agent deployment shall operate under a **distinct, attributable, least-privilege workload identity**, stated as a capability: the provisioning mechanism is a realization choice and shall not be constrained by this requirement.
  *Trace:* StR-SEC-01, StR-SEC-02. *Verification:* D (identity attribution shown in audit record), I.

- **SysR-P-IF-06 — Telemetry interface.** All telemetry shall be emitted via OpenTelemetry (OTLP): every model call, retrieval event, tool call, policy decision, and approval decision shall appear as spans/events with defined attributes, correlated by request and session identifiers end to end.
  *Trace:* StR-SEC-01, StR-OPS-01. *Verification:* T (trace-completeness assertions; OBJ-04).

- **SysR-P-IF-07 — Artifact interface.** Agent artifacts shall be OCI images identified by digest, with the SBOM associated to the digest; environment promotion shall be expressed exclusively as declarative GitOps state referencing the digest.
  *Trace:* StR-ORG-01. *Verification:* I.

- **SysR-P-IF-08 — Configuration interface.** A single environment-injected configuration schema shall carry: model endpoint(s) and identifiers, routing rules, retrieval bindings, tool endpoint bindings, policy-bundle references, and secret references; the agent shall read environment specifics only through this schema.
  *Trace:* StR-DX-04, StR-DX-05. *Verification:* I (schema inspection), T (same image, different config, different environment behavior).

- **SysR-P-IF-09 — Orchestrator adapter seam.** The agent's business logic shall interact with the agentic loop only through an internal orchestrator-adapter interface designed such that the phase-one loop-in-pod realization can be replaced by an Agent-as-a-Service realization (loop hosted in a shared runtime behind an OpenAI-compatible responses-style API) with no change to business logic, tool contracts, prompts' semantic content, or evaluation sets. **Only the seam is required in phase one; the second realization shall not be built.**
  *Trace:* StR-ORG-03. *Verification:* A (interface analysis demonstrating substitutability), I.

---

## 8. System Operations *(ISO 29148 §9.4.8)*

### 8.1 Human-system integration *(§9.4.8.1)*

Concentrated human-engineering attention applies to the **approval decision point**, where human error is most consequential: SysR-P-USE-01 (decision context) and SysR-P-F-08 (expiry default-deny) are the controlling requirements. No function allocated to personnel may be reallocated to the agent for write actions (StR-APR-01; POL-02).

### 8.2 Maintainability *(§9.4.8.2)*

- **SysR-P-OPS-01 — Standard observability.** Operators shall be able to observe agent SLOs, distributed traces, metrics, and application/audit logs through the organization's standard observability services, without agent-specific tooling.
  *Trace:* StR-OPS-01. *Verification:* D.

- **SysR-P-OPS-02 — Rollback.** Operators shall be able to revert the pilot deployment to the previously approved image digest through the declarative GitOps mechanism alone.
  *Trace:* StR-OPS-02. *Verification:* D (OS-08).

- **SysR-P-OPS-03 — Independent write kill switch.** Operators shall be able to disable the agent's write pathway independently of its read/answer pathway through a configuration or policy change, without redeploying the image.
  *Trace:* StR-OPS-03. *Verification:* T.

### 8.3 Reliability *(§9.4.8.3)*

Reliability is specified behaviorally rather than as a failure-rate figure (pilot scale does not support statistical apportionment): under model-endpoint failure the system routes to the fallback with a logged reason code (SysR-P-F-12); under tool failure or limit exhaustion the agent enters M-06 deterministically (SysR-A-F-05, SysR-A-F-07); recovery is by rollback (SysR-P-OPS-02). Pilot SLOs are defined in the pilot runbook (StR-OPS-01) and observed via SysR-P-OPS-01.

---

## 9. System Modes and States *(ISO 29148 §9.4.9)*

- **SysR-P-MODE-01 — Operational modes.** The system shall support the six operational modes M-01 through M-06 as defined in StRS §12, with the identical agent artifact (by digest) and identical contracts in M-03, M-04, and M-05, and with mode-specific behavior expressed only through injected configuration, secrets, policy bundles, endpoint selection, and data bindings.
  *Trace:* StR-DX-04, StR-ORG-01. *Verification:* I (environment definitions), D.

**States (informative).** Within a run, the agent transitions: `idle → running → (awaiting-approval | answered | degraded-stopped)`. A proposed write transitions: `drafted → pending-approval → (approved → executed | rejected → closed | expired → closed)`. Expiry and rejection never reach `executed` (SysR-A-F-04). M-06 is entered from `running` on model/tool failure or limit exhaustion (SysR-A-F-05, SysR-A-F-07).

---

## 10. Physical Characteristics *(ISO 29148 §9.4.10)*

### 10.1 Physical requirements *(§9.4.10.1 — tailored)*

Not applicable as hardware constraints (software-only system). The physical form of the system is its artifact set: see §16 (packaging) and SysR-P-PKG-01/02.

### 10.2 Adaptability requirements *(§9.4.10.2)*

- **SysR-P-ADP-01 — Phase-two attachment without rework.** The phase-one contracts (model client abstraction, MCP tool contracts with metadata, retrieval contract, policy-bundle format, configuration schema, OTLP telemetry) shall be designed such that the phase-two capabilities named in StRS §2c (data mesh, model routing grid, secure agent sandbox, memory tiers) can attach as realizations behind these contracts without changes to agent code or to the requirements of this SyRS. None of these capabilities shall be built in phase one.
  *Trace:* StR-ORG-03. *Verification:* A (attachment analysis per capability against each contract).

*(SysR-P-IF-09 — the orchestrator adapter seam — is the specific adaptability provision for the agentic-runtime hosting pattern.)*

## 11. Environmental Conditions *(ISO 29148 §9.4.11 — tailored)*

The system operates exclusively within: the organization's existing container platform (no new inference infrastructure procured, StRS §11); developer workstations with a local container runtime (M-01); and the enterprise network, identity, secret-management, and observability environment (StRS §5, §16e). Threat environment: adversarial content in retrieved documents and user input is assumed present (SysR-A-F-06). No natural/induced physical environmental requirements apply.

## 12. System Security *(ISO 29148 §9.4.12)*

- **SysR-P-SEC-01 — End-to-end attribution record.** For every agent interaction the system shall record and make determinable: the initiating user; the agent workload identity; the data retrieved and its authorization basis; the tool operations invoked; the model endpoint and model identifier/version used for each model call together with the routing reason code; whether approval was required and its outcome; and the credential or workload identity used for each access.
  *Trace:* StR-SEC-01. *Verification:* T (audit-record completeness assertions per interaction).

- **SysR-P-SEC-02 — No shared credentials.** The agent shall access the enterprise tool and the knowledge corpus only under authorization derived from the initiating user's identity and the agent's workload identity; broadly shared credentials shall not be used on any access path.
  *Trace:* StR-SEC-02. *Verification:* I (credential inventory), T (access under distinct identities asserted in audit records).

- **SysR-P-SEC-03 — Least-privilege tool credentials.** Tool-side credentials available to the agent shall be scoped read-only by default; write-capable scope shall be reachable only through the approval-gated execution path (SysR-P-F-09).
  *Trace:* StR-SEC-02. *Verification:* I (scope inspection), T (write attempt outside approval path is denied).

- **SysR-P-SEC-04 — Externalized secrets.** No secret shall be stored in the agent image, source repository, or template; all secrets shall be injected at deployment/runtime from the organization's secret-management service.
  *Trace:* StR-SEC-02, StR-ORG-01. *Verification:* I (image and repository scan), T (CI secret-exposure tests per SysR-P-F-05).

- **SysR-P-SEC-05 — Enforced deny path.** At least one policy deny path (an unauthorized tool call or a disallowed write) shall be enforced at runtime in staging and pilot production, and the denial shall be observable in telemetry.
  *Trace:* StR-SEC-04. *Verification:* T.

- **SysR-P-SEC-06 — Audit evidence on demand.** Approval decisions and interaction audit records shall be retrievable on demand as audit evidence for the duration of the pilot.
  *Trace:* StR-APR-03. *Verification:* D (audit retrieval exercise).

## 13. Information Management *(ISO 29148 §9.4.13)*

- **SysR-P-INFO-01 — Version control of behavioral content.** Prompts and prompt templates, tool schemas, policy bundles, configuration schemas, and evaluation sets (cases, thresholds, ground truth) shall be maintained under version control, and every deployed combination shall be reconstructible from recorded versions.
  *Trace:* StR-EVL-01, StR-SEC-04. *Verification:* I.

- **SysR-P-INFO-02 — Ground-truth validation record.** The expected outcomes of the evaluation set shall be authored or explicitly validated by the data/knowledge owner or a designated domain subject-matter expert, and that validation shall be recorded in the evaluation set's version history.
  *Trace:* StR-EVL-04. *Verification:* I (version-history inspection).

- **SysR-P-INFO-03 — Retention and retrievability.** Telemetry and audit evidence shall be retained per the configured retention policy and shall remain retrievable throughout the pilot and its exit analysis.
  *Trace:* StR-APR-03, StR-SEC-01. *Verification:* I (retention configuration), D.

- **SysR-P-INFO-04 — Synthetic data only in the blueprint.** All blueprint deliverables, seeded corpora, mock tool responses, and evaluation examples distributed with the blueprint shall use synthetic or public sample data only, with no organization-identifiable content.
  *Trace:* StR-ORG-02. *Verification:* I (content review).

- **SysR-P-INFO-05 — Evaluation run records.** Every evaluation run shall be recorded in an experiment/evaluation tracking system with: evaluation-set version, image digest, configuration reference, thresholds applied, and results, such that any promotion decision is reproducible from its records.
  *Trace:* StR-EVL-02. *Verification:* D (tracking-record inspection for a gated promotion).

## 14. Policies and Regulations *(ISO 29148 §9.4.14)*

- **SysR-P-POL-01 — Read-only default posture.** The default policy bundle shipped with the template shall grant no write-capable tool operations; write capability shall exist only as an approval-gated policy entry (SysR-P-F-08, SysR-P-F-09).
  *Trace:* StR-USR-02, StR-APR-01. *Verification:* I (default bundle inspection), T.

- **SysR-P-POL-02 — Complexity-envelope scope guard.** Any change that would increase a bound of the complexity envelope (StRS §18.1) shall require an explicitly recorded scope decision before implementation; the system's requirement set and realization table shall not silently absorb such an increase.
  *Trace:* StR-ORG-04. *Verification:* I (change-record inspection).

*(The operational policies POL-01..POL-09 of StRS §10 are realized across this SyRS: POL-01→SysR-P-F-06/PKG-01; POL-02→SysR-P-F-08/SysR-A-F-04; POL-03→SysR-P-POL-01/SEC-03; POL-04→SysR-P-IF-05/SEC-02; POL-05→SysR-P-F-07/INFO-05; POL-06→§7 in full; POL-07→SysR-A-F-07; POL-08→SysR-P-INFO-04; POL-09→SysR-P-ADP-01/IF-09. This mapping is informative; traces bind to StRs.)*

## 15. System Life Cycle Sustainment *(ISO 29148 §9.4.15)*

- **SysR-P-LC-01 — Pinned reused assets.** Validated patterns, quickstarts, and reference repositories reused by the blueprint shall be pinned by version and commit in the blueprint, such that instantiation is reproducible.
  *Trace:* StR-DX-06 (and StRS §18.3). *Verification:* I.

- **SysR-P-LC-02 — Realization independence.** No normative requirement of this SyRS shall name a product. Substituting any realization — including the agentic runtime hosting the loop — shall require only an update to the informative realization table, with no change to requirements or to agent source code, provided the protocol surfaces of §7 are preserved.
  *Trace:* StR-DX-05, StR-ORG-03. *Verification:* I (document inspection), A (substitution analysis).

- **SysR-P-LC-03 — Support-level assignment rule.** Realization selection shall follow, in order: (1) GA productized components with an Operator; (2) Technology Preview components only behind a contract of §7 with a documented swap path; (3) Developer Preview components only in local/demo use (M-01, and M-02 demonstrations), never in M-04 staging or M-05 pilot production; (4) upstream community components only with an explicitly recorded justification in the realization table.
  *Trace:* StR-ORG-03, StR-DX-05. *Verification:* I (realization-table audit).

- **SysR-P-LC-04 — Evaluation set precedes implementation.** The evaluation set for the pilot workflow shall exist under version control before the complete agent implementation is built, as evidenced by repository history.
  *Trace:* StR-EVL-03. *Verification:* I (repository-history inspection).

## 16. Packaging, Handling, Shipping and Transportation *(ISO 29148 §9.4.16 — tailored to artifacts)*

- **SysR-P-PKG-01 — Artifact contents.** The agent shall be packaged as a single OCI image containing: agent code and the agentic loop, prompts and prompt templates, tool schemas, and baseline policy defaults; the image shall exclude environment configuration, secrets, environment policy bundles, and data-source bindings.
  *Trace:* StR-ORG-01. *Verification:* I (image content inspection).

- **SysR-P-PKG-02 — SBOM per digest.** An SBOM shall be generated at build time and associated with the image digest in the artifact registry.
  *Trace:* StR-ORG-01. *Verification:* T (SBOM presence and digest association asserted in CI).

## 17. Verification *(ISO 29148 §9.4.17)*

Verification methods are assigned per requirement in §§4–16 and consolidated in **Annex T** (traceability matrix StR → SysR → method). Method conventions:

- **Inspection (I):** examination of artifacts (code dependencies, schemas, image contents, repositories, records) without execution.
- **Analysis (A):** reasoned assessment (interface substitutability, phase-two attachment) documented as an analysis note.
- **Demonstration (D):** operation of the system in a defined scenario (operational scenarios OS-01..OS-10 of StRS §17 are the demonstration scripts).
- **Test (T):** execution against pass/fail criteria with recorded results; agent behavioral tests execute as evaluation cases (SysR-P-F-03/05/07), so evaluation is itself the test harness (POL-05).

Verification of SysR-A-\* behavioral requirements shall use the version-controlled evaluation set (SysR-P-LC-04, SysR-P-INFO-01/02), making requirement verification and promotion gating the same evidence stream.

## 18. Assumptions and Dependencies *(ISO 29148 §9.4.18)*

1. The assumptions of Annex A (StRS-AGP-001-AXA v1.0) apply unchanged: OI-02 (ITSM data-source + tool pair, adopted), OI-03 (three-tier identity/policy depth, adopted), OI-04 (portal integration effort bounded, adopted). No SysR depends on a refuted assumption.
2. **Proposed new entry — OI-05 (next sequential ID):** *the selected agentic-runtime realization remains supported for the duration of the pilot.* Trigger: announcement of a successor, rename, or deprecation of the selected runtime realization. Action on trigger: revision of the realization table only; the requirements of this SyRS remain intact (guaranteed by SysR-P-LC-02 and SysR-P-IF-09). The full proposed entry text is delivered in the findings report; adoption is the author's decision.
3. Organizational dependency classes are those declared in StRS §18.1 (identity-provider access, tool-side credentials, staging data approval, pilot user group nomination, approver designation); none is restated here as a blocking third-party dependency.

---

## Annex T — Traceability Matrix (StR → SysR → Verification) *(normative annex)*

Method key: I = Inspection, A = Analysis, D = Demonstration, T = Test. The first listed method per SysR is primary.

| StR (baseline v1.0) | Derived SysR(s) | Verification method(s) |
|---|---|---|
| StR-DX-01 | SysR-P-F-01 | D |
| StR-DX-02 | SysR-P-F-02; SysR-P-PERF-01 | D; D |
| StR-DX-03 | SysR-P-F-03 | T |
| StR-DX-04 | SysR-P-F-04; SysR-P-F-02; SysR-P-IF-01; SysR-P-IF-02; SysR-P-IF-08; SysR-P-MODE-01; SysR-A-ARC-02 | I; D; I,T; I,D; I,T; I,D; I,D |
| StR-DX-05 | SysR-P-IF-01; SysR-P-IF-08; SysR-P-LC-02; SysR-P-LC-03; SysR-A-ARC-01; SysR-A-ARC-04 | I,T; I,T; I,A; I; I; T |
| StR-DX-06 | SysR-P-F-13; SysR-P-LC-01 | D; I |
| StR-USR-01 | SysR-A-F-01; SysR-P-IF-04 | T; T |
| StR-USR-02 | SysR-A-F-02; SysR-P-POL-01 | T; I,T |
| StR-USR-03 | SysR-A-F-03 | T |
| StR-USR-04 | SysR-A-F-05; SysR-A-F-07 | T; T |
| StR-APR-01 | SysR-P-F-08; SysR-P-F-09; SysR-A-F-04; SysR-P-POL-01 | T; I,D; T; I,T |
| StR-APR-02 | SysR-P-F-08; SysR-P-USE-01 | T; D |
| StR-APR-03 | SysR-P-F-08; SysR-P-SEC-06; SysR-P-INFO-03 | T; D; I,D |
| StR-APR-04 | SysR-P-F-08; SysR-A-F-04 | T; T |
| StR-SEC-01 | SysR-P-SEC-01; SysR-P-F-12; SysR-P-IF-05; SysR-P-IF-06; SysR-A-TEL-01; SysR-P-PERF-02; SysR-P-INFO-03 | T; T; D,I; T; T; T; I,D |
| StR-SEC-02 | SysR-P-SEC-02; SysR-P-SEC-03; SysR-P-SEC-04; SysR-P-IF-04; SysR-P-IF-05; SysR-P-IF-02 | I,T; I,T; I,T; T; D,I; I,D |
| StR-SEC-03 | SysR-P-F-10; SysR-P-IF-04 | D,I; T |
| StR-SEC-04 | SysR-P-F-11; SysR-P-SEC-05; SysR-A-F-06; SysR-P-INFO-01 | T; T; T; I |
| StR-EVL-01 | SysR-P-F-05; SysR-A-EVL-01; SysR-A-F-06; SysR-P-PERF-02; SysR-P-INFO-01 | D,T; T; T; T; I |
| StR-EVL-02 | SysR-P-F-07; SysR-P-F-05; SysR-P-INFO-05 | T; D,T; D |
| StR-EVL-03 | SysR-P-LC-04 | I |
| StR-EVL-04 | SysR-P-INFO-02 | I |
| StR-OPS-01 | SysR-P-OPS-01; SysR-P-IF-06; SysR-A-TEL-01 | D; T; T |
| StR-OPS-02 | SysR-P-OPS-02; SysR-P-PERF-03 | D; D |
| StR-OPS-03 | SysR-P-OPS-03 | T |
| StR-ORG-01 | SysR-P-F-06; SysR-P-F-04; SysR-P-IF-07; SysR-P-PKG-01; SysR-P-PKG-02; SysR-P-MODE-01; SysR-P-SEC-04; SysR-A-ARC-02 | T,I; I; I; I; T; I,D; I,T; I,D |
| StR-ORG-02 | SysR-P-INFO-04 | I |
| StR-ORG-03 | SysR-P-IF-03; SysR-P-IF-09; SysR-P-ADP-01; SysR-P-LC-02; SysR-P-LC-03; SysR-P-F-09; SysR-A-ARC-03 | I; A,I; A; I,A; I; I,D; I |
| StR-ORG-04 | SysR-P-POL-02; SysR-P-F-12; SysR-A-F-07 | I; T; T |

**Orphan detection.**

- *StRs without a derived SysR:* **none** (29/29 stakeholder requirements traced).
- *SysRs without a parent StR:* **none** (63/63 system requirements trace to at least one StR).

**SysR index (63 total).** Platform (50): SysR-P-F-01..13; SysR-P-IF-01..09; SysR-P-SEC-01..06; SysR-P-PERF-01..03; SysR-P-USE-01; SysR-P-MODE-01; SysR-P-ADP-01; SysR-P-INFO-01..05; SysR-P-POL-01..02; SysR-P-LC-01..04; SysR-P-OPS-01..03; SysR-P-PKG-01..02. Agent (13): SysR-A-F-01..07; SysR-A-ARC-01..04; SysR-A-EVL-01; SysR-A-TEL-01.

---

*End of System Requirements Specification SyRS-AGP-001 v0.2 (Draft, amended). Canonical language: English. Companion documents: SyRS-AGP-001 ES (literal translation), SyRS-AGP-001-RRT (informative Red Hat realization table). Derivation basis: StRS-AGP-001 v1.0 (Baseline), unmodified.*
