# Phase C runbook — manual bootstrap steps

Everything in this file is a **deliberate manual step**, done once by a
human operator with cluster access, never by the Tekton pipeline itself.
`DECISIONS.md` `DEC-024` records why: the pipeline's own `ServiceAccount`
(`pipelines/bootstrap/rbac.yaml`) is granted the minimum this project's own
namespaces need and nothing else — no cluster-scoped permissions, no
secret-material handling. These steps exist precisely because the pipeline
must not be trusted with them.

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

## 2. Model-endpoint credential (done — Step C1a)

The live MaaS credential (`MODEL_API_KEY`) is created directly as a
Kubernetes `Secret`, from the same value already used for local dev
(`.env`, gitignored) — never as a pipeline parameter, never written into a
`PipelineRun` spec, never committed:

```sh
set -a && . ./.env && set +a
oc create secret generic golden-path-agent-secrets \
  -n golden-path-agent-ephemeral-test \
  --from-literal=MODEL_API_KEY="$MODEL_API_KEY" \
  --from-literal=MCP_AUTH_TOKEN="not-needed"
```

`deploy/kustomize/base/deployment-agent.yaml`'s `envFrom.secretRef` already
references this Secret by name — no manifest change was needed to consume
it. If the credential ever needs rotating, re-run the same command (`oc
create secret` fails on an existing name; use `oc create secret ... -o
yaml --dry-run=client | oc apply -f -` to update in place instead).

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

## 5. Model-identity capture (for `eval-gate-live`) — deferred, not done at
this STOP; see §6 for why

If the live MaaS endpoint's response exposes a model identity/version
field (e.g. an OpenAI-compatible response's `model` field, or a system-
fingerprint-style header), each eval run should capture it alongside its
results — **read-only telemetry, never used to alter a request** (the same
constraint `agent/telemetry.py`'s own header comment holds itself to,
`DECISIONS.md` `DEC-020`). Purpose: the next time cross-session behavioral
drift shows up (another `DEC-022`-shaped finding), there's a chance to
correlate it against an actual observed model-identity change instead of
inferring one exists.

**Not implemented in `pipelines/tasks/eval-gate-live.yaml` at this STOP.**
Doing this properly means threading `response.model` through
`agent/model_client.py::OpenAICompatibleModelClient.complete()`'s return
tuple (the same pattern R4/`DEC-020` already used for `usage`), into
`model_calls` entries, and from there into `eval/reporter.py`'s output —
a real, multi-file addition, not a one-line change to the pipeline Task.
Given the size of this Step C1b batch already, this is deferred alongside
§6's OTel wiring rather than rushed in here — recorded honestly as
open, not silently implied done by this section's earlier draft.

## 6. Deferred: cluster-tier OTel wiring

`PINS.md` pins the Red Hat build of OpenTelemetry Operator
(`opentelemetry-product`, channel `stable`) as available on this cluster's
catalog, but **it is not yet installed, and the ephemeral deployment does
not yet export traces**. `operational-tests`'s kill-primary-fallback check
(§4 above, actually the check in `pipelines/tasks/operational-tests.yaml`)
is therefore a functional check (the call still succeeds) rather than a
trace-based one (`model.route: fallback` visible in an exported span,
matching `DEC-020`'s local demo). Not a silent scope cut: Checkpoint C's
own exit criteria (green pipeline, blocked bad-change promotion, displayed
digest equality) don't require live tracing, so this was deliberately
sequenced after the pipeline itself rather than blocking it — flagged here
as real remaining work, not forgotten.
