# CI Pipeline Failure Triage Procedure

This procedure describes how a CI pipeline failure reported under the CI
Pipeline Reference Architecture is triaged.

When a pipeline stage fails, the failure is first classified as either an
infrastructure failure (runner, cache, network) or an application failure
(failing test, failing scan finding). Infrastructure failures are routed
to the CI Platform Team; application failures are routed back to the
owning team. Known, recurring infrastructure issues — such as CI runner
cache corruption on concurrent builds — are tracked as known errors so
repeat occurrences can be triaged quickly by matching against the known
error record instead of re-investigating from scratch.

A failure that recurs three or more times in a week for the same root
cause is escalated to the CI Platform Team Lead for a permanent fix, not
just another workaround.
