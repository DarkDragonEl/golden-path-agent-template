# Direct chat with the agent (HTTP) — live verification report

**Scope:** the user asked to understand this repo's testing perspectives,
then correctly flagged that nothing done so far had "explored the
functional part, chat[ted] with some model and activate[d] the agent" —
every prior pass this session was static file reading plus offline
commands (`make eval-fast`, `pytest`), none of which touch the running
`agent.api` HTTP server or a real model. This report is the live
verification of that gap: an actual local stack, real chat queries
against the real pinned model (`granite-3-2-8b-instruct` via the
project's Red Hat MaaS endpoint), and a full write → approve/reject round
trip, evidence captured directly from command output — per `CLAUDE.md`'s
workflow-discipline rule ("prove the negative case with a test, not a
claim").

Designing this run surfaced three real defects (branch
`feature/phase-e-live-chat-verification`), fixed in the same pass and
re-verified live below:

1. `scripts/dev.sh` (`make up`/`make up-offline`) never started the
   `approval` role or wired `APPROVAL_SERVICE_ENDPOINT` — the agent's own
   default (`http://localhost:8082`) pointed at nothing inside its own
   container. Any write-classified query failed immediately with
   `fallback_reason: approval_service_failure:ConnectError` — the exact
   failure class `DECISIONS.md` `DEC-051` already recorded once for real,
   in a cluster deploy, for the identical reason.
2. `agent/cli.py`'s `--decision approve|reject` was dead code post-DEC-049:
   it set `approval_decision` directly via `graph.update_state` and
   re-invoked, but `human_approval_node` only ever authorizes execution
   when `approved_action` is set — a field only `approval_client.resolve_and_resume`
   populates, by querying the approval service's own terminal state.
   `--decision approve` silently behaved exactly like reject.
3. `docs/local-dev.md` documented `POST /approvals/{session_id}/resume`
   as taking `{"decision": "approve"|"reject"}` in its body.
   `agent/api.py`'s `ResumeRequest` is deliberately empty (DEC-045/DEC-049);
   the real decision must land on the standalone approval service first.

Fixes: `scripts/dev.sh` now starts a fourth container (`approval`) and
wires `APPROVAL_SERVICE_ENDPOINT`; `agent/approval_client.py` gained a
`decide_proposal` helper; `agent/cli.py`'s resume step now calls
`decide_proposal` + `resolve_and_resume`, the same logic `agent/api.py`'s
`/resume` endpoint uses; `docs/local-dev.md` and
`docs/testing-perspectives-guide.md` corrected/extended accordingly. A
regression test (`tests/test_cli_resume.py`) locks in fix #2 without
needing a live stack.

## 0. Pre-flight

```
$ .venv/bin/python -m pytest -q
254 passed in 5.73s

$ make eval-fast
[PASS] EXAMPLE-001
[PASS] EXAMPLE-002
2/2 cases passed

$ curl -H "Authorization: Bearer $MODEL_API_KEY" $MODEL_API_BASE_URL/models
HTTP 200  0.26s
```

Full offline suite green before touching containers; live model endpoint
reachable and the shared workshop API key valid.

## 1. Stack startup (4 containers, not 3)

```
$ make up
[dev.sh] live mode: reads MODEL_API_BASE_URL/MODEL_NAME from .env
...
$ podman ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
golden-path-agent-mcp-dev        Up   0.0.0.0:18081->8081/tcp
golden-path-otel-collector-dev   Up   0.0.0.0:4318->4318/tcp
golden-path-agent-approval-dev   Up   0.0.0.0:18082->8082/tcp   <- new, fix #1
golden-path-agent-dev            Up   0.0.0.0:18080->8080/tcp

$ curl :18080/healthz -> {"status":"ok"}
$ curl :18082/healthz -> {"status":"ok"}
```

**Result: PASS.** All four roles up; the previously-missing `approval`
container is now started by a plain `make up`.

## 2. Read-only chat — real model, real answer

```
POST :18080/invoke {"query": "What is the current status of incident INC-10255?", "write": false}
-> 200 pending_approval=false
   tool_calls=[{tool_name: itsm_search_records, classification: read,
                result: {record_id: INC-10255, status: resolved, ...}}]
   final_output: "INC-10255 (incident, status: resolved): Ingress
                  certificate auto-renewal failure on staging cluster"
```

**Result: PASS.** A genuine live-model tool-selection + grounded-answer
turn, not a scripted eval case.

## 3./4. Write → approve — submit → decide → resume → execute

A real topology finding while designing this check: with `MCP_MODE=mock`
(dev.sh's default), the agent calls the mock ITSM tool **in-process**,
inside its own container — a completely separate in-memory store from
the standalone `mcp` container's. Verifying "the store, not the agent's
self-report" (this project's own convention, `tests/test_write_gating.py`)
therefore requires `MCP_MODE=live` on the agent so tool calls actually
cross the network to the `mcp` container's REST store, which is what the
checks below use (a second, temporary agent container,
`MCP_MODE=live`/`AGENT_MODEL_MODE=live`, same network, port `18090` —
torn down with the rest at the end). This in-process-vs-networked split
is worth knowing before trusting any local write-path check by the
agent's own JSON response alone.

```
BEFORE: mcp :18081/records?record_type=request -> 2 records

POST :18090/invoke {"query": "Draft an access request for the staging namespace.", "write": true, "session_id": "verify-approve-002"}
-> 200 pending_approval=true, final_output=null

GET  :18082/proposals?originating_session_id=verify-approve-002 -> proposal_id=2810bb2b-...
POST :18082/proposals/2810bb2b.../decision {"decision": "approve"}
-> 200 state=approved, decided_by=dev-approver

POST :18090/approvals/verify-approve-002/resume {}
-> 200 final_output="Request REQ-30100 has been submitted (status: submitted)."
   tool_calls[1].result = {record_id: REQ-30100, status: submitted, source: mock-itsm}

AFTER: mcp :18081/records?record_type=request -> 3 records
GET  :18081/records/REQ-30100 -> 200, full record present
```

**Result: PASS.** Store-verified, not self-report: record count went
2 → 3, and the created record is independently fetchable from the `mcp`
container.

## 5. Write → reject — zero mutation

```
BEFORE: 3 records
POST :18090/invoke {"query": "Please log a formal information request about the onboarding procedure for a new team.", "write": true, "session_id": "verify-reject-001"}
-> 200 pending_approval=true

POST :18082/proposals/57749b7f.../decision {"decision": "reject"} -> 200 state=rejected
POST :18090/approvals/verify-reject-001/resume {}
-> 200 final_output="This request could not be completed safely right now
   (escalation reason: approval_not_granted:'rejected'). A human should
   review this session."
   fallback_reason: "approval_not_granted:'rejected'"

AFTER: 3 records (unchanged)
```

**Result: PASS.**

## 6.-8. CLI path — read, then the fixed `--decision approve`/`reject`

```
$ python -m agent.cli "What is the current status of incident INC-10261?"
-> model_calls[0]: {route: primary, response_model: granite-3-2-8b-instruct}
   final_output: "INC-10261 (incident, status: open): Service catalog
                  entry missing for new namespace onboarding template"
```

**Read path: PASS**, live model confirmed via `model_calls[0].response_model`.

```
BEFORE: 3 records
$ python -m agent.cli "Submit an information request ticket about the standard offboarding checklist." \
    --write --session-id cli-verify-approve2 --decision approve
-> approved_action: {tool_name: itsm_create_request, ..., approver_id: dev-approver}
   final_output: "Request REQ-30101 has been submitted (status: submitted)."
AFTER: 4 records
```

**Result: PASS — this is the direct regression check for fix #2.** Before
the fix, this exact call produced `fallback_reason:
"approval_not_granted: 'approve'"` and created nothing (confirmed by the
source-level defect: `human_approval_node` never reads
`approval_decision` for authorization, only `approved_action`, which the
old CLI code never set). After the fix, `--decision approve` genuinely
round-trips through the approval service and creates a real record.

```
BEFORE: 4 records
$ python -m agent.cli "Submit an information request ticket about the VPN renewal process." \
    --write --session-id cli-verify-reject --decision reject
-> approved_action: null, approval_decision: "rejected"
   fallback_reason: "approval_not_granted:'rejected'"
AFTER: 4 records (unchanged)
```

**Result: PASS.**

## 9. Cleanup

```
$ curl -X POST :18081/reset -> {"status":"reset"}
$ curl :18081/records?record_type=request -> 2 records (back to seed baseline)
$ podman rm -f golden-path-agent-verify-live
$ make down
$ podman ps -a | grep golden-path -> (none)
$ podman network ls | grep golden-path -> (none)
```

**Result: PASS.** No containers, network, or mock-ITSM state left behind.

## Verdict

All 8 scenarios pass. The direct-chat path (`POST /invoke`,
`POST /approvals/{session_id}/resume`, `python -m agent.cli`) works
end-to-end against the real running agent and a real model, independent
of and never exercised by `make eval`/`make test`. Three real defects
found while building this check were fixed and are now covered by a
regression test (`tests/test_cli_resume.py`, 254/254 total suite green)
for the parts that don't need a live stack, and by this report's live run
for the parts that do.
