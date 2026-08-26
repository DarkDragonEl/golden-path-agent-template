# Phase H0 — Documentation & DX audit

Read-only audit. Produced by three parallel exploration passes plus a
7-way parallel full classification of every `DEC-` comment hit across
`agent/ mcp_server/ approval_service/ scripts/ pipelines/ deploy/ platform/`.
Companion file: `reports/docs-terms-sheet.md`.

## 1. Markdown inventory — audience, freshness

16 files under `docs/`, plus the root `README.md`. None of the five
mission-referenced files (`docs/provenance.md`, `docs/glossary.md`,
`docs/naming-conventions.md`, `docs/access-and-credentials.md`,
`docs/README.md`) exist yet.

| File | Audience | Freshness |
|---|---|---|
| `README.md` | External reader | **Stale** — documents 7 of 19 real top-level directories; predates `approval_service/` (Phase D), the skeleton/scaffolder tree (Phase F), and the whole Platform Foundation split (Phase G) |
| `docs/architecture.md` | External reader / new engineer | Current — documents the three-image split (DEC-098/099) and explicitly marks the old single-Containerfile design superseded |
| `docs/direct-chat-walkthrough.md` | Operator/tester | Current in mechanics (4-container `make up` topology, correct ports) |
| `docs/drafts/AGENT-UI-MAP.draft.md` | Archaeologist | Explicitly draft/provisional, Phase D era (DEC-075) |
| `docs/environments.md` | Operator | Phase C/D era; no mention of the three-image split — re-check for drift |
| `docs/evaluation.md` | External/operator | Current, phase-agnostic |
| `docs/local-dev.md` | Operator | **Stale — direct drift**: Quickstart text says `make up-offline` "builds the image once ... starts all three roles" — the pre-G2 single-image model `docs/architecture.md` itself calls superseded |
| `docs/owner-walkthrough.md` | External/operator | Phase D dated (DEC-074/075/076), self-contained checkpoint record, no contradiction |
| `docs/phase-c-runbook.md` | Operator | Phase C dated, long, historical, pre-Phase-G |
| `docs/phase-d-runbook.md` | Operator | Phase D dated, pre-Phase-G |
| `docs/phase-e-kickoff-plan.md` | Archaeologist | Explicitly draft, pre-Phase-G |
| `docs/phase-f-kickoff-plan.md` | Archaeologist | Most current runbook (F0–F3 done); doesn't itself reference the G split |
| `docs/security-identity.md` | External/operator | **Stale — direct contradiction**: still calls the architecture "one-image-two-roles," which `docs/architecture.md` has since declared superseded |
| `docs/showcase-access.md` | Operator (internal) | Phase E dated, deliberately unfilled template |
| `docs/showcase-walkthrough-script.md` | External-facing | Phase E dated, pre-Phase-G |
| `docs/template-nine-output-mapping.md` | Archaeologist | **Most self-aware doc** — dated `DEC-098, 2026-08-26`, explicitly says it "will be re-partitioned when G2-G4 land, not rewritten now" |
| `docs/testing-perspectives-guide.md` | Operator/reviewer | Longest file (605 lines); content unaffected by the image split |

**Drift pair to fix in H2**: `docs/local-dev.md` and `docs/security-identity.md`
both still describe the pre-split single-image model that
`docs/architecture.md` and `docs/template-nine-output-mapping.md` already
document as superseded.

## 2. Link audit

Every relative link and "See X" prose reference across all 16 `docs/*.md`
files plus `README.md` was extracted and classified. **Zero broken in-repo
links found.** The only two class of pointer-related fix work are:

1. **Points outside this repo, unresolvable**:
   - `README.md:4` — inline cites `` `../Agentic_AI_Platform_MVP_Agnostic.md` ``, a file that exists but lives one level above this repo's root.
   - `README.md:53` and `docs/security-identity.md:62` — both cite an unnamed, unlinked "reuse-map artifact referenced from the parent workspace." No literal path is given anywhere; no file matching that description exists in this repo or its immediate parent directory.
