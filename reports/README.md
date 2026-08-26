# `reports/`

The evidence trail: one test-report artifact per phase/branch of work
(`reports/<branch-name>.md`, per `CLAUDE.md`'s verification discipline —
commands run, results, eval scores, what failed and why), plus the raw
diagnostic JSON/screenshot artifacts a handful of those reports cite
directly (e.g. `phase-b-tool-calling-spike-raw.json`,
`browser-walkthrough-screenshots/`).

**Consumed by**: a human reviewer or the owner (verifying a phase's DoD
before sign-off), `tools/trace-check/` (some reports are cited as
traceability evidence), and later phases' own reports, which frequently
cite an earlier report by exact filename rather than restating its
evidence.

Report content is this project's own session history — see the
[documentation hub](../docs/README.md) and
[`docs/template-nine-output-mapping.md`](../docs/template-nine-output-mapping.md)'s
"explicitly out of scope" list for why `reports/` is never carried into a
scaffolded child project.
