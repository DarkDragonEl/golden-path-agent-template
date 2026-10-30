# RHDH CI/CD visibility plugins

How the golden-path agent's RHDH component page shows its workloads,
its pipelines and (once enabled) its Argo CD deployment. The decision
record is `DECISIONS.md` `DEC-141`; this page is the operator's view.

## What is enabled, and what is only staged

RHDH 1.10.3 is the pinned operand (`PINS.md`, Phase F). Only plugins
that ship **inside the image** (`/opt/app-root/src/dynamic-plugins/dist/`)
are enabled. Tekton and Argo CD are not in the image in any 1.10.x
release; they are published only as OCI artifacts on `ghcr.io`, so they
are staged `disabled: true` instead.

| Plugin | Package | Version | 1.10 support level | State |
|---|---|---|---|---|
| Kubernetes backend | `./dynamic-plugins/dist/backstage-plugin-kubernetes-backend-dynamic` | 0.21.2 | GA | **enabled** |
| Kubernetes (frontend) | `./dynamic-plugins/dist/backstage-plugin-kubernetes` | 0.12.17 | Technology Preview | **enabled** |
| Topology | `./dynamic-plugins/dist/backstage-community-plugin-topology` | 2.12.4 | GA | **enabled** |
| Tekton | `oci://ghcr.io/…/backstage-community-plugin-tekton:{{inherit}}` | 3.37.0 | Community | staged, disabled |
| Argo CD backend (Community) | `oci://ghcr.io/…/backstage-community-plugin-argocd-backend@sha256:de3a311d…` | 1.4.0 | Community | staged, disabled |
| Argo CD (Community) | `oci://ghcr.io/…/backstage-community-plugin-argocd@sha256:4c922b0b…` | 2.8.1 | Community | staged, disabled |

What the enabled set gives the component page today:

- **Kubernetes tab**: the agent and MCP Deployments, their ReplicaSets
  and Pods, and their Services, in every namespace that carries them.
- **Topology tab**: the same workloads as a graph, the agent's Route
  (from its Ingress) as a link decorator, and the latest PipelineRun
  status as a node decorator. This is CI visibility from preinstalled
  plugins only; the decorator pairs a Deployment with the Pipeline that
  carries the same `app.kubernetes.io/instance` label.
