# RHDH CI/CD visibility plugins

How the golden-path agent's RHDH component page shows its workloads,
its pipelines and its Argo CD deployment. The decision records are
`DECISIONS.md` `DEC-141` (C1: what the image ships), `DEC-143` (C2:
Tekton and Argo CD enabled from `ghcr.io`) and `DEC-144` (C2: the Argo CD
token); this page is the operator's view.

## What is enabled

RHDH 1.10.3 is the pinned operand (`PINS.md`, Phase F). Kubernetes and
Topology ship **inside the image** (`/opt/app-root/src/dynamic-plugins/dist/`).
Tekton and Argo CD are not in the image in any 1.10.x release; they are
OCI artifacts on `ghcr.io`, pulled by RHDH's `install-dynamic-plugins`
init container at pod start and pinned by digest (`DEC-143`).

| Plugin | Package | Version | 1.10 support level | State |
|---|---|---|---|---|
| Kubernetes backend | `./dynamic-plugins/dist/backstage-plugin-kubernetes-backend-dynamic` | 0.21.2 | GA | **enabled** |
| Kubernetes (frontend) | `./dynamic-plugins/dist/backstage-plugin-kubernetes` | 0.12.17 | Technology Preview | **enabled** |
| Topology | `./dynamic-plugins/dist/backstage-community-plugin-topology` | 2.12.4 | GA | **enabled** |
| Tekton | `oci://ghcr.io/…/backstage-community-plugin-tekton@sha256:a26ed788…` | 3.37.0 | Community | **enabled** (from `ghcr.io`) |
| Argo CD backend (Community) | `oci://ghcr.io/…/backstage-community-plugin-argocd-backend@sha256:de3a311d…` | 1.4.0 | Community | **enabled** (from `ghcr.io`) |
| Argo CD (Community) | `oci://ghcr.io/…/backstage-community-plugin-argocd@sha256:4c922b0b…` | 2.8.1 | Community | **enabled** (from `ghcr.io`) |

What the component page shows:

- **Kubernetes tab**: the agent and MCP Deployments, their ReplicaSets
  and Pods, and their Services, in every namespace that carries them.
- **Topology tab**: the same workloads as a graph, the agent's Route
  (from its Ingress) as a link decorator, and the latest PipelineRun
  status as a node decorator. This is CI visibility from preinstalled
  plugins only; the decorator pairs a Deployment with the Pipeline that
  carries the same `app.kubernetes.io/instance` label.
- **CI tab** (Tekton): every PipelineRun of this repo's three
  pipelines, with TaskRun status.
- **CD tab** and an overview card (Argo CD): the
  `golden-path-agent-demo-prod` Application's sync and health, history
  and the images it deployed (`argocd/app-name`).

**Argo CD family: Community, not Roadie** (`DEC-141`). It's the pairing
Red Hat's 1.10 docs recommend. Both of its halves carry a Red Hat
community-support entry in the 1.10 plugin reference, while the Roadie
frontend has none. Mixing the two families is unsupported, so only the
Community entries are enabled.

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
| `catalog-info.yaml` | `backstage.io/kubernetes-id`, `janus-idp.io/tekton`, `argocd/app-name: golden-path-agent-demo-prod` | Kubernetes/Topology selection; Tekton CI tab; Argo CD CD tab |
| `deploy/kustomize/base/deployment-{agent,mcp}.yaml` | `backstage.io/kubernetes-id` on metadata **and** pod template; `app.kubernetes.io/instance` on metadata | Selection; Topology's PipelineRun decorator. Not in the selector (immutable). |
| `deploy/kustomize/base/service-{agent,mcp}.yaml`, `ingress.yaml` | `backstage.io/kubernetes-id`; Ingress also `router.openshift.io/reconcile-labels: "true"` | Topology resolves Route → Service → workload. OpenShift copies Ingress labels to the generated Route. |
| `pipelines/pipeline-*.yaml` | `backstage.io/kubernetes-id`, `app.kubernetes.io/instance` (same value as the matching Deployment) | Topology decorator |
| `pipelines/pipelinerun-template-*.yaml` | `backstage.io/kubernetes-id` | Tekton copies it onto TaskRuns and pods |

