# `deploy/`

This project's Kubernetes/OpenShift deployment manifests, split three
ways: `kustomize/base/` (one set of `Deployment`/`Service`/
`ServiceAccount`/`NetworkPolicy`/etc. per component — agent, mcp,
approval — pinned by image digest) and `kustomize/overlays/*/`
(per-environment config only: `demo-prod`, `ephemeral-test`, `staging`,
`pilot-prod`, `rhdh`, `approval-platform` — never a different image);
`argocd/` (the `Application`/`AppProject` objects the app-of-apps root
syncs, plus stub `Application`s for not-yet-activated environments); and
`otel/` (the local OTel Collector config `scripts/dev.sh` mounts).

**Consumed by**: `kubectl kustomize`/`oc apply -k` (a human operator or
`pipelines/tasks/deploy-ephemeral.yaml`), and ArgoCD (`argocd/`, synced
from the app-of-apps root).

See the [documentation hub](../docs/README.md) and
[`docs/environments.md`](../docs/environments.md) for the promotion model
and ownership split between pipeline-managed and ArgoCD-managed
environments.
