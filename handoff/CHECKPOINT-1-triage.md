# Checkpoint 1 — DEC-NNN disposition triage

**STOP — this needs your adjudication before Phase 2 (ADR drafting/amending) or
any citation edit begins.** Nothing below has been applied to any file.

## How this was built

113 distinct decision numbers are cited somewhere in the blueprint. For each
one: an exact occurrence count and its top citing files came from a direct
scan of every git-tracked file (excluding this repo's own lint tool and this
`handoff/` directory); whether it is already linked to an ADR came from
parsing every `docs/adr/*.md`'s own `## Journal` line (the one authoritative
map per the mission's ground rules — nothing below invents a mapping). That
split 113 into **51 already mapped** (55 DEC↔ADR pairs — a few DECs, e.g.
DEC-087, DEC-098, back more than one ADR) and **62 unmapped**. Of the 62, one
(DEC-037) turned out not to be a real citation at all (see below) — the
other 61 were each read in full from `agent-roadmap/DECISIONS.md` (read-only)
by a dedicated review pass and given a proposed disposition.

## Already mapped (51 DECs, 55 pairs) — no action needed here

Their citation *count* still gets resolved per-instance in Phase 3/5
(redirect to the ADR, or drop if the surrounding sentence already carries the
rationale) — that's mechanical, not a triage question. Grouped by ADR:

| ADR | DECs |
|---|---|
| ADR-001 (single approval-gated write path) | DEC-008, DEC-049 |
| ADR-002 (route assertion via call list) | DEC-009 |
| ADR-003 (model-swap five-category gate) | DEC-010, DEC-011 |
| ADR-004 (prompt/model params as measurement instrument) | DEC-012, DEC-015 |
| ADR-005 (decide/generate prompt split) | DEC-013 |
| ADR-006 (OTel read-only) | DEC-020, DEC-071 |
| ADR-007 (eval-gate exception allowlist) | DEC-016, DEC-017 |
| ADR-008 (identity/config contract enforcement) | DEC-046, DEC-053, DEC-063, DEC-065 |
| ADR-009 (single-pin, single-active-cluster) | DEC-078, DEC-083, DEC-084 |
| ADR-010 (explicit kubeconfig context) | DEC-086 |
| ADR-011 (three-image split) | DEC-101 |
| ADR-012 (Platform Foundation shared approval service) | DEC-098, DEC-103 |
| ADR-013 (Gitea as in-repo Git provider) | DEC-098, DEC-100, DEC-112 |
| ADR-014 (eval-only fault-injection fixture) | DEC-105 |
| ADR-015 (TechDocs pinning/local builder) | DEC-120, DEC-121 |
| ADR-016 (Route over Ingress) | DEC-074, DEC-087, DEC-094, DEC-097 |
| ADR-017 (Keycloak deployment/secret rotation) | DEC-054, DEC-056, DEC-059, DEC-087 |
| ADR-018 (CI pipeline ephemeral architecture) | DEC-024, DEC-025, DEC-030 |
| ADR-019 (build/CI discipline tooling) | DEC-023, DEC-034, DEC-044 |
| ADR-020 (OTel Collector deployment) | DEC-068, DEC-119 |
| ADR-021 (scaffolding and Gitea publish) | DEC-087, DEC-110, DEC-111, DEC-123 |
| ADR-022 (skeleton design) | DEC-087, DEC-088, DEC-090 |
| ADR-023 (platform catalog entity model) | DEC-102 |
| ADR-024 (static HTML approver UI) | DEC-072 |
| ADR-025 (approval service REST contracts) | DEC-045 |

## The DEC-098/DEC-099 discrepancy you asked about

**Resolved: DEC-099 → drop, nothing to fold in.** It's Phase G's parallel-
worktree scheduling/governance record (four-stage table, worktree isolation
rules, merge order) — process content, no architecture decision of its own.
The blueprint's paired "DEC-098/DEC-099" comments (the three-image-split /
Platform-Foundation-singleton architecture) are substantively DEC-098's
alone: ADR-011's and ADR-012's own Journal lines already cite DEC-098 (plus
DEC-101/DEC-103) and never DEC-099. All 95 blueprint citations of DEC-099
are short inline mentions, none narrative, so dropping the DEC-099 half of
every paired citation loses nothing.

## Orphan citation: DEC-037 has no entry at all

