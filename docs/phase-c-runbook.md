# Phase C runbook — manual bootstrap steps

Everything in this file is a **deliberate manual step**, done once by a
human operator with cluster access, never by the Tekton pipeline itself.
`DECISIONS.md` `DEC-024` records why: the pipeline's own `ServiceAccount`
(`pipelines/bootstrap/rbac.yaml`) is granted the minimum this project's own
namespaces need and nothing else — no cluster-scoped permissions, no
secret-material handling. These steps exist precisely because the pipeline
must not be trusted with them.

## Coverage shape: what each stage actually tests (read this before the
"why is eval-gate-live in-process" question comes up)

`DECISIONS.md` `DEC-025` records the finding; this is the explicit
statement of its consequence, written down before a reviewing architect
has to ask. **No single stage runs all 8 domain categories against the
deployed pods.** That's a deliberate split, not a gap:

- `eval-gate-live` tests **reasoning quality against the real model**, all
  8 domain categories, `DEC-017`'s exact deterministic-sampling contract —
  but in-process (`eval.cli run --domain`, unchanged from Phase B). Whether
  the agent decides correctly, cites correctly, refuses correctly does not
  change depending on which pod the process happens to run in — the model
  call, the prompt, the retrieval logic are identical either way.
- `security-tests`/`operational-tests` test **what the deployment
  actually changes**: environment injection (does the real `Secret`/
  `ConfigMap` reach the running container correctly), networking (does the
  `NetworkPolicy` actually block what it claims), the write path end to
  end over real HTTP (zero-mutation on a rejected write, against the
  live pod, not the in-process graph), and fallback (does the deployed
  pod's own `RoutedModelClient` actually recover from a broken primary).
  These are exactly the properties that *can* differ between "runs
  correctly on my laptop" and "runs correctly as a deployed pod," and
  exactly the properties an in-process eval run can never exercise.

**Named phase-two integration point**: an HTTP-based eval executor (one
that drives the eval case set against a deployed agent's `/invoke`/
`/approvals/{id}/resume` REST surface instead of `agent.graph.build_graph()`
in-process) would let a single stage genuinely test all 8 categories
against the real deployed pods. Not built now — real, unbudgeted scope for
Step C1b. It lands naturally alongside Phase D's real approval-service
component, which needs the same kind of REST-driven test harness for its
own `/proposals` API — one executor, not two, when that work starts.

## 1. Namespace + RBAC bootstrap (done — Step C1a)

```sh
oc apply -f pipelines/bootstrap/namespaces.yaml
oc apply -f pipelines/bootstrap/rbac.yaml
```

Creates `golden-path-agent-ci` and `golden-path-agent-ephemeral-test`
(both standing, not per-run — see `docs/environments.md`'s "Ephemeral-test
namespace lifecycle" section for why), the pipeline's `ServiceAccount`, and
its least-privilege `Role`/`RoleBinding`s. Verify the RBAC actually lands
scoped as intended before trusting it — don't assume from the YAML alone:

```sh
oc auth can-i create deployments \
  --as=system:serviceaccount:golden-path-agent-ci:golden-path-agent-ci-pipeline \
  -n golden-path-agent-ephemeral-test   # expect: yes
oc auth can-i create namespace \
  --as=system:serviceaccount:golden-path-agent-ci:golden-path-agent-ci-pipeline
  # expect: no -- this is the check that actually proves "no cluster-scoped
  # permission," not just an absence of a ClusterRoleBinding in the YAML
```

## 2. Model-endpoint credential (done — Step C1a; a second copy added at
Step C1c, `DEC-033`)

The live MaaS credential (`MODEL_API_KEY`) is created directly as a
Kubernetes `Secret`, from the same value already used for local dev
(`.env`, gitignored) — never as a pipeline parameter, never written into a
`PipelineRun` spec, never committed. **Two copies, in two namespaces, for
two different consumers** — `secretKeyRef`/`configMapKeyRef` cannot
cross namespaces, confirmed live (`CreateContainerConfigError` on
`eval-gate-live` before the second copy existed):

```sh
set -a && . ./.env && set +a
# Copy 1: the deployed agent pod's own envFrom.secretRef
# (deploy/kustomize/base/deployment-agent.yaml), read by whatever's
# actually running in the ephemeral-test namespace.
oc create secret generic golden-path-agent-secrets \
  -n golden-path-agent-ephemeral-test \
  --from-literal=MODEL_API_KEY="$MODEL_API_KEY" \
  --from-literal=MCP_AUTH_TOKEN="not-needed"

# Copy 2: eval-gate-live's own TaskRun, which executes in
# golden-path-agent-ci (running the in-process eval harness against the
# real model -- see that Task's own design note), not in
# golden-path-agent-ephemeral-test.
oc create secret generic golden-path-agent-secrets \
  -n golden-path-agent-ci \
  --from-literal=MODEL_API_KEY="$MODEL_API_KEY" \
  --from-literal=MCP_AUTH_TOKEN="not-needed"
```

`deploy/kustomize/base/deployment-agent.yaml`'s `envFrom.secretRef` already
references copy 1 by name — no manifest change was needed to consume it.
If the credential ever needs rotating, re-run the same command against
**both** namespaces (`oc create secret` fails on an existing name; use `oc
create secret ... -o yaml --dry-run=client | oc apply -f -` to update in
place instead).

**Verify the value is never echoed** when running or reviewing any command
that touches this secret — pipe through a redaction filter, or use
`jsonpath`/`-o name` forms that never print `.data`, as done above and in
`DEC-024`'s own evidence.

## 3. Promotion-PR git credential (mechanism finalized — Step C1b; creation
still a pending manual action before C1c can exercise `open-promotion-pr`)

