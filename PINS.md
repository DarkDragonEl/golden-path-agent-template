# PINS.md

Per `CLAUDE.md`'s "Reuse over building" rule: before writing infrastructure
code (pipeline, GitOps, observability, policy), search for the current
state of Red Hat Validated Patterns, AI Quickstarts, and official reference
repos; pin exact versions and commits here with the URL and date verified.
Never rely on memorized repo contents — every row below was verified
against a live source on the date listed, not assumed from training data.

Previously flagged as open work (`srs/DEFERRED.md` `SysR-P-LC-01`) — first
entry created at Step R4 (plan-B6/OTel closure), mission
`~/.claude/plans/read-claude-md-handoff-md-decisions-md-vast-hare.md`.

| Component | Realization | Channel/Version | Support level | Verified date | Source URL | Notes |
|---|---|---|---|---|---|---|
| Local dev OTel Collector | `otel/opentelemetry-collector` (core distribution, not `-contrib`) | `0.159.0` | Community (upstream OpenTelemetry, not a Red Hat build) | 2026-08-21 | https://github.com/open-telemetry/opentelemetry-collector-releases/releases · https://opentelemetry.io/docs/collector/install/docker/ | Core distribution chosen deliberately over `-contrib`: only an OTLP HTTP receiver + `debug` exporter are needed for this milestone's local-dev scope (`scripts/dev.sh`, `deploy/otel/otel-collector-config.yaml`) — `-contrib` is heavier and unnecessary here. **Revisited at Phase C, see the cluster-tier OTel row below** — this local-dev row's pin does not carry over. |

## Phase C — CI, gates, promotion (SNO)

Per `DECISIONS.md` `DEC-021`'s Phase C kickoff instruction: this section is
populated *before* any pipeline/GitOps/policy YAML is written, not after.
Every row verified either against the actual target cluster's own live
state (most authoritative — it is literally what's installable/running
there) or against an upstream releases API directly, not a search-result
snippet. **The target cluster is a shared, multi-tenant OpenShift SNO lab
cluster, not a dedicated one provisioned for this project** — see the
Phase C plan / `docs/environments.md` for what that means for isolation.
Component names/versions below only ever refer to this project's own
realization choices; no other tenant's project name appears here, per
`CLAUDE.md`'s anonymity rule.

