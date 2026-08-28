"""In-process mock-ITSM record store.

Persistence *design* is deliberately out of scope for this component per
srs/SRS-MIT.md ("this document does not specify the mock's ... persistence
design — which store, if any"; only the externally observable guarantee at
SRS-MIT-IF-05 is specified: state persists across calls within one running
instance). A dict guarded by a lock satisfies that guarantee without
over-building — no database is warranted here. Only the approval service
has a real restart-survival requirement.

Seed fixture IDs are contractual, not illustrative: eval/README.md commits
`eval/cases/domain/*.yaml` to these exact eight IDs and, in several cases,
to specific field values (e.g. INC-10255 must read `status: resolved`,
REQ-30052 must read `status: in_progress`). Do not rename or reseed
without updating the eval cases in the same PR — the same same-PR sync
rule this repo's SRS documents use elsewhere.
"""

import re
import threading
from datetime import datetime, timezone
from typing import Any

def _plural_tolerant_variants(needle: str) -> list[str]:
    """Tolerates a trailing-s mismatch between a caller's phrasing
    and a record's stored text, without full stemming. Returns the needle
    plus a single trailing-s variant."""
    if needle.endswith("s") and len(needle) > 3:
        return [needle, needle[:-1]]
    return [needle, needle + "s"]


_STATUS_SEPARATOR_RE = re.compile(r"[-_\s]+")


def _normalize_status(status: str) -> str:
    """Treats "in-progress"/"in_progress"/"in progress" as
    the same value -- collapses any run of hyphen/underscore/whitespace
    into one canonical separator and lowercases."""
    return _STATUS_SEPARATOR_RE.sub("_", status.strip().lower())


RECORD_TYPES = ("incident", "request", "known_error")
REQUEST_CATEGORIES = ("access", "provisioning", "break_fix", "information")

# Field set returned by itsm_search_records, per srs/SRS-MIT.md SRS-MIT-IF-02.
# Deliberately excludes `description`/`category`/`requested_for`/
# `related_record_id` — those are internal/creation-time fields, not part
# of the read contract's output shape.
_SEARCH_RESULT_FIELDS = (
    "record_id",
    "record_type",
    "status",
    "short_description",
    "opened_at",
    "updated_at",
    "owner_team",
)

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

_NEW_REQUEST_ID_FLOOR = 30100  # new requests mint sequentially above this


class ItsmStore:
    """Thread-safe in-process store for mock ITSM records."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}
        self._next_request_seq = _NEW_REQUEST_ID_FLOOR
        self.reset()

    def reset(self) -> None:
        """Restore exactly the seed set, discarding any created requests."""
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
        """Read-only search/lookup. Never creates, modifies, or deletes state.

        `_simulate_error` is a test-only fault-injection hook, driven only by
        the eval executor's `fault_params` (Phase B4) — never reachable from
        a real agent-constructed call, since the MCP tool wrapper in
        server.py does not expose this parameter at all.
        """
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
                # Tolerate a caller passing an exact record ID as `query`
                # instead of `record_id` -- observed empirically: a
                # capable, correctly-prompted model still sometimes makes
                # this choice, and a real ITSM search box would be no
                # stricter about it. Exact match only, case-insensitive;
                # does not affect any free-text substring match below.
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
        """Write. Mints a new REQ-NNNNN record and persists it.

        Per SRS-MIT-SEC-01, this operation itself exposes no bypass — it is
        only reachable at all through the agent's write-gated tool_invoke
        path (Phase B2). Approval gating is enforced by the agent's policy
        layer plus the approval service, not by this component.
        """
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
        """REST introspection only (SRS-MIT-IF-04) — full record, not the
        search-projected field set, since this is a demo/test-support
        surface, not the MCP read contract."""
        with self._lock:
            record = self._records.get(record_id)
            return dict(record) if record else None

    def list_records(
        self, record_type: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        """REST introspection only (SRS-MIT-IF-04) — full records."""
        with self._lock:
            records = list(self._records.values())
        if record_type is not None:
            records = [r for r in records if r["record_type"] == record_type]
        if status is not None:
            records = [r for r in records if r["status"] == status]
        return [dict(r) for r in records]


# Module-level singleton — one instance per running process, matching
# SRS-MIT-IF-05's "within one running instance" persistence guarantee.
store = ItsmStore()
