# Refresh #2 checklist — fresh multi-node cluster

Phase E refresh #2: a brand-new OpenShift cluster (cluster-admin,
nothing preinstalled), restored from Git alone by `make bootstrap` plus
one pipeline run per component, Phase F/G included (RHDH, Gitea, the
Gitea scaffolder plugin, Tools Template, catalog, TechDocs).

**Status: repo-only.** Nothing in this file was run against a cluster.
Mission C0 inventoried the hand steps; mission C2 (`DEC-143`–`DEC-147`)
closed them. **Every row below is now either done by bootstrap (or by
GitOps) or a named operator input.** Names only, never values.
`DECISIONS.md`/`HANDOFF.md` references are to the `agent-roadmap`
repository. Step numbers in brackets are `scripts/bootstrap.sh` steps.

## 1. Inventory: covered, or a named operator input

| # | Step | Status | How / where |
|---|---|---|---|
| M1 | Cluster-admin kubeconfig | **Operator input** | A dedicated `KUBECONFIG` (ADR-010). A token login is no longer required: M17 removed the only `oc whoami -t`. |
| M2 | Model endpoint URLs/names + API key | **Operator input** | `bootstrap.env` (validated [0], written [5]/[6]). |
| M3 | GitHub fine-grained PAT for promotion PRs | **Operator input** (optional, recommended) | `bootstrap.env` `GITHUB_TOKEN` → `golden-path-agent-github-token` [9]. |
| M4 | OLM `Manual` InstallPlan approval | Covered | `ensure_operator` [1], [3], [4b]. |
| M5 | Keycloak DB + admin Secrets | Covered | [2], create-once. |
| M6 | `golden-path-agent-ci-config` ConfigMap | Covered | [6]. |
| M7 | Pipeline/Task definitions | Covered | [7]. |
| M8 | Gitea operator, CR, admin password, org, scaffolder account/team/token | Covered | [4c]. |
| M9 | `ALTER ROLE rhdh CREATEDB` | Covered (GitOps) | The image's own start hook, mounted from a ConfigMap in `deploy/kustomize/overlays/rhdh/postgres.yaml`. It runs on every start and is idempotent. |
| M10 | RHDH browser Route | Covered | [4b] applies `platform/bootstrap/rhdh-routes.yaml` (no host; OpenShift assigns one, read back). |
| M11 | Keycloak browser Route | Covered | Same file, same step. |
| M12 | `PUBLIC_URL` | Covered | [5] writes `https://<RHDH Route host>` into `golden-path-agent-rhdh-oidc-secret` every run. |
| M13 | External `OIDC_METADATA_URL` + RHDH trusting it | Covered | [5] writes it from the Keycloak Route host. [4b] writes `golden-path-agent-rhdh-cluster-ca` (ingress + service CA), which the Backstage CR mounts and points `NODE_EXTRA_CA_CERTS` at. |
| M14 | Keycloak `proxy.headers: xforwarded` | Covered | `platform/bootstrap/keycloak-cr.yaml`, [3] (mission C0). |
| M15 | Restart RHDH after OIDC/discovery changes | Covered | Right after [5], whenever the RHDH Deployment exists. |
| M16 | Gitea scaffolder plugin image | **Operator input** (one-time build + one key) | Build and push once with `platform/rhdh-plugins/gitea-scaffolder/build.sh --write-pin` (needs the operator's registry login), then commit the digest (`pin.env` + PINS.md). `bootstrap.env` `RHDH_PLUGIN_REGISTRY`. [0] refuses `--with-rhdh` until both exist. [4b] renders the include RHDH loads. |
| M17 | RHDH plugin-loader registry credential | Covered | [4b] `platform/bootstrap/rhdh-plugin-puller.yaml` (ServiceAccount + token Secret + `system:image-puller`). [5] builds `auth.json` from it, plus the optional `RHDH_PLUGIN_REGISTRY_USERNAME`/`_PASSWORD` operator input for a private registry. |
| M18 | Gitea copy of this blueprint | Covered | [4c] pushes GitHub `main` plus one commit to `golden-path-agent-admin/golden-path-agent-template`, every run. |
| M19 | Gitea host in RHDH config + template | Covered | [5] discovers `GITEA_HOST` (`${GITEA_HOST}` in the catalog config). [4c] injects it into the Gitea copy's `allowedHosts`; Git keeps `gitea.example.com`. |
| M20 | Merge the promotion PRs [9b] opens | **Operator decision** (by design) | Merging is the promotion event (SysR-P-F-06); re-run bootstrap afterwards. |
| M21 | Rebuild + promote the approval image | Covered | [9b] `promote_component approval`. `open-promotion-pr` updates both of its pins in one PR, `tests/test_image_pins.py` blocks drift, and [9] checks the approval Deployment. |
| M22 | demo-prod agent reachable from outside (E2E probe) | Covered | Argo CD syncs `deploy/kustomize/overlays/demo-prod/route-agent.yaml`, a host-less Route that OpenShift assigns a host to (`DEC-149`; bootstrap no longer applies it). The real blocker was the Ingress's missing **host**: OpenShift's ingress-to-route controller skips host-less rules. It wasn't the IngressClass; `openshift-default` exists, and a class-less Ingress is still managed (`DEC-147`). |
| M23 | Approver-UI access (two `oc port-forward`s) | Walkthrough action, not a restore step | `docs/phase-d-runbook.md` D3. |
| M24 | Demo-user passwords | Covered | [5]; read from `golden-path-agent-demo-users`. |
| M25 | RHDH OIDC client on an already-imported realm | Covered | [5], create-if-missing. |
| M26 | Catalog `Group` `golden-path-agent-team` | Covered (GitOps) | `platform/catalog/group.yaml`, registered in `catalog-locations-config.yaml`. |
| M27 | Tools Template registered in RHDH | Covered (GitOps) | `template-tools.yaml` location (local-render only). |
| M28 | Gitea backup/restore exercise | Optional verification, not a restore step | `platform/bootstrap/gitea-backup-restore-probe.yaml`. |
| M29 | `ConfigMap` change → rollout restart | Operations, not a restore step | `DEC-065`; [9] restarts demo-prod and the approval service itself. |
| M30 | PAT rotation | Operations, deferred by the owner | `HANDOFF.md` §8. |
| M31 | `--with-rhdh` through `make bootstrap` | Covered | `make bootstrap WITH_RHDH=true` (mission C0). |
| M32 | Read-only Argo CD account + token for RHDH's CD tab | Covered | [4d] (`DEC-144`), writing `golden-path-agent-rhdh-argocd-secret`. |
| M33 | RHDH's CA bundle (was an implicit dependency on a Pipelines-injected ConfigMap, C7) | Covered | [4b] writes `golden-path-agent-rhdh-cluster-ca`. |

**Operator inputs, complete list:** M1 (kubeconfig); `bootstrap.env`
(M2 model endpoint, M3 optional `GITHUB_TOKEN`, M16
`RHDH_PLUGIN_REGISTRY` plus optional pull credentials); the one-time
plugin build and its committed digest (M16); merging promotion PRs (M20).

## 2. Cluster coupling (after C2)

| # | Where | Status |
|---|---|---|
| C1 | `catalog-locations-config.yaml` Gitea host | `${GITEA_HOST}`, discovered [5] (`DEC-146`). |
| C2 | `template.yaml` `allowedHosts` | `gitea.example.com` placeholder in Git. The real host exists only in the Gitea copy [4c]; the Template is registered from that copy only. |
| C3 | `template-schema*.json` `gitHost` default | Placeholder; the caller passes the host. |
| C4 | Gitea scaffolder plugin digest | External registry from `bootstrap.env`, digest in `pin.env`/PINS.md (`DEC-145`); no host in Git. |
| C5 | Component image digests | Cluster-local by nature; [9b] rebuilds agent, mcp **and approval** and promotes by PR. |
| C6 | `PUBLIC_URL`, `OIDC_METADATA_URL` | Derived from the [4b] Routes every run. |
| C7 | RHDH CA bundle | Bootstrap-written `golden-path-agent-rhdh-cluster-ca`; no Pipelines-injected dependency. |
| C8 | demo-prod external host (M22) | Assigned by OpenShift to the [2] Route, read back by [9]; nothing in Git. |
| — | `image-registry.openshift-image-registry.svc:5000`, the repository URL | Portable / repository coupling. Unchanged. |

## 3. Ordered steps for the local session

Every `oc` call uses a dedicated `KUBECONFIG` (ADR-010). Hosts are read
from the cluster at run time and are never written to Git or reports.

| Step | Action | Expected result |
|---|---|---|
| 0 | Local tools: `oc`, `jq`, `curl`, `openssl`, `python3`, GNU `base64`, `git`, `awk`, `sed`; plus `podman` and `skopeo` for step 2. | Bootstrap [0] checks these and lists any missing. |
| 1 | Log in to the new cluster as cluster-admin, into a dedicated kubeconfig (token or client certificate). | `oc auth can-i '*' '*' --all-namespaces` → `yes`. |
| 2 | **Once per plugin version:** `podman login <registry-host>`, then `RHDH_PLUGIN_REGISTRY=<host>/<namespace> platform/rhdh-plugins/gitea-scaffolder/build.sh --write-pin`. Put the printed digest into PINS.md's "Gitea scaffolder dynamic plugin (built image)" row, then commit and merge both files. | The factory finishes with "All operations completed successfully", and `pin.env` has `PLUGIN_DIGEST=sha256:…`. `pytest tests/test_rhdh_plugin_pins.py` passes. |
| 3 | Read-only precheck: `tools/cluster_precheck.sh --context <ctx> --allow-scratch-ns --output state/refresh-2-precheck.md`. | No `FAIL` rows. Egress confirmed to `github.com`, `ghcr.io`, `quay.io`, `registry.access.redhat.com`, the plugin registry and the model endpoint. |
| 4 | `cp bootstrap.env.example bootstrap.env` and fill in the keys (§4). | Present, gitignored. |
| 5 | `make bootstrap CLUSTER=<kubeconfig> WITH_RHDH=true` | [0] reports keys, tools and the plugin pin present. [1]/[3]/[4b] CSVs `Succeeded`. [4b] prints both Route hosts and renders the CA bundle and plugin include. [4c] Gitea ready, and the Gitea copy pushed. [4d] Argo CD account + token written. [5] "provision-identity-secrets.sh: done." [6] all `PASS`. [9b] on a fresh cluster: no committed digest exists, so agent, mcp and approval PipelineRuns are triggered; each reaches `open-promotion-pr`, opening three promotion PRs (with `GITHUB_TOKEN`), then "re-run this script once that PR is merged". |
| 6 | Owner merges the three promotion PRs (M20). | ArgoCD syncs demo-prod and the approval service onto the new digests. |
| 7 | Re-run `make bootstrap CLUSTER=<kubeconfig> WITH_RHDH=true`. | [9b] "already present" ×3. [9] all `PASS`: demo-prod agent/mcp 1/1, approval 1/1, every Application `Synced`, the E2E `/healthz` 200 through the agent's Route. Note [5] rotates credentials again (`DEC-059`) and restarts RHDH. |
| 8 | Real external-browser verification (`DEC-094`/`DEC-097`). | RHDH sign-in via Keycloak as `demo-user`. The `golden-path-agent` Component shows TechDocs, Kubernetes, Topology, CI (Tekton) and CD (Argo CD). The platform `System`/`API`/`Resource`/`Group` entities and both Templates are listed. The Create wizard's `publish:gitea` creates the two repos under `golden-path-agent-projects`; this is the first task-level read of the skeleton from Gitea (`DEC-146`). One write→approve→execute flow runs through the approver UI (M23). Then the `pre-flight` and `post-deploy` skills. |

## 4. Inputs and Secrets (names only)

**The operator provides** (`bootstrap.env`, validated at [0]):
`MODEL_API_BASE_URL`, `MODEL_NAME`, `MODEL_FALLBACK_API_BASE_URL`,
`MODEL_FALLBACK_NAME`, `MODEL_API_KEY`, and `RHDH_PLUGIN_REGISTRY` with
`--with-rhdh` (all required); `GITHUB_TOKEN`,
`RHDH_PLUGIN_REGISTRY_USERNAME`, `RHDH_PLUGIN_REGISTRY_PASSWORD`
(optional). Plus the cluster-admin kubeconfig and the plugin registry
login used by `build.sh`.

**Bootstrap creates everything else** (so nobody creates these by hand):

| Namespace | Secret / ConfigMap | Lifecycle |
|---|---|---|
| `golden-path-agent-keycloak` | `golden-path-agent-keycloak-db-secret`, `golden-path-agent-keycloak-admin` | create-once [2] |
| `golden-path-agent-keycloak` | `golden-path-agent-demo-users` | regenerated [5] |
| `golden-path-agent-demo-prod`, `golden-path-agent-ephemeral-test` | `golden-path-agent-secrets` | regenerated [5] |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-db-secret` | create-once [4b] |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-kubernetes-token`, `golden-path-agent-rhdh-plugin-puller-token` | token controller fills them, [4b] |
| `golden-path-agent-rhdh` | ConfigMaps `golden-path-agent-rhdh-cluster-ca`, `golden-path-agent-rhdh-gitea-plugin` | regenerated [4b] |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-argocd-secret` | [4d] (`DEC-144`) |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-oidc-secret` (`SESSION_SECRET` create-once; `OIDC_CLIENT_SECRET`, `PUBLIC_URL`, `OIDC_METADATA_URL` every run), `golden-path-agent-rhdh-gitea-scaffolder-secret` (incl. `GITEA_HOST`), `golden-path-agent-rhdh-registry-auth` | [5] |
| `golden-path-agent-gitea` | `golden-path-agent-gitea-admin-password`, `golden-path-agent-gitea-scaffolder-password` (create-once), `golden-path-agent-gitea-scaffolder-token` (regenerated) | [4c] |
| `golden-path-agent-ci` | `golden-path-agent-github-token` (only if `GITHUB_TOKEN` set), ConfigMap `golden-path-agent-ci-config` | [9], [6] |
