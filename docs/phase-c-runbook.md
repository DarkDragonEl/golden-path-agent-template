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
Step C1c, `DEC-033`; a third planned for Step C4, `DEC-039` — not yet
created, since `golden-path-agent-demo-prod` doesn't exist until the
bootstrap in §1 is extended and applied)

The live MaaS credential (`MODEL_API_KEY`) is created directly as a
Kubernetes `Secret`, from the same value already used for local dev
(`.env`, gitignored) — never as a pipeline parameter, never written into a
`PipelineRun` spec, never committed. **Three copies, in three namespaces,
for three different consumers** — `secretKeyRef`/`configMapKeyRef` cannot
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

# Copy 3 (Step C4, DEC-039): golden-path-agent-demo-prod. Unlike copies 1
# and 2, this copy ALSO carries the model-endpoint values themselves
# (MODEL_API_BASE_URL/MODEL_NAME/MODEL_FALLBACK_API_BASE_URL/
# MODEL_FALLBACK_NAME) -- demo-prod is ArgoCD-synced with selfHeal: true,
# which would continuously stomp any apply-time ConfigMap override (the
# mechanism copies 1/2's environment use) back to the committed
# placeholder. The Secret is never Kustomize/ArgoCD-managed, so this is
# safe; envFrom ordering in deployment-agent.yaml (secretRef listed after
# configMapRef) makes these values shadow the ConfigMap's placeholder at
# the container level -- see docs/environments.md's "Config that changes
# per environment" section for the full mechanism. Run only after
# golden-path-agent-demo-prod exists (pipelines/bootstrap/namespaces.yaml,
# extended at Step C4) -- must exist before demo-prod's Application's
# first sync, or its pod hits the same CreateContainerConfigError DEC-033
# already diagnosed once.
oc create secret generic golden-path-agent-secrets \
  -n golden-path-agent-demo-prod \
  --from-literal=MODEL_API_KEY="$MODEL_API_KEY" \
  --from-literal=MCP_AUTH_TOKEN="not-needed" \
  --from-literal=MODEL_API_BASE_URL="$MODEL_API_BASE_URL" \
  --from-literal=MODEL_NAME="$MODEL_NAME" \
  --from-literal=MODEL_FALLBACK_API_BASE_URL="$MODEL_FALLBACK_API_BASE_URL" \
  --from-literal=MODEL_FALLBACK_NAME="$MODEL_FALLBACK_NAME"
```

`deploy/kustomize/base/deployment-agent.yaml`'s `envFrom.secretRef` already
references copy 1 by name — no manifest change was needed to consume it.
If the credential ever needs rotating, re-run the same command against
**all three** namespaces (`oc create secret` fails on an existing name; use
`oc create secret ... -o yaml --dry-run=client | oc apply -f -` to update
in place instead).

**Verify the value is never echoed** when running or reviewing any command
that touches this secret — pipe through a redaction filter, or use
`jsonpath`/`-o name` forms that never print `.data`, as done above and in
`DEC-024`'s own evidence.

**"Why doesn't Kustomize just set the model endpoint for demo-prod, the
way the overlay already does for `MODEL_NAME`/`MCP_MODE`/etc.?"** — the
question a future reviewer will ask on first reading
`deploy/kustomize/overlays/demo-prod/kustomization.yaml`, answered once
here rather than left implicit:

1. The real endpoint value can never be committed to this public repo
   (anonymity/no-real-infrastructure-detail rule) — every committed
   overlay only ever has a safe placeholder for it.
2. `ephemeral-test` solves this by having the *pipeline* inject the real
   value at apply-time, into a scratch copy of the rendered manifest,
   once per `PipelineRun` — never reconciled again afterward, so the
   override sticks.
3. `demo-prod` has no such injection point: it is synced by ArgoCD with
   `syncPolicy.automated.selfHeal: true`. If the real value were somehow
   applied on top of the `ConfigMap` `kustomize`/ArgoCD manages, `selfHeal`
   would notice the drift from what's committed and revert it right back
   to the placeholder on its next reconciliation pass.
4. So the real value for `demo-prod` lives **only** in this `Secret` —
   an object ArgoCD/Kustomize never touches at all for these keys, by
   design (same reasoning `base/kustomization.yaml`'s own comment already
   gives for why `externalsecret.yaml` was dropped rather than replaced
   with a stub `Secret`).
5. **Precedence, not absence, is what makes this work**:
   `deploy/kustomize/base/deployment-agent.yaml`'s `envFrom` list has
   `configMapRef` *before* `secretRef`. Kubernetes resolves duplicate keys
   across an `envFrom` list by last-source-wins — so for
   `MODEL_API_BASE_URL`/`MODEL_NAME`/`MODEL_FALLBACK_API_BASE_URL`/
   `MODEL_FALLBACK_NAME`, which exist in *both* sources, the `Secret`'s
   real value always shadows the `ConfigMap`'s placeholder inside the
   running container. No code change, no extra manifest field — this
   ordering already existed (it's how `MODEL_API_KEY` itself has always
   worked, since it was never in the `ConfigMap` at all) and just needed
   naming as the mechanism.

## 2b. CI pipeline config (done — Step C1a; found undocumented at
`DECISIONS.md` `DEC-081`, Phase E's first from-scratch showcase bootstrap)

`golden-path-agent-ci-config`, a plain `ConfigMap` (not a `Secret` —
`MODEL_API_BASE_URL`/`MODEL_NAME`/`MODEL_FALLBACK_API_BASE_URL`/
`MODEL_FALLBACK_NAME` are not credential material) in
`golden-path-agent-ci`, read by both `pipelines/tasks/deploy-ephemeral.yaml`
and `pipelines/tasks/eval-gate-live.yaml` at apply-time — the same
apply-time-override mechanism §2 above uses for `demo-prod`'s `Secret`,
applied here to the *pipeline's own* run-time config instead of a
deployed environment's. `deploy-ephemeral.yaml`'s own header comment
already called this "C1a bootstrap," but the actual creation command was
never written down until now — found live when a genuinely fresh
`golden-path-agent-ci` namespace hit `CreateContainerConfigError` on
`deploy-ephemeral`'s own `render-with-digest-override` step, something
that could never surface on the SNO once this `ConfigMap` was created
there by hand, undocumented, at some earlier point in this project's
history.

```sh
set -a && . ./.env && set +a
oc create configmap golden-path-agent-ci-config \
  -n golden-path-agent-ci \
  --from-literal=MODEL_API_BASE_URL="$MODEL_API_BASE_URL" \
  --from-literal=MODEL_NAME="$MODEL_NAME" \
  --from-literal=MODEL_FALLBACK_API_BASE_URL="$MODEL_FALLBACK_API_BASE_URL" \
  --from-literal=MODEL_FALLBACK_NAME="$MODEL_FALLBACK_NAME"
