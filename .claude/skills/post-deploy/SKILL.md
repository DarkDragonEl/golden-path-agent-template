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

**`[NOT LIVE-TESTED]` — cluster access was excluded from the mission
that wrote this file (a separate session held live cluster access at
the time; see `reports/feature-workspace-tooling.md` for why). Every
name below is grounded in real source
(`deploy/argocd/apps/demo-prod.yaml`,
`deploy/kustomize/overlays/demo-prod/`) but this skill has never been
run against a real cluster. Live-test it after this branch merges.**

## Checks, in order

### 1. ArgoCD Application synced and healthy

The real Application object is `golden-path-agent-demo-prod` in
namespace `openshift-gitops` (source: `deploy/kustomize/overlays/demo-prod`,
confirmed from `deploy/argocd/apps/demo-prod.yaml` — auto-sync is on
there, the promotion PR merge is the human gate, not a manual `oc apply`):

```bash
oc get application golden-path-agent-demo-prod -n openshift-gitops \
  -o jsonpath='{.status.sync.status}{"\t"}{.status.health.status}{"\n"}'
```
**Green:** `Synced` / `Healthy`. **Red:** anything else — if it's still
`Progressing`, wait and recheck rather than treating it as a hard
failure; `OutOfSync` or `Degraded` is a real finding.

### 2. Running image digest matches the promoted digest (OBJ-02, the
immutable-artifact guarantee)

The promotion mechanism commits the promoted digest into the demo-prod
overlay's kustomize `images:` override (the same digest also appears
literally in the promotion PR's own commit message, e.g. `Promote
<sha>: image-registry.../golden-path-agent@sha256:<digest>` — cross-
check against that commit if you want a second source):

```bash
grep -A5 '^images:' deploy/kustomize/overlays/demo-prod/kustomization.yaml
oc get deployment golden-path-agent -n golden-path-agent-demo-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
```
**Green:** the two digests are byte-for-byte identical. **Red:** any
mismatch — this means the running pod is serving a different image than
what GitOps says was promoted, which breaks the one-immutable-artifact
invariant this whole pipeline exists to guarantee.

### 3. Pods ready

```bash
oc get pods -n golden-path-agent-demo-prod \
  -l app.kubernetes.io/part-of=golden-path-agent
# [VERIFY ON FIRST LIVE RUN] confirm this label selector matches the
# base Deployments' actual pod-template labels; if it returns nothing,
# fall back to a bare `oc get pods -n golden-path-agent-demo-prod`.
```
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
  [✓] 1. ArgoCD: Synced / Healthy
  [✓] 2. Image digest matches promoted digest (sha256:db408a27...)
  [✓] 3. Pods ready (3/3)
  [✓] 4. Recent logs clean (no errors in last 50 lines, all 3 deployments)

Verdict: promotion verified live in demo-prod.
```
On any `[✗]`, stop and report — don't paper over a digest mismatch or a
log error with a passing overall verdict.
