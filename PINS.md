# PINS.md

Per `CLAUDE.md`'s "Reuse over building" rule: before writing infrastructure
code (pipeline, GitOps, observability, policy), search for the current
state of Red Hat Validated Patterns, AI Quickstarts, and official reference
repos; pin exact versions and commits here with the URL and date verified.
Never rely on memorized repo contents — every row below was verified
against a live source on the date listed, not assumed from training data.

Previously flagged as open work (`srs/DEFERRED.md` `SysR-P-LC-01`) — first
entry created at Step R4 (plan-B6/OTel closure), mission
`~/.claude/plans/read-claude-md-handoff-md-decisions-md-vast-hare.md`.

| Component | Realization | Channel/Version | Support level | Verified date | Source URL | Notes |
|---|---|---|---|---|---|---|
| Local dev OTel Collector | `otel/opentelemetry-collector` (core distribution, not `-contrib`) | `0.159.0` | Community (upstream OpenTelemetry, not a Red Hat build) | 2026-08-21 | https://github.com/open-telemetry/opentelemetry-collector-releases/releases · https://opentelemetry.io/docs/collector/install/docker/ | Core distribution chosen deliberately over `-contrib`: only an OTLP HTTP receiver + `debug` exporter are needed for this milestone's local-dev scope (`scripts/dev.sh`, `deploy/otel/otel-collector-config.yaml`) — `-contrib` is heavier and unnecessary here. Red Hat does ship a build of OpenTelemetry (`docs.redhat.com`/`catalog.redhat.com`, search "red_hat_build_of_opentelemetry"), but it is an OpenShift-operator-managed distribution for cluster deployment — the right fit for the eventual SNO/Phase C-D observability stack, not this local-Podman context. **Revisit at Phase C**: pin the cluster-tier realization (Red Hat build vs. upstream Collector via the OpenShift OTel Operator) as a separate row when that work starts — do not assume this row's pin carries over unchanged. |
