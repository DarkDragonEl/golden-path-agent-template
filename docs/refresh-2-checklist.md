# Refresh #2 checklist — fresh multi-node cluster

Phase E refresh #2: a brand-new OpenShift cluster (cluster-admin,
nothing preinstalled), restored from Git alone by `make bootstrap` plus
one pipeline run per component, Phase F/G included (RHDH, Gitea, the
Gitea scaffolder plugin, Tools Template, catalog, TechDocs).

**Status: repo-only readiness review.** Nothing in this file was run
against a cluster. It lists (1) every step still done by hand, (2) every
place a cluster-specific value is coupled into the repo, (3) what is not
reachable from the bootstrap path today, and (4) the ordered steps the
local session runs, each with its expected result. Names only, never
values. `DECISIONS.md`/`HANDOFF.md` references are to the
`agent-roadmap` repository.

## 1. Manual-step inventory

"Covered" = does `scripts/bootstrap.sh` (step number in brackets) do it
today. "Proposed fix" is a proposal only — nothing beyond rows M14 and
M31 is changed on this branch.

| # | Step | Where documented | Covered by `bootstrap.sh` | Proposed fix |
|---|---|---|---|---|
| M1 | Authenticated cluster-admin kubeconfig | `scripts/bootstrap.sh` header; ADR-010 | No, by design (never runs `oc login`) | Keep: documented operator step. Must be a **token-based** login (see M17). |
| M2 | Model endpoint URLs/names + API key | `bootstrap.env.example`; `docs/phase-c-runbook.md` §2; `DEC-138` | Yes — input validated [0], written [5]/[6] | Keep: operator input in `bootstrap.env`. |
| M3 | GitHub fine-grained PAT for promotion PRs | `docs/phase-c-runbook.md` §3; `DEC-139` | Partial — Secret from `GITHUB_TOKEN` [9]; PAT creation is a human UI action | Keep: operator input. Strongly recommended for refresh #2 so [9b] opens PRs itself. |
| M4 | OLM `Manual` InstallPlan approval | `DEC-080`; `DEC-135` addendum | Yes — `ensure_operator` [1], [3], [4b] | None. |
| M5 | Keycloak DB + admin Secrets | `DEC-080`; `docs/phase-d-runbook.md` §1 | Yes [2], create-once | None. |
| M6 | `golden-path-agent-ci-config` ConfigMap | `DEC-081`; `docs/phase-c-runbook.md` §2b | Yes [6] | None. |
| M7 | Pipeline/Task definitions | `DEC-078` | Yes [7] | None. |
| M8 | Gitea operator, CR, admin password, org, scaffolder account/team/token | `DEC-100`/`DEC-137`/`DEC-138` | Yes [4c], `--with-rhdh` only | None (but see M31). |
| M9 | `ALTER ROLE rhdh CREATEDB` on RHDH's Postgres | `PINS.md` (RHDH CREATEDB row); `deploy/kustomize/overlays/rhdh/postgres.yaml` header | **No** | Automate GitOps-side: an sclorg `postgresql-start/` hook (ConfigMap-mounted script, runs on every start, idempotent) in `postgres.yaml` — no ordering race with ArgoCD. |
| M10 | RHDH native `Route` (edge, `Redirect`) | `DEC-094`; ADR-016 (out-of-band, never committed) | **No** | Bootstrap creates it with `oc create route edge` and **no `--hostname`** — OpenShift assigns `<name>-<ns>.<apps-domain>`, so nothing host-specific enters Git — then reads `.spec.host` back. |
| M11 | Keycloak native `Route` | `DEC-097`; ADR-016 | **No** | Same as M10, for `golden-path-agent-service`. |
| M12 | `PUBLIC_URL` key in `golden-path-agent-rhdh-oidc-secret` | `PINS.md` (PUBLIC_URL row); `oidc-app-config.yaml` header | **No** — `provision-identity-secrets.sh` never writes it, so `app.baseUrl` is unresolved on a fresh cluster | Write `https://<M10 host>` every run in `provision-identity-secrets.sh` step 4. |
| M13 | `OIDC_METADATA_URL` pointing at the **external** Keycloak host | `DEC-097` | Partial — written once at first creation, with the in-cluster Service URL a browser cannot reach | Derive from the M11 host and write it every run. |
| M14 | Keycloak `spec.proxy.headers: xforwarded` | `DEC-097`; ADR-016 | Was **No** (live patch only) — **fixed on this branch** in `platform/bootstrap/keycloak-cr.yaml`, applied by [3] | Done. |
| M15 | Restart RHDH after Keycloak issuer/endpoint changes (discovery-document cache) | `PINS.md` (discovery cache row); `DEC-097` | **No** | `oc rollout restart deployment/backstage-golden-path-agent` right after M12/M13 are written. |
| M16 | Build + push the Gitea scaffolder dynamic-plugin image, then pin its digest | `DEC-118`/`DEC-123`; `PINS.md` Phase G Stage 3; `agent-roadmap/reports/feature-g6-scaffolder-plugin-spike.md` | **No** — the factory recipe (`source.json`, `plugins-list.yaml`) isn't even committed; the pinned digest exists only in the old cluster's registry | Commit the recipe, add a Tekton task (or bootstrap step) that builds and pushes to `golden-path-agent-rhdh`, and land the new digest in `dynamic-plugins-config.yaml` by PR (same shape as image promotion). **Blocks RHDH entirely** (see §3). Larger than this mission — needs a go. |
| M17 | RHDH plugin-loader registry pull credential (`golden-path-agent-rhdh-registry-auth`) | `provision-identity-secrets.sh` comment; `DECISIONS.md` Borrowed-cluster follow-ups | Partial [5] — from `oc whoami -t`, a personal token that expires. **A client-certificate kubeconfig (the installer's) has no token, so step 5 fails outright and bootstrap stops after 3 retries.** | ServiceAccount-backed token (`system:image-puller` on `golden-path-agent-rhdh`) reformatted into `auth.json`. Until then, run bootstrap from an `oc login` session. |
| M18 | Mirror this blueprint into Gitea (`golden-path-agent-admin/golden-path-agent-template`) | `DEC-100` (by hand); Borrowed-cluster follow-ups | **No** — catalog location #3 404s on a fresh cluster | Mirror step in bootstrap (or a `tools/gitea_publish.py` mode), or drop location #3. |
| M19 | Gitea hostname in RHDH config + template defaults | `DEC-131` | **No** — the literal in Git is the old sandbox's | Cherry-pick `423b6ec` (on unmerged `feature/phase-i3`): `GITEA_HOST` discovered from the Gitea Route at [5], then `${GITEA_HOST}`. See §2 C2 for the one part it doesn't solve. |
| M20 | Merge the agent/mcp promotion PRs opened by [9b] | `DEC-139`; `SysR-P-F-06` | Partial, by design — merging is the owner's decision | Keep: documented operator step, then re-run bootstrap. |
| M21 | Rebuild + promote the **approval** image | `deploy/kustomize/overlays/approval-platform/kustomization.yaml` header ("kept manually in sync") | **No** — [9b] handles agent/mcp only; `open-promotion-pr` edits only `base/kustomization.yaml`, not the separate `approval-platform` pin; [9] never checks the approval Deployment | Add `promote_component approval` (overlay-aware digest check), and either have `open-promotion-pr` edit both pins or single-source the pin. Larger — needs a go. |
| M22 | External `Route` for `demo-prod`'s agent (`Ingress` has no `ingressClassName`) | `DEC-139` finding; `TODO(platform)` in `deploy/kustomize/base/ingress.yaml` | **No** — the [9] E2E probe FAILs if nothing admits the Ingress | Read the fresh cluster's `IngressClass` first (stock vs. SNO-specific is still undetermined), then set `ingressClassName` per overlay or use an M10-style Route. |
| M23 | Approver-UI access (two `oc port-forward`s) | `docs/phase-d-runbook.md` D3; `DEC-074`/`DEC-075` | No | Keep: documented walkthrough step. |
| M24 | Demo-user passwords | `provision-identity-secrets.sh` step 3 | Yes [5] — operator reads `golden-path-agent-demo-users` | None. |
| M25 | RHDH OIDC client on an already-imported realm | `PINS.md` (`KeycloakRealmImport` one-shot row) | Yes [5], create-if-missing | None. |
| M26 | Catalog `Group` `golden-path-agent-team` (cosmetic warning) | `DEC-097` | No | Commit a `Group` entity under `platform/catalog/`. |
| M27 | Tools Template registration in RHDH | not registered in `catalog-locations-config.yaml`; CLI-only (`tools/instantiate_agent_project.py`) | No | Owner decision: add a `template-tools.yaml` location (local-render only, no publish step). |
| M28 | Gitea backup/restore exercise | `platform/bootstrap/gitea-backup-restore-probe.yaml`; `DEC-103` | No | Keep: optional, one-time. |
| M29 | `ConfigMap` change → explicit rollout restart | `DEC-065` | No | Keep (operational, not bootstrap); `checksum/config` annotation still named. |
| M30 | PAT rotation (§8) | `HANDOFF.md` | No | Deferred by the owner. |
| M31 | Pass `--with-rhdh` through `make bootstrap` | `Makefile` | Was **No** — `make bootstrap` could never reach Phase F/G — **fixed on this branch** (`WITH_RHDH=true`) | Done. |

## 2. Cluster coupling

Searched `deploy/`, `pipelines/`, `scripts/`, `platform/`, `adapters/`,
`template*.yaml`, `template-schema*.json` and the RHDH app-config for
apps domains, cluster names, Route hosts and registry hosts. **No SNO or
showcase domain or cluster name appears outside comments.** One retired
sandbox's apps domain (its Gitea Route host, `DEC-131`) remains on
`main`:

| # | Where | What | Should come from |
|---|---|---|---|
| C1 | `deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml` lines 50, 55, 85 | Gitea Route host in `backend.reading.allow`, `integrations.gitea[].host`, and catalog location #3's URL | Discovered at bootstrap from the Gitea CR's `.status.giteaRoute` (or the Route's `.spec.host`), stored as `GITEA_HOST` in `golden-path-agent-rhdh-gitea-scaffolder-secret`, used as `${GITEA_HOST}`. Implemented in `423b6ec`, not on `main`. |
| C2 | `template.yaml` line 148 | `RepoUrlPicker` `allowedHosts` literal | Catalog entities get no `${VAR}` substitution, so this can't be env-driven. `423b6ec` swaps in a placeholder, which would block a real publish. Needs a decision: drop `allowedHosts` (the picker then offers the configured integrations) or render the template at bootstrap. |
| C3 | `template-schema.json` line 61, `template-schema-tools.json` line 39 | `gitHost` default for the CLI path | No real default; the caller passes the discovered Gitea host. `423b6ec`. |
| C4 | `deploy/kustomize/overlays/rhdh/dynamic-plugins-config.yaml` line 36 | `oci://image-registry.openshift-image-registry.svc:5000/golden-path-agent-rhdh/…@sha256:…` | The host is the stock internal-registry Service (same on every OpenShift cluster). The **digest** is a cluster-local artifact. From a build on the target cluster, promoted by PR (M16). |
| C5 | `deploy/kustomize/base/kustomization.yaml`, `overlays/approval-platform/kustomization.yaml` `images:` | Internal-registry digests | Same as C4: a portable host with cluster-local digests. [9b] rebuilds agent/mcp; approval isn't covered (M21). |
| C6 | `golden-path-agent-rhdh-oidc-secret` `PUBLIC_URL`, `OIDC_METADATA_URL` | Not committed (correct), but nothing derives them | From the M10/M11 Routes' `.spec.host`. Base domain, if ever needed: `oc get ingresses.config/cluster -o jsonpath='{.spec.domain}'`. |
| C7 | `deploy/kustomize/overlays/rhdh/backstage.yaml` line 57 | `config-service-cabundle` ConfigMap in `golden-path-agent-rhdh` | Nothing in this repo creates it. It's presumably injected per namespace by OpenShift Pipelines (installed at [1]). Verify on the fresh cluster (§4 step 7). |
| — | `image-registry.openshift-image-registry.svc:5000` (`provision-identity-secrets.sh`, `backstage.yaml` `extraFiles`, Pipeline tasks) | Stock internal registry | Portable across OpenShift. No change. |
| — | `github.com/DarkDragonEl/golden-path-agent-template` (`deploy/argocd/*`, catalog locations, `open-promotion-pr.yaml`) | Repository coupling, not cluster coupling | Fine for refresh #2 (same repo). Relevant only to a second adopter. |

## 3. Phase F/G reachability from `make bootstrap` + one pipeline run

| Component | Reachable today? | What's missing |
|---|---|---|
| Gitea | Yes, via [4c] — but only with `--with-rhdh`, which `make bootstrap` couldn't pass until M31 (fixed here) | — |
| RHDH operator | Yes [4b] | — |
| RHDH `Backstage` CR + app-config | Synced by root → `golden-path-agent-rhdh` [8] | **Won't start on a fresh cluster.** M16: the pinned plugin digest doesn't exist, so the `install-dynamic-plugins` init container fails and the whole pod stays down, not just `publish:gitea`. Also M12 (`app.baseUrl` unresolved) and M9 (`CREATEDB`). |
| RHDH browser login | No | M10, M11, M13, M15 (M14 fixed here) |
| Dynamic plugins | Partial | Lightspeed pulls from `registry.access.redhat.com` (needs egress). Gitea plugin: M16. |
| Template registration (`template.yaml`) | Yes, via the GitHub location, once RHDH is up | The Gitea-hosted copy needs M18 + M19. `publish:gitea` needs M16 + M19 + C2. |
| Tools Template | CLI only (`tools/instantiate_agent_project.py`) | Not registered in RHDH (M27) |
| Catalog (`catalog-info.yaml`, `platform/catalog/*`) | Yes, via GitHub, once RHDH is up | Cosmetic M26 |
| TechDocs | Yes, once RHDH is up (bundled local generator, reads GitHub) | — |
| Shared approval service | **No** | M21 — ImagePullBackOff on a fresh cluster, with no automated recovery |
| `demo-prod` agent/mcp | Yes, via [9b] + M20 | E2E probe depends on M22 |
| Step 9 verification | Partial | Checks RHDH only for `Synced`, never health. Doesn't check the approval Deployment. |

Also: root always syncs `deploy/argocd/apps/rhdh.yaml`, so a run
**without** `--with-rhdh` leaves `golden-path-agent-rhdh` failing (no
`Backstage` CRD). Refresh #2 must use `WITH_RHDH=true`.

## 4. Ordered steps for the local session

Every `oc` call uses a dedicated `KUBECONFIG` (ADR-010). Placeholders
like `<rhdh-host>` are read from the cluster at run time and are never
written to Git or reports.

| Step | Action | Expected result |
|---|---|---|
| 0 | Local tools: `oc`, `jq`, `curl`, `openssl`, `python3`, GNU `base64`, `git` (and `podman` for M16). | `command -v` succeeds for each. |
| 1 | Token-based login into a dedicated kubeconfig: `KUBECONFIG=<path> oc login --server=<api> -u <cluster-admin-user>`. | `oc whoami -t` prints a token (required, M17); `oc auth can-i '*' '*' --all-namespaces` → `yes`. |
| 2 | Read-only precheck: `tools/cluster_precheck.sh --context <ctx> --allow-scratch-ns --output state/refresh-2-precheck.md`. Also run `oc get ingressclass -o yaml` (for M22). | No `FAIL` rows. Outbound reachability to `github.com`, `registry.access.redhat.com`, `quay.io` and the model endpoint confirmed. Default-IngressClass annotation recorded. |
| 3 | `cp bootstrap.env.example bootstrap.env` and fill in the keys (see §5). | File present, gitignored. |
| 4 | Owner go/no-go on the gated fixes (M16, M19/`423b6ec`, M21, M9–M13/M15), and whether they land on `main` before step 5. | Recorded decision. Without M16, RHDH stays down until step 10. |
| 5 | `make bootstrap CLUSTER=<kubeconfig> WITH_RHDH=true` | [0] "all required keys present". [1]/[3]/[4b] CSVs `Succeeded` (Pipelines ≥1.22.5, GitOps ≥1.20.6, RHBK 26.6.6, RHDH 1.10.3). [4c] Gitea `adminSetupComplete`, route `200`, org/account/token provisioned. Keycloak `Ready`, RealmImport `Done`. [5] "provision-identity-secrets.sh: done." [6] all `PASS`. [9b] on a fresh cluster: committed digests absent → agent and mcp PipelineRuns triggered, each reaches `open-promotion-pr` within 20 min → (with `GITHUB_TOKEN`) two promotion PRs open → script exits 1 with "re-run this script once that PR is merged". This is the "one pipeline run" per component. |
| 6 | Owner reviews and merges both promotion PRs (M20). | `golden-path-agent-demo-prod` syncs the new digests. |
| 7 | Check the implicit dependency (C7): `oc get configmap config-service-cabundle -n golden-path-agent-rhdh`. | Exists. If not, RHDH's `extraFiles` mount fails. Stop and report. |
| 8 | Approval image (M21, until fixed): `oc create -f pipelines/pipelinerun-template-approval.yaml -n golden-path-agent-ci`. Once it passes, put the resulting digest in **both** `deploy/kustomize/base/kustomization.yaml` and `deploy/kustomize/overlays/approval-platform/kustomization.yaml` via a PR, then merge. | PipelineRun `Succeeded`. `golden-path-agent-approval` Deployment 1/1 in `golden-path-agent-approval`. |
| 9 | RHDH hand steps (until M9–M13/M15 are automated): (a) once `golden-path-agent-rhdh-db` is Running, `oc exec -n golden-path-agent-rhdh deploy/golden-path-agent-rhdh-db -- psql -U postgres -d postgres -c "ALTER ROLE rhdh CREATEDB;"`; (b) `oc create route edge` for `backstage-golden-path-agent` (ns `golden-path-agent-rhdh`) and `golden-path-agent-service` (ns `golden-path-agent-keycloak`, `--port=http`), `--insecure-policy=Redirect`, no `--hostname`; (c) set `PUBLIC_URL` (`https://<rhdh-host>`) and `OIDC_METADATA_URL` (`https://<keycloak-host>/realms/golden-path-agent/.well-known/openid-configuration`) in `golden-path-agent-rhdh-oidc-secret` (`oc set data`); (d) `oc rollout restart deployment/backstage-golden-path-agent -n golden-path-agent-rhdh`. | (a) prints `ALTER ROLE`. (b) each Route gets an apps-domain host, edge/Redirect. (c) both keys present. (d) rollout completes, and the backend log has no `app.baseUrl`, `permission denied to create database`, or `iss mismatch` errors. |
| 10 | Gitea plugin (M16): build with the pinned `dynamic-plugins-factory` image (Backstage `v1.49.0`, `workspace-path: "."`, shallow clone + `--use-local`, `--push-images` to `golden-path-agent-rhdh`), then PR the new digest into `dynamic-plugins-config.yaml` and merge. | `install-dynamic-plugins` init container completes. `GET /api/scaffolder/v2/actions` lists `publish:gitea`. |
| 11 | Gitea host (M19): if `423b6ec` landed before step 5 this is automatic; otherwise expect a catalog warning for location #3 and a `publish:gitea` host mismatch. | With the fix: no `NotAllowedError` for the Gitea host in the RHDH log. |
| 12 | Optional (M18): mirror this repo into Gitea as `golden-path-agent-admin/golden-path-agent-template`. | Catalog location #3 resolves. |
| 13 | Re-run `make bootstrap CLUSTER=<kubeconfig> WITH_RHDH=true`. | [9b] "already present" for agent and mcp. [9] all `PASS`, including the E2E `/healthz` `200` (subject to M22). Note: [5] rotates credentials again (`DEC-059`). |
| 14 | Real external-browser verification (`DEC-094`/`DEC-097` lesson): log in to RHDH as `demo-user` via OIDC; open the `golden-path-agent` Component (TechDocs tab renders) and the platform `System`/`API`/`Resource` entities; run the Create wizard (`publish:gitea` creates the two repos under `golden-path-agent-projects`); run one write→approve→execute flow through the approver UI (`docs/phase-d-runbook.md` D3). Then the `pre-flight` and `post-deploy` skills. | Every check observed in a real browser, not only via scripted API calls. |

## 5. Secrets and inputs (names only)

**The operator provides** (`bootstrap.env`, validated at step 0):
`MODEL_API_BASE_URL`, `MODEL_NAME`, `MODEL_FALLBACK_API_BASE_URL`,
`MODEL_FALLBACK_NAME`, `MODEL_API_KEY` (required), and `GITHUB_TOKEN`
(optional, recommended). Plus the token-based cluster-admin kubeconfig
from step 1.

**The operator sets by hand today** (until M12/M13 are automated), as
keys in `golden-path-agent-rhdh` / `golden-path-agent-rhdh-oidc-secret`:
`PUBLIC_URL`, `OIDC_METADATA_URL`. Both are derived from the step 9
Routes, not supplied from outside.

**Bootstrap creates these itself** (reference, so nobody creates them by
hand):

| Namespace | Secret / ConfigMap | Lifecycle |
|---|---|---|
| `golden-path-agent-keycloak` | `golden-path-agent-keycloak-db-secret`, `golden-path-agent-keycloak-admin` | create-once [2] |
| `golden-path-agent-keycloak` | `golden-path-agent-demo-users` | regenerated [5] |
| `golden-path-agent-demo-prod`, `golden-path-agent-ephemeral-test` | `golden-path-agent-secrets` | regenerated [5] |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-db-secret` | create-once [4b] |
| `golden-path-agent-rhdh` | `golden-path-agent-rhdh-oidc-secret` (`SESSION_SECRET` create-once, `OIDC_CLIENT_SECRET` regenerated), `golden-path-agent-rhdh-gitea-scaffolder-secret`, `golden-path-agent-rhdh-registry-auth` | [5] |
| `golden-path-agent-gitea` | `golden-path-agent-gitea-admin-password`, `golden-path-agent-gitea-scaffolder-password` (create-once), `golden-path-agent-gitea-scaffolder-token` (regenerated) | [4c] |
| `golden-path-agent-ci` | `golden-path-agent-github-token` (only if `GITHUB_TOKEN` set), ConfigMap `golden-path-agent-ci-config` | [9], [6] |
