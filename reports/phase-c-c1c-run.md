# Phase C, Step C1c — first real green `PipelineRun`, evidence report

**Run:** `PipelineRun/golden-path-agent-ci-xscz6`, namespace
`golden-path-agent-ci`, triggered against `main` at commit `3be02cb`
(`oc create -f pipelines/pipelinerun-template.yaml -n golden-path-agent-ci`).
**Result:** `status=False reason=Failed` — but the only failing stage is
`open-promotion-pr`, on the expected, correct cause (§4). Every other
stage succeeded.

This is the tenth `PipelineRun` this step produced (`golden-path-agent-ci-*`,
run identifiers `-jw2sr` through `-xscz6`); the prior nine each surfaced a
genuine cluster/config constraint, fixed and documented as its own
`DECISIONS.md` entry (`DEC-023` through `DEC-035`). This report covers
only the final, green run and the fixes that unblocked it
(`DEC-034`/`DEC-035`), not the full nine-run history — see `DECISIONS.md`
for the complete investigation trail.

## 1. Per-stage results

| Stage | Result | Duration |
|---|---|---|
| `fetch-source` | Succeeded | 9s |
| `unit-tests` | Succeeded | 20s |
| `eval-gate-offline` | Succeeded | 19s |
| `policy-validate` | Succeeded | 9s |
| `container-build` | Succeeded | 24s |
| `digest-capture` | Succeeded | 7s |
| `sbom-generate` | Succeeded | 10s |
| `deploy-ephemeral` | Succeeded | 21s |
| `eval-gate-live` | Succeeded | 36s (full live 8-domain-category suite) |
| `security-tests` | Succeeded | 15s |
| `operational-tests` | Succeeded | 21s |
| `destroy-ephemeral` | Succeeded | 4s |
| `open-promotion-pr` | **Failed (expected)** | 35s |

## 2. Digest chain — confirmed identical end to end

- `container-build` (buildah, cluster `Task` via the `cluster` resolver)
  pushed to this project's own `ImageStream`.
- `digest-capture`'s `TaskRun` result: `digest =
  sha256:3773367a47c8bd67fc8d82ad03903b243a67c9bd769b8f4af811b730b437bcb6`.
- The live `ImageStreamTag` (`golden-path-agent:pr-3be02cb8d13bde2bb40ea4ce821d5fd34e4b082f`)
  itself resolves to the identical
  `...@sha256:3773367a47c8bd67fc8d82ad03903b243a67c9bd769b8f4af811b730b437bcb6`.
- `deploy-ephemeral`'s own `TaskRun` spec shows it received exactly that
  same digest as its `image-ref` param.
- `open-promotion-pr`'s own `TaskRun` spec (params recorded even though
  the `Task` itself never ran a container) shows it would have received
  the identical digest — `pipeline.yaml` interpolates
  `$(tasks.digest-capture.results.digest)` into both call sites, confirmed
  by direct inspection of `pipeline.yaml`, not just by matching values.

## 3. Zero-mutation check — live REST, against the deployed pod

`security-tests`' `rest-zero-mutation-check` step output (verbatim,
`oc logs`):

```
OK: 2 request records before and after a rejected write -- zero mutation confirmed.
```

This exercised the deployed agent pod's real `/invoke` → `/approvals/{id}/resume`
→ `/records` HTTP surface (via `oc exec -i ... -- python3 -`, `DEC-034`),
not the local Podman path — the C1c requirement this stage exists to
prove.

## 4. `operational-tests` — live fallback recovery confirmed

`kill-primary-fallback-check` output (verbatim): a throwaway `Deployment`
with a deliberately broken primary model endpoint
(`https://model-endpoint.invalid/v1`) still returned a correct,
non-escalated answer (a real ITSM tool call/result for `INC-10240`),
proving the fallback route (`DEC-035`'s fix — previously entirely absent
from the K8s-deployed config path) actually absorbed the failure, live.

## 5. `destroy-ephemeral` — namespace left intact and clean

