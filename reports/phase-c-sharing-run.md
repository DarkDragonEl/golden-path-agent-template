# Phase C sharing artifact — live pipeline run, seeded gate failure, digest promotion

Per `E2E_DEMO_PLAN.md`'s E3 ("after C: showcase cluster live — pipeline
runs, the seeded gate failure, digest promotion; colleagues can watch a
`PipelineRun`"), this is the Phase C sharing moment. **One caveat up
front, stated plainly**: this was captured on the shared SNO lab cluster
this milestone actually used (`docs/environments.md`'s own shared-cluster
deviation note), not yet the dedicated Phase E showcase cluster — the
Git-bootstrapped artifacts here (`pipelines/`, `deploy/argocd/`) are
exactly what Phase E replays there; this is the first live proof they
work, not a doctored preview.

**Captured:** 2026-08-22. Every transcript below is real `oc`-captured
output — cluster-internal hostnames/registry paths are this project's own
already-public namespace names (`golden-path-agent-ci`, etc.), never a
real external endpoint; the live MaaS model endpoint itself never appears
(same anonymity discipline as Phase B's own sharing artifact).

## What a colleague is watching

1. A real `PipelineRun`, triggered against `main`, going green end to
   end — twelve stages, including a live model call and a real GitHub PR.
2. The exact same pipeline, triggered against a one-line seeded
   regression on a throwaway branch — failing at the gate, correctly,
   with no promotion.
3. The digest that promotion PR carries landing, unmodified, on the
   cluster's own always-on `demo-prod` deployment via GitOps sync.

## 1. The green run (`PipelineRun/golden-path-agent-ci-bmrfm`)

```
$ oc get taskrun -n golden-path-agent-ci -l tekton.dev/pipelineRun=golden-path-agent-ci-bmrfm

NAME                                              SUCCEEDED   REASON      DURATION
golden-path-agent-ci-bmrfm-fetch-source           True        Succeeded   10s
golden-path-agent-ci-bmrfm-unit-tests             True        Succeeded   20s
golden-path-agent-ci-bmrfm-eval-gate-offline      True        Succeeded   19s
golden-path-agent-ci-bmrfm-policy-validate        True        Succeeded   8s
golden-path-agent-ci-bmrfm-container-build        True        Succeeded   23s
golden-path-agent-ci-bmrfm-digest-capture         True        Succeeded   4s
golden-path-agent-ci-bmrfm-sbom-generate          True        Succeeded   10s
golden-path-agent-ci-bmrfm-deploy-ephemeral       True        Succeeded   21s
golden-path-agent-ci-bmrfm-eval-gate-live         True        Succeeded   26s   # full live 8-domain-category suite, real model
golden-path-agent-ci-bmrfm-security-tests         True        Succeeded   15s   # live zero-mutation check over real HTTP
golden-path-agent-ci-bmrfm-operational-tests      True        Succeeded   21s   # live kill-primary, fallback route absorbs it
golden-path-agent-ci-bmrfm-destroy-ephemeral      True        Succeeded   23s
golden-path-agent-ci-bmrfm-open-promotion-pr      True        Succeeded   32s   # opens the real GitHub PR

$ echo $?
0
```

The promotion PR this run opened: **[PR #1](https://github.com/DarkDragonEl/golden-path-agent-template/pull/1)**
(now merged), whose entire diff was one line:

```diff
 images:
   - name: golden-path-agent
     newName: image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci/golden-path-agent
-    digest: sha256:0000000000000000000000000000000000000000000000000000000000000
+    digest: sha256:d73ce33214c64fdfa19388ebbd111d1e8c24e0e17996e31b4b0df57549a242ac
```

## 2. The seeded gate failure (`PipelineRun/golden-path-agent-ci-c1d-pg8xq`)

Same `Pipeline` object, no special-casing — only the `revision` param
pointed at `test/c1d-seeded-eval-failure`, a branch carrying exactly one
seeded line (`policy/approval_rules.yaml`: a write-classified action
flipped to read-classified — a write silently skipping human approval).

```
$ oc get taskrun -n golden-path-agent-ci -l tekton.dev/pipelineRun=golden-path-agent-ci-c1d-pg8xq

NAME                                                SUCCEEDED   REASON
golden-path-agent-ci-c1d-pg8xq-fetch-source         True        Succeeded
golden-path-agent-ci-c1d-pg8xq-unit-tests           False       Failed
golden-path-agent-ci-c1d-pg8xq-eval-gate-offline    False       Failed
golden-path-agent-ci-c1d-pg8xq-policy-validate      False       Failed
golden-path-agent-ci-c1d-pg8xq-destroy-ephemeral    True        Succeeded   # finally: -- still runs, nothing to clean up

# container-build, digest-capture, sbom-generate, deploy-ephemeral,
# eval-gate-live, security-tests, operational-tests, open-promotion-pr:
# never appear here at all -- skipped, not failed, by normal Tekton DAG
# semantics once their upstream dependencies failed.

$ echo $?
1
```

The targeted proof — `eval-gate-offline`'s own output:

```
[PASS] EXAMPLE-001
[FAIL] EXAMPLE-002
    - invoke state_equals: expected 'pending_approval'==True, got False
    - invoke no_final_output: expected no final_output yet, got 'PLACEHOLDER_TOOL_RESPONSE_MARKER'

1/2 cases passed
```

**Two more gates independently caught the exact same one-line
regression**, through two completely different mechanisms — not staged
for effect, just what actually happened: `unit-tests` failed 4 separate
assertions tracing to the same root cause, and `policy-validate`'s own
drift check fired (`'placeholder_write_action':
policy/approval_rules.yaml='read' vs
policy/opa/approval_policy.rego='write'`) while `opa test` itself stayed
green (11/11) — correctly isolating that only the sync, not the rego
bundle's own logic, was broken.

**No promotion PR opened** — confirmed directly against GitHub, not
inferred from pipeline status: `GET
/repos/DarkDragonEl/golden-path-agent-template/pulls?state=all` returned
zero PRs at the time of this run. The seeded branch was never merged;
`main` was never touched.

## 3. Digest promotion, end to end

```
$ git log origin/main --oneline -1
de30536 Promote 19a8876f9137: golden-path-agent digest

$ oc get pod -n golden-path-agent-demo-prod -o jsonpath='{range .items[*]}{.metadata.name}{": "}{.spec.containers[0].image}{"\n"}{end}'
golden-path-agent-...: image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci/golden-path-agent@sha256:d73ce33214c64fdfa19388ebbd111d1e8c24e0e17996e31b4b0df57549a242ac
golden-path-agent-mcp-...: image-registry.openshift-image-registry.svc:5000/golden-path-agent-ci/golden-path-agent@sha256:d73ce33214c64fdfa19388ebbd111d1e8c24e0e17996e31b4b0df57549a242ac
```

Same digest, three independent sources: the build/`ImageStreamTag`,
what `main`'s merged commit carries, and what `demo-prod` is actually
running — sourced from one GitOps commit, never rebuilt, applied by
nothing but ArgoCD's own sync of that commit.

## What this shows

- **The gate is real, not theater.** A genuine one-line regression fails
  the pipeline, correctly, through multiple independent mechanisms — not
  a staged demo where the "bad" path is obviously different machinery
  from the "good" path.
- **Promotion is exclusively a reviewed PR merge.** No rebuild, no direct
  push, no bypass — the PR diff a human actually reviewed is the exact
  digest running in `demo-prod`.
- **`destroy-ephemeral` and `open-promotion-pr`'s skip/never-run behavior
  are both correct DAG semantics**, not something scripted around a
  specific failure — the same `Pipeline` definition produces both
  outcomes depending purely on whether the gates pass.

## What this is NOT yet

Not yet run on the Phase E showcase cluster (this milestone's SNO is
shared/pre-existing, not Git-bootstrapped from scratch — operator
installation is the one leg Phase C could not exercise, per
`docs/environments.md`). Not yet the full Phase D clickable flow
(approval trilogy, end-to-end trace) — that's the next sharing moment.
Model-identity capture and cluster-tier OTel wiring are named,
prioritized post-Checkpoint-C work, not part of this evidence.
