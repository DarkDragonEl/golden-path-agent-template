# SysR-P-F-01 nine-output mapping

Phase F2 (DECISIONS.md `DEC-087` item 1; `docs/phase-f-kickoff-plan.md` §6,
item 4). `SysR-P-F-01` requires the template to produce, in one operation:
"agent source scaffold, container build configuration, deployment
manifests, GitOps configuration, MCP tool skeleton, evaluation project,
telemetry configuration, policy scaffolding, and developer documentation."
This table maps each of those nine outputs to its concrete location in
`skeleton/`. Any output without a location below is a real gap, not a
footnote — there are none as of this pass.

| # | `SysR-P-F-01` output | Skeleton location | Notes |
|---|---|---|---|
| 1 | Agent source scaffold | `skeleton/agent/`, `skeleton/approval_service/` | Full application source, copied verbatim except identity literals (`OTEL_SERVICE_NAME`, `AGENT_WORKLOAD_ID`, OIDC client IDs in `config.py`). Domain-specific logic (`agent/prompts/`, `agent/retrieval_client.py::retrieve()`) is intentionally untouched by F2 — that's `TODO_DOMAIN.md`'s own, separate axis (domain customization, not identity parameterization), carried into the skeleton unchanged. |
| 2 | Container build configuration | `skeleton/Containerfile`, `skeleton/entrypoint.sh`, `skeleton/requirements.txt`, `skeleton/requirements-dev.txt`, `skeleton/pyproject.toml` | `pyproject.toml`'s `name` field is templated (`${{ values.repoName }}`, dropping the source repo's own `-template` suffix per `template-schema.json`'s documented default). No image-content changes — matches CLAUDE.md's "one immutable artifact" rule; the Containerfile's own `COPY` list is untouched, only identity strings inside copied files change. |
| 3 | Deployment manifests | `skeleton/deploy/kustomize/` | Every `base/*.yaml` and `overlays/*/kustomization.yaml` with an identity literal is templated — namespace names, resource names, labels, the shared image-registry path (`deploy/kustomize/base/kustomization.yaml`'s `images:` block). |
| 4 | GitOps configuration | `skeleton/deploy/argocd/`, `skeleton/pipelines/` | ArgoCD `Application`/`AppProject` manifests and Tekton `Pipeline`/`Task`/bootstrap manifests, including the git-repo-URL substitution (`${{ values.repoOwner }}/${{ values.repoName }}`) in `pipelines/pipeline.yaml`, `pipelines/tasks/open-promotion-pr.yaml`, and every `deploy/argocd/*.yaml`'s `repoURL`. |
| 5 | MCP tool skeleton | `skeleton/mcp_server/` | The five `@mcp.tool()` registrations (`placeholder_lookup`, `placeholder_write_action`, `itsm_search_records`, `itsm_create_request`, `healthcheck`) carry over unchanged in shape — **boundary DoD confirmed**: zero scaffold-invoking tool exists in the skeleton (`grep -c '@mcp.tool' skeleton/mcp_server/server.py` matches the source repo's own count exactly). `mcp_server/auth.py`'s `MCP_AUDIENCE` is templated. |
| 6 | Evaluation project | `skeleton/eval/` | `eval/cli.py`, `eval/schema.json` (its `$id` URI templated), `eval/cases/` (the 2 harness-mechanics fixtures carry over; the 62-case domain suite is this project's *own* domain content per `TODO_DOMAIN.md`'s own list — a real new project replaces those, same as the corpus). |
| 7 | Telemetry configuration | `skeleton/agent/telemetry.py` (part of output 1, above), `skeleton/deploy/otel/`, `skeleton/pipelines/bootstrap/otel-collector.yaml` | The `/v1/traces` endpoint-suffix fix (`DEC-020`) and the no-op-when-unset guard carry over unchanged (generic logic, no identity literal). The collector's own namespace/labels/image references are templated. |
| 8 | Policy scaffolding | `skeleton/policy/` | OPA rego + `approval_rules.yaml`, copied verbatim — no identity literals found in this directory during inventory (policy logic is domain-agnostic by design already). |
| 9 | Developer documentation | `skeleton/docs/` (`architecture.md`, `environments.md`, `evaluation.md`, `local-dev.md`, `owner-walkthrough.md`, `security-identity.md`), `skeleton/README.md`, `skeleton/TODO_DOMAIN.md` | This project's own session-history docs (`docs/phase-*-*.md`, `docs/showcase-*.md`, `docs/drafts/`) are deliberately excluded — they document *this instance's* history, not generic scaffold content. `TODO_DOMAIN.md` carries over unchanged: it already is, in effect, a hand-written "what to fill in next" guide for a scaffolded instance, predating this phase's own work. |

## Explicitly out of scope for this mapping

- **`catalog-info.yaml`** — not one of the nine outputs; F1 registers *this*
  blueprint repo in the catalog, but a scaffolded child project registering
  itself is a reasonable future enhancement, not required now.
- **`srs/`, `DECISIONS.md`, `HANDOFF.md`, `PINS.md`, `reports/`** — this
  project's own decision/session history, not generic template content.
- **`corpus/` domain content, `agent/prompts/*.md` content,
  `eval/cases/domain/*`** — `TODO_DOMAIN.md`'s own axis (domain
  customization), not this phase's identity-parameterization axis. Carried
  into the skeleton unchanged, exactly as they exist in the source repo,
  since a new implementer edits them directly per `TODO_DOMAIN.md`'s
  existing instructions.
- **`tools/trace-check/`, `tests/test_trace_check.py`, the Makefile's
  `trace` target** — found by F3's own execution-based verification
  (`DEC-090`), not by static review: `tests/test_trace_check.py::
  test_real_srs_documents_parse_without_error_and_match_known_counts`
  reads real files under `srs/`, which was already excluded above. This
  tool validates *this project's own* SyRS→StRS→SRS traceability
  methodology, not the running agent's behavior — a scaffolded child
  project isn't assumed to adopt that same formal-requirements discipline,
  so the whole directory (not just the one failing test) is excluded,
  consistent with `srs/`'s own exclusion. A handful of prose mentions of
  `trace-check` survive in `eval/THRESHOLDS.md`/`eval/README.md` — cosmetic
  documentation references only, not a functional dependency, left as a
  known minor rough edge rather than scrubbed.