2. **Same class of dangling reference, never rendered as a link**: `CLAUDE.md` is cited throughout `DECISIONS.md`/`HANDOFF.md`/`PINS.md`/`reports/*.md` but lives one directory above this repo's root, untracked by this repo's git history (confirmed via `find`). Not a broken markdown link (never written as one), but the identical failure mode a public reader would hit.

The one existing `[text](path)`-style link (`README.md:10` →
`TODO_DOMAIN.md`) works. No external `http(s)` links exist anywhere in
scope. **H1 fixes both instances above; H2 does not need a repo-wide broken-link sweep — there isn't one.**

## 3. Structure audit

Real top-level inventory (19 directories + governance/config files at
root), via `ls -la` and `find -maxdepth 2`:

`agent/ approval_service/ ci/ corpus/ deploy/ docs/ eval/ mcp_server/
pipelines/ platform/ policy/ reports/ scripts/ skeleton/ skeleton-tools/
srs/ state/ tests/ tools/` — plus root files `catalog-info.yaml`,
`Containerfile.agent/.approval/.mcp`, `entrypoint-*.sh`, `DECISIONS.md`,
`HANDOFF.md`, `PINS.md`, `Makefile`, `MISSION_UNATTENDED.md`,
`SHOWCASE_NOTES.md`, `requirements*.txt`, `template.yaml`,
`template-schema.json`, `template-schema-tools.json`, `template-tools.yaml`,
`TODO_DOMAIN.md`.

README's "Layout" section names only 7: `agent/`, `mcp_server/`, `eval/`,
`policy/`, `corpus/`, `deploy/`, `ci/`, plus a generic pointer to `docs/`.
**Not documented at all**: `approval_service/` (a fully independent,
separately-imaged component since Phase D — the most significant omission),
`pipelines/`, `platform/`, `.claude/`, `reports/`, `scripts/`, `skeleton/`,
`skeleton-tools/`, `srs/`, `state/`, `tests/`, `tools/`, `catalog-info.yaml`,
the three `Containerfile.*`, the three `entrypoint-*.sh`, `DECISIONS.md`,
`HANDOFF.md`, `PINS.md`, `Makefile`, `MISSION_UNATTENDED.md`,
`SHOWCASE_NOTES.md`, `requirements*.txt`, all four `template*` files.

**Correction to the mission brief's own assumption**: there is no
`template/` directory. Only `skeleton/`, `skeleton-tools/`, and the four
root `template*.{yaml,json}` files exist. H1's repo-map table must reflect
this real inventory, not the mission brief's draft.

Per-directory `README.md` presence: only `corpus/`, `eval/`, `skeleton/`,
`skeleton-tools/` have one. **15 of 19 top-level directories have none** —
`agent/`, `approval_service/`, `ci/`, `deploy/`, `docs/`, `mcp_server/`,
`pipelines/`, `platform/`, `policy/`, `reports/`, `scripts/`, `srs/`,
`state/`, `tests/`, `tools/`.

No `mkdocs.yml` exists anywhere. `catalog-info.yaml` carries no
`backstage.io/techdocs-ref` annotation. H3b is fully net-new tooling, not an
extension of anything already wired.

## 4. Comment census — complete

`git grep -n "DEC-"` across the seven directories the mission names,
**353 hits total**, matching the grep count exactly:

| Directory | Hits | Category-(a)/(b) one-liners | Narrative blocks | Category-(c) blocks |
|---|---:|---:|---:|---:|
| `agent/` | 48 | 1 | 33 | 5 |
| `mcp_server/` | 5 | 0 | 3 | 1 |
| `approval_service/` | 19 | 3 | 16 | 1 |
| `scripts/` | 22 | 5 | 13 | 6 |
| `pipelines/` | 77 | 3 | 42 | 1 |
| `deploy/` | 127 | 6 | 52 | 13 |
| `platform/` | 55 | 0 | 33 | 8 |
| **Total** | **353** | **18** | **192** | **35** |

**Every long comment block was individually read and cross-checked against
the `DECISIONS.md` entry it cites** (not sampled/extrapolated). One-line
pointer citations were fast-classified by inspection since a bare citation
has no narrative content to lose either way.

### The category-(c) list — complete, migrate before slimming (H4 blocker list)