- `oc get namespace golden-path-agent-ephemeral-test`: `Active`, not
  deleted (by design, `DEC-024`).
- `oc get deployment,replicaset,pod,service,networkpolicy,pdb,ingress,configmap,secret,serviceaccount
  -n golden-path-agent-ephemeral-test`: zero `Deployment`/`ReplicaSet`/
  `Pod`/`Service`/`NetworkPolicy`/`PodDisruptionBudget`/`Ingress` objects
  remain. Only OpenShift's own baseline objects (CA-bundle `ConfigMap`s,
  default `ServiceAccount` `dockercfg` `Secret`s) and the C1a-bootstrapped
  `golden-path-agent-secrets` `Secret` remain — nothing left over from
  this run's own workloads.

## 6. `open-promotion-pr` — expected, correct failure

```
Warning  Failed  kubelet  Error: secret "golden-path-agent-github-token" not found
```

The GitHub PAT has not been created yet (`docs/phase-c-runbook.md` §3 —
a deliberate, pending manual step). This is the expected and correct
outcome: the stage fails closed, with a plain, non-secret-leaking error,
rather than silently skipping or using a broader credential. It also
incidentally proves the stage cannot run without the credential existing
— no accidental fallback path.

## 7. Secret-material log/spec inspection (direct, not inferred)

- `eval-gate-live`, `security-tests`, `operational-tests` logs
  (`oc logs`, all containers): grepped for
  `api[_-]?key|bearer|authorization` (case-insensitive) — zero matches in
  all three.
- `open-promotion-pr`'s `TaskRun` object (`oc get taskrun -o json`):
  walked recursively for any GitHub PAT-shaped string
  (`ghp_...`/`github_pat_...`) — none found (expected: the container
  never started, so the env var was never resolved to a value at all).
- The `PipelineRun`'s own object (`oc get pipelinerun -o json`): same
  PAT-pattern scan across the full serialized spec/status — none found.
- No tracked file in this commit range contains a real model-endpoint URL
  or model name (`git diff` on the changed files, grepped for the real
  values) — confirmed clean before pushing (`DEC-035`).

## 8. Conclusion

Checkpoint C1c's evidence requirements are met: the green path runs
end to end through the expected, correct `open-promotion-pr` failure;
the digest chain is provably identical at every hop; the zero-mutation
check ran against the live deployed pod's real REST surface; fallback
recovery is proven live for the first time; `destroy-ephemeral` leaves
the namespace intact and clean; no secret material appears in any
inspected log or spec.

**Done, in a follow-up run:** the GitHub PAT was created and the real
promotion PR exercised — see §10 below. That was originally deferred out
of this report's own scope; recorded here once it closed rather than in
a separate document, since it's the direct conclusion of this same
Step C1c.

## 9. Findings — patterns worth carrying forward

**Environment-injected config completeness (`DEC-035`).** This is the
**second** independent instance of the same failure shape: a deployment
surface silently missing a key `agent/config.py` (the canonical
consumer) actually requires, undetected until the one stage that
exercises it finally runs. First instance: R4's `scripts/dev.sh` missing
`MODEL_API_KEY`/fallback vars for local dev. Second: none of the
K8s-facing config surfaces (base `ConfigMap`, `ephemeral-test` overlay,
the live `golden-path-agent-ci-config`) ever declared
`MODEL_FALLBACK_API_BASE_URL`/`MODEL_FALLBACK_NAME` — invisible for the
entire C1a–C1c build-out because `operational-tests` (the one stage that
exercises the fallback route) never reached its own HTTP call until
`DEC-034`'s unrelated `curl` fix unblocked it. Two instances of the same
class of gap is a pattern, not a coincidence. Added to the
post-Checkpoint-C backlog (`docs/phase-c-runbook.md` §5/6/7, item 3,
same priority tier as model-identity capture and OTel wiring): a
mechanical config-contract completeness check, deriving the required key
set from `agent/config.py`'s own `_env(...)` calls and validating every
deployment surface declares each one — cheap, and it closes off a third
instance before it can happen.

