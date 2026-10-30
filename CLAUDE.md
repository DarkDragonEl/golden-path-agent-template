# CLAUDE.md

Working rules for any agent (or person) changing this repository. This
repository is a **reference implementation** of an Agentic AI platform
golden path: a blueprint an adopter clones and bootstraps on their own
OpenShift cluster. It delivers an evaluation set, a local golden path,
and CI with promotion gates. Enterprise integration is a
contract-conformant mocked example tool, and the approval workflow runs
against a test system. Staging with real enterprise services and
production rollout are the adopter's own next steps, not this repo's
scope.

## Sources of truth (read in this order, never contradict them)

1. `srs/SyRS-AGP-001_EN.md` — normative system requirements (`SysR-P-*`
   platform, `SysR-A-*` pilot agent).
2. `srs/StRS_Agentic_AI_Platform_EN.md` — stakeholder requirements; §19
   defines this reference implementation's delivery scope.
3. `srs/SyRS-AGP-001-RRT_Realization_Table.md` — informative Red Hat
   realization mapping (pinned versions). Use it to choose components; it
   is not normative.
4. `srs/Annex_A_Open_Items_EN.md` — adopted assumptions (OI-02 ITSM
   scenario, OI-03 identity/policy framing; OI-04 closed — both
   instantiation paths ship as delivered capabilities).

The five software requirement sets (`srs/SRS-*.md`) derive from these. The
decision log (`DECISIONS.md`) and the session handoff (`HANDOFF.md`) live
in the companion roadmap repository.

Also:

- `PINS.md` — every pinned component, with source URL and verified date.
- `docs/` — how-to, reference and explanation; `docs/adr/` for the
  standing architecture decisions.
- If an implementation decision is not covered by these documents,
  **STOP and ask**. Do not invent requirements. Normative documents change only at a STOP, with the
  owner's explicit sign-off on a requirements-level diff.

## Hard rules

1. **One immutable artifact per component.** `agent`, `mcp` and
   `approval` are each one OCI image, built once in CI and promoted
   unchanged. Environment differences live only in config, secrets,
   policy bundles and bindings — never in an image.
2. **Promotion only by a merged GitOps PR.** Nothing writes an image
   digest to `main` directly; the pipeline's `open-promotion-pr` opens
   the PR and merging it is the promotion decision.
3. **Fail closed, and prove the negative case.** Every gate and every
   write path must refuse when unsure, and a test or seeded failure must
   show it refusing.
4. **Synthetic data only.** No real client or organization data in any
   environment, corpus, eval case or fixture.
5. **Anonymity.** No client organization, employee, person or
   identifiable internal system in any committed file, report or commit
   message. Environment hostnames, cluster domains and model endpoints
   are configuration — discovered or injected at bootstrap, never
   committed (every committed model endpoint is a placeholder). Run an
   anonymity sweep over the full diff range before any push or sharing
   artifact.
6. **Never write a secret value** — not to Git, a report, a log, a
   commit message or a shell trace. Refer to secrets by name only; no
   `set -x` in scripts that handle them.
7. **Reuse over building.** Before writing infrastructure code
   (pipelines, GitOps, observability, policy), check Red Hat Validated
   Patterns, AI Quickstarts and official reference repos; pin exact
   versions in `PINS.md` with the URL and date verified. Never rely on
   memorized repo contents.
8. **Contracts, not couplings; clean integration points, never
   implementations.** The agent talks to a standardized model API
   (endpoint injected via environment), to tools via MCP/REST contracts,
   and to retrieval via a retrieval contract. `agent/model_client.py` is
   the one adapter that imports a provider SDK; no other agent logic
   does, and nothing hardcodes a model name, endpoint or tool URL.
   Anything scoped to a later phase (Data Mesh, AI Routing Grid, Secure
   Agent Sandbox) gets a clean integration point and no implementation.
9. **Scope guard.** One agent, one knowledge domain (synthetic platform
   docs), one enterprise tool (the mock ITSM with persistent state), one
   model route plus one fallback with rules-based routing and logged
   reason codes, human approval for every write, OpenTelemetry on every
   run. A second tool, semantic routing, memory tiers, multi-agent
   orchestration or any "while we're at it" capability is scope creep:
   STOP, name it, and ask before proceeding.