```

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

## 5/6/7/8. Post-Checkpoint-C backlog (priority order, owner-confirmed —
NOT someday items)

Four items deferred out of Step C1b–C4's already-large batch. All four
are now explicitly **the first work items after Checkpoint C closes** —
not a someday backlog, per the owner's own instruction on reviewing this
runbook: the longer PipelineRuns exist without them, the more drift
evidence (items 1/2) or the more repeat instances of an already-observed
failure pattern (item 3) accumulate. Item 4 is the one genuine exception
to "the longer this waits the worse it gets" — explicitly lowest
priority, parked rather than urgent, per the owner's own call.

1. **Model-identity capture — DONE (`DECISIONS.md` `DEC-043`), before
   Phase D planning, per the owner's own priority.** If the live MaaS
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
3. **Config-contract completeness check — DONE (`DECISIONS.md` `DEC-044`),
   before Phase D planning, per the owner's own priority.** (Scope
   extended at the Checkpoint C closure review to a second, related
   pattern — see below; both implemented together.)
   `DECISIONS.md` `DEC-035` records the second instance of the first
   pattern: an environment surface silently missing a key
   `agent/config.py` (the canonical consumer) actually requires. First
   instance: R4's `scripts/dev.sh` missing `MODEL_API_KEY`/fallback vars
   for local dev. Second: the K8s-deployed config path (base `ConfigMap`,
   the `ephemeral-test` overlay, and the live `golden-path-agent-ci-config`)
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
   required key, failing loudly on any surface that's missing one.

   **Second pattern, folded into the same check at the Checkpoint C
   closure review**: `DEC-042`'s `REGISTRY_PLACEHOLDER` finding is the
   **third** instance of a related but distinct failure — not a *missing*
   key, but an *unresolved placeholder value* left in a manifest that a
   GitOps-synced environment consumes exactly as committed, with no
   apply-time injection step to ever resolve it. First instance:
   `deploy/argocd/*.yaml`'s `REPLACE_WITH_GIT_REPO_URL`/
   `REPLACE_WITH_GITOPS_NAMESPACE` (caught and fixed manually at C1a,
   before any environment tried to consume them as-committed). Second:
   the same overlay `configMapGenerator` placeholders
   (`http://dev-model-endpoint.example.com/v1` etc.) — harmless only
   because every environment that has ever actually run a pod from them
   also has a pipeline-side apply-time override, so far. Third:
   `REGISTRY_PLACEHOLDER/golden-path-agent`, which had exactly the same
   property — safe for `ephemeral-test` (pipeline-overwritten), fatal
   (`InvalidImageName`) for `demo-prod` (no override exists). The same
   check this item already builds should also scan every manifest a
   GitOps-synced `Application` (i.e., anything under `deploy/argocd/apps/`
   and the overlay paths it points to) consumes as-committed for
   placeholder-shaped values (`REPLACE_WITH_*`, `*_PLACEHOLDER`, and any
   future convention this repo adopts for the same purpose) and fail
   loudly if one is found with no corresponding out-of-band
   (`Secret`-shadowing or equivalent) resolution mechanism documented for
   it — the same "every required value has a stated origin, never
   silent" property item 1's own key-completeness check already enforces,
   applied to *values* left as placeholders rather than *keys* left
   absent. Cheap to build (a static-analysis script, no cluster access
   needed) and prevents a fourth instance of either pattern — the second
   (missing keys) has bitten twice, the first (unresolved placeholders)
   has now bitten three times.
4. **PAT rotation (parked, not forgotten).** The GitHub PAT stored as
   `golden-path-agent-github-token` was supplied directly in conversation
   twice (`DEC-036`, `DEC-039`) rather than run locally via the runbook's
   own intended flow — a broader exposure than the mechanism's original
   design (never seen by the agent at all). The owner explicitly deferred
   this ("PAT rotation is parked, not the focus now") while a functional
   promotion path was the priority. Lowest priority of the four — no
   drift evidence is lost by waiting, unlike items 1/2 — but real:
   regenerate the fine-grained PAT in GitHub's UI (same scopes, same
   single-repo restriction) and update the `Secret` in place
   (`docs/phase-c-runbook.md` §2's own rotation instructions already
   cover the mechanism) once this milestone's active work settles.

Neither model-identity capture nor OTel wiring blocks Checkpoint C
itself — its own exit criteria (green pipeline, blocked bad-change
promotion, displayed digest equality) don't require live tracing or
model-identity correlation, and the same is true of items 3/4 (a
build-time lint and a credential-hygiene follow-up, neither a runtime
gate). All four are explicitly sequenced right after Checkpoint C closes,
in the priority order above, not left to someday.
