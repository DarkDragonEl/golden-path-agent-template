# `ci/`

`pr-checks.yaml` is a **generic, CI-tool-agnostic pipeline definition** —
the stage shape (`unit-tests` → `eval-gate` → `container-build` → `sbom`)
every real CI product's own concrete pipeline must realize identically,
whether run on a laptop or in CI. It is documentation of intent, not
itself executable.

**Consumed by**: a human implementer choosing/wiring an actual CI
executor for a real engagement, and by `pipelines/`, which is this
project's own concrete Tekton realization of the same stage shape
(`pipelines/pipeline-agent.yaml` etc. — see `docs/environments.md`'s PR
CI row for how the two map onto each other).

See the [documentation hub](../docs/README.md),
[`docs/environments.md`](../docs/environments.md) for the environment
table this stage shape feeds into, and
[`pipelines/README.md`](../pipelines/README.md) for the concrete Tekton
realization.
