"""Eval-only mock ITSM fixture + test-only MCP client stub.

This module is a deliberate, intentional duplicate of the Tools Template's
own `mcp_server/itsm_store.py` search/create_request logic and seed data --
NOT a shared import, by design. The domain eval harness's deterministic
fault-injection needs (`_simulate_error`-style timeout/error scenarios)
may not be satisfied by adding any fault-injection surface to the real,
deployed MCP server, gated or otherwise -- "a config-gated fault-injection
surface on the real MCP server would ship in every MCP server the platform
ever scaffolds ... guarded only by an environment flag," which is
incoherent for a platform whose posture is structurally-gated writes, not
convention-gated ones. The real `mcp_server/itsm_store.py`'s own
`_simulate_error` hook and `server.py`'s refusal to expose it as a tool
parameter stay exactly as they are -- categorically unreachable via any
real call path. This fixture is where the *test's* fault-injection lives
instead: eval-tooling only, never shipped in any scaffolded project (the
Agent Template's own `mcp_server/` contains only `client.py` -- this file
lives in `eval/`, not `mcp_server/`, specifically so it can never be
mistaken for, or accidentally copied into, a real deployable).

SAME-PR SYNC RULE, extended: the real `mcp_server/itsm_store.py`'s own
seed-data contract (`eval/cases/domain/*.yaml` commit to these exact
eight record IDs and several exact field values, e.g. `INC-10255` must
read `status: resolved`) now has TWO copies that must move together --
that file (the Tools Template's own source of truth for what a real,
deployed server returns) and this one (what domain eval's fault-injected
scenarios simulate). Do not change one without the other in the same PR.
"""

import re
import threading
from datetime import datetime, timezone
from typing import Any


def _plural_tolerant_variants(needle: str) -> list[str]:
    if needle.endswith("s") and len(needle) > 3:
        return [needle, needle[:-1]]
    return [needle, needle + "s"]


_STATUS_SEPARATOR_RE = re.compile(r"[-_\s]+")


def _normalize_status(status: str) -> str:
    return _STATUS_SEPARATOR_RE.sub("_", status.strip().lower())


RECORD_TYPES = ("incident", "request", "known_error")
REQUEST_CATEGORIES = ("access", "provisioning", "break_fix", "information")

_SEARCH_RESULT_FIELDS = (
    "record_id",
    "record_type",
    "status",
    "short_description",
    "opened_at",
    "updated_at",
    "owner_team",
)

# Kept byte-for-byte identical to mcp_server/itsm_store.py's own
# _SEED_RECORDS -- see the same-PR sync rule above.
_SEED_RECORDS: list[dict[str, Any]] = [
    {
        "record_id": "INC-10234",
        "record_type": "incident",
        "status": "open",
        "short_description": "CI pipeline execution failing intermittently on shared runners",
        "description": (
            "Multiple CI pipeline runs are failing intermittently on shared runners with "
            "no clear pattern. Suspected resource contention; investigation ongoing."
        ),
        "opened_at": "2026-07-28T09:12:00Z",
        "updated_at": "2026-07-29T14:03:00Z",
        "owner_team": "platform-ci",
    },
    {
        "record_id": "INC-10240",
        "record_type": "incident",
        "status": "open",
        "short_description": "Namespace quota exhaustion blocking new workload deployment",
        "description": (
            "Team platform-api's namespace has hit its configured resource quota, blocking "
            "new workload deployments. Requires a quota increase request or workload cleanup."
        ),
        "opened_at": "2026-08-01T10:30:00Z",
        "updated_at": "2026-08-01T10:30:00Z",
        "owner_team": "platform-capacity",
    },
    {
        "record_id": "INC-10255",
        "record_type": "incident",
        "status": "resolved",
        "short_description": "Ingress certificate auto-renewal failure on staging cluster",
        "description": (
            "Automated ingress certificate renewal failed on the staging cluster due to an "
            "expired ACME account key. Key rotated and renewal re-triggered manually."
        ),
        "opened_at": "2026-07-15T08:00:00Z",
        "updated_at": "2026-07-16T11:45:00Z",
        "owner_team": "platform-networking",
    },
    {
        "record_id": "INC-10261",
        "record_type": "incident",
        "status": "open",
        "short_description": "Service catalog entry missing for new namespace onboarding template",
        "description": (
            "The service catalog is missing an entry for the new namespace onboarding "
            "template, so requesters can't find it via self-service search."
        ),
        "opened_at": "2026-08-05T13:20:00Z",
        "updated_at": "2026-08-05T13:20:00Z",
        "owner_team": "platform-idp",
    },
    {
        "record_id": "REQ-30021",
        "record_type": "request",
        "status": "submitted",
        "short_description": "VPN access request for platform team new hire",
        "description": "Requesting VPN access for a new hire joining the platform team.",
        "category": "access",
        "requested_for": "new-hire-placeholder",
        "related_record_id": None,
        "opened_at": "2026-08-10T09:00:00Z",
        "updated_at": "2026-08-10T09:00:00Z",
        "owner_team": "platform-identity",
    },
    {
        "record_id": "REQ-30052",
        "record_type": "request",
        "status": "in_progress",
        "short_description": "Namespace provisioning for Q3 sprint capacity",
        "description": "Provisioning a new namespace to cover Q3 sprint workload capacity.",
        "category": "provisioning",
        "requested_for": "platform-api-team",
        "related_record_id": None,
        "opened_at": "2026-08-04T15:10:00Z",
        "updated_at": "2026-08-06T09:00:00Z",
        "owner_team": "platform-capacity",
    },
    {
        "record_id": "KE-50007",
        "record_type": "known_error",
        "status": "active",
        "short_description": "CI runner cache corruption causing intermittent build failures",
        "description": (
            "Shared CI runner caches can become corrupted under concurrent writes, causing "
            "intermittent, hard-to-reproduce build failures. Ties to corpus doc KI-001."
        ),
        "opened_at": "2026-06-20T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "owner_team": "platform-ci",
    },
    {
        "record_id": "KE-50012",
        "record_type": "known_error",
        "status": "active",
        "short_description": "Namespace quota exhaustion known issue — workaround documented",
        "description": (
            "Namespace quota exhaustion recurs under bursty workloads; a documented "
            "workaround exists pending a permanent capacity-planning fix. Ties to corpus "
            "doc KI-002."
        ),
        "opened_at": "2026-06-25T00:00:00Z",
        "updated_at": "2026-07-10T00:00:00Z",
        "owner_team": "platform-capacity",
    },
]

