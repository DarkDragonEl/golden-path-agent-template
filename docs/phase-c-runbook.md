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

## 3. Promotion-PR git credential (TBD — Step C1b)

`open-promotion-pr` (the pipeline stage that opens the digest-promotion PR
against `https://github.com/DarkDragonEl/golden-path-agent-template`)
needs its own git write credential. Same rule as above: manually
provisioned once, scoped to this one repo only (a fine-grained GitHub PAT
or deploy key with write access to this repo alone — never a broad
account-wide token), stored as a `Secret` in `golden-path-agent-ci`, never
a pipeline parameter, never in a `PipelineRun` spec, never in Git, never
echoed in Tekton logs. Exact mechanism finalized and documented here at
the C1b manifest review.

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

## 5. Model-identity capture (for `eval-gate-live` — Step C1b)

If the live MaaS endpoint's response exposes a model identity/version
field (e.g. an OpenAI-compatible response's `model` field, or a system-
fingerprint-style header), `eval-gate-live` captures it alongside each
run's results — **read-only telemetry, never used to alter a request** (the
same constraint `agent/telemetry.py`'s own header comment holds itself to,
`DECISIONS.md` `DEC-020`). Purpose: the next time cross-session behavioral
drift shows up (another `DEC-022`-shaped finding), there's a chance to
correlate it against an actual observed model-identity change instead of
inferring one exists. Exact field and capture mechanism finalized at the
C1b manifest review, once the pipeline's own eval-invocation shape is
written.
