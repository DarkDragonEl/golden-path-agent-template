# Incident Escalation Procedure

This procedure defines when and how an incident is escalated.

An incident is escalated when it is not resolved within the defined
severity time window for its assigned severity level — each severity
level has its own resolution-time expectation, and an incident still open
past that window is automatically flagged for escalation rather than
staying with the original responder indefinitely.

Escalation follows the on-call responder chain: the incident is handed up
to the next on-call tier, and if that tier cannot resolve it within a
further window, it continues up the chain. Every escalation step is
logged against the incident record. This procedure is reviewed after
every severity-1 incident postmortem.
