# Declarative mirror of agent/policy.py::classify_action / requires_approval.
# This is
# a policy-*definition* validation gate (`opa test`, run in CI) proving the
# taxonomy's shape and fail-closed default are internally consistent -- it
# is NOT a second runtime enforcement point. agent/policy.py stays the one
# and only Policy Decision Point at request time; adding a live OPA
# server/sidecar here would be exactly the kind of second-PDP scope creep
# CLAUDE.md's scope guard flags. See Annex A OI-03: this is "policy
# scaffolding + one enforced deny path," not a policy platform.
#
# tool_classification below must be kept in sync with
# policy/approval_rules.yaml's `rules:` list by hand -- there is no
# generator; approval_policy_test.rego's tests catch drift between this
# file and Python's actual behavior (agent/policy.py's own unit tests are
# the ground truth), not between this file and the YAML directly.
package golden_path.approval

default_classification := "write"

tool_classification := {
	"itsm_search_records": "read",
	"itsm_create_request": "write",
	"placeholder_lookup": "read",
	"placeholder_write_action": "write",
}

# SRS-AGT-SEC-03: an action whose tool name is not in the taxonomy above
# always classifies "write" -- never read-only or directly executable.
# Mirrors Python's dict.get(tool_name, default_classification) exactly.
classify(tool_name) := object.get(tool_classification, tool_name, default_classification)

# APPROVAL_MODE == "auto" is the one global bypass (agent/policy.py's own
# requires_approval); every other action's approval need follows purely
# from its classification.
requires_approval(tool_name, approval_mode) if {
	approval_mode != "auto"
	classify(tool_name) == "write"
}

# The one enforced deny path this bundle proves (Annex A OI-03's
# "OPA bundles with >=1 proven fail-closed deny"): a write-classified
# action must never be marked directly executable/allowed on its own --
# it is only ever a *candidate* for human approval, never a bypass.
deny_direct_execution(tool_name) if {
	classify(tool_name) == "write"
}
