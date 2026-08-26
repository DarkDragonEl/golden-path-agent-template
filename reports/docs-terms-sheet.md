# Documentation terms sheet (Phase H0)

One page, canonical name + one-line definition for the concepts every
Wave-β stream (H1 README, H2 docs reorg, H3a docstrings) must use
consistently. This is a binding writing contract, not a suggestion — it is
also the seed of H2's `docs/glossary.md`.

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
