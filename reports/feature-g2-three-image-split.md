# G2 — three-image artifact split: test report

Branch: `feature/g2-three-image-split` (git worktree, not merged, not pushed).
Commit: `042b8ea`. Per `DEC-099`'s single-governance-owner rule, this
branch does **not** touch `DECISIONS.md`/`HANDOFF.md`/`PINS.md` — the
drafted decision entry is at the bottom of this report for the
coordinating session to land at merge.

## Status against the STOP-4 DoD

| DoD item | Status |
|---|---|
| Three green pipelines, each independently promoting its own component's image | **NOT DONE.** Three pipelines authored (`pipelines/pipeline-{agent,mcp,approval}.yaml`) and reviewed for correctness against this cluster's actual, previously-verified Task patterns, but **no live `PipelineRun` was executed this session.** |
| Seeded bad-change eval-gate failure still demonstrably blocks agent promotion, under the new three-pipeline shape | **NOT DONE.** Requires a live agent-pipeline run; not attempted. |
| Demo-prod runs the three fresh, independently-promoted digests | **NOT DONE.** No promotion has run; `deploy/kustomize/base/kustomization.yaml`'s three `images:` entries currently all carry the same pre-existing placeholder digest (`sha256:ba1c4228...`) until each pipeline promotes for real at least once. |
| `make test` / 62-case domain eval baseline pass unchanged | **`make test` equivalent: DONE, verified live** (below). **Domain eval baseline: NOT run** — no model credentials available in this environment (no `.env`); would need to run in a session with real MaaS access. |
| `MCP_MODE=live` validation genuinely exercised and passing | **DONE, verified live** (below) — this is the one item with the strongest, most direct evidence, since it was the specific mechanism DEC-096 flagged as a real risk. |

**Bottom line**: the file-level artifact split (Containerfiles, requirements,
entrypoints, pipelines, kustomize wiring) is complete and locally verified.
Live cluster execution (three real `PipelineRun`s, digest capture,
promotion PRs, demo-prod redeployment, bad-change-gate re-verification) is
**not done** — this is real, separate work requiring either another
session against the live cluster or the owner watching interactively,
consistent with this project's own history of every prior CI/pipeline
change needing multiple live-debugging rounds (Phase C's own C1a-c, per
`DECISIONS.md`).

## What was changed (file-level)

- **Import analysis, done first, not guessed**: grepped every third-party
  import across `agent/`, `mcp_server/`, `approval_service/` to build
  minimal, verified per-component `COPY` lists and `requirements-*.txt`
  files. Key finding: `mcp_server/client.py` (the agent-side calling
  surface) is imported by `agent/nodes/{tool_invoke,human_approval}.py`,
  so it ships inside the **agent** image (not the mcp image) — but its
  `if mcp_mode == "mock": from . import server` branch would `ImportError`
  in the split agent image, since `mcp_server/server.py` (and
  `auth.py`/`schemas.py`/`itsm_store.py`) are deliberately **not** copied
  into the agent image. This makes `MCP_MODE=live` mandatory for the
  split agent image, not just a validation nicety — confirmed and fixed
  everywhere it mattered (see next point).
- **Critical fix, found and applied, not just noted**:
  `deploy/kustomize/overlays/ephemeral-test/kustomization.yaml` was
  setting `MCP_MODE=mock` for the CI-deployed ephemeral agent — this
  would have crash-looped the split agent image on its first tool call,
  and (per `DEC-096`'s own finding, now doubly confirmed) was silently
  routing every ephemeral-test tool call in-process, meaning
  `security-tests.yaml`/`operational-tests.yaml` were **never actually
  proving the deployed agent and MCP pods talk to each other over the
  network**. Flipped to `MCP_MODE=live`; `MCP_TOOL_ENDPOINT` was already
  correctly set to the real Service DNS in `base/configmap.yaml`, so this
  was a one-line, low-risk, high-value fix.
- **Three Containerfiles** (`Containerfile.agent`, `.mcp`, `.approval`),
  each single-purpose (`ENTRYPOINT` only, no positional-arg dispatch —
  `entrypoint.sh`'s `DEC-047` case statement is retired, replaced by three
  one-line `entrypoint-{agent,mcp,approval}.sh` scripts).
- **Three `requirements-*.txt`** files, each containing only the packages
  that component's own code actually imports (verified by grep, not
  assumed) — e.g. `langgraph`/`langchain-core`/`openai`/`pyyaml` are
  agent-only; `mcp`/`pyjwt` mcp/approval-only as applicable. The original
  combined `requirements.txt` is **kept, unchanged** — CI's
  `unit-tests.yaml`/`eval-gate-*.yaml` Tasks install from it to run tests
  against the full checkout, which is unrelated to what ships in the
  production images.
