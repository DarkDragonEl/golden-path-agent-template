# Showcase sharing schedule + access list — template

Per `docs/phase-e-kickoff-plan.md` §5 (STOP 3) and `E2E_DEMO_PLAN.md`'s
E3. **Structure only — deliberately not filled in.** Who receives the
showcase URL/viewer account, and when, is the owner's own decision, not
something a plan or a session can invent on the owner's behalf.

**Recommendation, not a decision made here**: keep the filled-in version
of this table (real names/emails) out of Git entirely — a local or
private tracking mechanism instead. If it's ever committed anyway, it
needs the same anonymity-sweep discipline §5.2 already names for
everything else in this repo (`DECISIONS.md` `DEC-082` is a concrete,
recent example of that discipline catching a real violation before
push).

## Schedule

| Sharing moment | Date | Recipient(s) | Access type | Anonymity sweep done? | Notes |
|---|---|---|---|---|---|
| After A/B0 (repo walkthrough, no cluster) | | | | | Content: `reports/feature-phase-a-eval-set.md`, `reports/feature-phase-b0-srs.md`, SRS chain, `trace-check` output. |
| After B (recorded local run) | | | | | Content: `reports/phase-b-sharing-run.md`. |
| After C (showcase cluster live) | | | | | Content: `reports/phase-c-sharing-run.md` (captured on the SNO, caveated) — replay on the showcase once its own pipeline has promotion authority (`DECISIONS.md` `DEC-078` follow-up). |
| After D (full clickable flow) | | | | | Content: `reports/phase-d-sharing-run.md` (captured on the SNO, caveated). **Blocked on the showcase's own `demo-prod` serving a promoted digest** — see note below. |

## Known blocker for any showcase-hosted moment

Per `reports/phase-e-refresh-log.md`: the showcase's `demo-prod`-equivalent
is bootstrapped and `Synced`, but its pods stay `ImagePullBackOff` until
`DECISIONS.md` `DEC-078`'s first follow-up commit (the hosted-registry
migration) lands. **No colleague should receive the showcase URL before
then** — there is nothing running to show. This affects the "after C"
and "after D" moments specifically (both need a live cluster); "after
A/B0" and "after B" have no cluster dependency and can proceed on their
own schedule.

## Anonymity sweep procedure (run before every moment, not just once)

Per `docs/phase-e-kickoff-plan.md` §5.2: confirm no `*client*`/
`*research-notes*` files exist in what's being shared; confirm `.env`
was never tracked; grep all tracked files (and, before any *first* push
of new history, the full git history via pickaxe search) for real
hostnames, org names, emails, IP literals; confirm corpus/eval data
stays synthetic-only. Each new sharing moment can introduce new content
that needs its own sweep — a repeat gate, not a one-time checkbox.
