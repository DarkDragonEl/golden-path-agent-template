# opa test policy/opa/ -- structurally mirrors tests/test_policy_limits.py's
# cases, so both suites assert the same behavior against the same inputs
# (the actual proof this file is a faithful mirror, not just similar-looking
# rego).
package golden_path.approval_test

import data.golden_path.approval.classify
import data.golden_path.approval.deny_direct_execution
import data.golden_path.approval.requires_approval

test_itsm_search_records_classified_as_read if {
	classify("itsm_search_records") == "read"
}

test_itsm_create_request_classified_as_write if {
	classify("itsm_create_request") == "write"
}

test_placeholder_lookup_classified_as_read if {
	classify("placeholder_lookup") == "read"
}

test_placeholder_write_action_classified_as_write if {
	classify("placeholder_write_action") == "write"
}

# SRS-AGT-SEC-03 fail-closed default.
test_unknown_tool_fails_closed_to_write if {
	classify("some_unlisted_tool") == "write"
}

test_requires_approval_true_for_write_when_mode_required if {
	requires_approval("itsm_create_request", "required")
}

test_requires_approval_false_for_read_when_mode_required if {
	not requires_approval("itsm_search_records", "required")
}

# The one global bypass -- APPROVAL_MODE == "auto".
test_requires_approval_false_when_mode_auto_even_for_write if {
	not requires_approval("itsm_create_request", "auto")
}

# The proven fail-closed deny path (Annex A OI-03): a
# write-classified action is never directly executable/allowed on its own.
test_write_classified_action_denies_direct_execution if {
	deny_direct_execution("itsm_create_request")
}

test_read_classified_action_does_not_deny_direct_execution if {
	not deny_direct_execution("itsm_search_records")
}

test_unknown_tool_denies_direct_execution if {
	deny_direct_execution("some_unlisted_tool")
}