`pipelines/tasks/open-promotion-pr.yaml` needs a git write credential
scoped to exactly this one repo. Mechanism:

1. Create a **fine-grained GitHub Personal Access Token**
   (github.com → Settings → Developer settings → Fine-grained tokens →
   Generate new token), scoped to:
   - **Repository access**: only `DarkDragonEl/golden-path-agent-template`
     — never "All repositories."
   - **Permissions**: `Contents: Read and write` (push the promotion
     branch), `Pull requests: Read and write` (open the PR). Nothing else.
   - A short expiry (90 days is reasonable for a demo milestone) — rotate
     by repeating this step, not by widening scope.
2. Store it as a `Secret`, never in Git, never echoed:
   ```sh
   oc create secret generic golden-path-agent-github-token \
     -n golden-path-agent-ci \
     --from-literal=token="<the fine-grained PAT>"
   ```
3. `pipelines/tasks/open-promotion-pr.yaml`'s two steps reference this
   Secret by name only (`secretKeyRef`), as an env var — never a Tekton
   `param` (which Tekton persists into the `PipelineRun`'s own spec/status,
   visible via `oc get pipelinerun -o yaml`; an env var sourced from a
   `secretKeyRef` is not). Neither step's script ever echoes
   `$GITHUB_TOKEN` — verified by reading both scripts directly, not
   assumed: the token is only ever used inside a `-H "Authorization:
   Bearer ${GITHUB_TOKEN}"` header argument, never `echo`'d or logged.

**Not yet done**: step 1–2 above are a manual action for the human
operator, same as the MaaS credential — not performed automatically by
this session, since it requires generating a credential through GitHub's
own UI. `open-promotion-pr` will fail with a clear, non-secret-leaking
error (`Secret "golden-path-agent-github-token" not found`) until this is
done. This does not block C1c's negative-proof-#1 (a seeded bad change is
expected to fail before `open-promotion-pr` is ever reached) — it only
blocks the green-path run's final stage and the digest-promotion PR merge
itself.

## 4. Endpoint-drift diagnostic procedure (for `eval-gate-live` — Step C1b)

Per `DECISIONS.md` `DEC-022`: the live, externally-hosted MaaS model's
behavior on a given case is not guaranteed stable across measurement
sessions, even with `temperature=0`/`seed=42` pinned — confirmed directly
(`INJ-006` reversed from a firm 10/10 fail to 7/7 pass across sessions,
with the request to the model proven byte-identical both times). This is
not tribal knowledge; it's a documented, expected class of gate failure
with its own procedure, not a signal to immediately suspect the change
under test:

**If `eval-gate-live` fails on a `PipelineRun` for a PR that does not touch
the measurement instrument** (prompts, retrieval code, model choice, graph
topology, sampling params, or the eval case set itself — `DECISIONS.md`
`DEC-012`/`DEC-017`'s definition of "the instrument"), **do not conclude
the change under test is the cause without first re-running the isolated
failing case(s) N times** (5 reps, matching `DEC-022`'s and `DEC-017`'s
own precedent — `tools/diagnose_uaw003_flip.py`/`tools/diagnose_inj006_flip.py`
are the templates) **at the same pinned settings, outside the pipeline, to
distinguish:**

- **(a) genuine, reproducible failure** — the isolated re-run also fails
  consistently → the change (or something else that *did* change) is a
  real culprit; investigate further before blaming the model.
- **(b) non-reproducing flip** — the isolated re-run passes cleanly (or
  passes the majority of reps) → live-endpoint session-to-session drift,
  the `DEC-022` pattern; do not chase it as a regression in the PR under
  test. Record it (a comment on the `PipelineRun`, or a note in the promo-
  tion PR if one still opens) rather than silently re-running the whole
  pipeline until it happens to go green.

This procedure protects against exactly the failure mode `DEC-022` had to
investigate after the fact — it makes the diagnosis routine instead of a
fresh forensic exercise each time it recurs.

## 5/6/7. Post-Checkpoint-C backlog (priority order, owner-confirmed — NOT
someday items)

