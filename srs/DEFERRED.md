# Deferred SysR Requirements

SysR requirements intentionally out of scope for the five blueprint-component
SRS documents (`SRS-APR`, `SRS-MIT`, `SRS-AGT`, `SRS-RET`, `SRS-EVH`), each
with a one-line reason — per `MISSION_PHASE_B0.md`'s deliverable 3, so
`tools/trace-check`'s check (a) can distinguish "deferred deliberately" from
"forgotten."

This list was populated by running `tools/trace-check` for real against the
committed SRS set and adjudicating every SysR its check (a) reported as
untraced (19 of the 20 it originally found — the twentieth, `SysR-P-OPS-03`,
turned out to already be substantively covered by `srs/SRS-AGT.md`'s
SRS-AGT-F-09 and was fixed with an added trace there instead of deferred
here, since it isn't actually out of scope; see that requirement's own note
and `DECISIONS.md` DEC-007). None of the 19 below represents a gap in
platform capability — each is either realized directly by this repository's
existing non-SRS artifacts (`Containerfile`, `ci/`, `deploy/`, `Makefile`,
`scripts/`), or governs the SRS-derivation process itself rather than a
running component's behavior. A future phase that adds a platform-level or
CI-pipeline SRS document would be the natural place to formally claim these,
not a forced fit into one of the five component documents that exist today.

Format: `- **SysR-ID** — one-line reason.`

---

## Platform-level golden-path mechanics (template, local dev, packaging)

Realized directly by this repository's own scaffold, not by an agent-time
component.

- **SysR-P-F-01** — Template instantiation (IDP + CLI scaffolding of a new agent project, and, per `DECISIONS.md` `DEC-098`, a separate tools template scaffolding an independent MCP-server project) is platform template-tooling, not a requirement of any running agent-time component; out of the five-document deliverable scope.
- **SysR-P-F-02** — Local development environment (starting the local corpus/retrieval/mock-tool/model-endpoint stack together) is platform launch-configuration orchestration (`scripts/dev.sh`, `Makefile` targets), not a single component's own requirement; each service it starts (`SRS-RET`, `SRS-MIT`, `SRS-AGT`) already specifies its own local-dev-compatible behavior individually.
- **SysR-P-F-04** — Contract parity across environments is a cross-cutting property spanning every phase-one contract (model, tool, retrieval, policy, config) collectively; each component's own SRS document already specifies its contract in protocol-surface terms (never environment-specific), which is what makes parity possible, but the aggregate parity guarantee itself has no single owning component.
- **SysR-P-F-06** — Single immutable artifact promotion (one OCI image per change set, promoted unchanged via GitOps) is platform build/release mechanics, not a requirement any of the five components implements themselves.
- **SysR-P-F-13** — Blueprint documentation (sufficient for a second team to instantiate/run/evaluate/deploy unassisted) is a meta-requirement about the documentation set as a whole (this repository's own `README.md`, `docs/`, `TODO_DOMAIN.md`, etc.), not a single component's own SRS.
- **SysR-P-IF-07** — Artifact interface (OCI images identified by digest, SBOM associated to the digest) is platform packaging/registry mechanics.
- **SysR-P-PKG-01** — Artifact contents (what the single OCI image must and must not contain) is platform packaging policy spanning all components' code together, not any one component's own requirement.
- **SysR-P-PKG-02** — SBOM per digest is a CI/build-pipeline output, the same territory as `SysR-P-F-05` below.

## CI, build, and promotion pipeline mechanics

Explicitly Phase C, out of Phase B0's SRS-derivation scope.

- **SysR-P-F-05** — CI validation pipeline (four test categories, image build, SBOM generation, publishing evaluation results) is Phase C pipeline mechanics, explicitly out of Phase B0's SRS-derivation scope per `srs/SRS-EVH.md`'s own exclusion note.

## Operations: observability, rollback

Platform operational capabilities, not a component's own behavior.

- **SysR-P-OPS-01** — Standard observability (operators observe SLOs/traces/metrics/logs through the organization's own observability services, without agent-specific tooling) is a platform operations capability; every component that emits telemetry (`SRS-AGT-IF-08`, `SRS-RET-IF-03`, `SRS-APR-IF-03`) already specifies what it emits — this SysR is about the operator-facing access path to that telemetry, an organizational/platform commitment, not a per-component one.
- **SysR-P-OPS-02** — Rollback (revert to the previously approved image digest via GitOps alone) is platform release-management mechanics.
- **SysR-P-PERF-03** — Rollback objective (previously approved digest serving within a defined time objective after a rollback command) is a platform release-management timing measure, paired with `SysR-P-OPS-02` above.

## Lifecycle and realization governance (document-authoring and reuse discipline)

These SysRs govern how the blueprint's documents and realization choices are
produced, not what a running component must do.

- **SysR-P-LC-01** — Pinned reused assets (validated patterns/quickstarts/reference repos pinned by version and commit) governs `PINS.md`-style provenance tracking for infrastructure this blueprint reuses (per `CLAUDE.md`'s "Reuse over building" section) — a delivery-process discipline, not a component requirement. No `PINS.md` exists yet in this repository; open work for whoever next touches infrastructure/pipeline code, tracked here rather than silently dropped.
- **SysR-P-LC-02** — Realization independence (no requirement names a product) is a document-authoring meta-rule this SRS derivation itself follows, not a requirement any component derives from — already noted identically in `srs/SRS-RET.md`'s own orphan-check ("none of `srs/SRS-APR.md`, `srs/SRS-MIT.md`, `srs/SRS-AGT.md`, or `srs/SRS-RET.md` trace any requirement to it either").
- **SysR-P-LC-03** — Support-level assignment rule (GA-with-Operator preferred; Technology Preview only behind a contract; Developer Preview only in local/demo modes; community only with recorded justification) governs realization-table selection in `SyRS-AGP-001-RRT_Realization_Table.md`, an informative companion document outside this SRS-derivation's scope.
- **SysR-P-POL-02** — Complexity-envelope scope guard (any change increasing the envelope requires an explicit recorded decision) governs this delivery process's own change-control discipline — the same discipline `DECISIONS.md` exists to satisfy for this session's own scope decisions — not a requirement any running component implements.

## Cross-cutting adaptability and whole-golden-path measures

- **SysR-P-ADP-01** — Phase-two attachment without rework is a cross-cutting adaptability analysis over every phase-one contract collectively (model, tool, retrieval, policy, config, telemetry); each component's own protocol-surface-only interface style (naming no product) is what satisfies it, but the aggregate "can phase-two attach without rework" claim is an analysis exercise (`Verification: A`) over all contracts together, not a single component's derivable shall-statement.
- **SysR-P-MODE-01** — Operational modes (M-01..M-06, identical artifact and contracts across M-03/M-04/M-05) is a platform deployment-configuration property expressed through injected configuration alone; each component already specifies environment-agnostic, config-driven behavior (e.g. `SRS-AGT-IF-07`; `SRS-RET`'s and `SRS-MIT`'s interfaces carry no environment-specific values), which is what makes mode-independence possible, but the mode-set itself is a platform/deployment concept, not a component requirement.
- **SysR-P-PERF-01** — One-hour local start (template instantiation to a locally running, evaluated agent) is a whole-golden-path onboarding measure verified by a single timed demonstration scenario (OS-01) spanning template, local-dev environment, and eval CLI together — already explicitly excluded, for this same reason, by `srs/SRS-APR.md`, `srs/SRS-RET.md`, and `srs/SRS-EVH.md` each in their own Quality/Performance sections.
