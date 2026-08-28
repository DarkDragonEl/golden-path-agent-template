# ADR-013: Gitea as the Platform Foundation Git Provider

## Context
Scaffolded agent projects need a Git host that the Platform Foundation
controls directly, so that blueprint mirroring, org/team/token provisioning,
and scaffolded-project publishing don't depend on an external, out-of-cluster
Git service.

## Decision
An in-cluster Gitea instance (via `rhpds/gitea-operator`, pinned `v2.3.2`) is
adopted as the Platform Foundation's Git-hosting component. It is one shared
instance for the whole platform, not one per agent project. Scaffolded
projects target this Gitea instance exclusively — GitHub is this blueprint
repository's own public upstream only, never a legitimate scaffolded-child
target.

## Consequences
- Every scaffolded project's rendered GitOps and promotion content (ArgoCD
  `Application.repoURL`/`sourceRepos`, `open-promotion-pr` tooling, pipeline
  `repo-url` defaults) must resolve against the Gitea host, not a
  hardcoded GitHub reference; any hardcoded GitHub reference in scaffolded
  output is a bug, not an acceptable dual-support path.
- Path references in rendered manifests must match the actual on-disk
  repository layout after any repo-split (e.g. a `deploy/` prefix that only
  applies to a single-repo layout must be dropped for a split-repo target).
- Gitea's own OLM install path may not resolve on a given cluster (a shared
  resolver-cache class of failure, not fixed unilaterally); the accepted
  fallback is upstream kustomize install with RBAC narrowed from a
  cluster-wide `ClusterRoleBinding` to a namespace-scoped `RoleBinding`.
- The Gitea instance's admin credential must be provisioned via a Secret,
  never committed as plaintext.
- Adopters relying on RHDH template/catalog loading directly from Gitea
  should note that first-class `GiteaIntegration` wiring is required — a
  GitHub-integration-pointed-at-Gitea workaround does not register content.

## Supersedes / Superseded-by
None.

## Journal
DEC-098, DEC-100, DEC-112
