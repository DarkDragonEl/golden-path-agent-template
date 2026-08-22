# Golden Path Container Image Baseline

This standard defines the baseline every application container image on
the platform must build from.

Images must be built from the approved baseline image — no application
image may use an unapproved or unreviewed base image as its starting
point. The baseline image is reviewed on every rebuild: each rebuild goes
through a security and dependency review before it becomes the new
current baseline, and prior baseline versions remain available for a
transition period so teams can migrate without a hard cutover.

Teams that believe they need to deviate from the baseline (a different
base OS, a different language runtime version not yet included) must
request an exception from Platform Engineering rather than substituting
an unapproved image silently.
