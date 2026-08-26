# Naming conventions

Normalizes the nomenclature census in `reports/docs-audit.md` into stated
conventions, with real examples read directly out of this repo's own
manifests — not idealized. Where the repo itself is inconsistent, that's
recorded plainly as a **known deviation**, not silently smoothed over.
See `docs/glossary.md` for term definitions and `DECISIONS.md` for the
decisions (`DEC-NNN`) that established these patterns.

## Namespaces

Pattern: `golden-path-agent-<purpose>`, one namespace per concern, all
declared in `pipelines/bootstrap/namespaces.yaml` or an overlay's own
`namespace.yaml`.

| Namespace | Purpose |
|---|---|
| `golden-path-agent-ci` | Tekton pipelines, PipelineRuns, the CI ServiceAccount |
| `golden-path-agent-ephemeral-test` | Pre-promotion validation, pipeline-managed |
| `golden-path-agent-demo-prod` | The demo milestone's promoted, always-on environment, ArgoCD-managed |
| `golden-path-agent-keycloak` | Identity (Keycloak CR, realm, Postgres) |
| `golden-path-agent-otel` | Cluster-tier OpenTelemetry Collector |
| `golden-path-agent-rhdh` | The Internal Developer Portal (RHDH) |
| `golden-path-agent-approval` | The shared approval service (Platform Foundation, `DEC-098`) |
| `golden-path-agent-gitea` | In-cluster Git hosting |

`golden-path-agent-staging` and `golden-path-agent-pilot-prod` are named
in stub overlays/`Application`s only — **not deployed this milestone**
(`docs/environments.md`).

## Secrets

Pattern: `golden-path-agent-<component>-<kind>`, or the shared
cross-component `golden-path-agent-secrets` for workload credentials
consumed via `envFrom`. Examples actually in the manifests:
`golden-path-agent-secrets` (per-namespace, `MODEL_API_KEY`,
`MCP_AUTH_TOKEN`, `APPROVAL_OIDC_CLIENT_SECRET`), `golden-path-agent-
keycloak-admin`, `golden-path-agent-keycloak-db-secret`,
`golden-path-agent-demo-users` (demo-user/demo-approver passwords,
`golden-path-agent-keycloak` namespace only), `golden-path-agent-rhdh-
oidc-secret`, `golden-path-agent-gitea-admin-password`, `golden-path-
agent-github-token` (the promotion PR's fine-grained PAT,
`golden-path-agent-ci` namespace only).

**Never a real value in Git** — `platform/bootstrap/provision-identity-
secrets.sh` generates/rotates all of these at runtime; see
`docs/access-and-credentials.md`.

## Image / registry naming

**Known deviation from a common assumption**: this project does **not**
declare OpenShift `ImageStream` objects anywhere (`kind: ImageStream`
does not appear in this repo). Images are referenced directly by
registry path + digest. Three image names, one per artifact (`DEC-098`/
`DEC-099`, the three-image split): `golden-path-agent`, `golden-path-
agent-mcp`, `golden-path-agent-approval`, built from `Containerfile.agent`
/ `.mcp` / `.approval` respectively and pulled from
`image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci/
<image-name>`. `deploy/kustomize/base/kustomization.yaml`'s `images:`
block is the single place all three digests are pinned; a promotion PR
only ever edits one entry's `digest:` line (see Branch conventions
below).

## Keycloak realm / clients / roles / users

One realm: `golden-path-agent` (`platform/bootstrap/keycloak-realm-
import.yaml`, `DEC-058`). Clients follow `golden-path-agent-<consumer>-
<kind>` where `<kind>` is `workload` (service-account, machine-to-machine)
or absent for a UI-facing client:

| Client | Shape |
|---|---|
| `golden-path-agent-approval-workload` | confidential, service account — agent → approval service |
| `golden-path-agent-mcp-workload` | confidential, service account — agent → MCP tool server |
| `golden-path-agent-approver-ui` | public, Authorization Code + PKCE — the human approver's browser |
| `golden-path-agent-rhdh` | confidential, Authorization Code — RHDH's own sign-in |

One realm role: `approval-approver`. Two demo users, `demo-approver`
(has the role) and `demo-user` (does not) — the "correct by omission"
negative test (`DEC-054`). See `docs/access-and-credentials.md` for how
their passwords are provisioned and reset.