I ran this one down myself rather than through the review pass, since it's a
single, mechanical fact rather than a judgment call. Five blueprint
citations (`pipelines/tasks/deploy-ephemeral.yaml`,
`pipelines/tasks/open-promotion-pr.yaml`, and their `skeleton/`/
`skeleton-tools/` copies) cite "DEC-037" for two unrelated facts — a
`kustomize edit set image` whole-file-rewrite quirk, and a bare
`Authorization: Bearer` failing for `git push` over HTTPS. `DECISIONS.md`
jumps directly from `## DEC-036` to `## DEC-038`; no `## DEC-037` heading
exists. Both cited facts are, verbatim, **DEC-036**'s own "Bug 1" and
"Bug 2" findings — the code comments were written citing a number one
higher than the entry that actually contains this content. **Proposed fix:
mechanical, in Phase 5 — re-point all 5 citations from `DEC-037` to
`DEC-036`.** DEC-036 itself is triaged `drop` below (its content is already
fully restated at each citation site), so once corrected these become plain
drops like any other.

## New-ADR candidates (6)

Genuinely load-bearing, no existing ADR covers them.

| DEC | Proposed ADR | Why | Confidence |
|---|---|---|---|
| DEC-061 | Per-component ServiceAccount separation (agent/mcp/approval), client-credentials over SA-token OIDC federation | A real identity-boundary decision with a stated, deliberate tradeoff (SA-token federation named as the phase-two integration point). No existing ADR covers ServiceAccount topology. | medium |
| DEC-080 | Idempotent from-scratch cluster bootstrap sequence | First time the whole blueprint bootstrapped from Git alone; establishes `make bootstrap` as the adopter entrypoint plus several still-live choices (Manual InstallPlan approval scoped to the pinned CSV, create-once vs. regenerate-every-run secrets, two independent CR-readiness waits, the ArgoCD managed-by opt-in label). | medium |
| DEC-135 | Adopter-tolerant OLM operator/Subscription detection (package-name match, exact-CSV InstallPlan approval, channel+minimum-version tolerance) | Two real, still-live bugs fixed in reusable `scripts/bootstrap.sh` logic used for every operator install: match a pre-existing Subscription by package name (not this blueprint's own object name), and approve InstallPlans by matched CSV, never by trusting `status.installPlanRef` (confirmed wrong live under concurrent Manual upgrades). | medium |
| DEC-138 | Bootstrap input-validation contract: `bootstrap.env`, step-0 fail-fast, no mid-run manual STOPs | The single heaviest-cited unmapped DEC (19 citations). Every owner input declared in `bootstrap.env.example`, validated in full at step 0, credentials generated in-script, former STOP-and-exit blocks became real PASS/FAIL tables. No existing ADR covers bootstrap input handling. | medium |
| DEC-139 | Day-zero bootstrap rebuilds from the pinned recipe and promotes via a real PR (never pulls a pre-built digest by default) | An explicit, stated principle extending CLAUDE.md's own immutable-artifact/promotion-via-PR rules into concrete step-9b behavior, plus a real E2E-probe design (discovers the live Route, never assumes a host). No existing ADR covers first-cluster bootstrap. | high |
| DEC-092 | RHDH (developer portal) deployment: AllNamespaces operator + namespace-scoped CR, external Postgres, OIDC client provisioning | Structurally parallel to what ADR-013 (Gitea) and ADR-017 (Keycloak) already do for their own Platform Foundation components; no ADR covers RHDH's own deployment shape or the KeycloakRealmImport one-shot-Job limitation it found. **Flagged low confidence by the reviewer** — the facts are already stated concisely at each citation site, so the case rests on structural parity with the other two ADRs more than on missing information today. Worth a second look before committing to a new document. | low |

## Amend-existing candidates (10)

Real content, but it belongs inside an ADR that already exists.

| DEC | Fold into | What it adds |
|---|---|---|
| DEC-031 | ADR-018 (CI pipeline ephemeral architecture) | A documented upstream Kustomize limitation (kustomize#1040/#4581) forcing `deploy-ephemeral` to transiently edit `base/`'s own kustomization.yaml in a scratch checkout rather than relying on an overlay `images:` patch. |
| DEC-032 | ADR-018 | Pull-side counterpart to DEC-024's push-side `system:image-builder` grant — same pattern (namespace-scoped RoleBinding per consuming SA), already implicit in ADR-018's own Consequences. |
| DEC-040 | ADR-018 | Ephemeral-test is deliberately pipeline-managed and kept out of the ArgoCD app-of-apps root so `selfHeal` never fights the pipeline's own apply; demo-prod is fully GitOps-synced. Reviewer flagged medium-low confidence — couldn't confirm ADR-018 doesn't already state this. |
| DEC-047 | ADR-025 (approval service REST contracts) | Two load-bearing points not in ADR-025 today: the atomic terminal-transition relying on SQLite's file-level lock under concurrent decisions, and JWT algorithm derived from the matched JWK, never the token's own header. **Side finding**: the blueprint's actual "DEC-047" citations (entrypoints, `scripts/dev.sh`) are mislabeled — that content is DEC-048's, not DEC-047's. Worth fixing as its own small correction in Phase 5. |
| DEC-057 | ADR-017 (Keycloak deployment) | Two points not yet in ADR-017's text: deliberately no TLS/Route at the Keycloak layer, and `OIDC_ISSUER_URL` pinned to Keycloak's internal Service DNS so the `iss` claim stays consistent by construction between agent and approval service. |
| DEC-069 | ADR-025 | A real, previously-unnoticed gap: 3 of 4 approval-service routes ran with zero auth check under `AUTH_MODE=oidc`. Fixed by a shared, role-agnostic `get_authenticated_caller`. |
| DEC-104 | ADR-014 (eval-only fault-injection fixture) | ADR-014's own Context already describes this exact problem (in-process MCP monkey-patching breaking once the MCP server became a real network process) but its Journal cites only DEC-105, the resolution — DEC-104 is the escalation that led there and belongs alongside it. |
| DEC-118 | ADR-021 (scaffolding and Gitea publish) | The real, live Gitea Scaffolder dynamic plugin build (wired via the Backstage CR's `dynamicPluginsConfigMapName`/`extraFiles`) driving a real `publish:gitea` task — squarely ADR-021's own subject. |
| DEC-137 | ADR-013 (Gitea as in-repo Git provider) | One currently-undocumented fact: Gitea is provisioned conditionally, gated on `--with-rhdh`, because it exists solely to serve RHDH's Scaffolder publish action. Reviewer flagged low confidence — a close call against just dropping it, since a bug-fix narrative dominates the rest of the entry. |
| DEC-019 | ADR-007 (eval-gate exception allowlist) | A textbook application of ADR-007's own "named, dated, per-case, which assertions are excludable" convention — narrows ITR-004's known-gap scope after a partial fix. |

## Move (6) — blueprint prose itself needs to shrink, not just the citation

These aren't short inline citations; the reviewer found the *content itself*
reproduced as multi-sentence/paragraph narrative directly in shipped files.
Excising the narrative is a Phase 4/5 editorial task, not a mechanical strip
— each needs the file trimmed to the operationally necessary instruction,
with the removed narrative going to `handoff/to-roadmap/` for you to move
into `agent-roadmap` if it's worth keeping there.

| DEC | Where the narrative lives | What should survive in the blueprint |
|---|---|---|
| DEC-005 | `srs/SRS-EVH.md` (near-verbatim derivation narrative) | The requirement text itself — the "why" is already implied by the requirement. |
| DEC-022 | `docs/phase-c-runbook.md` §4 + `eval/cases/domain/prompt_injection.yaml`'s `threshold_notes` | The distilled operational rule only: re-run N=5 reps before treating a live-gate failure as a regression. |
| DEC-026 | `skeleton/pipelines/pipelinerun-template.yaml` header (lines 8-24) — **ships into every adopter's generated project** | A short comment stating the fact (`serviceAccountName` must be under `spec.taskRunTemplate`, not top-level) without the forensic story of how it was found. |
| DEC-042 | `docs/phase-c-runbook.md` lines ~295-329 | A short pointer to ADR-019 (which already owns the placeholder-scanning design this narrative argues for) instead of the incident story. |
| DEC-075 | `skeleton/docs/owner-walkthrough.md` "Pre-flight verification" (shared with DEC-076) — **ships into every adopter's generated project** | The actionable instruction only: use port 8082, not 18082. |
| DEC-076 | Same file/section as DEC-075 | The actionable instruction only: use a private/incognito window (no real logout control exists). |

## Drop (39) — citation can simply be stripped once Phase 3/5 reaches it

Every one of these was read in full; in every case the reviewer confirmed
the technical rationale is already fully restated at the blueprint's own
citation site(s), so nothing is lost by removing the `DEC-NNN` token. Grouped
loosely by theme for scanning, not by any further action needed here:

**Requirements/process bookkeeping, no runtime content:** DEC-001 (SRS
derivation order), DEC-002 (session-authorization scope check), DEC-003 /
DEC-007 (SRS traceability-anchor fixes), DEC-004 (session-authorization
re-confirmation), DEC-091 (OI-04 milestone tracking), DEC-114 (worktree
file-ownership coordination), DEC-130 (reference-implementation scope
reframe).

**One-off pipeline/cluster incident, fix already inline at the site:**
DEC-021 (Checkpoint B2 closure — **note:** some blueprint citations
attribute richer rationale to DEC-021 than its own text contains; that
rationale is either original blueprint prose or actually DEC-040's, already
captured under "amend" above), DEC-027 / DEC-028 (arbitrary-UID `HOME=/tmp`
CI fix and its pytest-invocation follow-on), DEC-029 (superseded by
DEC-030, already in ADR-018), DEC-033 (three pipeline pod-facing bugs),
DEC-035 (K8s config-path gap, actual pattern is DEC-044's, already in an
ADR), DEC-036 (see DEC-037 above), DEC-038 (seeded-regression gate proof),
DEC-039 (promotion-PR verification — **note:** some citations attribute a
Secret-shadowing mechanism to DEC-039 that isn't in its text), DEC-041
(ArgoCD AppProject field bug), DEC-043 (telemetry field threaded through,
mechanical), DEC-050 (retired kustomize workaround, blueprint already says
so), DEC-051 / DEC-052 (RBAC-applied-live + endpoint-config verification),
DEC-055 (poisoned shared-cluster CatalogSource — actual fix is DEC-056's),
DEC-058 (Keycloak realm import applied live), DEC-062 (five more config
keys, same established pattern as DEC-044), DEC-064 (ArgoCD whitelist gap,
already flagged twice before), DEC-081 (showcase-cluster storage-class
fix), DEC-085 (**note:** DEC-085's own text says a downstream citation of
it was an error — the real record is DEC-119; `PINS.md:74` and
`platform/bootstrap/otel-collector.yaml` should be corrected to DEC-119,
not just dropped), DEC-093 (RHDH STOP-5 verification), DEC-095 / DEC-122
(GithubUrlReader host-match bug, found twice), DEC-096 (three local-dev
defects), DEC-113 (incomplete/blocked spike, superseded by DEC-118/123),
DEC-136 (**[borrowed-cluster adaptation]**, by the entry's own
classification — not a blueprint decision at all).

**Eval-harness measurement/remediation rounds, rationale already in
`threshold_notes`/comments:** DEC-006, DEC-014, DEC-018, DEC-079.

## Consolidated open questions for you

1. **DEC-092 (RHDH new-ADR)** — low confidence. Worth a second look: does it
   genuinely deserve a standalone document for structural parity with
   ADR-013/ADR-017, or should it just be dropped like the rest of the
   "verification/status" entries?
2. **DEC-137 (amend into ADR-013)** — low confidence, a close call against
   dropping. Your call on whether the one undocumented fact (Gitea's
   conditional `--with-rhdh` gating) is worth a Consequences-section
   addition.
3. **DEC-040 (amend into ADR-018)** — medium-low confidence; the reviewer
   could not confirm ADR-018 doesn't already cover this exact point. Worth
   reading ADR-018's current body before committing.
4. Three **incidental mis-citation findings**, distinct from disposition and
   worth fixing alongside the citation cleanup itself, not folded into any
   ADR:
   - `PINS.md:74` and `platform/bootstrap/otel-collector.yaml` cite
     **DEC-085** for the OTel sidecar pin-pruning outage; DEC-085's own text
     says that citation is an error and the real record is **DEC-119**
     (already correctly cited in `skeleton/pipelines/bootstrap/otel-collector.yaml`).
   - `entrypoint-agent.sh`/`entrypoint-approval.sh`/`entrypoint-mcp.sh`,
     `Containerfile.agent`, and `scripts/dev.sh` cite **DEC-047** for the
     retired three-way entrypoint dispatch; that content is actually
     **DEC-048**'s.
   - `docs/environments.md` and `tools/check_config_contract.py` cite
     **DEC-039** for the Secret-shadowing/`envFrom`-ordering mechanism; that
     mechanism doesn't appear anywhere in DEC-039's actual text.
5. **DEC-099/DEC-098 resolution above** — please confirm you're comfortable
   with "DEC-099 drops entirely, DEC-098 is the real decision ADR-011/012
   already own" before Phase 5 touches the ~95 paired citations.
6. Is the **DEC-037 → DEC-036 renumbering** (orphan citation, no entry
   exists) fine to apply mechanically in Phase 5, or do you remember this
   differently and want to check `agent-roadmap` yourself first?

## Next step

Once you've adjudicated the above (confirm, adjust, or veto any row),
Phase 2 amends the 10 "amend-existing" ADRs and drafts the 6 (or 5, per
question 1) "new-adr" documents — nothing else moves until that table comes
back settled.
