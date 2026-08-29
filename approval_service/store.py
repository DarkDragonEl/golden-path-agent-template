"""SQLite-backed persistence for approval proposals -- SRS-APR-DATA-01
(restart-survival), SRS-APR-SEC-04 (immutability).

This module exposes exactly four operations on `ApprovalStore`:
create_proposal, get_proposal, list_pending, transition_to_terminal. The
*absence* of any update/delete method here -- on this class, and anywhere
else in this module -- is the SEC-04 enforcement itself, not an oversight.
Do not add one "for convenience"; correcting a bad record is an
out-of-scope append-only-correction workflow per SRS-APR-SEC-04's own
"alternative considered" note, not something this module does.

Persistence design (SQLite on a PVC, one file, one table) mirrors
mcp_server/itsm_store.py's own "no over-building" posture, scaled up only
for the one guarantee that component explicitly does not need and this one
does: survival across a process restart.
"""

import asyncio
import contextlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

_telemetry_logger = logging.getLogger("approval_service.telemetry")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    target_system_id TEXT NOT NULL,
    action_arguments TEXT NOT NULL,
    evidence_refs TEXT NOT NULL,
    initiating_user_id TEXT NOT NULL,
    agent_workload_id TEXT NOT NULL,
    originating_session_id TEXT NOT NULL,
    originating_request_id TEXT NOT NULL,
    idempotency_key TEXT,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_proposals_idempotency
    ON proposals(originating_session_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
"""


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["action_arguments"] = json.loads(record["action_arguments"])
    record["evidence_refs"] = json.loads(record["evidence_refs"])
    return record


class ApprovalStore:
    """One instance per running process (production: the module-level
    `store` singleton below). A fresh instance constructed against the
    same `db_path` -- e.g. after a restart, or a second instance in a test
    -- sees exactly the same records; that is SRS-APR-DATA-01's guarantee,
    and the reason this class opens a new SQLite connection per call
    rather than holding one open (no in-memory state to lose or diverge)."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or config.APPROVAL_DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextlib.contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        try:
            with conn:  # commits on clean exit, rolls back on exception
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _get_by_idempotency_key(self, originating_session_id: str, idempotency_key: str) -> dict | None:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM proposals WHERE originating_session_id = ? AND idempotency_key = ?",
                (originating_session_id, idempotency_key),
            ).fetchone()
        return _row_to_record(row) if row else None

    def create_proposal(
        self,
        *,
        action_type: str,
        target_system_id: str,
        action_arguments: dict,
        evidence_refs: list[str],
        initiating_user_id: str,
        agent_workload_id: str,
        originating_session_id: str,
        originating_request_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """SRS-APR-F-01/IF-01. F-07: a replayed `idempotency_key` for the
        same `originating_session_id` returns the *existing* proposal's
        current state rather than creating a duplicate pending approval."""
        if idempotency_key is not None:
            existing = self._get_by_idempotency_key(originating_session_id, idempotency_key)
            if existing is not None:
                return existing

        proposal_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        record = {
            "proposal_id": proposal_id,
            "action_type": action_type,
            "target_system_id": target_system_id,
            "action_arguments": action_arguments,
            "evidence_refs": evidence_refs,
            "initiating_user_id": initiating_user_id,
            "agent_workload_id": agent_workload_id,
            "originating_session_id": originating_session_id,
            "originating_request_id": originating_request_id,
            "idempotency_key": idempotency_key,
            "state": "pending",
            "created_at": created_at,
            "decided_by": None,
            "decided_at": None,
        }
        try:
            with self._connection() as conn:
                conn.execute(
                    """INSERT INTO proposals (
                        proposal_id, action_type, target_system_id, action_arguments,
                        evidence_refs, initiating_user_id, agent_workload_id,
                        originating_session_id, originating_request_id, idempotency_key,
                        state, created_at, decided_by, decided_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        proposal_id,
                        action_type,
                        target_system_id,
                        json.dumps(action_arguments),
                        json.dumps(evidence_refs),
                        initiating_user_id,
                        agent_workload_id,
                        originating_session_id,
                        originating_request_id,
                        idempotency_key,
                        "pending",
                        created_at,
                        None,
                        None,
                    ),
                )
        except sqlite3.IntegrityError:
            # A concurrent replay of the same idempotency key raced us and
            # won -- the partial unique index caught it. F-07's guarantee
            # holds under a race too, not just a sequential replay: return
            # whichever record actually landed.
            existing = self._get_by_idempotency_key(originating_session_id, idempotency_key)
            if existing is not None:
                return existing
            raise
        return record

    def get_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_pending(
        self, originating_session_id: str | None = None, originating_request_id: str | None = None
    ) -> list[dict[str, Any]]:
        """SRS-APR-IF-04/F-06."""
        query = "SELECT * FROM proposals WHERE state = 'pending'"
        params: list[str] = []
        if originating_session_id is not None:
            query += " AND originating_session_id = ?"
            params.append(originating_session_id)
        if originating_request_id is not None:
            query += " AND originating_request_id = ?"
            params.append(originating_request_id)
        query += " ORDER BY created_at ASC"
        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def transition_to_terminal(
        self, proposal_id: str, decision: str, decided_by: str | None, decided_at: str | None
    ) -> dict[str, Any] | None:
        """The ONE atomic write path for approve/reject *and* expiry
        (SEC-04) -- pass `decision="expired"`, `decided_by=None`,
        `decided_at=None` for expiry (ADR-008: an expired proposal's
        decided_by/decided_at stay None). One `UPDATE ... WHERE state =
        'pending'` per connection, SQLite's own `busy_timeout` serializing
        concurrent callers (SRS-APR-F-02). Returns the updated record, or
        `None` if the proposal wasn't `pending` at UPDATE time."""
        with self._connection() as conn:
            cursor = conn.execute(
                """UPDATE proposals
                   SET state = ?, decided_by = ?, decided_at = ?
                   WHERE proposal_id = ? AND state = 'pending'""",
                (decision, decided_by, decided_at, proposal_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_proposal(proposal_id)


class ExpiryScanner:
    """SRS-APR-F-03 -- in-process asyncio background task, started from
    the FastAPI app's lifespan (api.py). `sweep()` does one pass; called
    both by `start()`'s mandatory immediate pass (ADR-008: catches
    proposals already overdue when the previous process died) and by the
    periodic loop `start()` also launches -- one place expiry-detection
    logic lives."""

    def __init__(
        self, store: ApprovalStore, timeout_seconds: int, poll_interval_seconds: float = 30.0
    ) -> None:
        self._store = store
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._task: asyncio.Task | None = None

    def rebind_store(self, store: ApprovalStore) -> None:
        """Test-only hook (not part of the SRS-APR contract), mirroring
        api.py's own `_use_store` -- lets an already-constructed scanner
        be pointed at a fresh per-test store instance."""
        self._store = store

    def _is_overdue(self, record: dict, now: datetime) -> bool:
        created_at = datetime.fromisoformat(record["created_at"])
        return (now - created_at).total_seconds() >= self._timeout_seconds

    def sweep(self) -> int:
        """One pass: expire every `pending` proposal whose intake time
        plus the configured timeout has elapsed, via the same atomic
        `transition_to_terminal` guard approve/reject use. Returns the
        number actually expired by this call (0 if none were overdue, or
        if a concurrent caller already won the race on all of them)."""
        now = datetime.now(timezone.utc)
        expired = 0
        for record in self._store.list_pending():
            if not self._is_overdue(record, now):
                continue
            result = self._store.transition_to_terminal(
                record["proposal_id"], decision="expired", decided_by=None, decided_at=None
            )
            if result is not None:
                _telemetry_logger.info(
                    "approval_transition event=%s proposal_id=%s state=%s session_id=%s request_id=%s",
                    "proposal_expired",
                    result["proposal_id"],
                    result["state"],
                    result["originating_session_id"],
                    result["originating_request_id"],
                )
                expired += 1
        return expired

    async def _run_periodic(self) -> None:
        while True:
            await asyncio.sleep(self._poll_interval_seconds)
            self.sweep()

    def start(self) -> None:
        """Call once from the FastAPI lifespan's startup. Runs the
        mandatory immediate pass synchronously first (ADR-008), then
        starts the periodic loop as a background task."""
        self.sweep()
        self._task = asyncio.create_task(self._run_periodic())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None


# Module-level singleton -- one instance per running process, matching
# mcp_server/itsm_store.py's own convention. Constructed eagerly (creates
# the DB file/parent directory on import) so every caller in this process
# shares one store without threading a reference through every import.
store = ApprovalStore()