Each of these contains specific historical/design detail that is **not**
recoverable from the `DECISIONS.md` entry it cites, or cites a `DEC-NNN`
that doesn't exist at all. H4 must migrate each into a `DECISIONS.md`
addendum (or `docs/` page) before its comment may be slimmed.

**`agent/`** (5)
1. `agent/cli.py:1-21` — cites DEC-008/DEC-049, but the actual fact (fresh in-memory checkpointer per run, no cross-*process* resume; `--decision` now genuinely round-trips) is recorded under **DEC-096**, never cited here.
2. `agent/config.py:109-119` — cites DEC-012/013 (a different, later failure mode); the real finding (`draft_request`/`tool_selection` failing when the full `RETRIEVAL_TOP_K` context was injected verbatim — "a detailed procedure document out-competed the tool schemas") is **DEC-010's** finding, never cited.
3. `agent/config.py:157-161` — `AGENT_WORKLOAD_ID`'s deliberate distinctness from `OTEL_SERVICE_NAME` despite a shared default, and "can diverge in a future environment," is absent from DEC-020 and everywhere else (grepped).
4. `agent/telemetry.py:90-97` — the empty-string-not-omitted attribute rationale ("a consistent, always-present attribute is easier to query") is absent from DEC-071 and everywhere else.
5. `agent/tool_result_format.py:1-16` — the Phase B2/B3 bug-discovery narrative (found live-smoke-testing Phase B3 that the same formatting gap also hits `tool_invoke_node`'s read path) is absent from DECISIONS.md entirely.

**`mcp_server/`** (1)
6. `mcp_server/itsm_store.py:25-31` — cites DEC-014; the design-philosophy statement ("store behavior justified by the store's own intent, not a fix bent to match a specific eval outcome") is absent from DEC-014's entry.

**`approval_service/`** (1)
7. `approval_service/api.py:13-21` — cites DEC-046; the telemetry-via-structured-logging rationale (frozen `config.py` contract lacks `OTEL_*` fields) is absent from DEC-046 — it's echoed later under DEC-071, which itself quotes this comment as its source, so at the DEC-046 citation the reasoning lives only in code.

**`scripts/`** (6)
8. `scripts/bootstrap.sh:2-9` — cites DEC-078; this script's own Phase E/E1 purpose and the two operator Subscriptions being newly authored (vs. always-pre-installed elsewhere) is absent from DEC-078.
9. `scripts/bootstrap.sh:72-81` — cites DEC-055 (which only covers the OLM catalog blocker); `installPlanApproval: Manual` semantics and the safety property that `approve_pending_installplan` only ever approves the exact pinned CSV are absent everywhere.
10. `scripts/bootstrap.sh:137-148` — cites DEC-059; the `keycloak-cr.yaml` header-comment gap, the specific secret names, and the create-once-vs-`CreateContainerConfigError` reasoning are absent everywhere.
11. `scripts/bootstrap.sh:297-303` — cites DEC-098/099 (decision-only, "nothing built" entries); the gap-finding narrative that `pipelines/pipeline.yaml`/`tasks/*.yaml` were applied ad hoc during Phase C and never documented, causing `CouldntGetPipeline`, is absent everywhere.
12. `scripts/dev.sh:70-77` — the DEC-096 half duplicates cleanly, but the DEC-098/099-cited half (`Containerfile.agent` deliberately excludes `mcp_server/server.py` so `MCP_MODE=mock`'s in-process fallback would `ImportError`) is an implementation detail absent from both decision-only entries.
13. `scripts/dev.sh:99-102` — cites DEC-047 (approval_service's internal implementation only); the actual dev-loop wiring gap (`APPROVAL_SERVICE_ENDPOINT` defaulting to `localhost:8082`, pointing at nothing inside the container network) is DEC-096's territory, never cited.

**`pipelines/`** (1)
14. `pipelines/pipeline-mcp.yaml:1-9` — the framing of this pipeline as a "Layer-1/Tools-Template proof-of-independence in miniature, ahead of G3's actual separate template" is absent from DEC-098, DEC-099, DEC-101, and DEC-104.

**`deploy/`** (13)
15. `deploy/argocd/application-ephemeral-test.yaml:1-16` — cites DEC-021/DEC-040/DEC-039; **DEC-040 does not exist anywhere in DECISIONS.md** (confirmed by grep). The real content (this Application is filled in but deliberately never synced, kept as a future scaffold) is in DEC-024, uncited.
16. `deploy/argocd/application-root.yaml:1-20` — same nonexistent-DEC-040 problem; the specific "ephemeral-test/staging/pilot-prod stay out of the app-of-apps" reasoning traces to DEC-024, uncited.
17. `deploy/kustomize/base/networkpolicy-approval.yaml:32-39` — a live, still-open TODO ("VERIFY against this specific cluster live... before relying on it") about an OpenShift SDN ingress label; DEC-023 is cited only as a loose analogy and never discusses this NetworkPolicy at all.
18. `deploy/kustomize/base/networkpolicy.yaml:20-30` — cites DEC-098/099; the reasoning for why a second, narrow `podSelector` entry was chosen over widening the first ("avoids ReplicaSet adoption") is absent everywhere.
19. `deploy/kustomize/overlays/demo-prod/kustomization.yaml:12-25` — the explicit no-data-migration policy ("old demo-prod approval instance's SQLite state is demo-scope-only, not preserved") is absent from DEC-103.
20. `deploy/kustomize/overlays/demo-prod/kustomization.yaml:55-82` — the `envFrom`-ordering / third-Secret-copy shadowing mechanism is absent from the cited DEC-035/DEC-039; only a brief, uncited phrase in DEC-041 comes close.
21. `deploy/kustomize/overlays/demo-prod/namespace.yaml:1-16` — the ArgoCD mechanism detail (`syncOptions: CreateNamespace=true` only works when ArgoCD's own ServiceAccount has cluster-scoped Namespace permissions) is absent from DECISIONS.md entirely.
22. `deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml:1-25` — the verbatim UrlReader error text and the "merge is per-key-path, not whole-object-replace" semantics are absent; DEC-093 only tersely paraphrases.
23. `deploy/kustomize/overlays/rhdh/catalog-locations-config.yaml:32-90` — genuine lost debugging provenance: the exact source file `packages/integration/src/gitea/core.ts`, function `parseGiteaUrl`, and the URL-shape derivation are absent from DECISIONS.md entirely.
24. `deploy/kustomize/overlays/rhdh/oidc-app-config.yaml:1-10` — the exact operator-doc quote ("Each app-config ConfigMap must contain exactly one data entry") is absent everywhere.
25. `deploy/kustomize/overlays/rhdh/oidc-app-config.yaml:18-35` — the exact backend error text ("no longer supports the 'scope' configuration option") and the localhost:7007-default explanation are absent everywhere.
26. `deploy/kustomize/overlays/rhdh/oidc-app-config.yaml:64-72` — the exact runtime error text ("Authentication failed, authentication requires session support") and the cookie/express-session explanation are absent everywhere.
27. `deploy/kustomize/overlays/rhdh/postgres.yaml:17-31` — the per-backend-plugin DB-creation behavior, the exact error text ("permission denied to create database"), and the manual `oc exec`/`psql` command are absent from DECISIONS.md itself (only in PINS.md, a different document).

**`platform/`** (8)
28. `platform/bootstrap/gitea-backup-restore-probe.yaml:1-11` — the CSI RBD `VolumeSnapshotClass` name and the one-shot-vs-recurring-schedule rationale are absent everywhere.
29. `platform/bootstrap/gitea-cr.yaml:1-9` — the admin-password Secret field name and the "one shared instance, not per-agent-project" framing at implementation level are absent.
30. `platform/bootstrap/gitea-operator-upstream/kustomization.yaml:4-26` — a **different** OLM failure than DEC-055/056's Keycloak incident (a stuck `catalog-operator` resolver cache), including its root cause, commit hash, and resolved image digest, is absent from DECISIONS.md entirely.
31. `platform/bootstrap/keycloak-realm-import.yaml:39-42` — the "correct by omission" negative-test design reasoning is absent from DEC-054.
32. `platform/bootstrap/keycloak-realm-import.yaml:143-149` — the RHDH OIDC client's confidential/Authorization-Code shape and "distinct trust surface, dev-tooling sign-in vs. end-user approval auth" reasoning exist only in this comment.
33. `platform/bootstrap/otel-collector.yaml:103-127` — a real incident (the original image pin was pruned, causing a 12h+ silent OTLP-export outage) is **misattributed to DEC-085, an unrelated entry**; the incident itself is absent from DECISIONS.md entirely.
34. `platform/bootstrap/provision-identity-secrets.sh:279-286` — the `SESSION_SECRET` gap, the exact error text ("Authentication failed, authentication requires session support"), and the generate-once-never-rotate rationale are absent from DEC-092 and everywhere else.
35. `platform/bootstrap/rhdh-operator.yaml:16-19` — DEC-092 explicitly declines to restate this ("Standing decisions... followed as given, not re-litigated here"); the "not a new exposure class" reasoning genuinely exists only in this comment.

### Non-comment trap for H4

`eval/cli.py`'s `KNOWN_GAP_TOLERANCES` dict has narrative `"rationale"`
**string values** — runtime data printed in gate reports, not `#` comments.
A naive sweep must not touch these; they're outside the comment-policy's
scope entirely (and `eval/` is outside the mission's own 7-directory census
scope in the first place).

### What this means for H4's sizing

The 8-file sample taken during planning found zero category-(c) items and
suggested H4 might be near-mechanical. **The completed census overturns
that**: 35 real items need migration into `DECISIONS.md` (as addenda) or
`docs/` before their comments can be slimmed — including two comments citing
a `DEC-040` that was never written, one incident actively misattributed to
the wrong DEC number, and several cases of genuinely unique debugging
provenance (exact error text, source file/function names, root causes) that
would be permanently lost if slimmed first. H4 is real, scoped work, not a
formality — its two hard gates (Stage 2 merged, H3a merged) stay as planned;
this finding does not change phase ordering, only H4's effort estimate.

## 5. Prioritized fix list, mapped to phases

- **H1**: rewrite `README.md`'s Layout section against the real 19-directory
  inventory (esp. add `approval_service/`, the platform/pipelines split, the
  governance files); fix the two parent-workspace-reference dead ends
  (line 4, the Provenance section); build `scripts/install.sh`.
- **H2**: build `docs/README.md`, `docs/glossary.md`,
  `docs/naming-conventions.md`, `docs/access-and-credentials.md`,
  `docs/provenance.md` — none exist; fix the `local-dev.md`/
  `security-identity.md` single-image drift; add the 15 missing
  per-directory READMEs; track `tools/provision-demo-credentials.sh` and
  `tools/get-test-user-credential.sh` (after an anonymity sweep) since
  `access-and-credentials.md` will link them.
- **H3a**: add module docstrings to the 13 files confirmed missing one
  (see `reports/docs-terms-sheet.md`'s companion audit trail — the file
  list is unchanged from planning: `agent/api.py`, `agent/graph.py`,
  `agent/nodes/{decide,generate,retrieve,tool_invoke}.py`,
  `agent/routers.py`, `agent/state.py`, `eval/config.py`, `eval/loader.py`,
  `eval/reporter.py`, `eval/runner.py`, `mcp_server/schemas.py`).
- **H3b**: `mkdocs.yml` + TechDocs wiring is fully net-new; no existing
  tooling to extend.
- **H4**: migrate the 35 category-(c) items above (14 across `agent/`,
  `mcp_server/`, `approval_service/`, `scripts/`, `pipelines/` combined; 13
  in `deploy/`; 8 in `platform/`) into `DECISIONS.md` addenda or `docs/`
  pages, then apply the 3-line-contract + pointer policy to the remaining
  ~192 category-(b) narrative blocks and confirm the 18 one-liners are
  already minimal. Two items (`deploy/argocd/application-ephemeral-test.yaml`,
  `application-root.yaml`) cite a `DEC-040` that was never written — decide
  what to cite once their content is migrated, since there's nothing at
  DEC-040 to point back to.