**Shared-workspace contamination across Tasks in one `PipelineRun`
(`DEC-036`/`DEC-037`).** A related but distinct pattern, surfaced while
provisioning the promotion-PR credential: `deploy-ephemeral`'s
`kustomize edit set image` call mutates
`deploy/kustomize/base/kustomization.yaml` **in place**, and — because
every Task in a `PipelineRun` shares the same PVC-backed `source`
workspace, not just the Task that wrote it — that mutation was still
present, unreverted, when `open-promotion-pr` ran later in the same run
and sed-patched a digest onto an already-wrong file (wrong registry
hostname, whole-file reformatting). `DEC-031`'s own design note ("this
scratch, uncommitted workspace checkout") assumed the mutation was scoped
to `deploy-ephemeral`'s own concerns; it was not. Fixed by reverting the
file (`git checkout --`) once its content is captured into
`rendered-ephemeral.yaml`, the only artifact any later step actually
needs. Worth naming explicitly for a future reviewer: any Task in this
pipeline that edits a file in the shared `source` workspace for its own
transient purposes needs to either revert the mutation before exiting, or
operate on an isolated copy — the workspace is pipeline-lifetime-shared,
not Task-scoped, and nothing in Tekton enforces that isolation
automatically.

## 10. The real promotion PR (`PipelineRun/golden-path-agent-ci-bmrfm`)

A first retry with the owner's initial PAT (`golden-path-agent-ci-tgt6g`)
still failed — not on either bug above (both were confirmed fixed there:
the commit was already the correct one-field diff, and the auth mechanism
reached GitHub cleanly), but on a GitHub-side 403: `Permission to
DarkDragonEl/golden-path-agent-template.git denied to DarkDragonEl`. A
read-only API diagnostic (a throwaway pod, never printing the token)
confirmed the token correctly authenticated as `DarkDragonEl` but most
likely lacked the `Contents: Read and write` permission when created.
The owner supplied a new PAT; the `Secret` was updated in place, and a
fresh `PipelineRun` (`golden-path-agent-ci-bmrfm`) was triggered from
`main` (not a repair of the half-completed prior workspace, to avoid
reusing a partially-mutated PVC — see `DECISIONS.md` `DEC-039`).

**Fully green, first time end to end** — all twelve stages, including
`open-promotion-pr`. Verified directly against the GitHub API (not
inferred from pipeline status):

```
GET /repos/DarkDragonEl/golden-path-agent-template/pulls?state=open
-> 1 PR: #1, head=promote/19a8876..., base=main

GET /repos/DarkDragonEl/golden-path-agent-template/pulls/1/files
-> 1 file changed, 1 addition, 1 deletion:

--- deploy/kustomize/base/kustomization.yaml ---
@@ -32,4 +32,4 @@ commonLabels:
 images:
   - name: golden-path-agent
     newName: REGISTRY_PLACEHOLDER/golden-path-agent
-    digest: sha256:0000000000000000000000000000000000000000000000000000000000000
+    digest: sha256:d73ce33214c64fdfa19388ebbd111d1e8c24e0e17996e31b4b0df57549a242ac
```

`newName` untouched — `DEC-037`'s workspace-contamination fix holding
under a real, successful push. Digest chain confirmed identical, read
directly from each object: `digest-capture`'s result, `deploy-ephemeral`'s
and `open-promotion-pr`'s received `image-ref` params, the live
`ImageStreamTag`'s `dockerImageReference`, and the PR diff itself — all
`sha256:d73ce33214c64fdfa19388ebbd111d1e8c24e0e17996e31b4b0df57549a242ac`.

**Not merged.** Merging is the promotion event and stays behind the
owner's explicit authorization — holding at the pre-C3/C4 STOP with this
PR diff and the prepared C3/C4 manifest package presented together.

**Holding here, per instruction, before Step C1d** (negative proof #1,
seeded bad change) — since resolved; see `DECISIONS.md` `DEC-038` and
`reports/phase-c-c1d-run.md`.
