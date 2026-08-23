"""Phase D, Step D1 -- approval_service business-logic tests, covering
every "Needed" item in srs/SRS-APR.md's Section 6 verification table plus
the two DECISIONS.md DEC-046 additions (the absent-evidence_refs schema
reject, and the expired-proposal decided_by/decided_at parity check).

Store-level tests construct their own ApprovalStore/ExpiryScanner
instances against a per-test tmp_path DB file -- ApprovalStore has no
reset/delete method (SEC-04), so isolation is by fresh file, not by
clearing shared state. API-level tests go through approval_service.api's
FastAPI app via approval_service.api._use_store, its test-only hook for
repointing the module (and its background scanner) at that same kind of
fresh, isolated store.
"""

import concurrent.futures
import inspect
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from approval_service import api, auth, config
from approval_service.schemas import ProposalCreate, ProposalDecision
from approval_service.store import ApprovalStore, ExpiryScanner

# --- shared fixtures -------------------------------------------------------


def _valid_kwargs(**overrides):
    kwargs = dict(
        action_type="itsm_create_request",
        target_system_id="mock-itsm",
        action_arguments={"short_description": "VPN access", "requested_for": "alice"},
        evidence_refs=["KI-001"],
        initiating_user_id="alice",
        agent_workload_id="golden-path-agent",
        originating_session_id="sess-" + uuid.uuid4().hex[:8],
        originating_request_id="req-" + uuid.uuid4().hex[:8],
    )
    kwargs.update(overrides)
    return kwargs


def _valid_payload(**overrides):
    return _valid_kwargs(**overrides)


@pytest.fixture
def fresh_store(tmp_path):
    db_path = str(tmp_path / f"approvals-{uuid.uuid4().hex}.db")
    return ApprovalStore(db_path=db_path)


@pytest.fixture
def client(fresh_store, monkeypatch):
    monkeypatch.setattr(config, "AUTH_MODE", "none")
    api._use_store(fresh_store)
    with TestClient(api.app) as c:
        yield c


# --- SRS-APR-F-01 / IF-01: schema-reject cases ------------------------------

REQUIRED_FIELDS = (
    "action_type",
    "target_system_id",
    "action_arguments",
    "evidence_refs",
    "initiating_user_id",
    "agent_workload_id",
    "originating_session_id",
    "originating_request_id",
)


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_f01_missing_required_field_rejected_with_422_and_no_record(client, fresh_store, missing_field):
    payload = _valid_payload()
    del payload[missing_field]

    response = client.post("/proposals", json=payload)

    assert response.status_code == 422
    assert fresh_store.list_pending() == []


def test_f01_missing_evidence_refs_specifically_rejected(client, fresh_store):
    # DEC-046 correction 1: evidence_refs is required (no default) --
    # an *absent* field must 422, distinct from the general
    # missing-required-field parametrization above (called out explicitly
    # since this is the field DEC-046 corrected).
    payload = _valid_payload()
    del payload["evidence_refs"]

    response = client.post("/proposals", json=payload)

    assert response.status_code == 422
    assert fresh_store.list_pending() == []


def test_f01_empty_evidence_refs_list_is_accepted(client):
    # DEC-046: presence, not content -- an *empty* list is a valid,
    # distinct case from an *absent* field.
    payload = _valid_payload(evidence_refs=[])

    response = client.post("/proposals", json=payload)

    assert response.status_code == 201
    assert response.json()["state"] == "pending"


def test_f01_empty_action_arguments_dict_is_accepted(client):
    # Symmetric case: action_arguments has no default either, but an
    # empty dict is still a valid *value* for a required field.
    payload = _valid_payload(action_arguments={})

    response = client.post("/proposals", json=payload)

    assert response.status_code == 201


