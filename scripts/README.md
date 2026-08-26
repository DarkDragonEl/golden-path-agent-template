# `scripts/`

Two operator-facing entry points: `dev.sh` (the local dev loop —
`make up`/`make up-offline`/`make down`/`make logs` all shell out to
this; builds and runs all three images plus a local OTel Collector, no
compose tool required) and `bootstrap.sh` (`make bootstrap` — replays the
from-scratch cluster bootstrap sequence: operators, namespaces, RBAC,
Keycloak, cluster-tier OTel, the ArgoCD app-of-apps root, against any
already-authenticated OpenShift cluster).

**Consumed by**: a human developer (`dev.sh`, laptop-only, no cluster) and
a human operator with cluster access (`bootstrap.sh` — never run by CI;
see `docs/phase-c-runbook.md` for the manual steps it pauses for).

See the [documentation hub](../docs/README.md),
[`docs/local-dev.md`](../docs/local-dev.md) for `dev.sh`'s full topology,
and [`docs/architecture.md`](../docs/architecture.md) for the three
images it orchestrates.