_NEW_REQUEST_ID_FLOOR = 30100


class MockItsmFixture:
    """Eval-only equivalent of the Tools Template's own `ItsmStore`.

    Unlike the real store, `_simulate_error` staying reachable here is
    correct and intentional -- this class is never imported by, or
    shipped inside, any scaffolded project's own runtime code. It exists
    only to be driven directly by `domain_executor.py`'s fault-injection
    context manager.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}
        self._next_request_seq = _NEW_REQUEST_ID_FLOOR
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._records = {r["record_id"]: dict(r) for r in _SEED_RECORDS}
            self._next_request_seq = _NEW_REQUEST_ID_FLOOR

    def _project_search_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        return {k: record[k] for k in _SEARCH_RESULT_FIELDS}

    def search(
        self,
        record_type: str,
        query: str | None = None,
        record_id: str | None = None,
        status: str | None = None,
        limit: int = 10,
        _simulate_error: str | None = None,
    ) -> dict[str, Any]:
        if _simulate_error == "timeout":
            raise TimeoutError("simulated tool timeout")
        if _simulate_error is not None:
            raise ConnectionError(f"simulated tool error: {_simulate_error}")

        if record_type not in RECORD_TYPES:
            raise ValueError(f"invalid record_type: {record_type!r}")

        with self._lock:
            candidates = [r for r in self._records.values() if r["record_type"] == record_type]

            if record_id is not None:
                matches = [r for r in candidates if r["record_id"] == record_id]
            elif query and query.strip().upper() in {r["record_id"] for r in candidates}:
                matches = [r for r in candidates if r["record_id"] == query.strip().upper()]
            else:
                matches = candidates
                if status is not None:
                    target_status = _normalize_status(status)
                    matches = [r for r in matches if _normalize_status(r["status"]) == target_status]
                if query:
                    variants = _plural_tolerant_variants(query.lower())
                    matches = [
                        r
                        for r in matches
                        if any(
                            v in r["short_description"].lower() or v in r["description"].lower()
                            for v in variants
                        )
                    ]

            matches = matches[: max(limit, 0)]
            records = [self._project_search_fields(r) for r in matches]

        return {"records": records, "count": len(records), "source": "mock-itsm"}

    def create_request(
        self,
        short_description: str,
        description: str,
        category: str,
        requested_for: str,
        related_record_id: str | None = None,
        _simulate_error: str | None = None,
    ) -> dict[str, Any]:
        if _simulate_error == "timeout":
            raise TimeoutError("simulated tool timeout")
        if _simulate_error is not None:
            raise ConnectionError(f"simulated tool error: {_simulate_error}")

        if category not in REQUEST_CATEGORIES:
            raise ValueError(f"invalid category: {category!r}")

        with self._lock:
            record_id = f"REQ-{self._next_request_seq:05d}"
            self._next_request_seq += 1
            timestamp = datetime.now(timezone.utc).isoformat()
            record = {
                "record_id": record_id,
                "record_type": "request",
                "status": "submitted",
                "short_description": short_description,
                "description": description,
                "category": category,
                "requested_for": requested_for,
                "related_record_id": related_record_id,
                "opened_at": timestamp,
                "updated_at": timestamp,
                "owner_team": "platform-engineering",
            }
            self._records[record_id] = record

        return {"record_id": record_id, "status": "submitted", "source": "mock-itsm"}

    def get_record(self, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._records.get(record_id)
            return dict(record) if record else None

    def list_records(
        self, record_type: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._records.values())
        if record_type is not None:
            records = [r for r in records if r["record_type"] == record_type]
        if status is not None:
            records = [r for r in records if r["status"] == status]
        return [dict(r) for r in records]


# Module-level singleton, mirroring mcp_server/itsm_store.py's own
# `store` -- one instance per eval-harness process.
fixture = MockItsmFixture()


def eval_call_tool(tool_name: str, arguments: dict, timeout: float = 10.0) -> dict:
    """Test-only MCP client stub. Same dispatch shape as
    `mcp_server/client.py`'s own in-process "mock" branch used to have,
    but backed by `fixture` above instead of importing the real
    `mcp_server` package (which the split Agent Template cannot do at
    all). `timeout` is accepted, not used -- this call never
    actually blocks; kept for call-signature parity with the real
    `call_tool(tool_name, arguments, timeout=...)` so patching it in for
    `agent.nodes.tool_invoke.call_tool` / `agent.nodes.human_approval.call_tool`
    is a drop-in swap, not a call-site rewrite.
    """
    if tool_name == "placeholder_lookup":
        return {"result": "PLACEHOLDER_TOOL_RESPONSE_MARKER", "source": "mock"}
    if tool_name == "placeholder_write_action":
        return {"result": "PLACEHOLDER_TOOL_RESPONSE_MARKER", "source": "mock"}
    if tool_name == "itsm_search_records":
        return fixture.search(**arguments)
    if tool_name == "itsm_create_request":
        return fixture.create_request(**arguments)
    raise ValueError(f"unknown tool: {tool_name}")
