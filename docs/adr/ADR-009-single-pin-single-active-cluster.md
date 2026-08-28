# ADR-009: Single Pin, Single Active Cluster

## Context
The blueprint's promotion pipeline pins exactly one image digest in the
shared base manifests, and any cluster can bootstrap the same GitOps repo.
A second, independent cluster running its own pipeline with promotion
authority over that same pin could silently overwrite the digest a first
cluster's live environment depends on — a "break a working system" path
gated only by human PR review, not anything structural.

## Decision
One Git repository <-> one active cluster; `bootstrap.sh --reenable-sync`
is only relevant if you deliberately run two. The single active cluster
owns the shared pin and its pipeline promotes normally; any other cluster
bootstrapped from this repository keeps its own dev/pipeline inner loop
but is deliberately deprotected from GitOps auto-sync of the app-of-apps
root, live-only and never committed to Git, so it cannot be silently
drift-corrected back into contention for the pin.

## Consequences
- Switching the active cluster is a live-only operation (disabling or
  restoring a root Application's auto-sync), never a Git change: bootstrap
  skips re-applying the root manifest unless `--reenable-sync` is passed.
- Deprotecting a cluster's root Application stops GitOps sync for
  everything under its app-of-apps directory — directory-wide, not
  object-scoped.
- Only one cluster's promoted environment can be current at a time;
  adopters must not run two clusters' pipelines with promotion authority
  over the same shared pin simultaneously.
- Per-cluster overlay pins and parametrized promotion remain documented
  as the evolution path if two live clusters are ever needed again.

## Supersedes / Superseded-by
Supersedes an earlier three-part follow-up (hosted-registry migration,
per-cluster overlay pins, parametrized promotion), moot once the
two-active-clusters scenario it was designed for no longer exists.

## Journal
DEC-083, DEC-084, DEC-078
