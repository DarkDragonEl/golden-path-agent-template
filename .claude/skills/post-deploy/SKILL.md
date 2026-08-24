---
name: post-deploy
description: Verify a promotion actually landed correctly in demo-prod -- ArgoCD synced and healthy, the running pod's image digest matches what the promotion PR actually promoted (the immutable-artifact guarantee), pods ready, recent logs clean. Use right after a promotion PR merges, before telling anyone the new build is live.
allowed-tools:
  - Bash(oc *)
  - Bash(grep *)
  - Read
---

# /post-deploy

**Classification: read-only.** Every command is a `get`/`logs`/`grep` —
nothing here syncs, restarts, or patches anything.

**Live-tested** against real `golden-path-agent-demo-prod` during
`feature/workspace-tooling`'s release phase, once the parallel
Checkpoint-D session had finished. All 4 checks confirmed real, with two
corrections from the original static-source draft (see checks 1 and 2)
and one API-group gotcha worth knowing up front:

**`oc get application <name>` is ambiguous on this cluster** — it
resolves to the wrong CRD (`applications.app.k8s.io`, `NotFound`) unless
you're explicit about the API group. Always use `oc get
application.argoproj.io`.

## Checks, in order

### 1. ArgoCD Application synced and healthy

The real Application object is `golden-path-agent-demo-prod` in
namespace `openshift-gitops` (source: `deploy/kustomize/overlays/demo-prod`,
confirmed from `deploy/argocd/apps/demo-prod.yaml` — auto-sync is on
there, the promotion PR merge is the human gate, not a manual `oc apply`):

```bash
oc get application.argoproj.io golden-path-agent-demo-prod -n openshift-gitops \
  -o jsonpath='{.status.sync.status}{"\t"}{.status.health.status}{"\n"}'
```

**Green:** `Synced` / `Healthy`. **Red:** `OutOfSync`, or `Degraded`
health — a real finding.

**Confirmed-live nuance for `Progressing`:** don't just treat this as
"wait and recheck." On this environment, the aggregate app health sits
at `Progressing` **persistently** (confirmed stable across a 20s
recheck, not transient) — but it traces to exactly two resources, both
`Ingress` (`golden-path-agent`, `golden-path-agent-approval`), each with
an empty `.spec.rules[0].host` and empty `.status.loadBalancer`. This is
a known, already-documented, accepted state — `agent/static/
approver_ui.html`'s own source comment says outright "this project has
no working external Ingress this milestone," and access is deliberately
port-forward-only for now. Every functional resource (all 3 Deployments,
all 3 Services, the PVC, both PDBs) reports `Healthy` independently:

```bash
oc get application.argoproj.io golden-path-agent-demo-prod -n openshift-gitops \
  -o jsonpath='{range .status.resources[*]}{.kind}{"\t"}{.name}{"\t"}{.status}{"\t"}{.health.status}{"\n"}{end}'
```

**Correct verdict logic:** treat aggregate `Progressing` as green **only
if** every resource of kind `Deployment`/`Service`/`StatefulSet`/`PVC`
in that per-resource list reports `Healthy`, and the only non-`Healthy`
entries are the two known `Ingress` resources. If a `Deployment` or
`Service` itself shows anything but `Healthy`, that's the real `Red` —
don't let the known Ingress gap mask a genuinely new problem hiding
behind the same aggregate status.

### 2. Running image digest matches the promoted digest (OBJ-02, the
immutable-artifact guarantee)

**Correction from the original static-source draft:** the `images:`
transform does **not** live in the demo-prod overlay — it's in
`deploy/kustomize/base/kustomization.yaml`, and applies uniformly across
every overlay that inherits from base (per that file's own comment: "the
identical image is promoted unmodified across ephemeral-test ->
demo-prod"). The same digest also appears in the promotion PR's own
commit message (`Promote <sha>: image-registry.../golden-path-agent@
sha256:<digest>`) as a second source, if you want to cross-check against
git history instead of the live overlay.

```bash
grep -A3 '^images:' deploy/kustomize/base/kustomization.yaml
oc get deployment golden-path-agent -n golden-path-agent-demo-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```
**Green:** the two digests are byte-for-byte identical (confirmed live:
`sha256:db408a271673f0d6ce5c6945d9dd531ce97a2ef8348a0c3640a23483e12ed25e`
on both sides). **Red:** any mismatch — this means the running pod is
serving a different image than what GitOps says was promoted, which
breaks the one-immutable-artifact invariant this whole pipeline exists
to guarantee.

### 3. Pods ready

```bash
oc get pods -n golden-path-agent-demo-prod \
  -l app.kubernetes.io/part-of=golden-path-agent
```
Label selector confirmed live — matches all 3 deployments' pods
(`golden-path-agent`, `golden-path-agent-mcp`,
`golden-path-agent-approval`) correctly, nothing missed.

**Green:** all pods `Running`, `READY` shows all containers ready.
**Red:** any pod not ready, or in `CrashLoopBackOff`/`ImagePullBackOff`.

### 4. Recent logs clean

```bash
for d in golden-path-agent golden-path-agent-mcp golden-path-agent-approval; do
  echo "== $d =="
  oc logs deployment/$d -n golden-path-agent-demo-prod --tail=50 | grep -i error
done
```
**Green:** no output (grep finds nothing). **Red:** any error line —
quote it, don't just report "errors found."

## Output format

```
/post-deploy
  [✓] 1. ArgoCD: Synced / Progressing (Ingress-only, known gap -- all
        3 Deployments/Services/PDBs independently Healthy)
  [✓] 2. Image digest matches promoted digest (sha256:db408a27...,
        pinned in deploy/kustomize/base/kustomization.yaml)
  [✓] 3. Pods ready (3/3)
  [✓] 4. Recent logs clean (no errors in last 50 lines, all 3 deployments)

Verdict: promotion verified live in demo-prod.
```
(this is real captured output from a live run against
`golden-path-agent-demo-prod` during `feature/workspace-tooling`'s
release phase, not a hypothetical example)

On any `[✗]`, stop and report — don't paper over a digest mismatch, a
non-Ingress health problem, or a log error with a passing overall
verdict.