def test_f01_pydantic_schema_itself_rejects_missing_evidence_refs():
    # I (schema inspection): direct pydantic-level confirmation, not just
    # through the HTTP layer.
    payload = _valid_payload()
    del payload["evidence_refs"]
    with pytest.raises(Exception):  # pydantic.ValidationError
        ProposalCreate(**payload)

    # An empty list, by contrast, validates fine.
    ok_payload = _valid_payload(evidence_refs=[])
    ProposalCreate(**ok_payload)  # must not raise


# --- SRS-APR-IF-01: created-shape + F-05 decision-context completeness ----


def test_if01_create_returns_proposal_id_and_pending_state(client):
    response = client.post("/proposals", json=_valid_payload())
    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {"proposal_id", "state"}
    assert body["state"] == "pending"
    assert body["proposal_id"]


def test_f05_decision_context_availability(client):
    payload = _valid_payload(
        action_arguments={"short_description": "Namespace onboarding", "requested_for": "bob"},
        evidence_refs=["KI-002", "REQ-30021"],
        initiating_user_id="bob",
    )
    created = client.post("/proposals", json=payload).json()

    listed = client.get(
        "/proposals", params={"originating_session_id": payload["originating_session_id"]}
    ).json()

    assert len(listed) == 1
    entry = listed[0]
    assert entry["proposal_id"] == created["proposal_id"]
    assert entry["action_type"] == payload["action_type"]
    assert entry["action_arguments"] == payload["action_arguments"]
    assert entry["evidence_refs"] == payload["evidence_refs"]
    assert entry["initiating_user_id"] == payload["initiating_user_id"]


# --- SRS-APR-F-06 / IF-04: pending-proposal query surface -------------------


def test_f06_list_reflects_true_pending_set_across_transitions(client):
    p1 = client.post("/proposals", json=_valid_payload()).json()
    p2 = client.post("/proposals", json=_valid_payload()).json()

    pending_ids = {p["proposal_id"] for p in client.get("/proposals").json()}
    assert {p1["proposal_id"], p2["proposal_id"]}.issubset(pending_ids)

    client.post(f"/proposals/{p1['proposal_id']}/decision", json={"decision": "approve"})

    pending_ids_after = {p["proposal_id"] for p in client.get("/proposals").json()}
    assert p1["proposal_id"] not in pending_ids_after
    assert p2["proposal_id"] in pending_ids_after


def test_if04_list_filters_by_originating_session_id(client):
    payload_a = _valid_payload()
    payload_b = _valid_payload()
    a = client.post("/proposals", json=payload_a).json()
    client.post("/proposals", json=payload_b).json()

    filtered = client.get(
        "/proposals", params={"originating_session_id": payload_a["originating_session_id"]}
    ).json()

    assert [p["proposal_id"] for p in filtered] == [a["proposal_id"]]


def test_if04_list_filters_by_originating_request_id(client):
    payload_a = _valid_payload()
    payload_b = _valid_payload()
    client.post("/proposals", json=payload_a).json()
    b = client.post("/proposals", json=payload_b).json()

    filtered = client.get(
        "/proposals", params={"originating_request_id": payload_b["originating_request_id"]}
    ).json()

    assert [p["proposal_id"] for p in filtered] == [b["proposal_id"]]


# --- SRS-APR-F-02 / IF-02: single-decision lifecycle, concurrency ----------


def test_f02_approve_then_second_decision_refused_with_409_and_actual_state(client):
    created = client.post("/proposals", json=_valid_payload()).json()
    proposal_id = created["proposal_id"]

    first = client.post(f"/proposals/{proposal_id}/decision", json={"decision": "approve"})
    assert first.status_code == 200
    assert first.json()["state"] == "approved"

    second = client.post(f"/proposals/{proposal_id}/decision", json={"decision": "reject"})
    assert second.status_code == 409
    assert second.json()["detail"]["state"] == "approved"
    assert second.json()["detail"]["proposal_id"] == proposal_id


