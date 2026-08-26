# Live chat verification — session report

**What was attempted**: close the gap between this project's offline
testing perspectives (eval harness, unit tests — all in-process, no HTTP)
and an actual live conversation with the running agent over its real HTTP
surface, against a real model, including a full write→approve/reject
round trip.

**Commands run and real output**: see `reports/direct-chat-http-verification.md`
for the full transcript (stack startup, `/invoke`, `/proposals/.../decision`,
`/approvals/.../resume`, CLI invocations, cleanup) — not duplicated here.

**What passed**: all 8 verification scenarios (read query, write→approve,
write→reject, CLI read, CLI write→approve, CLI write→reject, plus the
two-container independent-store-verification technique) — see that
report's "Verdict" section. Full pytest suite 254/254. `make eval-fast`
2/2.

**What's left open**:
- Branch `feature/phase-e-live-chat-verification` is uncommitted — needs
  owner review before merge.
- `make eval-domain` (the 62-case live domain suite) was **not** re-run
  this session — only the offline `eval-fast` pair was used as the
  regression check for the `agent/cli.py`/`approval_client.py` changes.
  Worth running before merge, since domain eval exercises the same
  `approval_client` module (via `eval/fake_approval_client.py`'s patched
  version) that gained a new function.
- Testing perspectives 2–6 in `docs/testing-perspectives-guide.md` are
  researched/documented but, unlike perspective 1, not live-executed this
  session — only perspective 1 (the direct-chat path) got an actual live
  run.
- No regression guard exists for the `scripts/dev.sh` defect itself (only
  for the `agent/cli.py` logic it exposed) — nothing currently asserts
  `make up` wires `APPROVAL_SERVICE_ENDPOINT` or starts all four roles,
  so this specific class of regression could recur silently. Possible
  follow-up, not done here (would be new scope).

**Related draft**: `docs/drafts/DEC-085.draft.md` (provisional DEC entry
for this work — not yet in `DECISIONS.md`, needs owner review and a
fresh tail-check before commit).
