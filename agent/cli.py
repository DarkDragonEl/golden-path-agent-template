"""Single-shot local invocation for dev convenience.

Runs the whole invoke -> (pause) -> approve/reject -> resume sequence in
ONE process. This is convenient (no server to run), but it is NOT
network-free: a `--write` query still submits a real proposal to the
standalone approval service via approval_client.submit_proposal, exactly
as agent/api.py's /invoke does, so APPROVAL_SERVICE_ENDPOINT must be
reachable for any --write call regardless of this CLI.

Unlike agent/api.py (where `_graph` is built once and reused across
requests, so state genuinely persists between an /invoke and a later
/approvals/.../resume call), this builds a fresh in-memory checkpointer
every run — there is no cross-*process* resume here. But within this one
process, --decision now genuinely round-trips through the approval
service: it POSTs the decision to {approval_service}/proposals/{id}/decision
(standing in for a real approver) and then calls
approval_client.resolve_and_resume, the same terminal-state-query-then-
inject logic agent/api.py's /resume endpoint uses (DECISIONS.md
DEC-008/DEC-049 -- a decision is never trusted from local state, only
from the approval service's own record of it).
"""

import argparse
import json
import sys

from . import approval_client
from .graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Single-shot local agent invocation")
    parser.add_argument("query")
    parser.add_argument("--write", action="store_true", help="mark this as a write-classified action")
    parser.add_argument("--session-id", default="local-cli")
    parser.add_argument(
        "--decision",
        choices=["approve", "reject"],
        help="skip the interactive prompt and resolve a pending approval with this decision",
    )
    args = parser.parse_args()

    graph = build_graph()
    thread_config = {"configurable": {"thread_id": args.session_id}}
    result = graph.invoke(
        {
            "session_id": args.session_id,
            "user_id": "cli",
            "input_query": args.query,
            "write_requested": args.write,
            "messages": [],
            "reasoning_steps": 0,
            "tool_calls": [],
            "pending_approval": False,
        },
        thread_config,
    )

    if result.get("pending_approval"):
        decision = args.decision
        if decision is None:
            if sys.stdin.isatty():
                answer = input("This action requires approval. Approve? [y/N] ").strip().lower()
                decision = "approve" if answer == "y" else "reject"
            else:
                print(
                    "pending_approval with no --decision and no interactive TTY — defaulting to reject",
                    file=sys.stderr,
                )
                decision = "reject"
        proposal_id = graph.get_state(thread_config).values["proposal_id"]
        approval_client.decide_proposal(proposal_id, decision)
        result = approval_client.resolve_and_resume(graph, thread_config)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
