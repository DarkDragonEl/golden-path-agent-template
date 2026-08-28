import asyncio
import inspect

import pytest

from mcp_server import itsm_store
from mcp_server.server import (
    healthcheck,
    itsm_create_request,
    itsm_search_records,
    mcp,
    placeholder_lookup,
)

# Store reset-per-test and the shared `rest_client` fixture both live in
# tests/conftest.py now -- see its docstring for why `rest_client` must be
# process-session-scoped, not module-scoped.


def test_both_itsm_tools_registered_with_catalog_metadata():
    # SRS-MIT-IF-01: tool name, semantic version, certification status.
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name in ("itsm_search_records", "itsm_create_request"):
        assert name in tools
        assert tools[name].meta is not None
        assert "semver" in tools[name].meta
        assert "certification_status" in tools[name].meta


def test_placeholder_and_healthcheck_still_registered():
    tools = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "placeholder_lookup" in tools
    assert "healthcheck" in tools


def test_itsm_search_records_signature_matches_srs_mit_if_02():
    params = set(inspect.signature(itsm_search_records).parameters)
    assert params == {"record_type", "query", "record_id", "status", "limit"}


def test_itsm_create_request_signature_matches_srs_mit_if_03():
    params = set(inspect.signature(itsm_create_request).parameters)
    assert params == {
        "short_description",
        "description",
        "category",
        "requested_for",
        "related_record_id",
    }


def test_simulate_error_not_reachable_through_the_public_tool_functions():
    # Fault injection is a store-only, test-only hook (the eval
    # executor drives it directly against mcp_server.itsm_store.store) --
    # never exposed on the MCP-facing tool wrapper signatures a real agent
    # call would use.
    with pytest.raises(TypeError):
        itsm_search_records(record_type="incident", _simulate_error="timeout")
    with pytest.raises(TypeError):
        itsm_create_request(
            short_description="a",
            description="a",
            category="access",
            requested_for="alice",
            _simulate_error="timeout",
        )


def test_itsm_search_records_read_only_never_mutates():
    before = itsm_store.store.list_records()
    itsm_search_records(record_type="incident", query="CI pipeline")
    after = itsm_store.store.list_records()
    assert before == after


def test_itsm_create_request_then_search_round_trip():
    created = itsm_create_request(
        short_description="Test request",
        description="Testing the write-then-read round trip via the MCP tool wrappers.",
        category="access",
        requested_for="dana",
    )
    assert created["record_id"].startswith("REQ-")
    assert created["status"] == "submitted"

    found = itsm_search_records(record_type="request", record_id=created["record_id"])
    assert found["count"] == 1
    assert found["records"][0]["record_id"] == created["record_id"]


def test_placeholder_lookup_unaffected_by_itsm_additions():
    result = placeholder_lookup(query="anything")
    assert result["result"] == "PLACEHOLDER_TOOL_RESPONSE_MARKER"


def test_healthcheck_unaffected():
    assert healthcheck() == {"status": "ok"}


# --- REST introspection surface (SRS-MIT-IF-04) ---


def test_rest_get_records_lists_seed_set(rest_client):
    resp = rest_client.get("/records")
    assert resp.status_code == 200
    ids = {r["record_id"] for r in resp.json()["records"]}
    assert "INC-10234" in ids
    assert len(ids) == 8


def test_rest_get_single_record_found_and_not_found(rest_client):
    resp = rest_client.get("/records/INC-10255")
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    resp = rest_client.get("/records/NOPE-00000")
    assert resp.status_code == 404


def test_rest_filters_by_record_type_and_status(rest_client):
    resp = rest_client.get("/records", params={"record_type": "request", "status": "in_progress"})
    assert resp.status_code == 200
    ids = {r["record_id"] for r in resp.json()["records"]}
    assert ids == {"REQ-30052"}


def test_rest_reset_restores_seed_set_after_a_write(rest_client):
    itsm_create_request(
        short_description="a", description="a", category="access", requested_for="alice"
    )
    resp = rest_client.post("/reset")
    assert resp.status_code == 200

    resp = rest_client.get("/records")
    ids = {r["record_id"] for r in resp.json()["records"]}
    assert len(ids) == 8


# --- REST tool-call surface (the MCP_MODE=live path's real ---
# --- HTTP target -- previously a 404, mcp_server/client.py's own note) --


def test_rest_call_tool_unknown_tool_name_gets_404(rest_client):
    resp = rest_client.post("/tools/not_a_real_tool", json={})
    assert resp.status_code == 404


def test_rest_call_tool_dispatches_to_the_real_tool_function(rest_client):
    resp = rest_client.post("/tools/itsm_search_records", json={"record_type": "incident"})
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_rest_call_tool_default_auth_mode_none_requires_no_token(rest_client, monkeypatch):
    monkeypatch.delenv("MCP_AUTH_MODE", raising=False)
    resp = rest_client.post("/tools/placeholder_lookup", json={"query": "anything"})
    assert resp.status_code == 200


def test_rest_call_tool_oidc_mode_missing_token_gets_401(rest_client, monkeypatch):
    monkeypatch.setenv("MCP_AUTH_MODE", "oidc")
    resp = rest_client.post("/tools/placeholder_lookup", json={"query": "anything"})
    assert resp.status_code == 401


def test_rest_state_matches_mcp_tool_state_for_the_same_record(rest_client):
    # SRS-MIT-IF-04's own verification method: "state visible via REST
    # matches state returned via MCP" for the same record.
    created = itsm_create_request(
        short_description="Consistency check",
        description="REST and MCP must agree on this record's state.",
        category="information",
        requested_for="erin",
    )
    record_id = created["record_id"]

    via_mcp = itsm_search_records(record_type="request", record_id=record_id)["records"][0]
    via_rest = rest_client.get(f"/records/{record_id}").json()

    for field in via_mcp:
        assert via_rest[field] == via_mcp[field]
