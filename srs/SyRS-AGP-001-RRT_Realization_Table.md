# Red Hat Realization Table (Informative)

**Document ID:** SyRS-AGP-001-RRT · **Version:** 0.2 (Draft) · **Date:** 2026-08-28
**Applies to:** SyRS-AGP-001 v0.3 (Draft), derived from StRS-AGP-001 v1.1 (amended baseline)

**Revision note (0.2):** Row 24 (Gitea realization) corrected — deployed via upstream kustomize, not the OLM path this row originally described (`DECISIONS.md` DEC-100). Row 13 (RHDH) independently re-verified against `PINS.md` — already accurate, no change. Reference-implementation reframe, `DECISIONS.md` DEC-130.
**Status:** **Informative, non-normative.** No entry in this table is a requirement. Every entry realizes a protocol surface or capability defined in SyRS-AGP-001 §7 and §§4–16. Substituting any realization is an edit to this table only (SysR-P-LC-02); support-level placement follows SysR-P-LC-03.

**Verification note.** Product versions and support levels below were verified by web search against Red Hat documentation on **2026-08-12**. The agentic runtime has changed name and support level across releases; the current state is recorded explicitly in §2. Language: English only (product names and support-level terms are vendor-canonical); the table is shared by both language versions of the SyRS.

---

## 1. Version pin: Red Hat OpenShift AI

**Pinned: Red Hat OpenShift AI Self-Managed 3.4 (GA), latest z-stream 3.4.2 (security updates through July 2026).**

Rationale (per SysR-P-LC-03 assignment rule):

- 3.4 is the newest **GA** release. New features of 3.4 GA are documented in the 3.4 release notes; z-streams 3.4.1 (June 2026) and 3.4.2 (July 2026) exist. Source: https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html-single/release_notes/index
- 3.5 is currently at **EA2 (Early Access)**. Per the RHOAI Self-Managed life cycle, EA releases carry **no support, no security updates, no CVE fixes**, and are explicitly not recommended where production support is required. GA releases carry seven months of full support. Source: https://access.redhat.com/support/policy/updates/rhoai-sm/lifecycle and https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/index ("Red Hat OpenShift AI 3.5 EA2 Release notes")
- The 2.x stream (2.25, EUS) remains supported but the 3.x stream is the current architecture (Gateway-API OIDC auth, LLMInferenceService/llm-d serving, MaaS); pinning 2.25 would build the golden path on a superseded serving architecture. Upgrade path 2.25→3.3+ exists. Source: https://developers.redhat.com/articles/2026/08/07/upgrade-openshift-ai-faster-using-ai-coding-assistant

