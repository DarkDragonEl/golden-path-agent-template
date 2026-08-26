# Glossary

Canonical name + one-line definition for the concepts used consistently
across this repo's documentation. The first block below is seeded
verbatim from `reports/docs-terms-sheet.md` (Phase H0's binding writing
contract for the Wave-β documentation streams); the second block adds
terms encountered while building this documentation hub, the naming
conventions reference, and the access/credentials guide that weren't
already covered.

See also `docs/naming-conventions.md` for the literal string patterns
(namespaces, secrets, IDs) these terms map onto.

## Core terms (seeded from `reports/docs-terms-sheet.md`)

| Term | Definition |
|---|---|
| **Golden path** | The single, deliberately constrained agent workflow this repo demonstrates end-to-end: one LangGraph agent, one MCP tool contract, one model route + fallback, human approval gated on every write, evaluated by a CI promotion gate. |
| **Platform Foundation** | The shared infrastructure layer the three runtime artifacts deploy onto but that isn't itself one of them: identity (Keycloak/OIDC), telemetry (OpenTelemetry), Gitea, the Internal Developer Portal (RHDH), and the GitOps (ArgoCD) machinery. |
| **The three artifacts** | The agent, MCP tool server, and approval service — three independently built, independently promoted OCI images (post-G2 three-image split), each with its own Containerfile and Tekton pipeline. |
| **Promotion gate** | The CI checks (the eval harness plus lint/tests) an image must pass before a promotion PR moves its digest from the ephemeral test environment to demo-prod. |
| **Bad-change gate** | A deliberately seeded regression used to prove the promotion gate actually blocks a bad change, not just passes good ones — the negative case, demonstrated with a test, not claimed. |
| **Ephemeral test** | The short-lived test environment/namespace a pipeline run stands up to exercise a freshly built image before it's eligible for promotion. |
| **One-immutable-artifact** | The rule that each of the three images is built exactly once in CI and promoted unchanged across environments; environment differences live only in config, secrets, policy bundles, and bindings — never baked into the image. |
| **STOP** | A mandatory checkpoint where a session pauses work for the owner's review before continuing — not a suggestion to summarize progress, an actual hold. |
| **DEC** | A numbered, append-only entry in `DECISIONS.md` recording one ambiguity → finding → decision → evidence → status; the project's single decision log. |
| **Fail-closed** | Any gate, policy check, or approval path denies by default — an unauthorized or unverified action is blocked, not allowed through on error, timeout, or ambiguity. |
| **Approval flow** | The human-in-the-loop gate the agent must clear before executing any write against the mock ITSM tool: the agent drafts, a human approver explicitly approves or rejects, only then does the write execute. |
| **Showcase cluster** | The shared OpenShift cluster used for live demos and owner walkthroughs (Phase E onward) — distinct from a pipeline run's own throwaway ephemeral test namespace. |
| **Worktree stream** | An isolated unit of parallel work that runs in its own `git worktree` and branch, commits locally, and never pushes or merges to `main` itself — it stages its changes and drafts its DEC entry in its own report for the coordinating session to land. |
| **Held tail** | A piece of one stream's work that is deliberately deferred until a named dependency (another stream's merge, or a STOP) clears — the work isn't lost, it just doesn't land prematurely. |
| **Coordinating session** | The single session that owns `DECISIONS.md`, `HANDOFF.md`, and `PINS.md`; it reviews each worktree stream's diff and report, re-checks the decision log's real tail, and performs the actual merge to `main`. |

## Additional terms (Phase H2)

| Term | Definition |
|---|---|
| **MCP (Model Context Protocol)** | The open protocol the agent uses to call tools out-of-process. This repo's one tool server (`mcp_server/`) implements it as a FastMCP streamable-HTTP service; see `docs/architecture.md`'s contract-boundaries table. |
| **Mock ITSM** | The synthetic, in-memory ITSM (IT service management) tool this demo's MCP server exposes — the one tool the golden path calls, standing in for a real enterprise ITSM platform per `Annex_A_Open_Items_EN.md` OI-02. Never a real ticketing system; state resets on container restart in dev, persists per-environment on cluster. |
| **Workload identity** | The Kubernetes `ServiceAccount` (and, where wired, OIDC client credential) a Deployment runs under — the identity anchor `docs/security-identity.md` documents per component. |
| **Keycloak realm** | The single OIDC realm (`golden-path-agent`) holding every client and demo user this project defines — see `docs/naming-conventions.md` for the realm/client/role/user naming pattern and `docs/access-and-credentials.md` for who the demo users are. |
| **Approval-approver role** | The one realm role (`approval-approver`) that gates who may decide (approve/reject) a pending write proposal — assigned to `demo-approver`, deliberately not to `demo-user`, so the wrong-role-denied path has a real negative test case. |
| **EXAMPLE-NNN case** | A harness-mechanics eval fixture (`eval/cases/EXAMPLE-001.yaml`, `EXAMPLE-002.yaml`) that proves the eval harness itself runs end-to-end (invoke/resume, the approval interrupt, mock tool mode) — distinct from the domain eval cases below. |
| **Domain eval case ID** | A category-prefixed eval case ID in `eval/cases/domain/` (`KQA-*`, `ITR-*`, `TSEL-*`, `DRQ-*`, `OOD-*`, `UAW-*`, `INJ-*`, `OPS-*`) — see `docs/evaluation.md` and `eval/THRESHOLDS.md` for what each category gates. |
| **Known-gap tolerance** | A named, dated, deliberately excluded eval failure the promotion gate accepts without failing the build — tracked so it can't silently become a standing exemption; see `eval/cli.py`'s `KNOWN_GAP_TOLERANCES`. |
| **Tekton Pipeline/Task** | The CI execution unit this project's promotion gate runs on-cluster (`pipelines/pipeline-agent.yaml`, `-mcp.yaml`, `-approval.yaml`, one per artifact, each composed of the reusable `Task`s in `pipelines/tasks/`). |
| **App-of-apps root** | The single ArgoCD `Application` (`deploy/argocd/application-root.yaml`) that, once applied, syncs every other GitOps-managed `Application` this project defines — applying one object is enough to instantiate every synced environment from Git alone. |
| **RHDH / Internal Developer Portal** | Red Hat Developer Hub, this project's Backstage-based internal developer portal — the catalog and Scaffolder Template UI referenced throughout Phase F/G docs. |
| **Scaffolder Template / skeleton** | The RHDH Scaffolder Template (`template.yaml`, `template-tools.yaml`) that renders `skeleton/`/`skeleton-tools/` into a new, independently instantiated project — see `docs/template-nine-output-mapping.md`. |
| **trace-check** | This project's own SyRS→StRS→SRS requirement-traceability validator (`tools/trace-check/`) — validates this project's formal-requirements discipline, not the running agent's behavior. |