- **CI and CD tabs**: not shown until Tekton and Argo CD are enabled
  (see [Enabling Tekton and Argo CD](#enabling-tekton-and-argo-cd)).

**Argo CD family: Community, not Roadie** (`DEC-141`). It's the pairing
Red Hat's 1.10 docs recommend. Both of its halves carry a Red Hat
community-support entry in the 1.10 plugin reference, while the Roadie
frontend has none. Mixing the two families is unsupported, so only the
Community entries are staged.

### How "preinstalled" was established

`reports/rhdh-plugin-inventory.md` was not present in either repository
when this was written, so the image's plugin set was reconstructed from
three primary sources that agree with each other:

1. The RHDH 1.10 *Dynamic plugins reference* (docs.redhat.com) lists 41
   `./dynamic-plugins/dist/` paths. Tekton and both Argo CD families
   appear only as `oci://ghcr.io/...` paths.
2. The `redhat-developer/rhdh` source at tag `1.10.3` (and `1.10.6`,
   `release-1.10`) has exactly **42** `dynamic-plugins/wrappers/`
   packages, the same count `DEC-110` found live in the pod's `dist/`
   directory. None is Tekton or Argo CD.
3. The 1.10 catalog index image (`quay.io/rhdh/plugin-catalog-index:1.10`,
   which supplies `dynamic-plugins.default.yaml`) lists 41 `dist`
   entries plus 16 OCI entries. Tekton (digest `sha256:a26ed788…`) and
   Roadie Argo CD are among the 16 OCI ones. This is why
   `dynamic-plugins.default.yaml` alone can make Tekton and Argo CD
   look installed: they are listed there, but as disabled, remote
   artifacts.

## Identity and RBAC

The RHDH Operator runs the Backstage pod with
`automountServiceAccountToken: false`, so the Kubernetes plugin needs an
explicit identity:

- `platform/bootstrap/rhdh-kubernetes-rbac.yaml` declares a ServiceAccount
  `golden-path-agent-rhdh-kubernetes`, its `kubernetes.io/service-account-token`
  Secret `golden-path-agent-rhdh-kubernetes-token`, a ClusterRole
  `golden-path-agent-rhdh-read-only` and the ClusterRoleBinding between them.
- The ClusterRole is read-only (`get`/`list`) on exactly: `pods`,
  `services`, `deployments`, `replicasets`, `routes`, `pipelines`,
  `pipelineruns`, `taskruns`. There's no `pods/log`, no Secrets or
  ConfigMaps, and no write verbs.
  `deploy/kustomize/overlays/rhdh/cicd-app-config.yaml` fetches exactly
  these kinds (`objectTypes` + `customResources`), so the plugin never
  asks for something it can't read.
- The binding is cluster-wide because the plugin selects by label
  across namespaces: PipelineRuns live in `golden-path-agent-ci`,
  workloads in `golden-path-agent-demo-prod` and
  `golden-path-agent-ephemeral-test`. A namespaced RoleBinding can't
  serve a cluster-wide list.
- The file is applied by `scripts/bootstrap.sh --with-rhdh` (step 4b),
  not by ArgoCD. The `golden-path-agent` AppProject whitelists no
  cluster-scoped kinds, and that stays true.
- The Backstage CR mounts the token Secret at
  `/opt/app-root/src/kubernetes-sa/` (backend container only), and the
  app-config reads `token` and `ca.crt` from there by path (`$file`,
  `caFile`). TLS is verified (`skipTLSVerify: false`). No token value
  ever passes through Git, an env var, or a human.

## The label and annotation contract

Anything labeled `backstage.io/kubernetes-id: <component>` shows up on
that component's page. For the blueprint itself, `<component>` is
`golden-path-agent`.

| Where | What | Why |
|---|---|---|
| `catalog-info.yaml` | `backstage.io/kubernetes-id`, `janus-idp.io/tekton`, `argocd/app-name: golden-path-agent-demo-prod` | Kubernetes/Topology selection; staged Tekton and Argo CD plugins |
| `deploy/kustomize/base/deployment-{agent,mcp}.yaml` | `backstage.io/kubernetes-id` on metadata **and** pod template; `app.kubernetes.io/instance` on metadata | Selection; Topology's PipelineRun decorator. Not in the selector (immutable). |
| `deploy/kustomize/base/service-{agent,mcp}.yaml`, `ingress.yaml` | `backstage.io/kubernetes-id`; Ingress also `router.openshift.io/reconcile-labels: "true"` | Topology resolves Route → Service → workload. OpenShift copies Ingress labels to the generated Route. |
| `pipelines/pipeline-*.yaml` | `backstage.io/kubernetes-id`, `app.kubernetes.io/instance` (same value as the matching Deployment) | Topology decorator |
| `pipelines/pipelinerun-template-*.yaml` | `backstage.io/kubernetes-id` | Tekton copies it onto TaskRuns and pods |

`skeleton/` carries the same annotations and labels with
`${{ values.name }}`, so every new agent scaffolded from the Agent
Template gets the same page. The Tools Template (`skeleton-tools/`) isn't
covered yet.

## Secrets the local session must create

**None for what is enabled.** `golden-path-agent-rhdh-kubernetes-token`
is created by `oc apply` of `platform/bootstrap/rhdh-kubernetes-rbac.yaml`.
The cluster's token controller fills in `token` and `ca.crt`, and no
value is ever supplied.

**Only when enabling Argo CD:** `golden-path-agent-rhdh-argocd-secret` in
namespace `golden-path-agent-rhdh`, with keys:

- `ARGOCD_INSTANCE1_URL`: the `openshift-gitops` server URL RHDH can
  reach (kept out of Git, like `PUBLIC_URL`).
- `ARGOCD_AUTH_TOKEN`: an API token for a read-only Argo CD account.

The Backstage CR does **not** reference this Secret yet. Referencing it
before it exists would stop the RHDH pod from starting.

## Live steps (local session)

Every `oc` call pins an explicit context (`ADR-010`/`DEC-086`). Run them
from a checkout of this branch, as cluster-admin.

1. **Apply the identity and RBAC.**
   `oc --context="$CTX" apply -f platform/bootstrap/rhdh-kubernetes-rbac.yaml`.
   Expect `created` for the serviceaccount, secret, clusterrole and
   clusterrolebinding.
2. **Check the token was issued (without printing it).**
   `oc --context="$CTX" get secret golden-path-agent-rhdh-kubernetes-token -n golden-path-agent-rhdh -o jsonpath='{.data.token}' | wc -c`.
   Expect a number well above 0. Run the same for `{.data.ca\.crt}`.
3. **Check the grant is exactly read-only.** Run
   `oc --context="$CTX" auth can-i <verb> <resource> -A --as=system:serviceaccount:golden-path-agent-rhdh:golden-path-agent-rhdh-kubernetes`:
   - `list pipelineruns.tekton.dev`, `list deployments.apps`, and
     `list routes.route.openshift.io` should each say **yes**.
   - `list secrets`, `get pods --subresource=log` and
     `delete deployments.apps` should each say **no**.
4. **Re-apply the Pipelines** (bootstrap-managed, not ArgoCD):
   `oc --context="$CTX" apply -f pipelines/pipeline-agent.yaml -f pipelines/pipeline-mcp.yaml -f pipelines/pipeline-approval.yaml -n golden-path-agent-ci`.
   Expect `configured`. Only labels change.
5. **Merge `feat/rhdh-cicd-plugins` (owner's call).** ArgoCD then syncs:
   - `golden-path-agent-demo-prod`: Deployment/Service/Ingress labels.
     The pod-template label rolls the agent and MCP pods once.
   - `golden-path-agent-rhdh`: the new `golden-path-agent-rhdh-cicd-config`
     ConfigMap, the dynamic-plugins ConfigMap and the CR. The RHDH pod
     restarts.

   If a target cluster has that Application's auto-sync disabled (the
   SNO's `DEC-083` freeze), sync it explicitly or leave it for refresh #2.
6. **Check plugin loading.** In the RHDH pod's `install-dynamic-plugins`
   init-container log, expect the three enabled packages installed and
   `Skipping disabled dynamic plugin` for Tekton and both Argo CD
   entries. Then
   `oc --context="$CTX" logs deploy/backstage-golden-path-agent -n golden-path-agent-rhdh -c backstage-backend | grep -i kubernetes`
   should show no `401`/`403`/TLS errors.
7. **Create one labeled PipelineRun** (runs from before this change
   carry no label):
   `oc --context="$CTX" create -f pipelines/pipelinerun-template-agent.yaml -n golden-path-agent-ci`.
8. **Verify in a real browser** (`DEC-094`/`DEC-097`: a scripted call
   isn't evidence of what a browser shows). On the `golden-path-agent`
   component:
   - The **Kubernetes** tab lists the agent and MCP Deployments and Pods.
   - The **Topology** tab shows both nodes, the agent's Route decorator,
     and a PipelineRun decorator on the agent node once step 7's run
     exists.
   - No CI or CD tab yet.
9. **Rollback**, if needed: revert the merge commit, then
   `oc --context="$CTX" delete -f platform/bootstrap/rhdh-kubernetes-rbac.yaml`.

On a fresh cluster (refresh #2), `scripts/bootstrap.sh --with-rhdh`
performs step 1 itself, before the GitOps sync of the RHDH overlay.
Step 7 is also covered by step 9b's PipelineRun.

## Enabling Tekton and Argo CD

This is an owner decision (`DEC-141`): it means pulling plugin code
from outside the image at pod start.

**Tekton.** Set `disabled: false` on the Tekton entry in
`deploy/kustomize/overlays/rhdh/dynamic-plugins-config.yaml`. The RHDH
pod's init container must be able to reach `ghcr.io`. If it can't,
mirror the artifact into the internal registry and repoint the
package, the same way `DEC-118` did for the Gitea module:
`skopeo copy docker://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-community-plugin-tekton@sha256:a26ed788824fbd29e65b02f956dad8f35275a8ccd1110b23fc17957104d38a01 docker://image-registry.openshift-image-registry.svc:5000/golden-path-agent-rhdh/backstage-community-plugin-tekton`.
No new RBAC is needed. The log viewer additionally needs `pods/log`
(see Known limits).

**Argo CD (Community).** Three steps:

1. Create a read-only Argo CD account with an API token on the
   `openshift-gitops` instance: `accounts.rhdh: apiKey` in the ArgoCD
   CR's `extraConfig`, and `g, rhdh, role:readonly` in its RBAC policy.
   Then generate the token. On the owner's SNO that CR belongs to the
   owner's cluster-ops repository (`DEC-135`), so the change belongs
   there, not in a live patch.
2. Create `golden-path-agent-rhdh-argocd-secret` (keys above) and add
   it to `backstage.yaml` → `spec.application.extraEnvs.secrets`.
3. Set `disabled: false` on both Argo CD entries.

The CD tab then shows `golden-path-agent-demo-prod`, via the
`argocd/app-name` annotation.

## Known limits

- **No pod logs.** `pods/log` isn't granted, so Topology's and Tekton's
  log views show a permission error. If logs are wanted, add `pods/log`
  to the ClusterRole. Note that any signed-in RHDH user could then read
  agent logs, since no RBAC plugin is enabled.
- **The Topology decorator depends on `app.kubernetes.io/instance`.** If
  a cluster's Argo CD tracks resources by label with that key, it
  overwrites the label and the decorator silently disappears. The
  owner's SNO tracks by annotation (`DEC-135`). To check:
  `oc --context="$CTX" get deploy golden-path-agent -n golden-path-agent-demo-prod -o jsonpath='{.metadata.labels.app\.kubernetes\.io/instance}'`
  should print `golden-path-agent`.
- **Selection is cluster-wide.** `ephemeral-test` copies appear while a
  PipelineRun's deploy step has them up.
- **Route decorator depends on the Ingress being admitted.** The agent's
  Route exists only if something admits its Ingress. On the owner's SNO
  nothing does (no `ingressClassName`, no default `IngressClass`:
  `DEC-139`'s open finding), so no Route decorator appears there until
  that's fixed.
- **Not covered yet:** the approval service's own Component
  (`golden-path-agent-approval-service`) and the Tools Template.