**Base platform prerequisite:** OpenShift AI 3.x requires OpenShift Container Platform 4.19 or later (3.0 release notes; fast-3.x channel). Pin proposed below: OCP 4.21 (GA 2026-02-03), to be confirmed against the RHOAI 3.4 Supported Configurations article (https://access.redhat.com/articles/rhoai-supported-configs-3.x) for the target cluster.

## 2. Agentic-runtime state in OpenShift AI 3.4 (verified 2026-08-12)

This is the component the SyRS deliberately keeps **off the critical path** via loop-in-pod (SysR-A-ARC-02) and the orchestrator adapter seam (SysR-P-IF-09):

| Component (RHOAI 3.4) | Support level | Notes |
|---|---|---|
| Llama Stack Distribution + Llama Stack Operator | **Technology Preview** | 3.4 stream ships Open Data Hub Llama Stack 0.6.0.1+rhai0 (upstream Llama Stack 0.6.0, documented at 3.4 EA2); 3.3.0 shipped 0.4.2.1+rhai0 (upstream 0.4.2). PostgreSQL Operator required for server deployments since 3.2; SQLite deprecated for production metadata since 3.2. |
| Responses API on Llama Stack | **Technology Preview** (promoted from Developer Preview in 3.4) | OpenAI-parity alignment work landed in 3.4. This is the surface a future Agent-as-a-Service realization would sit behind (SysR-P-IF-09). |
| Conversations API; Llama Stack Connectors | Technology Preview | |
| Human-in-the-Loop tool-call approval in the Llama Stack agent | **Developer Preview** | Cannot realize StR-APR-\*/SysR-P-F-08 in M-04/M-05 (SysR-P-LC-03 forbids DP there). The approval workflow is therefore a blueprint component. |
| MCP Catalog, mcp-lifecycle-operator, mcp-gateway | **Developer Preview** | M-01 local/demo exploration only. In M-04/M-05 the MCP tool server is a blueprint container speaking plain MCP. |
| AgentCard / AgentRuntime (Kagenti: SPIFFE workload identity, AuthBridge, per-agent OTel) | **Developer Preview** | Matches Annex A OI-03 "explicitly deferred" tier (cryptographic workload attestation). Phase-two candidate realization of SysR-P-IF-05's capability. |

Source for all rows: RHOAI 3.4 release notes (GA / Technology Preview / Developer Preview chapters), https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html-single/release_notes/index

## 3. Realization table

Support levels: **GA** = generally available, production SLA · **TP** = Technology Preview (no production SLA) · **DP** = Developer Preview (no support; local/demo only per SysR-P-LC-03) · **community** = upstream, justification recorded.

| # | SyRS surface / capability | Realization | Pinned version | Support level | Permitted modes | Substitution path |
|---|---|---|---|---|---|---|
| 1 | Container platform (StRS §11) | Red Hat OpenShift Container Platform | 4.21 (GA 2026-02-03; 4.22 GA 2026-07 also admissible) | GA | all | Any CNCF-conformant Kubernetes exposing the same operator services; contracts unaffected |
| 2 | Model interface — OpenAI-compatible inference (SysR-P-IF-01) | OpenShift AI model serving: vLLM runtime via LLMInferenceService / Distributed Inference with llm-d | RHOAI 3.4 (3.4.2) | GA | M-03..M-05 (M-01 uses the shared dev endpoint) | Any OpenAI-compatible endpoint (internal or approved external provider); config-only change (SysR-A-ARC-04) |
| 3 | Model endpoint governance: subscriptions, API keys, quotas, rate limits (supports SysR-P-F-12 operation) | OpenShift AI Models-as-a-Service (MaaS) | RHOAI 3.4 | **GA** (core); external-OIDC auth, vLLM-on-MaaS, observability dashboard, external-model egress each **TP** | M-03..M-05 (GA core only) | Direct serving endpoints without MaaS; routing abstraction is blueprint code either way |
| 4 | Rules-based routing + reason codes (SysR-P-F-12) | Blueprint model-client abstraction (template code) | blueprint v0.x | blueprint component | all | Phase two: AI Model Routing Grid attaches behind the same client contract (SysR-P-ADP-01) |
| 5 | Agentic loop hosting (SysR-A-ARC-02) | **Loop-in-pod: blueprint agent image** (no shared runtime) | blueprint v0.x | blueprint component | all | AaaS swap at the adapter seam (SysR-P-IF-09) → Llama Stack Responses API (TP, §2) when it reaches GA |
| 6 | Optional AaaS realization behind the adapter seam (SysR-P-IF-09) | Llama Stack Distribution + Operator (Responses API) | RHOAI 3.4 · ODH Llama Stack 0.6.0.1+rhai0 | **TP** | M-01 experimentation only in phase one; not on critical path | Re-evaluate at GA; requirements intact by design (proposed Annex A OI-05) |
| 7 | Tool interface — MCP (SysR-P-IF-02/03) | Blueprint MCP tool server container (mock in M-01; enterprise-bridging in M-04/M-05); MCP protocol per upstream spec | blueprint v0.x; MCP spec rev pinned at template freeze | blueprint component (protocol: open spec) | all | Managed hosting via MCP Catalog / mcp-gateway (DP, §2) when GA; contract metadata (SysR-P-IF-03) already registry-compatible |
| 8 | Retrieval contract + vector store (SysR-P-IF-04) | Blueprint retrieval service + organization-approved vector-capable database (e.g., PostgreSQL + pgvector via org DB service) | blueprint v0.x; DB per org standard | blueprint component + org service (pgvector *as a Llama Stack provider* is TP — not used on critical path) | all | Phase two: Data Mesh data products attach behind the same retrieval contract (SysR-P-ADP-01) |
| 9 | Identity — OIDC user auth (SysR-P-IF-05) | Organization OIDC IdP; RHOAI 3.4 direct OIDC via Gateway API on the platform side; Red Hat build of Keycloak if the org lacks an IdP | RHOAI 3.4 (GA feature); RHBK 26.x | GA | all | Any OIDC-conformant IdP |
| 10 | Identity — workload identity capability (SysR-P-IF-05) | Kubernetes ServiceAccounts (one per agent deployment) + scoped tool credentials | OCP 4.21 | GA | all | Phase two: SPIFFE/SPIRE via Kagenti AgentRuntime (DP, §2); capability wording unchanged |
| 11 | Policy evaluation — deny path (SysR-P-F-11, SysR-P-SEC-05) | OPA (library/sidecar) evaluating versioned policy bundles | OPA pinned at template freeze (record exact version + commit per SysR-P-LC-01) | **community — justification:** phase one requires policy *scaffolding* with one enforced deny path (Annex A OI-03); no GA Red Hat product realizes agent-action policy bundles today; OPA is the de-facto bundle format the phase-two Secure Agent Sandbox is expected to consume | all | Productized policy/authorization gateway (e.g., Kuadrant-based Connectivity Link — version not pinned in this pass) or Gatekeeper Operator where applicable; bundle format preserved |
| 12 | Human approval workflow (SysR-P-F-08/09, SysR-P-USE-01) | Blueprint approval service (minimal, audit-logged) — **owner decision D-02 pending:** blueprint component vs. reuse of the ITSM platform's native approval flow | blueprint v0.x | blueprint component | M-02..M-05 (mock approver in M-01) | Executor engine swappable behind the tool contract (SysR-P-F-09); Llama Stack HIL (DP) is not admissible in M-04/M-05 |
| 13 | IDP template exposure (SysR-P-F-01) | Red Hat Developer Hub (software templates; MCP server + OpenShift AI connector available since 1.8) | 1.10 (GA 2026-06) | GA | n/a (dev-time) | Direct CLI instantiation is normatively required in parallel (SysR-P-F-01(b)); portal outage never blocks the golden path (Annex A OI-04) |
| 14 | CI pipeline (SysR-P-F-05/06/07) | Red Hat OpenShift Pipelines (Tekton) | 1.23 (current GA per OpenShift Operator life cycle) | GA | M-02 | Any CI executor producing the same evidence (SBOM, eval results, digest) |
| 15 | GitOps promotion (SysR-P-IF-07, SysR-P-OPS-02) | Red Hat OpenShift GitOps (Argo CD) | 1.21.0 (GA 2026-06-24; supports OCP 4.14–4.22) | GA | M-03..M-05 | Any declarative GitOps controller reconciling the same repo state |
| 16 | Artifact registry, vulnerability data, SBOM association (SysR-P-PKG-01/02) | Red Hat Quay (with Clair) | 3.17 (3.17.3, 2026-06; Clair 4.9) | GA | M-02..M-05 | Any OCI-conformant registry with digest-addressed SBOM attachment |
| 17 | Telemetry pipeline (SysR-P-IF-06) | Red Hat build of OpenTelemetry (Collector + Operator) | 3.9 (3.9.3, 2026-05) | GA | all | OTLP is the contract; any OTLP-compatible backend. RHOAI centralized observability stack (COO/Tempo) is **TP** — optional, behind OTLP |
| 18 | Metrics & SLO dashboards (SysR-P-OPS-01) | OpenShift Monitoring (Prometheus, user-workload monitoring) + OpenShift console dashboards | OCP 4.21 built-in | GA | M-03..M-05 | Grafana (community operator) only with recorded justification per SysR-P-LC-03(4) |
| 19 | Experiment / evaluation tracking (SysR-P-INFO-05) | MLflow (RHOAI managed component, `mlflowoperator` in DataScienceCluster) | RHOAI 3.4 | **GA** (promoted in 3.4) | M-02..M-05 | Any tracking system recording {eval-set version, digest, config, thresholds, results} |
| 20 | Evaluation harness (SysR-P-F-03, SysR-A-EVL-01) | Blueprint version-controlled harness + local CLI (normative realization) | blueprint v0.x | blueprint component | all | Optional backend: RHOAI EvalHub SDK/CLI + Evaluation Stack UI (**TP**) behind the harness's result schema; LM-Eval UI (TP) |
| 21 | Secrets (SysR-P-SEC-04) | Organization enterprise secret-management service (external interface per StRS §11) | org-defined | org service | all | Any secret store injectable at deploy/runtime |
| 22 | Local container runtime (M-01) | Podman (RHEL container-tools) or Docker | Podman 5.8.x | GA (as RHEL component) / community | M-01 | Interchangeable; compose file is the contract |
| 23 | Guardrails (optional; **not** an MVP requirement — flag before adding: SysR-P-POL-02) | NeMo Guardrails (RHOAI) | RHOAI 3.4 | GA | — (out of MVP scope) | Would attach behind the model-client contract if a scope decision admits it |
| 24 | Git/source-control hosting for scaffolded project repositories (supports `SysR-P-F-01`'s template-repository target; `DECISIONS.md` DEC-098) | In-cluster Gitea via upstream kustomize (`config/default`, not OLM — the `rhpds/gitea-operator` OLM `Subscription` path never resolved, stuck resolver cache, and was abandoned; `DECISIONS.md` DEC-100) | `v2.3.2`, image digest `sha256:ec115feaa606459300c33f8aecd751d637217185e5e9087513f0280768695613` (verified live 2026-08-26) | **community — justification:** no GA Red Hat product provides in-cluster Git repository hosting for scaffolded projects; same justification pattern as row 11 (OPA) | Platform bootstrap; all instantiated projects | Organization's existing enterprise Git hosting (GitHub/GitLab/hosted Gitea) where already available; this in-cluster Gitea is the self-contained default, not an assumed sole answer |
| 25 | Combined platform bootstrap: RHDH + OpenShift GitOps + OpenShift Pipelines installed together to enable RHDH's "AI Software Templates" capability (bootstrap tooling only — does not replace rows 13/14/15) | `redhat-ai-dev/ai-rhdh-installer` Helm charts | Release tag `v0.11.0`, commit `cfcdfe96765a634d8f532b0125bd4fc6ccb0b7ca` (reproducible, recommended); HEAD `6dd5aed6dfba3799f839e8c7a90345e1e55463e6` (2026-05-29) pre-staged as an alternative — G1 decides which at execution time | community | G1 bootstrap only, one-time; not a runtime dependency thereafter | Install RHDH operator, OpenShift Pipelines operator, OpenShift GitOps operator individually per rows 13/14/15 — the exact path Phase F4 already used (`DEC-092`-`DEC-094`) without this installer |
| 26 | Portal-driven publish to Git for scaffolded projects (`SysR-P-F-01`(a)'s portal path; `DECISIONS.md` DEC-118/DEC-123) — **proven and landed**, no longer "not available" | RHDH dynamic plugin `@backstage/plugin-scaffolder-backend-module-gitea`, built from upstream Backstage core via `redhat-developer/rhdh-dynamic-plugin-factory` | Backstage source `backstage/backstage@v1.49.0` (matched to this RHDH instance's live `@backstage/backend-defaults@0.16.0`); build tool `quay.io/rhdh-community/dynamic-plugins-factory:1.10`, digest `sha256:ab3ab5eb73ba2f2080697f334478b9987c68468ce878d18802a4baeb90dac96c`; both verified live 2026-08-26 | **community — justification:** no GA/first-party RHDH dynamic plugin exists for Gitea (row 13's own "software templates" GA support covers the GitHub/GitLab-scaffolder-publish case, not Gitea); this project builds it from upstream using RHDH's own first-party factory tool, the identical mechanism RHDH's own maintainers used for the bundled GitHub/GitLab equivalents | G6+ (per-instance, once landed); all future portal-driven instantiations | `SysR-P-F-01`(b)'s direct CLI path (`tools/gitea_publish.py`, `DECISIONS.md` DEC-111) publishes the identical two-repo structure without any RHDH plugin — already proven, normatively required in parallel regardless of this row's own status, not a fallback superseded by it |

## 4. Support-level audit against SysR-P-LC-03

- **Critical path (M-04 staging, M-05 pilot):** rows 1, 2, 3(core), 9, 10, 14, 15, 16, 17, 18, 19 — all **GA**. Rows 4, 5, 7, 8, 12, 20, 21 are blueprint components or organization services, which the rule does not restrict. **No TP or DP component is on the staging/pilot path.**
- **TP behind a contract with documented swap path:** rows 6 (behind SysR-P-IF-09), 8-note (pgvector-as-provider not used), 17-note (COO stack optional behind OTLP), 20-note (EvalHub behind harness schema), 3 sub-features (not enabled for pilot).
- **DP confined to local/demo:** §2 rows (MCP Catalog, HIL, Kagenti) — M-01 exploration only.
- **Community with recorded justification:** row 11 (OPA), justification recorded in-row; row 22 (Docker option).

## 5. Sources (verified 2026-08-12)

1. RHOAI 3.4 Release Notes — https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.4/html-single/release_notes/index
2. RHOAI Self-Managed Life Cycle (EA/GA/EUS policy) — https://access.redhat.com/support/policy/updates/rhoai-sm/lifecycle
3. RHOAI 3.5 Release Notes (EA2 status) — https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/index
4. RHOAI 3.3 "Working with Llama Stack" (versions, TP status) — https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.3/html-single/working_with_llama_stack/index
5. RHOAI 3.0 Release Notes (3.x/OCP 4.19+ requirement) — https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.0/pdf/release_notes/Red_Hat_OpenShift_AI_Self-Managed-3.0-Release_notes-en-US.pdf
6. Red Hat Developer Hub 1.10 (GA, June 2026) — https://developers.redhat.com/articles/2026/07/14/whats-new-developers-red-hat-openshift-4-22
7. OpenShift GitOps 1.21.0 Release Notes (GA 2026-06-24) — https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.21/pdf/release_notes/Red_Hat_OpenShift_GitOps-1.21-Release_notes-en-US.pdf
8. OpenShift Operator Life Cycles (Pipelines 1.23, GitOps 1.21) — https://access.redhat.com/support/policy/updates/openshift_operators
9. Red Hat Quay 3.17 Release Notes (3.17.3, Clair 4.9) — https://docs.redhat.com/en/documentation/red_hat_quay/3.17/pdf/red_hat_quay_release_notes/Red_Hat_Quay-3.17-Red_Hat_Quay_Release_Notes-en-US.pdf
10. Red Hat build of OpenTelemetry 3.9 (3.9.3 advisory RHSA-2026:14162) — https://access.redhat.com/errata/RHSA-2026:14162
11. OpenShift Container Platform 4.21/4.22 GA — https://developers.redhat.com/articles/2026/02/03/whats-new-developers-openshift-4-21 and https://developers.redhat.com/articles/2026/07/14/whats-new-developers-red-hat-openshift-4-22

*End of Red Hat Realization Table v0.1 (Informative). Editing this table is the sanctioned mechanism for realization substitution (SysR-P-LC-02).*