def test_f02_concurrent_decisions_one_wins_one_refused(fresh_store):
    record = fresh_store.create_proposal(**_valid_kwargs())
    proposal_id = record["proposal_id"]
    barrier = threading.Barrier(2)

    def _decide(decision, approver):
        barrier.wait()
        return fresh_store.transition_to_terminal(
            proposal_id, decision=decision, decided_by=approver, decided_at=_now_iso()
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_decide, "approved", "alice")
        f2 = pool.submit(_decide, "rejected", "bob")
        r1, r2 = f1.result(), f2.result()

    winners = [r for r in (r1, r2) if r is not None]
    losers = [r for r in (r1, r2) if r is None]
    assert len(winners) == 1, "exactly one concurrent decision must win"
    assert len(losers) == 1, "exactly one concurrent decision must be refused"

    final = fresh_store.get_proposal(proposal_id)
    assert final["state"] in ("approved", "rejected")
    assert final["state"] == winners[0]["state"]


def test_if02_decide_unknown_proposal_returns_404(client):
    response = client.post("/proposals/does-not-exist/decision", json={"decision": "approve"})
    assert response.status_code == 404


def test_if02_reject_returns_decided_metadata(client):
    created = client.post("/proposals", json=_valid_payload()).json()
    response = client.post(f"/proposals/{created['proposal_id']}/decision", json={"decision": "reject"})

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "rejected"
    assert body["decision"] == "reject"
    assert body["decided_by"] == "dev-approver"  # AUTH_MODE=none placeholder
    assert body["decided_at"]


def test_f02_decision_audit_logged_on_refusal(client, caplog):
    created = client.post("/proposals", json=_valid_payload()).json()
    proposal_id = created["proposal_id"]
    client.post(f"/proposals/{proposal_id}/decision", json={"decision": "approve"})

    with caplog.at_level(logging.WARNING, logger="approval_service.audit"):
        client.post(f"/proposals/{proposal_id}/decision", json={"decision": "reject"})

    assert any("refused decision attempt" in r.message for r in caplog.records)
    assert any("not_pending" in r.message for r in caplog.records)


# --- SRS-APR-IF-05 / F-04: terminal-state query, unmodified arguments ------


def test_if05_approved_proposal_query_has_unmodified_arguments(client):
    arguments = {"short_description": "Persisted, not recomputed", "requested_for": "carol"}
    created = client.post("/proposals", json=_valid_payload(action_arguments=arguments)).json()
    proposal_id = created["proposal_id"]

    client.post(f"/proposals/{proposal_id}/decision", json={"decision": "approve"})
    terminal = client.get(f"/proposals/{proposal_id}").json()

    assert terminal["state"] == "approved"
    assert terminal["action_arguments"] == arguments
    assert terminal["decided_by"] == "dev-approver"
    assert terminal["decided_at"]


def test_if05_pending_proposal_query_has_none_decision_fields(client):
    created = client.post("/proposals", json=_valid_payload()).json()
    terminal = client.get(f"/proposals/{created['proposal_id']}").json()

    assert terminal["state"] == "pending"
    assert terminal["decided_by"] is None
    assert terminal["decided_at"] is None


def test_if05_unknown_proposal_returns_404(client):
    response = client.get("/proposals/does-not-exist")
    assert response.status_code == 404


