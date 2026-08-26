# `policy/`

Declarative policy content, kept separate from the code that enforces
it: `approval_rules.yaml` (the intended future home for the
read-vs-write classification `agent/policy.py::classify_action()`
hardcodes today) and `baseline_policy.yaml`, plus `opa/` — an actual Open
Policy Agent Rego policy (`approval_policy.rego`) with its own test suite
(`approval_policy_test.rego`) and OLM `manifest.yaml`.

**Consumed by**: `pipelines/tasks/policy-validate.yaml` (the CI gate that
checks policy bundle content before promotion), and, once wired, the
approval service / agent at runtime via `POLICY_BUNDLE_REF`.

See the [documentation hub](../docs/README.md),
[`docs/security-identity.md`](../docs/security-identity.md) for the
approval gate this policy content backs, and
[`docs/architecture.md`](../docs/architecture.md)'s contract-boundaries
table for the policy contract.
