# ADR-020: OTel Collector deployment

## Context
The platform needs cluster-tier trace collection for cross-service
correlation (agent, approval service) without a full tracing backend
for a demo-scope milestone, and without repeating the shared-cluster
operator-catalog friction identity infrastructure already hit once. The
upstream Collector image is fully distroless, blocking any in-pod
exec/copy read of its own file-exporter output.

## Decision
The OTel Collector runs as a plain `Deployment` in its own namespace,
not via an operator — a stateless forwarder needs no CRD-based
lifecycle management. It exports to both `debug` (live `oc logs`) and
`file` (JSON Lines to a shared `emptyDir`), with a small HTTP sidecar
serving that file's contents, since the distroless main container can't
be exec'd or copied from. The sidecar image is pinned to a stable,
generally-published base (currently a Red Hat UBI Python image) with no
relationship to this project's own CI/build/promotion lifecycle.

## Consequences
- No second operator install, and no dependency on the shared cluster's
  operator catalog for observability infrastructure.
- Trace data is queryable via a small script hitting the sidecar's HTTP
  port — sufficient for demo-scope verification, not a real backend.
- The sidecar's pin must never be an image tied to this project's own
  build lifecycle (e.g. its own CI `ImageStream`): such an image is
  pruned over time by design, silently breaking the sidecar with no
  relationship to any actual config change — this already happened
  once and is why the decoupling is explicit.
- No `NetworkPolicy` restricts ingress to the collector, matching this
  project's treatment of other shared platform infrastructure. Each
  workload must set its own explicit `OTEL_SERVICE_NAME`; an inherited
  default produces spans indistinguishable from another's.

## Supersedes / Superseded-by
None.

## Journal
DEC-068, DEC-119
