# `pipelines/`

This project's concrete Tekton realization of `ci/pr-checks.yaml`'s
generic stage shape: three independent `Pipeline`s, one per promoted
artifact (`pipeline-agent.yaml`, `-mcp.yaml`, `-approval.yaml`), built
from the shared `Task`s in `tasks/` (`fetch-source`, `unit-tests`,
`eval-gate-offline`/`-live`, `policy-validate`, `security-tests`,
`sbom-generate`, `deploy-ephemeral`, `operational-tests`,
`digest-capture`, `open-promotion-pr`, `destroy-ephemeral`).
`bootstrap/` holds the one-time, human-applied cluster setup
(`namespaces.yaml`, `rbac.yaml`, the two OLM operator Subscriptions) —
never applied by the pipeline itself.

**Consumed by**: Tekton (`PipelineRun`s created from
`pipelinerun-template-*.yaml`), and a human operator running
`scripts/bootstrap.sh`/`make bootstrap` for the one-time setup in
`bootstrap/`.

See the [documentation hub](../docs/README.md),
[`docs/environments.md`](../docs/environments.md) for the promotion model
these pipelines implement, [`docs/phase-c-runbook.md`](../docs/phase-c-runbook.md)
for the manual steps that precede a pipeline ever running, and
[`ci/README.md`](../ci/README.md) for the generic stage shape this
realizes concretely.
