# `srs/`

This project's own Software Requirements Specifications, one per area
(`SRS-AGT.md` agent, `SRS-APR.md` approval, `SRS-EVH.md` eval harness,
`SRS-MIT.md` MCP tool interface, `SRS-RET.md` retrieval), plus
`FINDINGS.md`, `DEFERRED.md`, and `REVIEW_INDEX.md`. These are the third,
most granular tier of this project's formal-requirements chain: SyRS
(`SyRS-AGP-001_EN.md`) → StRS (`StRS_Agentic_AI_Platform_EN.md`) → SRS
(here) — see `docs/naming-conventions.md` for the ID scheme
(`SRS-<AREA>-<KIND>-NN`) each file uses.

**Consumed by**: a human reviewer tracing an implementation decision back
to its formal requirement, and `tools/trace-check/` (validates that all
three tiers trace to each other consistently — this project's own
methodology check, not part of the running agent's behavior).

Not carried into a scaffolded child project — see the
[documentation hub](../docs/README.md) and
[`docs/template-nine-output-mapping.md`](../docs/template-nine-output-mapping.md)'s
"explicitly out of scope" list.
