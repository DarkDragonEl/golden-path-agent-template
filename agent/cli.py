"""Single-shot local invocation for dev convenience.

Runs the whole invoke -> (pause) -> approve/reject -> resume sequence in
ONE process, so it needs no server. Unlike agent/api.py (where `_graph` is
built once and reused across requests, so state genuinely persists between
an /invoke and a later /approvals/.../resume call), this builds a fresh
in-memory checkpointer every run — there is no cross-invocation resume
mode here. For the real cross-request approval flow, run the actual
server (scripts/dev.sh / make up) and call
POST /approvals/{session_id}/resume against it.
"""

import argparse
import json
import sys

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
        graph.update_state(thread_config, {"approval_decision": decision})
        result = graph.invoke(None, thread_config)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