Three items deferred out of Step C1b/C1c's already-large batch. All three
are now explicitly **the first work items after Checkpoint C closes** —
not a someday backlog, per the owner's own instruction on reviewing this
runbook: the longer PipelineRuns exist without them, the more drift
evidence (items 1/2) or the more repeat instances of an already-observed
failure pattern (item 3) accumulate.

1. **Model-identity capture** (highest priority). If the live MaaS
   endpoint's response exposes a model identity/version field (an
   OpenAI-compatible response's `model` field, or a system-fingerprint-
   style header), capture it alongside every eval run's results —
   **read-only telemetry, never used to alter a request** (the same
   constraint `agent/telemetry.py`'s own header comment holds itself to,
   `DECISIONS.md` `DEC-020` — no `DEC-012`-style re-baseline needed for
   this specific addition, same reasoning as `DEC-020`'s own token-usage
   capture). Not implemented at the C1b STOP: doing it properly means
   threading `response.model` through
   `agent/model_client.py::OpenAICompatibleModelClient.complete()`'s
   return tuple (the same pattern R4/`DEC-020` used for `usage`), into
   `model_calls` entries, and from there into `eval/reporter.py`'s output
   — a real, multi-file addition, not a one-line Task change.
   **Rationale for the priority, not just the existence, of this item**:
   its entire value is correlating *future* cross-session drift
   (`DEC-022`'s pattern) against an *observed* model-identity change —
   and every `PipelineRun` from C1c onward is itself a fresh measurement
   session. Every run executed without this capture is drift evidence
   permanently lost, not deferred; it cannot be captured retroactively
   for a run that already happened.
2. **Cluster-tier OTel wiring.** `PINS.md` pins the Red Hat build of
   OpenTelemetry Operator (`opentelemetry-product`, channel `stable`) as
   available on this cluster's catalog, but it is not yet installed, and
   the ephemeral deployment does not yet export traces. `operational-tests`'s
   kill-primary-fallback check (`pipelines/tasks/operational-tests.yaml`)
   is therefore a functional check (the call still succeeds) rather than
   a trace-based one (`model.route: fallback` visible in an exported
   span, matching `DEC-020`'s local demo).
3. **Config-contract completeness check.** `DECISIONS.md` `DEC-035`
   records the second instance of the same failure pattern: an
   environment surface silently missing a key `agent/config.py` (the
   canonical consumer) actually requires. First instance: R4's
   `scripts/dev.sh` missing `MODEL_API_KEY`/fallback vars for local dev.
   Second: the K8s-deployed config path (base `ConfigMap`, the
   `ephemeral-test` overlay, and the live `golden-path-agent-ci-config`)
   never declaring `MODEL_FALLBACK_API_BASE_URL`/`MODEL_FALLBACK_NAME` at
   all — undetected for the entire C1a–C1c build-out because
   `operational-tests` (the one stage that would exercise it) never
   successfully reached its own HTTP call until `DEC-034`'s unrelated
   `curl` fix. Two independent instances of the same class of gap is a
   pattern, not a coincidence — the fix is mechanical, not another
   one-off patch: a check that derives the required key set directly from
   `agent/config.py`'s own `_env(...)` calls (the canonical source of
   truth for what the application actually reads) and validates that
   every deployment surface — `.env.example`, `scripts/dev.sh`, the base
   `ConfigMap`, and each overlay's `configMapGenerator` — declares each
   required key, failing loudly on any surface that's missing one. Cheap
   to build (a static-analysis script, no cluster access needed) and
   prevents a third instance of a pattern that has now bitten twice.

Neither model-identity capture nor OTel wiring blocks Checkpoint C
itself — its own exit criteria (green pipeline, blocked bad-change
promotion, displayed digest equality) don't require live tracing or
model-identity correlation, and the same is true of item 3 (a build-time
lint, not a runtime gate). All three are explicitly sequenced right after
Checkpoint C closes, in the priority order above, not left to someday.
