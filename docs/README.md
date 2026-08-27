# Documentation hub

Every document in `docs/` is reachable from this page in at most two
clicks. Organized [Diátaxis](https://diataxis.fr/)-style: **Tutorials**
(learn by doing a full run-through), **How-to / runbooks** (accomplish
one specific operational task), **Reference** (look up a fact), and
**Explanation** (understand why something is the way it is). A short
**Historical & draft records** section at the end covers the handful of
documents that are neither current reference nor an active runbook —
kept for provenance, not duplicated into the four sections above.

New here? Start with `docs/architecture.md` for the shape of the system,
then `docs/owner-walkthrough.md` for what it looks like end to end.

## Tutorials

Learn the golden path by walking through it.

- **[Owner walkthrough](owner-walkthrough.md)** — the live approver-UI
  click-through that formally closes Checkpoint D: log in as the demo
  approver, decide a pending write proposal, see it complete.
- **[Showcase walkthrough script](showcase-walkthrough-script.md)** —
  the ~20-minute owner-facing narration script, from template
  instantiation through the promotion gate to the live approval UI.
- **[Direct-chat walkthrough](direct-chat-walkthrough.md)** — talk to the
  running agent over HTTP directly, including a full write → approve/
  reject round trip — the path the eval harness itself never exercises.

## How-to / runbooks

Accomplish one task against a real environment.

- **[Phase C runbook](phase-c-runbook.md)** — manual cluster bootstrap
  steps for the CI/ephemeral-test/demo-prod environments (namespaces,
  RBAC, the pipeline's own ServiceAccount).
- **[Phase D runbook](phase-d-runbook.md)** — manual bootstrap steps for
  identity (Keycloak namespace, operator, database, realm import).
- **[Access and credentials](access-and-credentials.md)** — the demo
  accounts, how their secrets are provisioned/rotated, the self-service
  reset flow, and showcase access.
- **[Local dev](local-dev.md)** — `make up` / `make up-offline`: run all
  three images plus a local OTel Collector on a laptop, no cluster
  needed.
- **[Showcase access](showcase-access.md)** — the sharing schedule
  template and the anonymity-sweep procedure to run before every sharing
  moment.
- **[Testing perspectives guide](testing-perspectives-guide.md)** — the
  six distinct verification mechanisms this project relies on (unit
  tests, offline eval, live-model eval, direct HTTP chat, operational
  tests, trace-check) and when to reach for each one.
- **[Previewing this documentation site](techdocs-preview.md)** — how to
  run this same `docs/` tree through `mkdocs serve` locally, including the
  fuller mkdocstrings-generated API reference that RHDH's own live
  TechDocs page can't render.

## Reference

Look up a fact.

- **[Environments](environments.md)** — the environment table (local,
  PR CI, ephemeral test, demo-prod, staging, pilot-prod), the promotion
  model, and what's deployed this milestone vs. deferred.
- **[Evaluation](evaluation.md)** — the eval harness: case format,
  assertion types, determinism guarantees, and how it gates CI.
- **[Glossary](glossary.md)** — canonical term definitions used
  consistently across this documentation set.
- **[Naming conventions](naming-conventions.md)** — namespaces, secrets,
  image names, Keycloak realm/client/role/user names, Tekton
  pipeline/task names, branch conventions, eval case IDs, and
  `DEC-NNN`/`OI-NN`/requirement IDs, with real examples and known
  deviations.
- **[Code comment policy](code-comment-policy.md)** — the three-category
  rule (keep / slim-to-pointer / migrate-then-slim) applied repo-wide to
  every `DEC-NNN`-citing comment.
- **[Pinned versions and sources (`PINS.md`)](https://github.com/DarkDragonEl/golden-path-agent-template/blob/main/PINS.md)** — every
  pinned component version, commit, and the date it was last verified
  live.
- **[Template nine-output mapping](template-nine-output-mapping.md)** —
  where each of `SysR-P-F-01`'s nine required scaffolder outputs lives in
  `skeleton/`.

## Explanation

Understand why the system is shaped this way.

- **[Architecture](architecture.md)** — the graph shape, the four
  contract boundaries (model, retrieval, tool/MCP, policy), and the
  three-image split.
- **[Security & identity](security-identity.md)** — workload identity,
  secrets, the network boundary between components, and the human-
  approval gate's actual control flow.
- **[Decision log (`DECISIONS.md`)](https://github.com/DarkDragonEl/golden-path-agent-template/blob/main/DECISIONS.md)** — the append-only
  record of every `DEC-NNN` ambiguity → finding → decision → evidence →
  status entry this project has made.

## Historical & draft records

Kept for provenance. Each one is explicitly self-dated or marked
draft/provisional in its own text — none of them is a current
authoritative reference, and none contradicts the documents above (where
an overlap exists, the current doc says so explicitly).

- **[Phase E kickoff plan](phase-e-kickoff-plan.md)** — the shared
  showcase-cluster proposal, pre-Phase-G. Marked draft/awaiting
  authorization in its own text.
- **[Phase F kickoff plan](phase-f-kickoff-plan.md)** — the RHDH/
  Internal-Developer-Portal phase plan, pre-Phase-G. Tracks its own
  completion status inline as later phases closed it out.
- **[Approver UI map (draft)](drafts/AGENT-UI-MAP.draft.md)** —
  provisional page/element inventory for the approver UI, explicitly
  marked "must be verified against the real running UI before promotion."