`skeleton/` carries the same annotations and labels with
`${{ values.name }}`, so every new agent scaffolded from the Agent
Template gets the same page. The Tools Template (`skeleton-tools/`) isn't
covered yet.

## Secrets

**None is created by hand.** Every Secret RHDH reads is written by
`scripts/bootstrap.sh --with-rhdh`:

| Secret (namespace `golden-path-agent-rhdh`) | Written by | Holds |
|---|---|---|
| `golden-path-agent-rhdh-kubernetes-token` | step 4b, `platform/bootstrap/rhdh-kubernetes-rbac.yaml` | filled in by the cluster's token controller (`token`, `ca.crt`) |
| `golden-path-agent-rhdh-argocd-secret` | step 4d (`DEC-144`) | `ARGOCD_INSTANCE1_URL`, `ARGOCD_AUTH_TOKEN` of a read-only local Argo CD account bootstrap creates (`golden-path-agent-rhdh`, `role:readonly`) |

The Backstage CR references `golden-path-agent-rhdh-argocd-secret` only
because bootstrap writes it before ArgoCD's first sync (step 8). On a
cluster where RHDH already runs, run bootstrap from a checkout that has
this change **before** merging it, or the RHDH pod can't start.

## Live verification

The ordered refresh steps are in `docs/refresh-2-checklist.md`. After
`make bootstrap CLUSTER=<kubeconfig> WITH_RHDH=true`, check:

1. **Plugin loading.** The RHDH pod's `install-dynamic-plugins` init
   container log lists Kubernetes, Topology, Tekton, both Argo CD
   halves and the Gitea module as installed, with no OCI pull errors.
   A `ghcr.io` pull error means the cluster has no egress there (see
   [Mirroring is debt](#mirroring-is-debt)).
2. **Backend errors.** In the `backstage-backend` container log there
   are no `401`/`403`/TLS errors from `kubernetes` or `argocd`.
3. **Read-only grant.** `oc --context="$CTX" auth can-i list pipelineruns.tekton.dev -A --as=system:serviceaccount:golden-path-agent-rhdh:golden-path-agent-rhdh-kubernetes`
   says `yes`, and the same command for `list secrets` or
   `delete deployments.apps` says `no`.
4. **Real browser** (`DEC-094`/`DEC-097`: a scripted call isn't evidence
   of what a browser shows). The `golden-path-agent` component shows:
   - the Kubernetes and Topology tabs, with the agent and MCP;
   - a CI tab listing step 9b's PipelineRuns;
   - a CD tab showing `golden-path-agent-demo-prod`.

## Mirroring is debt

Tekton and Argo CD are pulled from `ghcr.io` at every RHDH pod start
(`DEC-143`). A cluster without egress to `ghcr.io` fails the init
container, and RHDH stays down. The remedy is recorded as debt, not
built:
- Copy the three pinned digests into `golden-path-agent-rhdh`'s own
  ImageStreams, e.g.
  `skopeo copy docker://ghcr.io/redhat-developer/rhdh-plugin-export-overlays/backstage-community-plugin-tekton@sha256:a26ed788824fbd29e65b02f956dad8f35275a8ccd1110b23fc17957104d38a01 docker://image-registry.openshift-image-registry.svc:5000/golden-path-agent-rhdh/backstage-community-plugin-tekton`.
- Repoint the three packages at those copies.

The pull identity this needs already exists
(`golden-path-agent-rhdh-plugin-puller`, `DEC-147`).

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
- **Route decorator comes from bootstrap's Route.** OpenShift never
  generates a Route from the host-less base Ingress (`DEC-147`). The
  agent's Route is `pipelines/bootstrap/demo-prod-route.yaml` (labeled
  for Topology), applied by bootstrap step 2.
- **Not covered yet:** the approval service's own Component
  (`golden-path-agent-approval-service`) and the Tools Template.
