# ADR-021: Scaffolding and Gitea Publish

## Context
The scaffolder turns a rendered project skeleton into real repositories on
the platform's Gitea instance. Its Definition of Done is local rendering
only; actually publishing is a stretch goal requiring separate sign-off, and
fleet-wide rollout is out of scope. Two implementation approaches exist: a
portal wizard built as a custom RHDH dynamic plugin, and a CLI that talks to
Gitea's REST API directly.

## Decision
Publish ships as two independently complete, adopter-facing paths, not a
primary path with a fallback: a CLI (`tools/instantiate_agent_project.py`
plus `tools/gitea_publish.py`) that renders and publishes via Gitea's REST
API, and a Scaffolder `template.yaml` wired to a Gitea dynamic plugin that
runs the same publish through the RHDH portal wizard. Both paths produce the
same two-repository split: `deploy/` (kustomize, argocd, otel) goes to a
`<name>-gitops` repository, everything else to a `<name>` source repository.

## Consequences
- Adopters get a working publish path without building RHDH plugin
  infrastructure, and portal users are not limited to CLI-only.
- The two-repo split is binding: any change to what belongs in which repo
  must be applied to both paths' publish logic to keep output equivalent.
- Publish credentials are scoped, non-admin machine-account tokens injected
  via environment/secret — never a literal value in Git, never a CLI flag.
- The published GitOps repo's `argocd/*.yaml` and the promotion-PR pipeline
  task still assume a GitHub-hosted source repo; making that content
  Gitea-aware is a known, separately-scoped follow-up, not covered here.
- Both paths stay local-render/publish-only per the Definition of Done;
  opening a promotion PR or any fleet onboarding automation is out of scope
  absent separate approval.

## Supersedes / Superseded-by
None. Both paths are additive, delivered options — the CLI path was not
retired once the portal-wizard path landed.

## Journal
DEC-110, DEC-111, DEC-123, DEC-087 (item 4 only)