10. **Execute verification yourself — never delegate testing to the
    owner.** Evidence over assertion: run the tests and the local eval
    CLI, render the manifests, exercise API surfaces with curl, and
    exercise the real path. A scripted API call is not evidence of what a
    real browser shows. A task with unexecuted verification is not done.
11. **The measurement instrument is frozen.** Prompts, model choice,
    retrieval, graph topology and sampling parameters change only with a
    fresh multi-pass re-baseline (see the invariants in `HANDOFF.md`).

## Clusters

- **Cloud sessions never touch a cluster.** If `CLAUDE_CODE_REMOTE=true`,
  never run `oc`, `kubectl`, or anything else that targets a cluster
  (including `scripts/bootstrap.sh` and the `pre-flight`/`post-deploy`
  skills). Work repo-only, and hand the local session an exact,
  ordered list of live steps with the expected result of each.
- **Explicit context, always** (ADR-010): every `oc` call pins
  `--context` or a dedicated `KUBECONFIG`, never the ambient shared one.
- **Git is the source of truth.** ArgoCD self-heals: a live patch to a
  GitOps-managed object is reverted within minutes. Change the manifest,
  not the cluster. A deliberate cluster-local exception is recorded as a
  borrowed-cluster adaptation, never folded into the blueprint.

## Workflow

- **Branches:** image-content changes (anything a `Containerfile.*`
  copies: `agent/`, `mcp_server/`, `approval_service/`, `policy/`, …) go
  through a `feature/<phase>-<short-name>` branch and the pipeline's
  promotion gate before merging. Other work uses its own branch too
  (`fix/`, `chore/`, `feat/`); see `docs/naming-conventions.md`. Never
  merge to `main` without the owner's go. There is no direct-to-main
  exception: docs, decisions and non-image tooling go through a branch
  and the owner's go too (`DEC-148`).
- **Decisions:** every non-obvious decision becomes a `DEC-NNN` entry
  (ambiguity → finding → decision → evidence → status). Code comments
  state the current rule in a few lines and point at the `DEC-NNN`; the
  narrative lives in the decision log.
- **Journal:** `DEC-NNN` entries are written to the roadmap repository's
  `DECISIONS.md`, continuing its numbering — never to this repository.
  Run `tools/journal_census.py` before any commit here. It still exits
  non-zero on its existing baseline, which is informational, but never
  add findings on top of that baseline.
- **Reports:** a short test report goes to `reports/<branch>.md` in the
  roadmap repository: commands run, results, eval scores, what failed
  and why. Reports live there, not in this repository.
- **Every mission ends in a STOP with evidence,** and waits for the
  owner's go before anything further.
- **Checks before a push:** `pytest -q`, `python tools/verify_skeleton.py`,
  `python tools/check_config_contract.py`, `shellcheck` on touched
  scripts, and `kustomize build` (validated with `kubeconform`) for every
  touched overlay. `tests/test_overlays_build.py` builds every overlay,
  including the rendered templates'.

## Skills and commands

Claude Code skills (auto-invocable, read-only) and commands
(explicit-invocation-only) live in the companion roadmap repository,
under `.claude/skills/` and `.claude/commands/`. Governance rule:
anything that runs automatically is read-only; anything that modifies
state requires explicit human invocation. The classification is stated
at the top of each file.

- `/pre-flight` (skill, read-only, cluster) — verify demo-prod is healthy
  before any owner-facing walkthrough or demo.
- `/run-evals` (skill, read-only, local stack) — run the local eval gate
  N times and compare against the standing baseline and known-gap
  tolerances.
- `/probe-tool` (skill, read-only with respect to project state, local
  stack) — call the mock ITSM MCP tools directly, bypassing the model.
- `/post-deploy` (skill, read-only, cluster) — verify a promotion landed
  correctly (Argo CD sync/health, image digest).
- `/start-step` (command) — bootstrap session context from `HANDOFF.md`,
  recent `DEC` entries, `PINS.md` and the current phase artifact.
- `/close-step <name>` (command) — draft, never commit, a `DEC` entry and
  a report skeleton for the session's work.

## Language

Code, comments and deliverable documents: English (canonical).
Conversation with the owner: mirror their language.
