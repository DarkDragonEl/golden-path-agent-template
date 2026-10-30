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

## Sources of truth

- `srs/` — the requirements: stakeholder (`StRS_Agentic_AI_Platform_EN.md`),
  system (`SyRS-AGP-001_EN.md` and its realization table), open items
  (`Annex_A_Open_Items_EN.md`) and the five software requirement sets
  (`SRS-*.md`). The decision log (`DECISIONS.md`) and the session handoff
  (`HANDOFF.md`) live in the companion roadmap repository.
- `PINS.md` — every pinned component, with source URL and verified date.
- `docs/` — how-to, reference and explanation; `docs/adr/` for the
  standing architecture decisions.
- If an implementation decision is not covered by these documents,
  **STOP and ask**. Normative documents change only at a STOP, with the
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
8. **Clean integration points, never implementations,** for anything
   scoped to a later phase. **Contracts, not couplings:** components
   meet over documented interfaces configured by env vars.
9. **Scope guard.** One enterprise tool (the mock ITSM with persistent
   state), one model route plus one fallback. Name a "while we're at it"
   addition instead of building it.
10. **Execute verification yourself.** Evidence over assertion: run the
    tests, render the manifests, exercise the real path. A scripted API
    call is not evidence of what a real browser shows.
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
  merge to `main` without the owner's go.
- **Decisions:** every non-obvious decision becomes a `DEC-NNN` entry
  (ambiguity → finding → decision → evidence → status). Code comments
  state the current rule in a few lines and point at the `DEC-NNN`; the
  narrative lives in the decision log.
- **Checks before a push:** `pytest -q`, `python tools/verify_skeleton.py`,
  `python tools/check_config_contract.py`, `shellcheck` on touched
  scripts, and `kustomize build` (validated with `kubeconform`) for every
  touched overlay. `tests/test_overlays_build.py` builds every overlay,
  including the rendered templates'.
