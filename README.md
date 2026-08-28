# Golden-Path Agent Template

## What this is

This repository is the golden path for a deliberately constrained
agentic-AI pattern: one LangGraph agent, gated behind a single MCP
(Model Context Protocol) tool contract, with a human-approval gate on
every write and an evaluation harness wired in as a CI promotion gate. Nothing here is a
general-purpose agent framework — every capability is a fixed, minimal
slice chosen to prove the pattern end to end, not to be feature-complete.
The pattern is realized as three independently built, independently
promoted OCI images — the agent, the MCP tool server, and the approval
service — plus a shared Platform Foundation (identity, telemetry, Gitea,
the Internal Developer Portal, and the GitOps machinery) that all three
deploy onto but that isn't itself one of the three artifacts. Each image
is built exactly once in CI and promoted unchanged from an ephemeral test
environment to demo-prod (the one-immutable-artifact rule) — every
environment difference lives only in config, secrets, policy bundles, and
bindings, never in the image itself.

This template intentionally ships **without** a knowledge corpus, domain
prompts, or real domain tools — those are the pieces every future use
case supplies. See [`TODO_DOMAIN.md`](TODO_DOMAIN.md) for the exact list
of what to fill in.

## Architecture at a glance

```mermaid
flowchart TB
    subgraph CI["CI: build and promotion gate"]
        direction LR
        BUILD["Build 3 images:<br/>agent / MCP tool server / approval service"]
        DEPLOY["Deploy to ephemeral test"]
        GATE["Eval harness<br/>(promotion gate, incl. the bad-change gate)"]
        BUILD --> DEPLOY --> GATE
    end

    GATE -->|pass| PROMOTE["Promotion PR<br/>(bumps the pinned digest)"]
    GATE -->|fail| BLOCKED["Blocked<br/>(fail-closed)"]
    PROMOTE -->|merge| GITOPS["GitOps sync<br/>(one-immutable-artifact:<br/>same image, promoted unchanged)"]
    GITOPS --> DEMOPROD["demo-prod"]

    subgraph GOLDEN["Golden path — runs in both ephemeral test and demo-prod"]
        direction LR
        AGENT["Agent<br/>(LangGraph)"]
        APPROVAL["Approval service"]
        MCP["MCP tool server"]
        AGENT -->|draft write| APPROVAL
        APPROVAL -->|human approve / reject| AGENT
        AGENT -->|approved write only| MCP
    end

    DEPLOY -.exercises.-> GOLDEN
    DEMOPROD -.runs.-> GOLDEN

    subgraph FOUNDATION["Platform Foundation"]
        direction LR
        IDENTITY["Identity (OIDC)"]
        TELEMETRY["Telemetry (OpenTelemetry)"]
        GITEA["Gitea"]
        RHDH["Internal Developer Portal (RHDH)"]
        ARGOCD["GitOps machinery (ArgoCD)"]
    end

    GOLDEN -.deploys onto.-> FOUNDATION
```

## Repo map

### The blueprint

The agent, its one tool, its approval gate, and everything that builds,
tests, deploys, and evaluates them.

