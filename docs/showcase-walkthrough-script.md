# The ~20-minute owner-facing walkthrough script

Per `docs/phase-e-kickoff-plan.md` §7 (STOP 4) and `E2E_DEMO_PLAN.md`'s
E5. **Draft for owner review — not yet treated as demo-ready.** Structure
and the "what this is NOT yet" list below are carried over from the
already-reviewed kickoff plan, not redrafted; this document adds timing,
the exact evidence each beat points at, and a live-narration script.

Maintained as the showcase grows — any colleague session should follow
this same arc, whether live or from the recorded backup (not yet
recorded — see the end of this document).

## Running order (~20 minutes)

### 1. Template instantiation (~3 min)

Narrate, don't re-derive live: "This entire environment — namespaces,
RBAC, two operators, Keycloak, cluster-tier telemetry, the GitOps
app-of-apps root — comes from one command against a completely empty
OpenShift cluster." Show `Makefile`'s `bootstrap` target and
`scripts/bootstrap.sh`'s step list (9 steps, `scripts/bootstrap.sh`
header). Point at `reports/phase-e-refresh-log.md`'s `showcase-refresh-1`
entry as the live proof this actually happened, on a cluster that had
never seen this project before, in ~38 minutes including live debugging.

### 2. The inner loop (~3 min)

`make up && make eval` on a laptop — no cluster, no network dependency
in offline mode. Reference `reports/phase-b-sharing-run.md`'s own
recorded transcript for the exact commands and output shape. Point:
independence by construction — every phase completes on local
infrastructure alone before the cluster ever enters the picture.

### 3. Gate failure + recovery (~3 min)

`reports/phase-c-sharing-run.md` §2: the same `Pipeline` object, run
against a one-line seeded regression, failing at three independent
gates (`unit-tests`, `eval-gate-offline`, `policy-validate`) through
three different mechanisms — not staged, what actually happened. No
promotion PR opens. Point: the gate is real, not theater.

### 4. Immutable-digest promotion (~3 min)

`reports/phase-c-sharing-run.md` §3: one digest, three independent
sources (the build, `main`'s merged commit, the running pod) all
agreeing, sourced from one GitOps commit, never rebuilt. Point: promotion
is exclusively a reviewed PR merge — no rebuild, no direct push, no
bypass.

### 5. The approval trilogy (~4 min)

`reports/phase-d-sharing-run.md` §§2–4: draft → approve → ticket exists;
draft → reject → nothing written; draft → expire → nothing written.
Point at `tool_calls[0].result: None` in both the reject and expiry
transcripts — the block is real execution-prevention, not a hidden UI
state. If live: the owner's own browser click-through
(`docs/owner-walkthrough.md`) is the strongest version of this beat —
Section 5 of the sharing report documents exactly what it found and
fixed getting there.

### 6. Trace (~2 min)

`reports/phase-d-sharing-run.md` §6: one `session.id` query stitching
two independent processes (`golden-path-agent`, `golden-path-agent-approval`)
across the async human-decision gap into one ordered story. Point: the
attribute-correlation mechanism works exactly as designed, not merely as
claimed.

### 7. "What this is NOT yet" (~2 min)

State plainly, on a slide, not glossed over — verbatim from
`docs/phase-e-kickoff-plan.md` §7.2:

- **Steps 4–6** (`StRS_Agentic_AI_Platform_EN.md` §18.2/§19: staging
  integration, controlled pilot, the production architecture decision) —
  explicitly phase-two; this milestone covers Steps 1–3 only.
- **No external HTTP routing this milestone** — no working `Ingress`
  exists yet for any of this project's services; every live interaction
  goes through `oc port-forward`.
- **Attestation / per-agent sandbox profiles** — `Annex_A_Open_Items_EN.md`
  OI-03's "explicitly deferred" tier. Say so on a slide; don't fake it.
- **ESO/Vault secrets integration** — deferred phase-two, per
  `docs/security-identity.md` and `PINS.md`.
  `platform/bootstrap/provision-identity-secrets.sh`'s own header
  comment calls itself "the demo-scale realization" of what a real
  ESO/Vault integration would do continuously — that framing is
  walkthrough material, not a caveat to hide.
- **The `DEC-065` `ConfigMap`-rollout gap** — `ConfigMap`-only changes to
  a GitOps-synced overlay don't roll already-running pods; the
  `checksum/config`-annotation pattern is named, explicitly, as this
  gap's Phase E hardening candidate.
- **The four named known-gaps** (`INJ-006`, `UAW-003`, `ITR-004`,
  `TSEL-004`) — declared final per `HANDOFF.md` invariant #7.
  `INJ-006` (jailbreak framing can still get a write action drafted, but
  the human-approval gate held 100% across every measurement — defense
  in depth demonstrated, not a weakness hidden), `UAW-003`
  (measurement-tolerance, one irreproducible non-deterministic flip, not
  a stable behavior), `ITR-004` (a narrow scorer string-comparison
  artifact, the functional half already fixed), `TSEL-004` (a
  query-phrasing classification tendency, no unsafe behavior results).

**Add, new this session, not in the original kickoff-plan list**: the
showcase cluster's own `demo-prod`-equivalent isn't serving a promoted
digest yet (`DECISIONS.md` `DEC-078` Option 2) — this walkthrough
currently narrates the SNO's real, working system plus the showcase's
proven-but-unpromoted bootstrap, not a single fully-live showcase
end-to-end. Say so if presenting from the showcase cluster directly,
until `DEC-078`'s follow-up lands.

## Recorded backup

**Not yet recorded.** `E2E_DEMO_PLAN.md`'s E5 calls for "a recorded
happy path... kept current as backup for whenever a live demo isn't
possible." Recording this needs a live cluster with a promoted digest on
its `demo-prod` (blocked the same way `docs/showcase-access.md` is
blocked) — named here as a real, tracked gap, not silently skipped.
