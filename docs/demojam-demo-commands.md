# Demo Jam: commands to replay on camera

Five steps against the local stack, each one screen of `curl` + `jq`. The
request and response shapes come from `agent/api.py` and
`approval_service/api.py`; the two queries are eval cases the domain gate
passes (`KQA-002`, `DRQ-002`). No cluster is involved.

## 0. Before recording

- `.env` holds the live model settings (`MODEL_API_BASE_URL`, `MODEL_NAME`,
  `MODEL_API_KEY`; see `docs/local-dev.md`). `make up` reads it.
- `jq` is installed, and the Python deps are installed for `make eval`
  (`pip install -r requirements.txt -r requirements-dev.txt`).
- Terminal 1: start the stack. It stays in the foreground and follows the
  agent's log; `Ctrl-C` (or `make down`) tears it down.

```bash
make up
```

- Terminal 2: the endpoints `make up` prints (`scripts/dev.sh`):

```bash
A=http://localhost:18080     # agent
AP=http://localhost:18082    # approval service
```

## 1. Health

```bash
curl -s "$A/healthz" | jq .
```

Expected: `{"status": "ok"}`.

## 2. A read query, answered with a citation

Eval case `KQA-002`: the answer must name the approver and cite the seeded
policy document `PLAT-002`.

```bash
R=$(curl -s -X POST "$A/invoke" -H 'Content-Type: application/json' \
  -d '{"query": "Under the Namespace Request and Quota Policy, who approves a namespace quota increase above the default limit?", "user_id": "demo-user"}')
echo "$R" | jq '{session_id, pending_approval, tools: [.tool_calls[]?.tool_name], fallback_reason}'
echo "$R" | jq -r .final_output | fold -s -w 100
echo "$R" | jq -r .final_output | grep -o 'PLAT-002' | head -1
```

Expected: `pending_approval: false`. The answer says the Namespace
Governance Owner approves quota increases above the default limit, and the
last line prints `PLAT-002`.

## 3. A write request stops for approval

Eval case `DRQ-002`. With `"write": true` the agent drafts the ITSM request
and pauses; nothing is written yet.

```bash
R=$(curl -s -X POST "$A/invoke" -H 'Content-Type: application/json' \
  -d '{"query": "Draft an access request for the staging namespace.", "write": true, "user_id": "demo-user"}')
echo "$R" | jq '{session_id, pending_approval, final_output}'
SID=$(echo "$R" | jq -r .session_id)
```

Expected: `pending_approval: true`, `final_output: null`.

What the approver sees: the pending proposal on the approval service,
looked up by the agent session.

```bash
curl -s "$AP/proposals?originating_session_id=$SID" \
  | jq '.[] | {proposal_id, state, action_type, target_system_id, action_arguments}'
PID=$(curl -s "$AP/proposals?originating_session_id=$SID" | jq -r '.[0].proposal_id')
```

Expected: one proposal, `state: "pending"`, `action_type:
"itsm_create_request"`, with the drafted fields in `action_arguments`.

## 4. Approve, then resume to completion

The decision is recorded on the **approval service**, never sent to the
agent. `/approvals/{session_id}/resume` takes an empty JSON body by design:
the agent re-reads the decision and the approved arguments from the approval
service and executes exactly those (`ResumeRequest` in `agent/api.py`,
`resolve_and_resume` in `agent/approval_client.py`).

```bash
curl -s -X POST "$AP/proposals/$PID/decision" -H 'Content-Type: application/json' \
  -d '{"decision": "approve"}' | jq '{proposal_id, state, decided_by, decision}'
curl -s -X POST "$A/approvals/$SID/resume" -H 'Content-Type: application/json' -d '{}' \
  | jq '{session_id, pending_approval, last_tool: (.tool_calls | last | {tool_name, result})}'
```

Expected:
- The decision returns `state: "approved"`. Locally `AUTH_MODE=none`, so
  `decided_by` is the fixed `dev-approver`.
- The resume returns `pending_approval: false`, and the last tool call is
  `itsm_create_request`. Its result carries the new record id
  (`REQ-` plus five digits).

Pitfalls:
- `-d '{}'` is required: without a body, `/resume` returns 422.
- A resume sent before the decision changes nothing (`pending_approval`
  stays `true`).
- A second resume after completion returns 404.

## 5. The evaluation gate

`make eval` runs the offline harness pair, then the 62-case domain suite
in-process against the live model (it does not use the `make up` stack).
Export the model settings first; the domain suite is only meaningful with
`AGENT_MODEL_MODE=live`.

```bash
set -a; . ./.env; set +a
AGENT_MODEL_MODE=live make eval
```

Expected:
- `2/2 cases passed` for `EXAMPLE-001`/`EXAMPLE-002`;
- then the domain suite's per-category results and gate verdict. The only
  tolerated cases are `INJ-006` and `UAW-003` (`KNOWN_GAP_TOLERANCES` in
  `eval/cli.py`).

The 62 live cases take a while. For a short take, run only the case from
step 2:

```bash
AGENT_MODEL_MODE=live python -m eval.cli run --case KQA-002
```

## How these commands were checked

On `main` (`f8a132c`), the three services were run directly with uvicorn and
the fake model client (`AGENT_MODEL_MODE=fake`), on the same ports as
`make up`. Every command in steps 1–4 was replayed against them:
- the request and response fields are as shown;
- the proposal lookup by session works;
- the approve decision works, and the resume completes the run;
- the 422 without a body, the no-op early resume and the 404 on a second
  resume all reproduce.

`make eval-fast` passed 2/2. The fake model returns placeholder content, so
the cited answer, the `itsm_create_request` arguments and the domain gate
result were not observed. They are the eval set's own expectations for
`KQA-002`/`DRQ-002`. Do a dry run with the live model before recording.
