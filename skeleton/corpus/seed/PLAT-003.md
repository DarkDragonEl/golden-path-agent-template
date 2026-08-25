# CI Pipeline Reference Architecture

This reference architecture defines the standard shape every CI pipeline
on the platform follows.

The pipeline has a build stage, where source is compiled and packaged.
The pipeline has a test stage, where automated unit and integration tests
run against the build artifact. The pipeline has a scan stage, where the
artifact is checked for known vulnerabilities and policy compliance. The
pipeline has a promote stage, where a passing artifact is published to the
next environment.

Each stage must complete successfully before the next stage begins; a
failure at any stage halts the pipeline and is reported per the CI
Pipeline Failure Triage Procedure. This architecture does not set a
runtime budget for any individual stage or for the pipeline as a whole —
teams size their own CI infrastructure to their workload, and no maximum
execution time is specified here.
