"""Phase B kickoff, Task 1 — tool-calling spike + fallback selection.

Throwaway probe script, not agent code. Deliverable is the evidence and the
decision (recorded in reports/phase-b-tool-calling-spike.md), not a module
other code imports. Tool schemas below are transcribed field-for-field from
srs/SRS-MIT.md's SRS-MIT-IF-02/IF-03 (approved, Checkpoint B0-a) — this is
the authoritative source, not eval/README.md's provisional version.

Usage: .venv/bin/python tools/phase_b_tool_calling_spike.py
Requires MODEL_API_BASE_URL / MODEL_API_KEY in the environment (loaded from
.env below, matching agent/config.py's own convention).
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_dotenv(REPO_ROOT / ".env")

BASE_URL = os.environ["MODEL_API_BASE_URL"].rstrip("/")
API_KEY = os.environ["MODEL_API_KEY"]

PRIMARY = "granite-3-2-8b-instruct"
CANDIDATES = ["codellama-7b-instruct", "phi3-mini-cpu", "qwen25-3b-cpu"]

# Transcribed field-for-field from srs/SRS-MIT.md SRS-MIT-IF-02/IF-03.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "itsm_search_records",
            "description": "Search or look up mock ITSM records (incidents, requests, known errors). Read-only; never creates, modifies, or deletes state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_type": {
                        "type": "string",
                        "enum": ["incident", "request", "known_error"],
                        "description": "Which kind of record to search.",
                    },
                    "query": {"type": "string", "description": "Free-text search query."},
                    "record_id": {
                        "type": "string",
                        "description": "When present, return that one record instead of a list.",
                    },
                    "status": {"type": "string", "description": "Optional status filter."},
                    "limit": {"type": "integer", "description": "Max records to return (default 10)."},
                },
                "required": ["record_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "itsm_create_request",
            "description": "Draft a new ITSM service request. Write operation — approval-gated; calling this only drafts the request, it does not execute until a human approves it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "short_description": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["access", "provisioning", "break_fix", "information"],
                    },
                    "requested_for": {"type": "string"},
                    "related_record_id": {"type": "string"},
                },
                "required": ["short_description", "description", "category", "requested_for"],
            },
        },
    },
]

# label, prompt, expected in {"read", "write", "none", "ambiguous"}
PROMPTS = [
    (
        "clear_read",
        "What's the current status of incident INC-10255?",
        "read",
    ),
    (
        "clear_write",
        "I'm a new hire on the platform team and I need VPN access set up. "
        "Please submit a request for me (requested_for: alex.rivera).",
        "write",
    ),
    (
        "none_of_the_above",
        "What's the weather like in Paris today?",
        "none",
    ),
    (
        "ambiguous",
        "I'm having trouble accessing the VPN — can you help?",
        "ambiguous",
    ),
]

REQUIRED_ARGS = {
    "itsm_search_records": ["record_type"],
    "itsm_create_request": ["short_description", "description", "category", "requested_for"],
}
VALID_RECORD_TYPES = {"incident", "request", "known_error"}
VALID_CATEGORIES = {"access", "provisioning", "break_fix", "information"}


def call_model(model: str, prompt: str, timeout: float = 90.0):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0,
    }
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        latency = time.monotonic() - start
        return {"ok": True, "latency_s": latency, "response": data}
    except urllib.error.HTTPError as e:
        latency = time.monotonic() - start
        return {"ok": False, "latency_s": latency, "error": f"HTTP {e.code}: {e.read().decode()[:500]}"}
    except Exception as e:  # noqa: BLE001 - probe script, want to record any failure mode
        latency = time.monotonic() - start
        return {"ok": False, "latency_s": latency, "error": f"{type(e).__name__}: {e}"}


def evaluate(result, expected):
    """Return (verdict, detail) — verdict in {pass, fail, observe, error}."""
    if not result["ok"]:
        return "error", result["error"]

    try:
        message = result["response"]["choices"][0]["message"]
    except (KeyError, IndexError) as e:
        return "error", f"unexpected response shape: {e}: {json.dumps(result['response'])[:300]}"

    tool_calls = message.get("tool_calls") or []

    malformed = []
    parsed_calls = []
    for tc in tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name")
        raw_args = fn.get("arguments", "")
        if name not in REQUIRED_ARGS:
            malformed.append(f"unknown tool name {name!r}")
            continue
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError as e:
            malformed.append(f"{name}: arguments not valid JSON ({e})")
            continue
        missing = [f for f in REQUIRED_ARGS[name] if f not in args or args[f] in (None, "")]
        if missing:
            malformed.append(f"{name}: missing required args {missing}")
        if name == "itsm_search_records" and "record_type" in args and args["record_type"] not in VALID_RECORD_TYPES:
            malformed.append(f"itsm_search_records: invalid record_type {args['record_type']!r}")
        if name == "itsm_create_request" and "category" in args and args["category"] not in VALID_CATEGORIES:
            malformed.append(f"itsm_create_request: invalid category {args['category']!r}")
        parsed_calls.append((name, args))

    names_called = [n for n, _ in parsed_calls]

    if expected == "ambiguous":
        return "observe", f"tool_calls={names_called or 'none'}" + (f"; malformed={malformed}" if malformed else "")

    if malformed:
        return "fail", f"malformed tool_calls: {malformed}"

    if expected == "none":
        if names_called:
            return "fail", f"spurious tool call(s): {names_called}"
        return "pass", "no tool call, as expected"

    if expected == "read":
        if names_called == ["itsm_search_records"]:
            return "pass", f"correct: {parsed_calls}"
        return "fail", f"expected exactly one itsm_search_records call, got {names_called or 'none'}"

    if expected == "write":
        if names_called == ["itsm_create_request"]:
            return "pass", f"correct: {parsed_calls}"
        return "fail", f"expected exactly one itsm_create_request call, got {names_called or 'none'}"

    return "error", f"unhandled expected={expected!r}"


def main():
    models = [PRIMARY] + CANDIDATES
    all_results = {}
    for model in models:
        print(f"\n=== {model} ===")
        model_results = []
        for label, prompt, expected in PROMPTS:
            result = call_model(model, prompt)
            verdict, detail = evaluate(result, expected)
            latency = result.get("latency_s", float("nan"))
            print(f"  [{verdict:7s}] {label:18s} ({latency:5.1f}s)  {detail}")
            model_results.append(
                {
                    "label": label,
                    "expected": expected,
                    "verdict": verdict,
                    "detail": detail,
                    "latency_s": round(latency, 2),
                }
            )
        all_results[model] = model_results

    out_path = REPO_ROOT / "reports" / "phase-b-tool-calling-spike-raw.json"
    out_path.write_text(json.dumps(all_results, indent=2))
    print(f"\nRaw results written to {out_path}")


if __name__ == "__main__":
    main()
