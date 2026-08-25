# Golden-Path Agent Template

A use-case-independent scaffold for the "deliberately constrained agent"
pattern described in `../Agentic_AI_Platform_MVP_Agnostic.md`: one LangGraph
agent, one MCP tool contract, a human-approval gate, an evaluation harness
wired as a CI promotion gate, and environment-promoted Kubernetes packaging.

This template intentionally ships **without** a knowledge corpus, domain
prompts, or real domain tools — those are the pieces every future use case
supplies. See [`TODO_DOMAIN.md`](TODO_DOMAIN.md) for the exact list of what
to fill in.

## Quickstart

```sh
cp .env.example .env
make up-offline      # fake model client + mock MCP tool, no network required
make eval-fast        # offline harness-mechanics smoke pair (EXAMPLE-001/002)
make test
```

For a live model endpoint, edit `.env` (`MODEL_API_BASE_URL`, `MODEL_NAME`)
and run `make up` instead. Once live, `make eval` is the real promotion
gate: `eval-fast`'s offline pair plus all 8 domain categories (62 cases)
against the real model, scored under a deterministic-sampling gate
contract (`DECISIONS.md` `DEC-017`) — domain categories need a live model
to be meaningful, since the fake client doesn't simulate real reasoning,
tool selection, or citation.

## Layout

- `agent/` — LangGraph agent shell (retrieve → reason → tool_invoke →
  human_approval → respond, with a deterministic fallback path)
- `mcp_server/` — MCP tool server contract stub (one placeholder tool).
  Named `mcp_server`, not `mcp` — a directory literally named `mcp` would
  shadow the installed `mcp` SDK package.
- `eval/` — evaluation harness + CI promotion gate
  (`python -m eval.cli run --all`)
- `policy/` — baseline policy + approval rule bundles
- `corpus/` — RAG corpus template (empty — TODO(domain))
- `deploy/` — Kustomize base + overlays, ArgoCD Applications
- `ci/` — pull-request check pipeline

See `docs/` for architecture, environments, security/identity, and
evaluation detail.

## Provenance

This scaffold is original work, informed by structural patterns observed in
prior internal engagements (agent orchestration shape, container/GitOps
packaging conventions, evaluation-harness design). No client code, secrets,
configuration values, or literal file contents from any other engagement
were copied into this repository — see the reuse-map artifact referenced
from the parent workspace for what those patterns were and how they were
adapted. This note exists so whoever inherits this repo has a clear record
of its origin.