| Path | What it is |
|---|---|
| [`agent/`](agent/) | The LangGraph agent: `decide` → `retrieve`/`tool_invoke` → `human_approval` → `respond`, with a deterministic fallback path. |
| [`mcp_server/`](mcp_server/) | The one MCP tool contract — a mock ITSM tool with persistent state. |
| [`approval_service/`](approval_service/) | The human-approval gate: a human approver explicitly approves or rejects every write before it executes. Independently built and promoted since Phase D, same as the agent and the MCP tool server. |
| [`deploy/`](deploy/) | Kustomize base + overlays and ArgoCD `Application` manifests for the ephemeral test and demo-prod environments. |
| [`pipelines/`](pipelines/) | Tekton `Pipeline`/`Task` definitions for each of the three components' independent build → test → promote pipeline. |
| [`platform/`](platform/) | Platform Foundation bootstrap manifests and scripts — identity (Keycloak), Gitea, the Internal Developer Portal (RHDH), and the cluster-tier OpenTelemetry collector. |
| [`policy/`](policy/) | Baseline policy and approval-rule bundles the agent and approval service load at runtime. |
| [`eval/`](eval/) | The evaluation harness — the CI promotion gate (`python -m eval.cli run --all`) plus the domain eval-case set. |
| [`corpus/`](corpus/) | The synthetic RAG corpus the agent retrieves against. |
| [`docs/`](docs/) | Deeper architecture, environment, and operational reference — see [Docs index](#docs-index) below. |
| [`scripts/`](scripts/) | Operator-facing entry points: the local dev loop (`dev.sh`) and the fresh-cluster install sequence (`bootstrap.sh`, `install.sh`). |
| [`tools/`](tools/) | One-off operator and diagnostic scripts (trace queries, skeleton verification, Gitea publish, credential helpers). |
| [`skeleton/`](skeleton/) | The single-service scaffolding template a new agent project is instantiated from. |
| [`skeleton-tools/`](skeleton-tools/) | The single-tool-server scaffolding template a new MCP tool project is instantiated from. |
| [`ci/`](ci/) | The pull-request check pipeline definition (`pr-checks.yaml`): unit tests, the offline eval gate, container build, SBOM. |
| [`tests/`](tests/) | Unit and integration tests for the agent, MCP tool server, and approval service. |

`state/` is created at runtime (git-ignored) for the approval service's
local SQLite store — it doesn't exist in a fresh clone and has no
tracked content to link to.

### Decisions and history

ADRs live in `docs/adr/`. The full engineering journal — decision log,
handoffs, per-task reports — lives in the sibling `agent-roadmap`
repository. `PINS.md` and `srs/` remain here.

### Other root files

Build and packaging plumbing that doesn't belong to either group above.

| Path | What it is |
|---|---|
| [`Makefile`](Makefile) | Every make target used in this README (`up-offline`, `eval-fast`, `test`, `up`, `eval`, `bootstrap`, ...). |
| [`Containerfile.agent`](Containerfile.agent), [`Containerfile.mcp`](Containerfile.mcp), [`Containerfile.approval`](Containerfile.approval) | The three independent image build definitions, one per artifact. |
| [`entrypoint-agent.sh`](entrypoint-agent.sh), [`entrypoint-mcp.sh`](entrypoint-mcp.sh), [`entrypoint-approval.sh`](entrypoint-approval.sh) | Each image's container entrypoint. |
| [`requirements.txt`](requirements.txt), [`requirements-agent.txt`](requirements-agent.txt), [`requirements-mcp.txt`](requirements-mcp.txt), [`requirements-approval.txt`](requirements-approval.txt), [`requirements-dev.txt`](requirements-dev.txt) | Pinned Python dependencies, split per component plus a dev set. |
| [`template.yaml`](template.yaml), [`template-schema.json`](template-schema.json), [`template-tools.yaml`](template-tools.yaml), [`template-schema-tools.json`](template-schema-tools.json) | Backstage/RHDH software-template definitions used to scaffold a new agent project (from `skeleton/`) or tool project (from `skeleton-tools/`) out of this blueprint. |
| [`catalog-info.yaml`](catalog-info.yaml) | This repo's own Backstage/RHDH catalog entry. |
| [`.env.example`](.env.example) | The local-dev environment template Quickstart A copies from. |
| [`pyproject.toml`](pyproject.toml) | Shared Python project metadata/tooling config. |
| [`TODO_DOMAIN.md`](TODO_DOMAIN.md) | The exact list of domain-specific pieces (corpus, prompts, tools) a real use case must supply. |
| [`SHOWCASE_NOTES.md`](SHOWCASE_NOTES.md) | Operator notes for running a live demo on the showcase cluster. |

## Quickstart A — laptop (no cluster, no network)

Requires a container engine (`podman` or `docker`) and Python 3. Nothing
here talks to a real model or a real cluster.

```sh
cp .env.example .env
make up-offline      # fake model client + mock MCP tool, no network required
make eval-fast        # offline harness-mechanics smoke pair (EXAMPLE-001/002)
make test             # unit + integration test suite
make down              # tear down the three dev containers
```

Verified against this repo's actual `Makefile`: `make test` passes
(253 passed, 1 skipped), `make eval-fast` passes (`2/2 cases passed`),
and `make up-offline` brings up all three containers and answers a real
HTTP request end to end — see
[`reports/feature-h1-readme-rewrite.md`](reports/feature-h1-readme-rewrite.md)
for the full commands-and-output transcript.

**Live-model variant**: edit `.env` (`MODEL_API_BASE_URL`, `MODEL_NAME`,
`MODEL_API_KEY`, and the fallback route —
`MODEL_FALLBACK_API_BASE_URL`/`MODEL_FALLBACK_NAME`) and run `make up`
instead of `make up-offline`. Once live, `make eval` is the real promotion gate —
`eval-fast`'s offline pair plus the full domain eval-case set
(`eval-domain`) against the real model, scored under a
deterministic-sampling gate contract (see `DECISIONS.md` `DEC-017`).
The domain categories need a live model to be meaningful: the fake
client doesn't simulate real reasoning, tool selection, or citation.

## Quickstart B — fresh OpenShift cluster

**Prerequisites**: an already-authenticated kubeconfig (this path never
runs `oc login` for you — authenticate first, the same way you would for
any other `oc` command), a model-endpoint credential, and cluster-admin
on the target cluster.

**Primary path** — one command:

```sh
./scripts/install.sh <kubeconfig-path>
```

This runs `scripts/bootstrap.sh` — operators, namespaces, RBAC, identity,
telemetry, pipelines, the ArgoCD app-of-apps root, and (as one of its own
internal steps) `platform/bootstrap/provision-identity-secrets.sh`
(OIDC client secrets and demo-user passwords) — stopping immediately if
it exits non-zero. Pass `--yes` to skip the interactive confirmation
described in the warning box below (`bootstrap.sh` still runs either
way — `--yes` only removes the prompt, and only one script ever runs:
`install.sh` never calls the identity-secrets script a second time,
since `bootstrap.sh`'s own internal call is the one that actually
rotates credentials).

**Alternative** — run the two underlying scripts by hand:

```sh
./scripts/bootstrap.sh <kubeconfig-path>
./platform/bootstrap/provision-identity-secrets.sh
```

(`make bootstrap CLUSTER=<kubeconfig-path>` is equivalent to the first
line alone, without the second script.)

> **Before you run either path, read this:**
>
> 1. **Re-running the identity/secrets provisioning script rotates
>    credentials and invalidates live sessions.**
>    `platform/bootstrap/provision-identity-secrets.sh` regenerates the
>    OIDC client secrets and demo-user passwords on *every* run, by
>    design — there is no "only if missing" branch (`DECISIONS.md`
>    `DEC-059`). Safe on a fresh install; on an already-live cluster,
>    anyone currently signed in gets signed out.
> 2. **`scripts/bootstrap.sh`'s `--reenable-sync` flag exists because
>    auto-sync may be deliberately frozen on a cluster.** A cluster's
>    GitOps auto-sync can be intentionally disabled to make it the sole
>    active environment for a shared digest pin; a plain re-run of
>    `bootstrap.sh` detects that freeze and skips re-applying the
>    ArgoCD root `Application` rather than silently reversing it. Only
>    pass `--reenable-sync` if you deliberately intend to reverse that
>    specific cluster's freeze (`DECISIONS.md` `DEC-083`).
>    `scripts/install.sh` never passes this flag — that choice belongs
>    to the cluster operator, made explicitly, not to a one-button
>    wrapper.
>
> See [`docs/phase-c-runbook.md`](docs/phase-c-runbook.md) and
> [`docs/environments.md`](docs/environments.md) for the full runbook
> behind both scripts, including the manual steps `bootstrap.sh` pauses
> for.

## Docs index

Full index: **[`docs/README.md`](docs/README.md)** — every document under
`docs/` reachable in at most two clicks, organized
[Diátaxis](https://diataxis.fr/)-style. Start there for the complete map;
the four groups below are the fastest way in from here.

**Learn** — [`docs/README.md#tutorials`](docs/README.md#tutorials):
[`docs/architecture.md`](docs/architecture.md) (the agent's graph shape
and the three-image split), [`docs/owner-walkthrough.md`](docs/owner-walkthrough.md)
(a full live run, start to finish).

**Operate** — [`docs/README.md#how-to--runbooks`](docs/README.md#how-to--runbooks):
[`docs/local-dev.md`](docs/local-dev.md), [`docs/phase-c-runbook.md`](docs/phase-c-runbook.md)
(the manual steps behind Quickstart B), [`docs/access-and-credentials.md`](docs/access-and-credentials.md).

**Reference** — [`docs/README.md#reference`](docs/README.md#reference):
[`docs/environments.md`](docs/environments.md),
[`docs/glossary.md`](docs/glossary.md),
[`docs/naming-conventions.md`](docs/naming-conventions.md),
[`PINS.md`](PINS.md).

**Decisions**
- `docs/adr/` — architecture decision records for this blueprint's
  load-bearing design choices.
- The full decision log lives in the sibling `agent-roadmap` repository.

---

Provenance and reuse policy: see [`docs/provenance.md`](docs/provenance.md).
Decision history: the sibling `agent-roadmap` repository's `DECISIONS.md`
has the full history of every ambiguity, finding, and decision behind
this blueprint; `docs/adr/` here has the load-bearing design choices.