## Tekton pipeline / task names

Pipelines: `golden-path-agent-ci-<component>` (`golden-path-agent-ci-
agent`, `-mcp`, `-approval`) — one per independently-promoted artifact.
Tasks are unprefixed, verb-first, shared across all three pipelines
where identical: `fetch-source`, `unit-tests`, `eval-gate-offline`,
`eval-gate-live`, `policy-validate`, `security-tests`, `sbom-generate`,
`deploy-ephemeral`, `operational-tests` (plus per-component variants
`mcp-operational-test`, `approval-operational-test`), `digest-capture`,
`open-promotion-pr`, `destroy-ephemeral`.

## Branch conventions

Real, observed conventions in this repo's own branch list — not all of
them were anticipated in earlier planning docs:

| Prefix | Meaning | Example |
|---|---|---|
| `feature/<phase>-<short-name>` | Normal delivery work, one phase/stream per branch (`CLAUDE.md`'s own required convention) | `feature/g2-three-image-split`, `feature/h2-docs-ia` |
| `fix/<short-name>` | A targeted correction, not a full phase | `fix/g2-bootstrap-initial-digests` |
| `test/<short-name>` | A deliberately seeded regression, proving the promotion gate's negative case (`CLAUDE.md`'s "fail closed... prove the negative case") | `test/g2-seeded-eval-failure` |
| `promote/<component>/<commit-sha>` | CI-opened only, never hand-created — one promotion PR's source branch (`pipelines/tasks/open-promotion-pr.yaml`) | `promote/mcp/<sha>` |

**Known deviation**: two remote branches predating the G2 three-image
split still exist as `promote/<commit-sha>` (no `<component>` segment) —
`promote/19a8876f913746985b59e829a40322a685f61a5f`,
`promote/fd141bb7a1f072825f69e32533239d6af98fa854`. The current
`open-promotion-pr` Task always includes `<component>`, added specifically
so three concurrent per-artifact promotions off one commit don't collide
on a single `promote/<sha>` branch name — the two old branches are
historical artifacts of the pre-split single-image pipeline, not evidence
of an inconsistent current convention. Neither has been cleaned up as of
this writing; that's a housekeeping item, not a documentation error.

## Eval case IDs

Two distinct ID schemes, deliberately not unified (`eval/README.md`
explains why): `EXAMPLE-NNN` (`EXAMPLE-001`, `EXAMPLE-002`) for the
harness-mechanics fixtures, and a category-prefixed scheme for the domain
suite — `KQA-*` (knowledge QA), `ITR-*` (read-only retrieval), `TSEL-*`
(tool selection), `DRQ-*` (draft request), `OOD-*` (out-of-domain),
`UAW-*` (unauthorized write), `INJ-*` (prompt injection), `OPS-*`
(operational) — each file under `eval/cases/domain/` holding exactly one
category. See `docs/evaluation.md` and `eval/THRESHOLDS.md`.

## `DEC-NNN` / `OI-NN` / requirement IDs

- **`DEC-NNN`** — sequential, append-only, never renumbered or rewritten,
  in `DECISIONS.md`. The single decision log (`docs/glossary.md`).
- **`OI-NN`** — an Open Item from `Annex_A_Open_Items_EN.md` (e.g. `OI-02`
  the ITSM scenario, `OI-04` template instantiation) — an adopted
  assumption, not a decision log entry.
- **Requirement IDs** — `SysR-P-*` (platform) / `SysR-A-*` (pilot agent)
  in `SyRS-AGP-001_EN.md`; `StR-*` in `StRS_Agentic_AI_Platform_EN.md`;
  `SRS-<AREA>-<KIND>-NN` (e.g. `SRS-APR-SEC-01`, `SRS-EVH-F-01`) in the
  per-area files under `srs/` (`SRS-AGT`, `SRS-APR`, `SRS-EVH`, `SRS-MIT`,
  `SRS-RET`). `tools/trace-check/` validates these three tiers trace to
  each other consistently.

## What this document does not cover

Python module/function naming, Rego policy naming, and YAML manifest
field ordering are ordinary language/tool conventions, not
project-specific decisions — not in scope here. Nothing in this document
authorizes renaming anything already committed; deviations are recorded,
not corrected, per this mission's own scope.