- **`deploy/kustomize/base/kustomization.yaml`**: one `images:` entry
  split into three (`golden-path-agent`, `golden-path-agent-mcp`,
  `golden-path-agent-approval`), each independently digest-pinned.
- **`deploy/kustomize/base/deployment-{agent,mcp,approval}.yaml`**:
  removed the `args: ["agent"|"mcp"|"approval"]` positional dispatch;
  `deployment-mcp.yaml`/`deployment-approval.yaml`'s `image:` field now
  points at their own kustomize image-name key.
- **`pipelines/tasks/deploy-ephemeral.yaml`**: generalized from one
  `image-ref` param to three optional `{agent,mcp,approval}-image-ref`
  params (default `""` = "leave this component's committed digest
  untouched") — this is the mechanism that lets one pipeline test its
  fresh build against the other two components' last-promoted digests,
  which is the only sane integration-test shape once builds/promotions
  are independent.
- **`pipelines/tasks/open-promotion-pr.yaml`**: added `image-name` (which
  kustomize `images[].name` entry to edit) and `component` (for
  collision-free branch naming) params. The original Task's blind
  `sed -i "s#digest: sha256:.*#...#"` would have corrupted **all three**
  digest lines at once now that there's more than one — replaced with a
  sed **address range** scoped to the one `- name: <image-name>` block,
  verified against the file's own real three-line-per-entry shape.
  Branch name is now `promote/<component>/<sha>`, not `promote/<sha>` —
  three independent pipelines can otherwise promote off the same commit
  and collide on branch name.
- **Two new lean per-component Tasks**: `mcp-operational-test.yaml`
  (NetworkPolicy negative-proof + a real end-to-end tool call through the
  agent, proving the freshly-deployed MCP pod actually works) and
  `approval-operational-test.yaml` (NetworkPolicy negative-proof +
  `/healthz` via an allowed caller). Neither duplicates
  `security-tests.yaml`'s agent-specific `rest-zero-mutation-check`,
  which stays agent-pipeline-only.
- **Three Pipelines** (`pipeline-{agent,mcp,approval}.yaml`) and three
  `PipelineRun` templates, replacing `pipeline.yaml`/
  `pipelinerun-template.yaml` (deleted). The agent pipeline keeps the
  full original gate set (`unit-tests`, `eval-gate-offline`,
  `policy-validate`, `eval-gate-live`, `security-tests`,
  `operational-tests`) since none of those were ever mcp/approval-specific.
  mcp/approval pipelines run `unit-tests` (still valuable — a schema/store
  change can break agent-side contracts pytest already covers) plus their
  own new operational-test Task.
- **`scripts/dev.sh`**, **`Makefile`**, **`scripts/bootstrap.sh`**: updated
  to build/apply the three images/pipelines instead of the retired single
  ones — all three were genuinely broken by the split until fixed (`make
  build`/`make up` would have failed outright on a missing
  `./Containerfile`; `bootstrap.sh` would have failed applying a deleted
  `pipelines/pipeline.yaml`).
- **`docs/architecture.md`**: "One image, two runtime roles" section
  (already stale before this session — it said *two* roles when the repo
  had *three* since `DEC-047`) rewritten to describe the three-image
  reality.

## Live local verification (commands run, actual output)

**1. All three images build independently** (`make build`, podman):
```
$ make build
...
Successfully tagged localhost/golden-path-agent:dev
Successfully tagged localhost/golden-path-agent-mcp:dev
Successfully tagged localhost/golden-path-agent-approval:dev

$ podman images | grep golden-path-agent
localhost/golden-path-agent-approval   dev   a69c3950e93b   201 MB
localhost/golden-path-agent-mcp        dev   882327ca1839   197 MB
localhost/golden-path-agent            dev   6e25e31a6d0f   243 MB
```

**2. Full pytest suite, run inside a `python:3.12-slim` container against
the split worktree** (matches `unit-tests.yaml`'s own method exactly):
```
253 passed, 1 skipped, 1 warning in 8.94s
```
Matches `DEC-096`'s own recorded baseline (254 total) exactly — the split
introduced zero test regressions.

**3. Local dev stack up, all four containers healthy**
(`./scripts/dev.sh up --offline`):
```
$ podman ps --format "{{.Names}}\t{{.Status}}"
golden-path-agent-mcp-dev        Up 7 seconds
golden-path-agent-approval-dev   Up 5 seconds
golden-path-agent-dev            Up 4 seconds
golden-path-otel-collector-dev   Up 7 seconds

$ curl -sf http://localhost:18080/healthz
{"status":"ok"}
$ curl -sf http://localhost:18082/healthz
{"status":"ok"}
```

**4. `MCP_MODE=live` genuine cross-container network round trip** — the
one piece of evidence this session most needed to produce. Ran inside the
**agent** container (proving the split agent image's own
`mcp_server/client.py` reaches the separately-running **mcp** container
over the network, not in-process):
```
$ podman exec -e PYTHONPATH=/opt/app-root/src -w /opt/app-root/src \
    golden-path-agent-dev python3 /tmp/mcp_live_check.py
MCP_MODE in agent container: live
MCP_TOOL_ENDPOINT: http://golden-path-agent-mcp-dev:8081
REAL NETWORK CALL RESULT: {'records': [{'record_id': 'INC-10240', 'record_type': 'incident',
  'status': 'open', 'short_description': 'Namespace quota exhaustion blocking new workload
  deployment', 'opened_at': '2026-08-01T10:30:00Z', 'updated_at': '2026-08-01T10:30:00Z',
  'owner_team': 'platform-capacity'}], 'count': 1, 'source': 'mock-itsm'}
```
An intermediate run (before fixing the test script's own tool arguments)
failed with a real HTTP 500, whose traceback — captured from the **mcp**
container's own logs — confirmed the request physically reached
`mcp_server/server.py`'s `rest_call_tool` handler inside the separate
container before failing on an unrelated missing-argument issue in my
test script, not a defect in the split. Corrected and re-run to the clean
success above.

Stack torn down after verification (`./scripts/dev.sh down`); scratch
verification script removed before commit.

## Real gaps and judgment calls found — named, not silently absorbed

1. **Shared ephemeral-test namespace is a real concurrency hazard.**
   `pipelines/bootstrap/namespaces.yaml` provisions exactly one
   `golden-path-agent-ephemeral-test` namespace, and all three
   Deployments there have fixed names. Three pipelines' `deploy-ephemeral`
   phases **must not run concurrently** — they would stomp on each
   other's in-flight ephemeral deployment. This session did not
   parameterize the ephemeral namespace/suffix per pipeline (real
   additional infra work); until that's done, run the three pipelines'
   ephemeral-test phases sequentially, not simultaneously. This is a
   genuine constraint on "independent," not just an operational footnote
   — flagging for the owner to decide whether it's acceptable as-is or
   needs a follow-up.
2. **`approval-operational-test.yaml` does not exercise the full
   `SRS-APR-IF-01`/`IF-02` propose-then-decide contract** — only
   reachability/health. A real round trip needs OIDC credentials minted
   for the Task; not wired up this session (would be real scope beyond
   "split the artifact"). Named here rather than silently assumed covered.
3. **Pre-existing test-design weakness inherited, not introduced or
   fixed**: `security-tests.yaml`'s (and now `mcp-operational-test.yaml`'s
   and `approval-operational-test.yaml`'s) `disallowed-egress-proof` step
   curls `.../healthz` on the MCP/approval Service and treats any `curl
   -sf` failure as "NetworkPolicy blocked it." Verified locally that
   `mcp_server/server.py` has **no `/healthz` route at all** (confirmed:
   `curl -v` returns a clean `404 Not Found`, not a connection failure) —
   so this check cannot actually distinguish "blocked by NetworkPolicy"
   from "route doesn't exist" for the MCP case. This is not new — it was
   already true of the original `security-tests.yaml` before this
   session — but copying the pattern into two new Tasks doubles its
   footprint. Recommend a follow-up: target a route that genuinely
   returns 200 for an allowed caller (e.g. a `POST /tools/healthcheck`
   call) instead of a nonexistent `/healthz`, so the negative test is
   unambiguous.
4. **`corpus/ingest.py` depends on `eval/corpus-manifest.yaml` at a
   repo-root-relative path** (`Path(__file__).resolve().parent.parent /
   "eval" / "corpus-manifest.yaml"`), which is **not** copied into any of
   the three images (nor was it in the original single image). Whether
   this is exercised by the live deployed agent at all, or is dev/eval-CLI
   only, was not fully resolved this session — pre-existing, unrelated to
   the split, not fixed, named so it isn't mistaken for something this
   change introduced.
5. **Placeholder digest**: all three `images:` entries in
   `kustomization.yaml` currently share the same pre-existing placeholder
   digest (`sha256:ba1c4228...`) until each pipeline promotes for real —
   expected and harmless, but worth knowing before reading that file cold.

## Immediate next steps (not done this session)

1. Apply the three Pipelines + updated Tasks to the live cluster
   (`oc apply -f pipelines/pipeline-{agent,mcp,approval}.yaml -n
   golden-path-agent-ci`, `oc apply -f pipelines/tasks/ -n
   golden-path-agent-ci`) and trigger each `PipelineRun` in turn
   (sequentially, per gap 1 above).
2. Confirm each pipeline's own STOP-4 evidence live: green run, correct
   digest promoted, demo-prod rollout status.
3. Re-verify the seeded bad-change gate specifically on the **agent**
   pipeline (the one carrying `eval-gate-live`/`policy-validate`), since
   that's the gate `DEC-099`'s merge-order rule is actually waiting on.
4. Only once (3) passes: G1's held tail (ArgoCD repoint + approval-service
   extraction to the Platform Foundation) may proceed, per `DEC-099`.

## Drafted decision entry (numbered as a placeholder — land at the
coordinating session's own next available `DEC-NNN`, wording free to
adjust to match the log's exact tail at merge time)

```
## DEC-1xx — G2: monolithic image split into three independent,
independently-buildable artifacts (agent/mcp/approval); MCP_MODE=live
ephemeral-test fix; three pipelines authored, NOT yet run live

**Context**: DEC-099's Stage 1, second parallel stream (alongside G1's
Gitea stand-up). Ran in worktree branch `feature/g2-three-image-split`
per DEC-099's worktree-isolation rule; this coordinating session lands
this entry, the worktree stream never touched DECISIONS.md/HANDOFF.md/
PINS.md directly.

**What changed**: three Containerfiles (agent/mcp/approval) with
import-verified minimal COPY lists and per-component requirements files
replace the single Containerfile + entrypoint.sh positional-role
dispatch (DEC-047's case statement retired). Three independent Tekton
Pipelines replace golden-path-agent-ci; deploy-ephemeral now overrides
only the digest of the component under test (the other two render at
their last-promoted committed digest — the standard "test against
what's deployed" pattern, and the only one that makes sense once builds
promote independently); open-promotion-pr's digest edit is now
range-scoped per image name (the original blind sed would have
corrupted all three digest lines once there was more than one) and its
promotion branch name is component-qualified to avoid collisions when
multiple pipelines promote off the same commit.

**Critical fix found and applied**: ephemeral-test's committed
MCP_MODE=mock would have crash-looped the split agent image (which
deliberately excludes mcp_server/server.py — MCP_MODE=mock's in-process
fallback does `from . import server`) and was silently routing every
ephemeral-test tool call in-process regardless — the exact DEC-096 gap,
now confirmed to also apply to the CI ephemeral-test path, not just
local dev. Flipped to MCP_MODE=live (MCP_TOOL_ENDPOINT was already
correctly Service-DNS-pointed in base/configmap.yaml).

**Verified live, locally**: all three images build independently; the
full pytest suite passes unchanged (253 passed, 1 skipped, matching
DEC-096's own baseline); a genuine cross-container MCP_MODE=live network
round trip confirmed via the local dev stack (agent container's
mcp_server.client.call_tool() reaching the separate mcp container over
the podman bridge network, real ITSM record returned).

**NOT done, explicitly**: no live Tekton PipelineRun was executed against
the showcase cluster this session. No digest has been captured, no
promotion PR opened, demo-prod has not been redeployed with the three
independent digests, and the seeded bad-change eval-gate has not been
re-verified under the new three-pipeline shape. STOP 4 is therefore NOT
yet cleared — this entry records the artifact-split design and its local
verification, not the live-cluster DoD.

**Named gaps, not silently absorbed**: (1) the shared
golden-path-agent-ephemeral-test namespace means the three pipelines'
ephemeral-test phases cannot run concurrently without a further
namespace-parameterization change, not built this session; (2)
approval-operational-test.yaml checks reachability/health only, not a
full SRS-APR-IF-01/IF-02 round trip (needs OIDC credentials not wired up
this session); (3) the disallowed-egress-proof pattern (inherited from
security-tests.yaml, now also in the two new operational-test Tasks)
curls a /healthz route that mcp_server/server.py does not actually have,
so it cannot distinguish "NetworkPolicy blocked" from "route doesn't
exist" -- pre-existing weakness, not introduced or fixed here; (4)
corpus/ingest.py's eval/corpus-manifest.yaml dependency (a repo-relative
path never copied into any image, before or after this split) was
noticed but not resolved -- unclear if it's exercised by the deployed
agent at all.

**Status**: Design and local verification complete. Live-cluster
execution and STOP 4 remain open -- see reports/feature-g2-three-image-split.md
for the full evidence and immediate next steps.
```