# --- SRS-APR-F-03: expiry, plus DEC-046's two additions ---------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_f03_overdue_pending_proposal_expires_via_scanner_sweep(fresh_store):
    record = fresh_store.create_proposal(**_valid_kwargs())
    with sqlite3.connect(fresh_store.db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        conn.execute(
            "UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, record["proposal_id"])
        )

    scanner = ExpiryScanner(fresh_store, timeout_seconds=60)
    expired_count = scanner.sweep()

    assert expired_count == 1
    final = fresh_store.get_proposal(record["proposal_id"])
    assert final["state"] == "expired"


def test_f03_not_yet_overdue_proposal_is_left_pending(fresh_store):
    record = fresh_store.create_proposal(**_valid_kwargs())
    scanner = ExpiryScanner(fresh_store, timeout_seconds=3600)

    expired_count = scanner.sweep()

    assert expired_count == 0
    assert fresh_store.get_proposal(record["proposal_id"])["state"] == "pending"


def test_dec046_expired_proposal_has_none_decided_by_and_decided_at(fresh_store):
    # DEC-046 correction 2 (parity test), asserted directly at the store
    # level: decided_by/decided_at are None for an expired proposal, since
    # no approver ever decided it -- not inferred from resemblance to a
    # rejection, but a direct field assertion.
    record = fresh_store.create_proposal(**_valid_kwargs())
    with sqlite3.connect(fresh_store.db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute(
            "UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, record["proposal_id"])
        )
    ExpiryScanner(fresh_store, timeout_seconds=1).sweep()

    final = fresh_store.get_proposal(record["proposal_id"])
    assert final["state"] == "expired"
    assert final["decided_by"] is None
    assert final["decided_at"] is None


def test_dec046_expired_parity_at_the_api_level_if05(client, fresh_store):
    # Same parity check, but through the actual IF-05 query surface
    # (approval_service level, as the brief specifies for this test suite).
    created = client.post("/proposals", json=_valid_payload()).json()
    proposal_id = created["proposal_id"]
    with sqlite3.connect(fresh_store.db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute("UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, proposal_id))
    ExpiryScanner(fresh_store, timeout_seconds=1).sweep()

    terminal = client.get(f"/proposals/{proposal_id}").json()

    assert terminal["state"] == "expired"
    assert terminal["decided_by"] is None
    assert terminal["decided_at"] is None


def test_dec046_app_lifespan_startup_pass_expires_overdue_proposal(client, fresh_store):
    # Same DEC-046 guarantee, exercised through the real wiring api.py's
    # lifespan uses (_expiry_scanner.start()), not just the ExpiryScanner
    # class in isolation: a fresh TestClient entry re-runs the lifespan's
    # startup, which must immediately pick up an already-overdue proposal.
    created = client.post("/proposals", json=_valid_payload()).json()
    with sqlite3.connect(fresh_store.db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        conn.execute(
            "UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, created["proposal_id"])
        )
    api._expiry_scanner._timeout_seconds = 3600  # 1h, well under the 2h backdate above

    # A fresh lifespan entry -- the app-level analogue of a process restart.
    with TestClient(api.app):
        pass

    final = fresh_store.get_proposal(created["proposal_id"])
    assert final["state"] == "expired"
    assert final["decided_by"] is None
    assert final["decided_at"] is None


def test_dec046_restart_overdue_pickup_on_fresh_scanner_startup_pass(tmp_path):
    # DEC-046: a proposal already overdue when the previous process died
    # must still expire correctly after restart, via the mandatory
    # immediate startup pass -- not only the periodic loop, and without
    # needing to wait out the poll interval.
    db_path = str(tmp_path / "restart-overdue.db")
    original_store = ApprovalStore(db_path=db_path)
    record = original_store.create_proposal(**_valid_kwargs())

    # Simulate the intake having happened well before the process died --
    # setup-only direct DB manipulation (not exercised through the store's
    # own public write surface, which has no such method by design/SEC-04).
    with sqlite3.connect(db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        conn.execute(
            "UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, record["proposal_id"])
        )
    del original_store  # the "process died" -- no further ops against it

    # "Restart": a fresh store instance AND a fresh scanner instance,
    # pointed at the same DB file.
    restarted_store = ApprovalStore(db_path=db_path)
    restarted_scanner = ExpiryScanner(restarted_store, timeout_seconds=3600)  # 1h, well under 2h overdue

    expired_count = restarted_scanner.sweep()  # the startup pass -- called directly, no sleep/interval wait

    assert expired_count == 1
    final = restarted_store.get_proposal(record["proposal_id"])
    assert final["state"] == "expired"
    assert final["decided_by"] is None
    assert final["decided_at"] is None


# --- SRS-APR-F-07 / DATA-01: idempotency, restart-persistence --------------


def test_f07_replayed_idempotency_key_returns_existing_proposal(client, fresh_store):
    payload = _valid_payload(idempotency_key="idem-key-1")

    first = client.post("/proposals", json=payload)
    second = client.post("/proposals", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["proposal_id"] == second.json()["proposal_id"]
    assert len(fresh_store.list_pending()) == 1


def test_f07_same_idempotency_key_different_session_creates_separate_proposals(client):
    payload_a = _valid_payload(idempotency_key="shared-key")
    payload_b = _valid_payload(idempotency_key="shared-key")  # different session_id, generated fresh

    a = client.post("/proposals", json=payload_a).json()
    b = client.post("/proposals", json=payload_b).json()

    assert a["proposal_id"] != b["proposal_id"]


def test_f07_idempotency_key_holds_under_a_concurrent_replay_race(fresh_store):
    kwargs = _valid_kwargs(idempotency_key="race-key")
    barrier = threading.Barrier(2)

    def _create():
        barrier.wait()
        return fresh_store.create_proposal(**kwargs)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_create)
        f2 = pool.submit(_create)
        r1, r2 = f1.result(), f2.result()

    assert r1["proposal_id"] == r2["proposal_id"]
    assert len(fresh_store.list_pending()) == 1


def test_data01_proposal_survives_a_fresh_store_instance_same_db_file(tmp_path):
    db_path = str(tmp_path / "restart-persistence.db")
    store_1 = ApprovalStore(db_path=db_path)
    record = store_1.create_proposal(**_valid_kwargs())
    del store_1

    store_2 = ApprovalStore(db_path=db_path)
    fetched = store_2.get_proposal(record["proposal_id"])

    assert fetched is not None
    assert fetched["proposal_id"] == record["proposal_id"]
    assert fetched["state"] == "pending"
    assert fetched["action_arguments"] == record["action_arguments"]
    assert fetched["evidence_refs"] == record["evidence_refs"]


def test_data01_decided_proposal_survives_a_fresh_store_instance(tmp_path):
    db_path = str(tmp_path / "restart-persistence-decided.db")
    store_1 = ApprovalStore(db_path=db_path)
    record = store_1.create_proposal(**_valid_kwargs())
    store_1.transition_to_terminal(
        record["proposal_id"], decision="approved", decided_by="alice", decided_at=_now_iso()
    )
    del store_1

    store_2 = ApprovalStore(db_path=db_path)
    fetched = store_2.get_proposal(record["proposal_id"])

    assert fetched["state"] == "approved"
    assert fetched["decided_by"] == "alice"
    assert fetched["decided_at"]


# --- SRS-APR-SEC-01: fail-closed on internal error --------------------------


def test_sec01_store_failure_during_decision_leaves_proposal_pending(client, fresh_store, monkeypatch):
    created = client.post("/proposals", json=_valid_payload()).json()
    proposal_id = created["proposal_id"]
    real_transition = fresh_store.transition_to_terminal

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated store dependency failure")

    monkeypatch.setattr(fresh_store, "transition_to_terminal", _boom)
    with pytest.raises(RuntimeError):
        client.post(f"/proposals/{proposal_id}/decision", json={"decision": "approve"})
    monkeypatch.setattr(fresh_store, "transition_to_terminal", real_transition)

    still_pending = fresh_store.get_proposal(proposal_id)
    assert still_pending["state"] == "pending"


def test_sec01_no_execution_side_effect_when_store_raises(client, fresh_store, monkeypatch):
    # A stronger form of the same guarantee: assert directly that no
    # terminal-state record was ever written -- not just that the HTTP
    # call raised.
    created = client.post("/proposals", json=_valid_payload()).json()
    proposal_id = created["proposal_id"]

    real_transition = fresh_store.transition_to_terminal

    def _boom(*args, **kwargs):
        raise ConnectionError("simulated dependency failure")

    monkeypatch.setattr(fresh_store, "transition_to_terminal", _boom)
    with pytest.raises(ConnectionError):
        client.post(f"/proposals/{proposal_id}/decision", json={"decision": "approve"})
    monkeypatch.setattr(fresh_store, "transition_to_terminal", real_transition)

    assert proposal_id in {p["proposal_id"] for p in client.get("/proposals").json()}


# --- SRS-APR-SEC-02/03: approver authorization, identity propagation ------


def _rsa_keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def _make_token(private_key, **claims):
    return pyjwt.encode(claims, private_key, algorithm="RS256")


class _FakeSigningKey:
    def __init__(self, key, algorithm_name="RS256"):
        self.key = key
        self.algorithm_name = algorithm_name


class _FakeJWKSClient:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return _FakeSigningKey(self._public_key)


@pytest.fixture
def oidc_client(fresh_store, monkeypatch):
    monkeypatch.setattr(config, "AUTH_MODE", "oidc")
    monkeypatch.setattr(config, "OIDC_ISSUER_URL", "https://idp.example.invalid/realms/demo")
    monkeypatch.setattr(config, "OIDC_AUDIENCE", "approval-service")
    monkeypatch.setattr(config, "APPROVER_ROLE_CLAIM", "roles")
    monkeypatch.setattr(config, "APPROVER_ROLE_VALUE", "approval-approver")
    api._use_store(fresh_store)
    with TestClient(api.app) as c:
        yield c


def test_sec02_non_approver_identity_gets_403(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(
        private_key,
        sub="agent-workload-identity",
        aud="approval-service",
        iss="https://idp.example.invalid/realms/demo",
        roles=["some-other-role"],  # explicitly lacks approval-approver
    )
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = oidc_client.post(
        f"/proposals/{created['proposal_id']}/decision",
        json={"decision": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_sec02_non_approver_refusal_is_audit_logged(oidc_client, monkeypatch, caplog):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(
        private_key,
        sub="agent-workload-identity",
        aud="approval-service",
        iss="https://idp.example.invalid/realms/demo",
        roles=[],
    )
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"}
    ).json()

    with caplog.at_level(logging.WARNING, logger="approval_service.audit"):
        oidc_client.post(
            f"/proposals/{created['proposal_id']}/decision",
            json={"decision": "approve"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert any("missing_approver_role" in r.message for r in caplog.records)


def test_sec02_approver_role_present_succeeds(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _make_token(
        private_key,
        sub="grace",
        aud="approval-service",
        iss="https://idp.example.invalid/realms/demo",
        roles=["approval-approver"],
    )
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = oidc_client.post(
        f"/proposals/{created['proposal_id']}/decision",
        json={"decision": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["decided_by"] == "grace"


def test_sec02_missing_bearer_token_gets_401(oidc_client, monkeypatch):
    # The decision endpoint's own missing-token case -- setup still needs
    # A valid token now that create_proposal itself requires one (DEC-069).
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    setup_token = _make_token(
        private_key, sub="agent-workload-identity", aud="approval-service",
        iss="https://idp.example.invalid/realms/demo",
    )
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {setup_token}"}
    ).json()
    response = oidc_client.post(f"/proposals/{created['proposal_id']}/decision", json={"decision": "approve"})
    assert response.status_code == 401


def test_sec02_agent_workload_token_without_approver_role_is_rejected_same_as_anyone_else(
    oidc_client, monkeypatch
):
    # The plan's own design point: the agent's workload token must never
    # successfully call the decision endpoint. This module enforces that
    # via the same role-check logic applied to any caller -- distinguishing
    # "agent token" from "approver token" is D2's role-assignment concern,
    # not application logic here.
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    agent_token = _make_token(
        private_key,
        sub="golden-path-agent",
        aud="approval-service",
        iss="https://idp.example.invalid/realms/demo",
        roles=["agent-workload"],
    )
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {agent_token}"}
    ).json()

    response = oidc_client.post(
        f"/proposals/{created['proposal_id']}/decision",
        json={"decision": "approve"},
        headers={"Authorization": f"Bearer {agent_token}"},
    )

    assert response.status_code == 403


def test_sec03_proposal_decision_schema_has_no_identity_field():
    # There is no identity field on this schema to spoof in the first
    # place -- the approver identity always comes from the validated
    # bearer token (auth.get_current_approver), never from the request
    # body.
    fields = set(ProposalDecision.model_fields.keys())
    assert fields == {"decision"}
    for spoofable in ("approver_id", "decided_by", "identity", "user_id", "sub"):
        assert spoofable not in fields


# --- DEC-069: create_proposal/list_pending_proposals/get_proposal found
# running with NO auth check at all under AUTH_MODE=oidc -- fail-open,
# contradicting SEC-01 applied everywhere else. Fixed with
# get_authenticated_caller (identity+audience only, no role check --
# neither the agent's own workload nor an approver checking pending
# proposals needs the approver role just to submit/read).


def _oidc_token(private_key, **claims):
    defaults = {"aud": "approval-service", "iss": "https://idp.example.invalid/realms/demo"}
    defaults.update(claims)
    return _make_token(private_key, **defaults)


def test_create_proposal_missing_token_gets_401(oidc_client):
    response = oidc_client.post("/proposals", json=_valid_payload())
    assert response.status_code == 401


def test_create_proposal_valid_token_no_role_needed_succeeds(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _oidc_token(private_key, sub="golden-path-agent", roles=[])  # no roles at all
    response = oidc_client.post("/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201


def test_list_pending_proposals_missing_token_gets_401(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _oidc_token(private_key, sub="golden-path-agent")
    oidc_client.post("/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"})

    response = oidc_client.get("/proposals")
    assert response.status_code == 401


def test_list_pending_proposals_valid_token_succeeds(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _oidc_token(private_key, sub="golden-path-agent")
    oidc_client.post("/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"})

    response = oidc_client.get("/proposals", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_proposal_missing_token_gets_401(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _oidc_token(private_key, sub="golden-path-agent")
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = oidc_client.get(f"/proposals/{created['proposal_id']}")
    assert response.status_code == 401


def test_get_proposal_valid_token_succeeds(oidc_client, monkeypatch):
    private_key, public_key = _rsa_keypair()
    monkeypatch.setattr(auth, "_get_jwks_client", lambda issuer_url: _FakeJWKSClient(public_key))
    token = _oidc_token(private_key, sub="golden-path-agent")
    created = oidc_client.post(
        "/proposals", json=_valid_payload(), headers={"Authorization": f"Bearer {token}"}
    ).json()

    response = oidc_client.get(f"/proposals/{created['proposal_id']}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["proposal_id"] == created["proposal_id"]


def test_auth_mode_none_leaves_all_three_endpoints_unauthenticated(fresh_store):
    # AUTH_MODE=none's own dev-convenience posture -- get_authenticated_caller
    # short-circuits the same way get_current_approver already does.
    api._use_store(fresh_store)
    with TestClient(api.app) as client:
        created = client.post("/proposals", json=_valid_payload())
        assert created.status_code == 201
        assert client.get("/proposals").status_code == 200
        assert client.get(f"/proposals/{created.json()['proposal_id']}").status_code == 200


def test_sec03_auth_mode_none_never_reads_identity_from_the_request_body(client):
    # AUTH_MODE=none returns a fixed placeholder identity regardless of
    # anything in the request -- confirms decided_by is never influenced
    # by client-supplied content, even indirectly.
    created = client.post("/proposals", json=_valid_payload()).json()
    response = client.post(
        f"/proposals/{created['proposal_id']}/decision",
        json={"decision": "approve"},
        headers={"X-Impersonate-User": "someone-else"},
    )
    assert response.json()["decided_by"] == "dev-approver"


# --- SRS-APR-SEC-04: audit-record immutability (structural) ---------------


def test_sec04_store_exposes_exactly_the_four_documented_operations():
    from approval_service import store as store_module

    public_methods = {
        name
        for name, _ in inspect.getmembers(store_module.ApprovalStore, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert public_methods == {"create_proposal", "get_proposal", "list_pending", "transition_to_terminal"}


def test_sec04_no_update_or_delete_operation_anywhere_in_the_store_module():
    from approval_service import store as store_module

    forbidden_substrings = ("update", "delete", "remove", "modify", "edit", "patch", "reset")

    candidates = list(inspect.getmembers(store_module.ApprovalStore, predicate=inspect.isfunction))
    candidates += list(inspect.getmembers(store_module, predicate=inspect.isfunction))
    candidates += list(inspect.getmembers(store_module.ExpiryScanner, predicate=inspect.isfunction))

    for name, _ in candidates:
        if name.startswith("_"):
            continue
        lowered = name.lower()
        assert not any(s in lowered for s in forbidden_substrings), (
            f"public callable {name!r} looks like an update/delete operation -- "
            "SEC-04 requires no such operation be exposed anywhere in this module"
        )


def test_sec04_attempted_mutation_of_a_terminal_record_is_a_no_op(fresh_store):
    # "Attempted mutation... fails" (SEC-04's own T verification wording),
    # realized as: once terminal, transition_to_terminal (the only write
    # path) refuses to touch the record again -- exercised directly here,
    # distinct from F-02's already-pending-focused concurrency test.
    record = fresh_store.create_proposal(**_valid_kwargs())
    fresh_store.transition_to_terminal(
        record["proposal_id"], decision="approved", decided_by="alice", decided_at=_now_iso()
    )

    second_attempt = fresh_store.transition_to_terminal(
        record["proposal_id"], decision="rejected", decided_by="mallory", decided_at=_now_iso()
    )

    assert second_attempt is None
    final = fresh_store.get_proposal(record["proposal_id"])
    assert final["state"] == "approved"
    assert final["decided_by"] == "alice"


# --- SRS-APR-IF-03: telemetry emission (logging-based realization) --------


def test_if03_create_emits_a_correlated_telemetry_event(client, caplog):
    payload = _valid_payload()
    with caplog.at_level(logging.INFO, logger="approval_service.telemetry"):
        created = client.post("/proposals", json=payload).json()

    events = [r.message for r in caplog.records if "approval_transition" in r.message]
    assert any(created["proposal_id"] in e and payload["originating_session_id"] in e for e in events)


def test_if03_decision_emits_a_correlated_telemetry_event(client, caplog):
    created = client.post("/proposals", json=_valid_payload()).json()
    with caplog.at_level(logging.INFO, logger="approval_service.telemetry"):
        client.post(f"/proposals/{created['proposal_id']}/decision", json={"decision": "approve"})

    events = [r.message for r in caplog.records if "approval_transition" in r.message]
    assert any("proposal_decided" in e and created["proposal_id"] in e for e in events)


def test_if03_expiry_emits_a_correlated_telemetry_event(fresh_store, caplog):
    record = fresh_store.create_proposal(**_valid_kwargs())
    with sqlite3.connect(fresh_store.db_path) as conn:
        overdue = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        conn.execute(
            "UPDATE proposals SET created_at = ? WHERE proposal_id = ?", (overdue, record["proposal_id"])
        )

    with caplog.at_level(logging.INFO, logger="approval_service.telemetry"):
        ExpiryScanner(fresh_store, timeout_seconds=1).sweep()

    events = [r.message for r in caplog.records if "approval_transition" in r.message]
    assert any("proposal_expired" in e and record["proposal_id"] in e for e in events)
