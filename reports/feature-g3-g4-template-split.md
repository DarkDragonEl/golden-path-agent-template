# G3+G4 — Tools Template + slimmed Agent Template: session report

Branch: `feature/g3-g4-template-split` (git worktree, not merged, not
pushed). Per `DEC-099`'s single-governance-owner rule, this branch does
**not** touch `DECISIONS.md`/`HANDOFF.md`/`PINS.md` — drafted decision
entries are at the bottom of this report for the coordinating session to
land at merge.

## FOLLOW-UP (this revision) — DEC-104's eval-harness gap closed per
DEC-105's ruling

`DEC-104` escalated the eval-harness/`mcp_server.itsm_store` coupling
named in this report's original revision (below). `DEC-105` decided: move
the mock ITSM store logic into an eval-only fixture, decoupled from the
real MCP server; domain eval's fault injection runs against it via a
test-only MCP client stub; the real server's own `_simulate_error`
guarantee stays exactly as it is. Assigned back to this stream. Status:
**done, verified live, closing the gap for real** — see the final status
table immediately below, superseding the original revision's "NOT
DONE"/"significant gap" rows for this specific item.

| DEC-105 task | Status |
|---|---|
| Move the mock ITSM store logic (incl. `_simulate_error` semantics) into a new eval-only fixture | **DONE** — `eval/mock_itsm_fixture.py`, an intentional, documented duplicate of `mcp_server/itsm_store.py` (seed data byte-for-byte identical, same-PR sync rule stated explicitly in both files) |
| Update `domain_executor.py` to use a test-only MCP client stub instead of patching the real module | **DONE** — `eval_call_tool()` in the new fixture module, patched onto both `agent.nodes.tool_invoke.call_tool` and `agent.nodes.human_approval.call_tool` for the duration of each domain case |
| Re-verify `test_dec009_route_assertion.py`/`test_gate_tolerance.py`/`test_eval_harness_smoke.py` pass against the split Agent Template | **DONE, verified live** — all three pass; full suite went from 84/95 (11 excluded/failing before this fix) to **95/95** |
| Run the actual domain eval suite and confirm the same pass/fail verdict shape as before the split | **DONE, verified live, with a real model** — `eval-fast`: 2/2. `eval-domain` (real credentials from this project's own `.env`, not a mock/fake run): **60/62 passed, gate verdict PASS**, the same two named/dated known-gap tolerances (`ITR-004`, `TSEL-004`, since 2026-08-21) as G2's own pre-split baseline report recorded — an exact match, not just a plausible one |
| Explicit complement: a genuine network-level fault case in the `MCP_MODE=live` integration/live-validation suite | **DONE, authored** (not live-cluster-verified — out of this session's own scope, same limitation as every other pipeline/deploy-manifest change in this report). No existing case covered this (`mcp-operational-test.yaml`/`security-tests.yaml` only test the NetworkPolicy boundary against an *unauthorized* caller, never the *authorized* agent's own behavior when MCP is genuinely unreachable) — added a new `kill-mcp-connectivity-check` step to `operational-tests.yaml`, in both the top-level project's own copy and `skeleton/`'s template copy, mirroring the already-proven `kill-primary-fallback-check` throwaway-clone pattern |

### What changed, in detail

**`eval/mock_itsm_fixture.py` (new)**: `MockItsmFixture` class + seed data,
copied from `mcp_server/itsm_store.py` deliberately (DEC-105 forbids a
shared import — the Agent Template cannot import the Tools Template's own
package at all), with a prominent same-PR sync-rule comment in both files.
Unlike the real store, `_simulate_error` staying reachable here is
correct and intentional — this class is eval-tooling only, never shipped
in `mcp_server/` or any rendered project. `eval_call_tool(tool_name,
arguments, timeout=...)` is the test-only MCP client stub: same call
signature as the real `mcp_server/client.py::call_tool` (a drop-in
`patch(..., side_effect=eval_call_tool)` target, not a call-site rewrite),
dispatching to the fixture for `itsm_search_records`/`itsm_create_request`
and returning the same placeholder marker for `placeholder_lookup`/
`placeholder_write_action`.

**`eval/domain_executor.py`**: `import mcp_server.itsm_store` removed
entirely. `_apply_fault`'s `tool_timeout`/`tool_error` branch now patches
the fixture's own `search`/`create_request` methods instead of the real
store's. **The actual dispatch fix, not just the fault-injection
mechanism**: `agent.nodes.tool_invoke.call_tool` and
`agent.nodes.human_approval.call_tool` are now explicitly patched to
`eval_call_tool` for every domain case, not just fault scenarios — this
is what actually makes tool calls work at all in the split Agent
Template's eval harness (previously, only `MCP_MODE`'s env-var-driven
branching decided this, which the real `call_tool`'s own "mock" path
can no longer satisfy since `server.py` isn't bundled here).

**`eval/executor.py` (EXAMPLE-*.yaml harness-mechanics, a *separate* code
path from `domain_executor.py` — found live, not assumed)**: the exact
same structural gap existed here too and was not part of `DEC-104`'s
original finding — `test_eval_harness_smoke.py`'s two tests
(EXAMPLE-001/002) still failed after the `domain_executor.py` fix alone,
with a *different* symptom (a wrong behavioral outcome, not an
`ImportError`, since some other test module's own `MCP_MODE=live`
`setdefault` had already won process-wide by the time this file's tests
ran). Same fix applied: `call_tool` patched at both node-import
boundaries for the duration of each EXAMPLE case.

**`eval/domain_scorer.py`**: same import swap, same `list_records` call
retargeted to the fixture.

**`operational-tests.yaml` (both the top-level project's own copy and
`skeleton/`'s template copy) — new `kill-mcp-connectivity-check` step**:
a throwaway clone of the standing agent Deployment (same
label-merge-not-replace pattern already proven correct for
`kill-primary-fallback-check`/`DEC-101`) with `MCP_TOOL_ENDPOINT`
overridden to an unreachable address (`http://mcp-endpoint.invalid:8081`)
— a genuine network-level fault (DNS/connection failure), not a
simulated one. Verifies three things together: the request completes
well under 30s (bounded by `TOOL_TIMEOUT_SECONDS=10` plus round-trip
margin, not hung), `final_output` contains the real fallback escalation
message, and `fallback_reason` correctly attributes it to a tool error
specifically (`tool_error:...`), not a different failure class.
**Design choice, stated explicitly**: chose an unreachable-endpoint env
override over literally killing the mcp pod or editing a live
`NetworkPolicy` — functionally equivalent (a real network-level failure
either way) but fully isolated to a disposable clone, whereas the other
two approaches would affect the standing deployment other stages in the
same `PipelineRun` still depend on.

### Live verification performed (this revision)

1. Re-rendered the Agent Template fresh (three iterations, the first two
   against stale/mid-edit renders that gave misleading results — the
   final one against the actual post-fix `skeleton/`).
2. Full `pytest` run inside `python:3.12-slim`: **95/95 passed** (up from
   84/95 excluding-3-known-failures in the original revision, and up from
   an initial 5 failures + 2 collection errors on this report's very
   first real run before any fix landed).
3. `make eval-fast`-equivalent (`AGENT_MODEL_MODE=fake python -m eval.cli
   run --all`) against the rendered project: **2/2 cases passed**.
4. `make eval-domain`-equivalent (`python -m eval.cli run --domain`)
   against the rendered project, **using this project's own real `.env`
   model credentials** (the shared dev `LITELLM_URL` endpoint,
   `AGENT_MODEL_MODE=live` — not a fake/offline run): **60/62 passed,
   gate verdict PASS**, tolerated failures `ITR-004`/`TSEL-004` (both
   named, dated `2026-08-21`) — an exact match to G2's own pre-split
   baseline report, the actual proof this decision works, not just unit
   tests passing.
5. `tools/verify_skeleton.py` re-run after all changes: both templates
   still `PASS` (179 files for the Agent Template, up one from the new
   fixture file; 38 for the Tools Template, unchanged).
6. Both new `operational-tests.yaml` files validated for YAML syntax;
   **not** live-cluster-verified (no cluster access in this session's own
   scope, same limitation as this report's original revision) — named
   here, not silently assumed passing.
7. All scratch render directories and temp files cleaned up after
   verification.

### What still isn't done (unchanged from the original revision, restated
for completeness)

Cross-template `NetworkPolicy` admission for `operational-tests.yaml`'s
fallback-demo clone; per-project CI bootstrap scope; `tools/
instantiate_agent_project.py` not extended for the Tools Template; a full
`skeleton/docs/*.md` narrative pass. None of these were in `DEC-105`'s own
assigned scope for this revision.

## Original session report (Stage 2 / G3+G4 core split) — historical,
preserved for continuity

## Status: core split complete and functionally verified live; one
significant, unresolved gap named explicitly (the eval harness)

| Item | Status |
|---|---|
| New Tools Template (`skeleton-tools/`, `template-tools.yaml`, `template-schema-tools.json`) producing a standalone MCP server | **DONE** |
| Agent Template re-cut: `mcp_server/`/`approval_service/` removed, consumed over the network only | **DONE** |
| Boundary guard (no scaffold-invoking tool in the Tools Template's MCP server) | **DONE, verified** (grep, zero hits) |
| Both templates render cleanly (no leaked source-repo literals, no unresolved placeholders, schema/skeleton property parity) | **DONE, verified live** — `tools/verify_skeleton.py`, extended to check both, actually run |
| Both rendered projects' own test suites pass | **DONE, verified live** — Agent: 84/84 (excluding 3 pre-existing eval-CLI-coupled files, named below); Tools: 55/55 |
| Both rendered projects' own Containerfiles build and the images actually run | **DONE, verified live** — real `podman build`, real container start, real `/healthz` response from the agent image |
| Real bugs found and fixed along the way | **6**, listed below, none hypothetical |
| Eval harness (`eval/domain_executor.py`, `eval/domain_scorer.py`) decoupling from `mcp_server.itsm_store` | **NOT DONE — the single most significant gap this session leaves open.** See "What did NOT get resolved" below. |
| Catalog `dependsOn`/`consumesApis` wiring | **DONE** (local YAML only, not live-registered — out of scope per this session's own instructions) |
| Cross-template `NetworkPolicy` multi-consumer admission | **NOT DONE** — named limitation, single-consumer only this phase |
| Live cluster/RHDH registration | **Deliberately not attempted** — out of scope per this session's instructions |

## What was built

### New Tools Template (`skeleton-tools/`)

A complete, independent scaffold producing a standalone MCP server:
`mcp_server/{__init__,server,auth,schemas,itsm_store}.py` (the full
server, `client.py` deliberately excluded — that's the Agent Template's
own calling surface, not the server's concern), its own single-purpose
`Containerfile`/`entrypoint.sh`/`requirements.txt`, `deploy/kustomize/`
(Deployment, Service, ServiceAccount, NetworkPolicy, PDB, ConfigMap — all
new, none copied from the old co-deployed shape without adaptation),
three Tekton Pipeline Tasks reused verbatim where genuinely generic
(`fetch-source`, `unit-tests`, `digest-capture`, `sbom-generate`,
`open-promotion-pr`) and two rewritten for a standalone repo
(`deploy-ephemeral`, `destroy-ephemeral`) plus one Task built fresh
(`mcp-operational-test`, using throwaway consumer-labeled probe pods
instead of a co-deployed agent, which this repo has none of), a
`catalog-info.yaml` declaring a `Component` + `API` entity, and
`template-tools.yaml`/`template-schema-tools.json` at the blueprint
repo's root (sibling to the Agent Template's own).

### Agent Template re-cut (`skeleton/`)

`mcp_server/` trimmed to `__init__.py` + `client.py` only (matches G2's
own already-proven `Containerfile.agent` COPY-list decision exactly, not
re-derived independently); `approval_service/` removed entirely — no
Python import in `agent/` ever referenced it directly (confirmed by
grep before deleting, not assumed), only prose comments. Single-purpose
`Containerfile`/`entrypoint.sh`, mirroring G2's `Containerfile.agent`/
`entrypoint-agent.sh`. `requirements.txt` trimmed to agent-only packages.
`deploy/kustomize/base/`: removed every `*-mcp.yaml`/`*-approval.yaml`
manifest and the old co-deployed `networkpolicy.yaml` (that boundary now
lives in the Tools Template's own repo, protecting *its* ingress, not
this one). New required scaffold parameters `mcpEndpoint`/
`approvalServiceEndpoint` (no default — genuinely required, there is no
same-project value to fall back to anymore) plus optional
`oidcIssuerUrl`/`modelRoute`/`mcpApiName`. `catalog-info.yaml` declares
`consumesApis: [${{ values.mcpApiName }}]` and `dependsOn:
[resource:default/platform-approval-service]` (a fixed, platform-level
resource name, deliberately not derived from this project's own name).
`docs/architecture.md` rewritten for the new topology (mirrors G2's own
already-proven pattern of naming the old design explicitly rather than
silently deleting its description).

## Real bugs found and fixed (all found live, none hypothetical)

1. **Leaked source-repo literal in three new files**
   (`skeleton/catalog-info.yaml`, `skeleton-tools/catalog-info.yaml`,
   `skeleton-tools/README.md`) — caught by `verify_skeleton.py`'s own
   sweep on the very first run. Two different root causes: (a) a
   hardcoded platform-resource name baked this project's own name into
   what should be a fixed, project-agnostic Platform Foundation entity
   name (`golden-path-agent-approval-service` → `platform-approval-service`);
   (b) custom Backstage annotation-key namespaces literally used
   `golden-path-agent/` as a prefix (`→ tool-contract.io/`); (c) README
   provenance prose used the exact hyphenated literal instead of the
   space-separated form the existing `skeleton/README.md` title already
   established as the safe convention (`golden-path-agent` →
   `Golden Path Agent`, matching precedent rather than inventing a new one).
2. **`ephemeral-test`'s own `MCP_MODE=mock` ConfigMap override,
   untouched since before the split, latent** — the exact `DEC-096`/
   `DEC-101` class of bug G2 already found and fixed for the
   non-templated project, still present in `skeleton/`'s own ephemeral-test
   overlay because G2 was explicitly out of scope for touching `skeleton/`.
   A pod-spec `envFrom` value beats the image's own `ENV MCP_MODE=live`
   default, so this would have silently reintroduced the ImportError
   crash-loop the moment this template's own CI pipeline ran live. Removed,
   with the reasoning recorded inline so it isn't reintroduced a third time.
3. **`eval/domain_scorer.py`-adjacent code aside, three separate
   in-suite unit tests relied on `MCP_MODE`'s in-process "mock" dispatch
   to real mock-tool logic** (`test_write_gating.py`,
   `test_graph_shell.py`, `test_tool_invoke_dispatch.py`) — all three
   `ImportError`'d or produced wrong assertions once `mcp_server/server.py`
   was removed, since `client.py`'s own `mock` branch does
   `from . import server`. Fixed by patching `call_tool` at each
   importing module's own boundary (`agent.nodes.tool_invoke.call_tool`,
   `agent.nodes.human_approval.call_tool`) with return values matching
   exactly what the real mock tools would have returned (including the
   real seeded `INC-10255` record content for the one test that asserts
   on real seeded data, not just a generic marker) — verified live,
   84/84 tests pass post-fix (up from an initial 5 failures + 2 hard
   collection errors on the first real render+test run).
4. **`security-tests.yaml`'s `rest-zero-mutation-check` read a
   hardcoded co-deployed `${{ values.name }}-mcp:8081` Service DNS** to
   verify zero-mutation-on-reject — no longer resolvable once mcp isn't
   co-deployed. Fixed to read the agent pod's own already-configured
   `MCP_TOOL_ENDPOINT` environment variable instead (the same value the
   agent's real tool calls already use) rather than hardcoding a second,
   now-wrong assumption about where the tool server lives.
5. **`security-tests.yaml`'s `disallowed-egress-proof` step tested a
   NetworkPolicy this repo no longer owns** (the old co-deployed mcp
   ingress restriction) — removed; the Tools Template's own
   `mcp-operational-test.yaml` (built this session) is the correct home
   for this check now, from the side that actually owns the resource
   being tested.
6. **`operational-tests.yaml`'s `kill-primary-fallback-check` clone
   dropped `commonLabels`-injected labels via a full replacement,
   latent since before the split** — proactively fixed with the same
   merge-based pattern the coordinating session already applied to the
   non-templated project's equivalent bug (`DEC-101`), rather than
   waiting for a live run to rediscover the identical class of bug a
   third time. Not independently live-verified this session (no live
   cluster run attempted, per this session's own scope), but the fix is
   mechanically identical to one already proven correct.

## What did NOT get resolved — named, not silently absorbed

**The eval harness's coupling to `mcp_server.itsm_store` is a real,
significant, unresolved architectural gap**, discovered while trying to
get the Agent Template's own rendered test suite fully green:
`eval/domain_executor.py` and `eval/domain_scorer.py` both
`import mcp_server.itsm_store` directly, and `domain_executor.py`
specifically **monkey-patches** `itsm_store.store.search`/
`create_request` in-process to deterministically inject failure
scenarios for domain eval cases (`_simulate_error`-style scenario
injection). This is a fundamentally different, deeper coupling than the
three unit-test files fixed above (which needed only a return-value
mock at a call boundary) — in-process method patching cannot be
replicated across a real network boundary at all once the MCP server is
a genuinely separate, independently-deployed process. This affects:
`tests/test_dec009_route_assertion.py`, `tests/test_gate_tolerance.py`,
and `tests/test_eval_harness_smoke.py` (all three still fail/error against
the rendered Agent Template — left failing, not worked around), and by
direct extension `make eval`/`eval-fast`/`eval-domain` and the CI
pipeline's own `eval-gate-offline`/`eval-gate-live` Tasks, none of which
were exercised against the split Agent Template this session.

This is not a small follow-up — it needs a real design decision (a
debug/test-only scenario-injection surface on the Tools Template's own
server, accepting simulated-failure parameters via the request itself;
or a different eval-harness architecture entirely for domain cases that
need deterministic tool-level failure injection) before the Agent
Template's own eval gate can be trusted to actually run against the
split shape. Recommend this become its own explicitly-scoped follow-up,
not squeezed into a future session's margins.

**Other named, smaller gaps, not resolved:**
- **Cross-template `NetworkPolicy` admission for the
  `operational-tests.yaml` fallback-demo clone**: that clone deliberately
  carries a distinct `component=agent-fallback-demo` label (to avoid
  ReplicaSet adoption by the standing agent Deployment) — but the Tools
  Template's own `NetworkPolicy` only admits `component=agent`. A real
  cross-repo coordination question (documented inline in
  `operational-tests.yaml`'s own comment), not solved here.
- **Per-project CI bootstrap for the Tools Template**: this session did
  not create a `pipelines/bootstrap/` for the new Tools Template (its own
  CI namespace/RBAC). The existing Agent Template's own
  `pipelines/bootstrap/` still contains Keycloak/RHDH/GitOps/Pipelines-
  operator install manifests predating the Platform Foundation split
  (G1's own territory now) — untouched, since re-architecting what
  "bootstrap" means per-project vs. platform-wide for either template is
  out of proportion to this session's own scope. Both templates'
  per-project CI namespace/RBAC provisioning needs a real decision.
- **`tools/instantiate_agent_project.py` (F3's CLI) was not extended**
  to support rendering the Tools Template — it's still hardcoded to the
  single Agent Template schema/skeleton via module-level constants.
  `tools/verify_skeleton.py` was extended (per this session's explicit
  scope); the CLI's own equivalent extension is a small, mechanical
  follow-up, not attempted here to keep this session's diff focused.
- **A full `skeleton/docs/*.md` consistency pass was not done** — only
  `docs/architecture.md` (the structurally significant one) was rewritten.
  `docs/environments.md`/`local-dev.md`/`security-identity.md`/
  `owner-walkthrough.md` were spot-checked for the exact leaked-literal
  classes this session's own verification catches, found clean, but not
  rewritten for full narrative accuracy against the new topology.
- **Model-route wiring (`modelRoute`)**: added to the schema per this
  session's own instructions, recorded as a `catalog-info.yaml`
  annotation, but deliberately not wired into any actual model-endpoint
  configuration — real model config still flows entirely through
  per-environment kustomize overlays, unrelated to scaffold-time
  templating. This is the seam a future catalog-backed picker (G5) would
  replace, not a functional gap in what exists today.

## Live verification performed (commands run, actual outcomes)

1. **`tools/verify_skeleton.py`, extended to check both templates,
   actually run**: found 3 real leaked-literal failures on the first
   pass (listed above), fixed, re-run clean — `PASS` on both targets
   (178 files swept for the Agent Template, 38 for the Tools Template),
   plus a new schema/test-values completeness check (every declared
   schema property is exercised by the verification's own test values)
   that also passed for both.
2. **Boundary guard**: `grep` across `skeleton-tools/mcp_server/*.py` for
   any scaffold-invoking reference — zero hits.
3. **Both templates rendered to real scratch directories** (not just
   swept in place) via `skeleton_renderer.render_skeleton()` directly.
4. **Full `pytest` run against each real rendered project**, inside a
   `python:3.12-slim` container (matching this project's own established
   CI method exactly, `--userns=keep-id` needed for the container to
   write to the rendered-directory mount under this sandbox's own
   permission model — noted for whoever repeats this): Agent Template
   went from 5 failures + 2 hard collection errors (on the very first
   real run) → 84 passed (excluding the 3 eval-harness-coupled files
   named above as unresolved) after the fixes in this report. Tools
   Template: 55 passed, clean on the first real run.
5. **Both rendered `Containerfile`s actually built** with `podman build`
   — real, successful builds, not just `Dockerfile` syntax review.
6. **Both rendered images actually started as real containers**: the
   Tools Template's MCP server came up cleanly (`Uvicorn running on
   http://0.0.0.0:8081`, `StreamableHTTP session manager started`) and
   shut down cleanly on stop. The Agent Template's agent came up cleanly
   (`Uvicorn running on http://0.0.0.0:8080`) and its real `/healthz`
   endpoint returned `{"status":"ok"}` via a real HTTP request from
   inside the running container.
7. All scratch render directories, temporary images, and temporary
   containers cleaned up after verification — nothing left behind in the
   worktree beyond the intended source changes.

## Drafted decision entry (numbered as a placeholder — land at the
coordinating session's own next available `DEC-NNN`, wording free to
adjust to match the log's exact tail at merge time)

```
## DEC-1xx — G3+G4 complete: Tools Template created, Agent Template
re-cut to consume it and the platform approval service over the network
only; one significant gap named -- the eval harness's own
mcp_server.itsm_store coupling is not yet resolved

**Context**: DEC-099's Stage 2, combined into one worktree stream
(rather than two separate G3/G4 streams) because both operations
partition the same skeleton/ tree -- doing them as uncoordinated
parallel streams would recreate the exact file-collision risk Stage 1's
G1/G2 streams already taught this project to avoid. This coordinating
session lands this entry; the worktree stream never touched
DECISIONS.md/HANDOFF.md/PINS.md directly.

**What changed**: a new Tools Template (skeleton-tools/,
template-tools.yaml, template-schema-tools.json) produces a standalone
MCP server -- full server implementation, its own single-purpose
Containerfile/pipeline/deploy manifests, a catalog Component+API
declaration. The existing Agent Template (skeleton/) is re-cut:
mcp_server/ trimmed to client.py only (mirroring G2's own already-proven
Containerfile.agent COPY list), approval_service/ removed entirely (zero
Python import ever referenced it directly, confirmed by grep before
deleting). New required scaffold parameters mcpEndpoint/
approvalServiceEndpoint (genuinely required, no default -- there is no
same-project value to derive them from anymore); optional
oidcIssuerUrl/modelRoute/mcpApiName. catalog-info.yaml added to both
templates: the Agent Template's declares consumesApis (the Tools
Template's own API, by name) and dependsOn a fixed, platform-level
Resource name (platform-approval-service -- deliberately not derived
from any specific project's own name, since it's a shared singleton).

**Six real bugs found and fixed, all live, none hypothetical**: three
leaked source-repo literals in new catalog-info.yaml/README.md files
(caught by tools/verify_skeleton.py's own sweep, extended this session
to check both templates); a latent MCP_MODE=mock ConfigMap-override bug
in skeleton/'s own ephemeral-test overlay, untouched since before the
split and structurally identical to the DEC-096/DEC-101 class of bug
G2 already fixed for the non-templated project (G2 was explicitly out
of scope for skeleton/, so this instance was never caught until now);
three unit tests relying on MCP_MODE=mock's in-process dispatch to real
mock-tool logic, fixed by mocking call_tool at each importing module's
own boundary with return values matching the real mock tools exactly
(verified live: 84/84 Agent Template tests pass post-fix, up from 5
failures + 2 collection errors on the first real run); a
security-tests.yaml check reading a hardcoded co-deployed mcp Service
DNS that no longer resolves, fixed to read the agent's own already-
configured MCP_TOOL_ENDPOINT instead; a security-tests.yaml check
testing a NetworkPolicy this repo no longer owns, removed (the Tools
Template's own new mcp-operational-test.yaml is the correct home now).

**Verified live, not just rendered**: both templates render cleanly (zero
leaked literals, zero unresolved placeholders, schema/skeleton property
parity -- tools/verify_skeleton.py extended and actually run, not just
edited); both rendered projects' own full test suites pass (Agent:
84/84 excluding three eval-harness-coupled files named as a real,
unresolved gap below; Tools: 55/55); both rendered Containerfiles
actually build with podman; both built images actually start as real
containers and respond to a real HTTP request (the agent's /healthz
returned {"status":"ok"} from inside a running container; the Tools
Template's MCP server came up and shut down cleanly).

**SIGNIFICANT GAP, not resolved, recorded plainly**: the eval harness
(eval/domain_executor.py, eval/domain_scorer.py) imports
mcp_server.itsm_store directly and monkey-patches its methods in-process
to inject deterministic failure scenarios for domain eval cases -- a
fundamentally deeper coupling than the three unit-test fixes above
(in-process method patching cannot cross a real network boundary at
all). tests/test_dec009_route_assertion.py, tests/test_gate_tolerance.py,
and tests/test_eval_harness_smoke.py all still fail/error against the
split Agent Template, left failing rather than worked around, and by
extension make eval/eval-fast/eval-domain and the CI pipeline's own
eval-gate-offline/eval-gate-live Tasks were not exercised against the
split shape this session. This needs a real design decision (a
debug-only scenario-injection surface on the Tools Template's own
server; or a different eval-harness architecture for domain cases
needing deterministic tool-level failure injection) -- named here as
its own explicitly-scoped follow-up, not something to squeeze into a
future session's margins.

**Other named gaps, deliberately not resolved this session**: (1) a
cross-template NetworkPolicy admission question for
operational-tests.yaml's fallback-demo clone (documented inline in that
file); (2) per-project CI bootstrap (namespace/RBAC) was not created for
the new Tools Template, and the Agent Template's own pipelines/bootstrap/
still contains pre-Platform-Foundation operator-install manifests,
untouched -- a real decision for G1/G6 about what "bootstrap" means
per-project vs. platform-wide; (3) tools/instantiate_agent_project.py
(F3's CLI) was not extended to support the Tools Template -- still
hardcoded to the Agent Template's own schema/skeleton; (4) a full
skeleton/docs/*.md narrative-accuracy pass was not done, only
docs/architecture.md.

**Status**: G3+G4's core split is complete and functionally verified
live. STOP 5/6 (per the original phase design's own numbering) are not
yet declared cleared -- the eval-harness gap above is significant enough
that this entry recommends treating it as a precondition for declaring
either template "done," not a footnote to note in passing.
```

## Drafted decision entry, this revision (numbered as a placeholder --
land at the coordinating session's own next available `DEC-NNN`)

```
## DEC-1xx — DEC-104's eval-harness gap closed per DEC-105: domain eval
now runs against an in-process eval-only fixture, decoupled from the
real MCP server; the network-fault fidelity complement is authored in
the MCP_MODE=live integration suite

**Context**: DEC-105 assigned implementation back to the G3+G4 stream.
This entry records that work as done and verified live, not just
attempted.

**What changed**: a new `eval/mock_itsm_fixture.py` duplicates
`mcp_server/itsm_store.py`'s search/create_request logic and seed data
(byte-for-byte identical, a same-PR sync rule stated in both files) --
deliberately, per DEC-105's own ruling that this must be a decoupled
copy, never a shared import (the Agent Template cannot import the Tools
Template's own package at all). Its `eval_call_tool()` is the test-only
MCP client stub, patched onto `agent.nodes.tool_invoke.call_tool` and
`agent.nodes.human_approval.call_tool` for the duration of every domain
eval case in `eval/domain_executor.py` -- fault injection
(`_apply_fault`'s timeout/error scenarios) now patches the fixture's own
methods, never touching the real, deployed server at all. The real
server's own `_simulate_error` guarantee and `server.py`'s refusal to
expose it as a tool parameter are untouched, exactly as DEC-105 required.

**A second, independent instance of the same structural gap found live,
not assumed**: `eval/executor.py` (the EXAMPLE-*.yaml harness-mechanics
path, a separate code path from `domain_executor.py`) had the identical
missing-call_tool-patch problem, undiscovered by DEC-104's own original
finding since its failure symptom was different (a wrong behavioral
result, not an ImportError, because of test-file execution order and a
shared process-wide MCP_MODE env var). Fixed identically.

**Verified live, not just unit-tested**: the full rendered Agent
Template's test suite went from 84/95 (11 failing/excluded, DEC-104's own
finding) to 95/95. `eval-fast`: 2/2. `eval-domain`, run with this
project's own real dev-model credentials (not fake/offline):
**60/62 passed, gate verdict PASS**, tolerated failures ITR-004/TSEL-004
(named, dated 2026-08-21) -- an exact match to G2's own pre-split
baseline. This is the real proof DEC-105's architecture works, not an
assumption resting on unit tests alone.

**Explicit complement, not optional (DEC-105's own condition)**: neither
`mcp-operational-test.yaml` nor `security-tests.yaml` covers this --
both test the NetworkPolicy boundary against an unauthorized caller,
never the authorized agent's own behavior when MCP is genuinely
unreachable. Added `kill-mcp-connectivity-check` to `operational-
tests.yaml` (both the top-level project's own copy and skeleton/'s
template copy): a throwaway clone (same label-merge pattern already
proven correct for kill-primary-fallback-check/DEC-101) with
MCP_TOOL_ENDPOINT overridden to an unreachable address -- a genuine
network fault, not simulated. Verifies the request completes well under
30s (bounded by TOOL_TIMEOUT_SECONDS, not hung), the real fallback
escalation message appears, and fallback_reason correctly attributes it
to a tool error. Authored and YAML-validated; **not live-cluster-verified
this session** (no cluster access in this stream's own scope) -- named
plainly, not silently assumed passing.

**Status**: DEC-104's gap is closed. Domain eval, the EXAMPLE-*.yaml
harness-mechanics suite, and the three previously-failing test files all
verified live against the actual rendered, split Agent Template. The one
remaining open item is live-cluster verification of the new
kill-mcp-connectivity-check step itself -- a live-cluster session's own
job, not this stream's.
```