| Component | Realization | Channel/Version | Support level | Verified date | Source URL | Notes |
|---|---|---|---|---|---|---|
| OpenShift Pipelines (Tekton) | `openshift-pipelines-operator-rh` | channel `pipelines-1.22`, CSV `v1.22.2` | GA, Red Hat | 2026-08-21 | live cluster (`oc get csv -A`) | Already installed cluster-wide by another tenant's prior work — no install action needed. `SyRS-AGP-001-RRT_Realization_Table.md` prospectively pinned "1.23" (as of its own 2026-08-12 snapshot); superseded by the live-installed reality on the actual target cluster, per this file's own "verify, don't trust stale figures" rule. |
| OpenShift GitOps (Argo CD) | `openshift-gitops-operator` | channel `gitops-1.20`, CSV `v1.20.4` | GA, Red Hat | 2026-08-21 | live cluster (`oc get csv -A`) | Already installed cluster-wide. RRT pinned "1.21.0" — same supersession as above. |
| Red Hat build of OpenTelemetry (cluster tier) | `opentelemetry-product` | channel `stable`, CSV `opentelemetry-operator.v0.152.0-3` | GA, Red Hat | 2026-08-21 | live cluster's own OperatorHub catalog (`redhat-operator-index:v4.20`) | Not yet installed — closes the local-dev row's "revisit at Phase C" note above. Matches RRT Row 17's realization choice (RRT pinned "3.9.3" as a product-line version; the CSV string above is the actual installable unit on this cluster's catalog, which is what a `Subscription` needs). A `Subscription`/`OperatorGroup` is a new, scoped action (this project's own namespace, not cluster-wide) — see the Phase C plan's C1a. |
| Container registry | OpenShift internal image registry | `Managed`, PVC-backed storage, route `default-route-openshift-image-registry.apps.sno.lab.local` | Built into OCP | 2026-08-21 | live cluster (`oc get configs.imageregistry.operator.openshift.io/cluster`) | This is the "not Quay" substitution the accepted delivery plan already decided (`SysR-P-LC-02` logged substitution vs. RRT Row 16's Quay 3.17.3 pin) — resource-budget reasons on a shared SNO. Already enabled; no install action. Namespace-scoped `ImageStream` per project, the standard OpenShift pattern already in use elsewhere on this cluster. |
| syft (SBOM) | `anchore/syft` container image | `v1.51.0` | Community (Anchore) | 2026-08-21 | https://github.com/anchore/syft/releases (GitHub releases API, published 2026-08-10) | Matches `ci/pr-checks.yaml`'s existing tool choice; now pinned to an exact tag for Tekton `Task` use instead of `latest`. |
| OPA (policy-definition unit-test gate) | `openpolicyagent/opa` container image | `1.19.1` (Docker Hub tag — note: **no `v` prefix**, unlike the GitHub release tag `v1.19.1`; confirmed by directly listing Docker Hub's tag list after the `v`-prefixed pull failed with "manifest unknown") | Community, justified (RRT Row 11 / Annex A `OI-03`: scaffolding + one enforced deny path, not a policy platform) | 2026-08-21 | https://github.com/open-policy-agent/opa/releases (GitHub releases API, published 2026-08-17) · https://hub.docker.com/r/openpolicyagent/opa/tags | Runs as a static `opa test` CLI step (`policy/opa/`) validating the policy *definition*, not a live admission controller — **no Gatekeeper Operator, no OPA server/sidecar deployed.** Verified working: `opa test policy/opa/ -v` → 11/11 PASS via this exact pinned image. **C1b addendum**: the plain `1.19.1` image has no shell at all (`sh: not found`, confirmed live) — Tekton's `script:` step field needs one, so `pipelines/tasks/policy-validate.yaml`'s data-dump step uses `1.19.1-debug` instead (same OPA binary, adds a busybox shell); the `opa test` step itself uses direct `command`/`args` exec, no shell needed, plain `1.19.1` is correct there. |
| buildah | `quay.io/buildah/stable` container image, run directly in a custom Task step | `v1.43.2` | Community (Buildah project) | 2026-08-21 | https://quay.io/repository/buildah/stable?tab=tags (Quay API, verified live) | **Revised from the C0a pin**: ClusterTasks are confirmed deprecated (Pipelines 1.10+), but the Tekton Hub catalog `buildah` Task itself is also mid-migration (its own hub.tekton.dev page is marked "(deprecated)" in favor of `tektoncd-catalog` repos and OCI-published bundles whose exact current bundle-resolver reference is a moving target). For this demo-scope MVP, a minimal custom Task running `buildah bud`/`buildah push` directly against this one pinned image is simpler and more self-contained than chasing an external, fast-moving bundle reference — `pipelines/tasks/container-build.yaml`. |
| git-clone | `alpine/git` container image, run directly in a custom Task step | `2.54.0` | Community | 2026-08-21 | https://hub.docker.com/r/alpine/git/tags (Docker Hub API, verified live) | Same rationale as buildah above — a plain `git clone` in a custom Task, not the Tekton Hub `git-clone` Task (its own hub.tekton.dev page is also marked deprecated). `pipelines/tasks/fetch-source.yaml`. |
| `oc`/`kubectl` CLI (for `deploy-ephemeral`/`destroy-ephemeral` Task steps) | `quay.io/openshift/origin-cli` container image | `4.20` | Community (OpenShift Origin) | 2026-08-21 | https://quay.io/repository/openshift/origin-cli?tab=tags (Quay API, verified live) | Matches the target cluster's own OCP version (`4.20.23`, this file's own row above) — deliberately not a newer tag, to avoid a client/server skew mismatch on API compatibility. |
| OCP (target cluster) | — | `4.20.23` | GA, Red Hat | 2026-08-21 | live cluster (`oc version`) | RRT prospectively pinned "4.21/4.22"; this shared lab cluster runs one minor behind that and is **not under this project's authority to upgrade** — documented as-is, not treated as a gap to close. |
| External Secrets Operator | Red Hat build, `openshift-external-secrets-operator` | channel `stable-v1` (default), CSV `v1.2.0` | GA, Red Hat | 2026-08-21 | live cluster's own OperatorHub catalog | **Deliberately not adopted this phase** — the Phase C plan's secret-handling decision uses a plain `Secret`, manually provisioned once, instead (the RRT itself treats secrets as an org-external interface, out of this MVP's realization scope). Recorded here, pinned and ready, as the clean phase-two/pilot-prod integration point (`CLAUDE.md`'s "clean integration points, never implementations" rule) — so a future session doesn't have to re-research it. |
