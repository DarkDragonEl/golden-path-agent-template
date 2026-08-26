# `platform/`

The shared Platform Foundation's own bootstrap and catalog content —
infrastructure every Agent Template instance deploys onto, but that
isn't itself one of the three promoted artifacts. `bootstrap/` holds the
one-time, human-applied manifests and scripts for Gitea, Keycloak
(operator, CR, Postgres, realm import), the cluster-tier OTel Collector,
RHDH's operator, and `provision-identity-secrets.sh` (credential
provisioning/rotation, see `docs/access-and-credentials.md`). `catalog/`
holds this project's Backstage/RHDH catalog entities (`system.yaml`,
`approval-service.yaml`, `model-routes.yaml`).

**Consumed by**: a human operator with cluster access (`bootstrap/`,
applied manually per `docs/phase-d-runbook.md` — never by the Tekton
pipeline, which has no cluster-scoped permissions), and RHDH itself
(`catalog/`, registered via `catalog-info.yaml`).

See the [documentation hub](../docs/README.md),
[`docs/architecture.md`](../docs/architecture.md) for where the Platform
Foundation sits relative to the three artifacts,
[`docs/naming-conventions.md`](../docs/naming-conventions.md) for the
namespace/secret names these manifests declare, and
[`docs/access-and-credentials.md`](../docs/access-and-credentials.md)
for the credential-provisioning script here.
