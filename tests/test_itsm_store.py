import pytest

from mcp_server.itsm_store import ItsmStore

CONTRACTUAL_SEED_IDS = {
    "INC-10234",
    "INC-10240",
    "INC-10255",
    "INC-10261",
    "REQ-30021",
    "REQ-30052",
    "KE-50007",
    "KE-50012",
}


@pytest.fixture
def store():
    s = ItsmStore()
    yield s
    s.reset()


def test_seed_set_matches_eval_readme_contractual_ids(store):
    seeded_ids = {r["record_id"] for r in store.list_records()}
    assert seeded_ids == CONTRACTUAL_SEED_IDS


def test_inc_10255_is_resolved(store):
    # eval/cases/domain/itsm_read.yaml ITR-002: record_id lookup on
    # INC-10255 must result_contains "resolved".
    result = store.search(record_type="incident", record_id="INC-10255")
    assert result["records"][0]["status"] == "resolved"


def test_inc_10240_is_open(store):
    # ITR-008: record_id lookup on INC-10240 must result_contains "open".
    result = store.search(record_type="incident", record_id="INC-10240")
    assert result["records"][0]["status"] == "open"


def test_req_30021_is_submitted(store):
    # ITR-005: record_id lookup on REQ-30021 must result_contains "submitted".
    result = store.search(record_type="request", record_id="REQ-30021")
    assert result["records"][0]["status"] == "submitted"


def test_req_30052_findable_by_in_progress_status(store):
    # ITR-004: status=in_progress list query must include REQ-30052.
    result = store.search(record_type="request", status="in_progress")
    assert any(r["record_id"] == "REQ-30052" for r in result["records"])


def test_req_30052_findable_by_hyphenated_in_progress_status(store):
    # R2 remedy (DEC-018): a hyphenated status value ("in-progress",
    # mirroring how a model sometimes formats it) must also match
    # REQ-30052's seeded "in_progress" status.
    result = store.search(record_type="request", status="in-progress")
    assert any(r["record_id"] == "REQ-30052" for r in result["records"])


def test_inc_10234_findable_by_ci_pipeline_query(store):
    # ITR-001: query="CI pipeline", status=open must include INC-10234.
    result = store.search(record_type="incident", query="CI pipeline", status="open")
    assert any(r["record_id"] == "INC-10234" for r in result["records"])


def test_inc_10234_findable_by_plural_ci_pipelines_query(store):
    # R2 remedy (DEC-014): a plural query ("CI pipelines", mirroring how a
    # user's own question is naturally phrased) must also find INC-10234,
    # whose seeded description uses the singular "CI pipeline".
    result = store.search(record_type="incident", query="CI pipelines", status="open")
    assert any(r["record_id"] == "INC-10234" for r in result["records"])


def test_inc_10261_findable_by_service_catalog_query(store):
    # ITR-007: query="service catalog", status=open must include INC-10261.
    result = store.search(record_type="incident", query="service catalog", status="open")
    assert any(r["record_id"] == "INC-10261" for r in result["records"])


def test_ke_50007_findable_by_ci_runner_cache_query(store):
    # ITR-006: query="CI runner cache corruption" must include KE-50007.
    result = store.search(record_type="known_error", query="CI runner cache corruption")
    assert any(r["record_id"] == "KE-50007" for r in result["records"])


def test_ke_50012_findable_by_quota_exhaustion_query(store):
    # ITR-003: query="namespace quota exhaustion" must include KE-50012.
    result = store.search(record_type="known_error", query="namespace quota exhaustion")
    assert any(r["record_id"] == "KE-50012" for r in result["records"])


def test_search_result_fields_match_srs_mit_if_02(store):
    # SRS-MIT-IF-02: records array items are exactly {record_id,
    # record_type, status, short_description, opened_at, updated_at,
    # owner_team} -- no `description`, `category`, etc. leaking through.
    result = store.search(record_type="incident", record_id="INC-10234")
    record = result["records"][0]
    assert set(record.keys()) == {
        "record_id",
        "record_type",
        "status",
        "short_description",
        "opened_at",
        "updated_at",
        "owner_team",
    }


def test_search_never_mutates_state(store):
    before = store.list_records()
    store.search(record_type="incident", query="CI pipeline")
    store.search(record_type="request", record_id="REQ-30021")
    after = store.list_records()
    assert before == after


def test_search_rejects_invalid_record_type(store):
    with pytest.raises(ValueError):
        store.search(record_type="not-a-real-type")


def test_create_request_mints_sequential_ids_above_floor(store):
    first = store.create_request(
        short_description="a", description="a", category="access", requested_for="alice"
    )
    second = store.create_request(
        short_description="b", description="b", category="access", requested_for="bob"
    )
    assert first["record_id"] == "REQ-30100"
    assert second["record_id"] == "REQ-30101"
    # never collides with a seed ID or an already-minted one
    assert first["record_id"] not in CONTRACTUAL_SEED_IDS
    assert second["record_id"] not in CONTRACTUAL_SEED_IDS


def test_create_request_output_shape_matches_srs_mit_if_03(store):
    result = store.create_request(
        short_description="a", description="a", category="access", requested_for="alice"
    )
    assert set(result.keys()) == {"record_id", "status", "source"}
    assert result["status"] == "submitted"
    assert result["source"] == "mock-itsm"


def test_create_request_rejects_invalid_category(store):
    with pytest.raises(ValueError):
        store.create_request(
            short_description="a", description="a", category="not-a-category", requested_for="alice"
        )


def test_write_then_read_round_trip_within_one_instance(store):
    # SRS-MIT-IF-05: a record created by itsm_create_request shall
    # subsequently be visible to itsm_search_records within the instance.
    created = store.create_request(
        short_description="VPN access for new hire",
        description="Needs VPN access.",
        category="access",
        requested_for="carol",
    )
    found = store.search(record_type="request", record_id=created["record_id"])
    assert found["count"] == 1
    assert found["records"][0]["record_id"] == created["record_id"]
    assert found["records"][0]["short_description"] == "VPN access for new hire"


def test_reset_restores_exactly_the_seed_set_discarding_created_requests(store):
    store.create_request(
        short_description="a", description="a", category="access", requested_for="alice"
    )
    assert len(store.list_records()) == len(CONTRACTUAL_SEED_IDS) + 1

    store.reset()

    seeded_ids = {r["record_id"] for r in store.list_records()}
    assert seeded_ids == CONTRACTUAL_SEED_IDS


def test_reset_restores_sequential_id_floor(store):
    store.create_request(
        short_description="a", description="a", category="access", requested_for="alice"
    )
    store.reset()
    first_after_reset = store.create_request(
        short_description="b", description="b", category="access", requested_for="bob"
    )
    assert first_after_reset["record_id"] == "REQ-30100"


@pytest.mark.parametrize("op", ["search", "create_request"])
def test_simulate_error_timeout_raises_timeout_error(store, op):
    with pytest.raises(TimeoutError):
        if op == "search":
            store.search(record_type="incident", _simulate_error="timeout")
        else:
            store.create_request(
                short_description="a",
                description="a",
                category="access",
                requested_for="alice",
                _simulate_error="timeout",
            )


@pytest.mark.parametrize("op", ["search", "create_request"])
def test_simulate_error_other_raises_connection_error(store, op):
    with pytest.raises(ConnectionError):
        if op == "search":
            store.search(record_type="incident", _simulate_error="connection_refused")
        else:
            store.create_request(
                short_description="a",
                description="a",
                category="access",
                requested_for="alice",
                _simulate_error="retries_exhausted",
            )
