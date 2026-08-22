from agent.tool_result_format import format_tool_result


def test_search_records_formats_each_record_readably():
    result = {
        "records": [
            {
                "record_id": "INC-10255",
                "record_type": "incident",
                "status": "resolved",
                "short_description": "Ingress certificate auto-renewal failure",
                "opened_at": "x",
                "updated_at": "x",
                "owner_team": "platform-networking",
            }
        ],
        "count": 1,
        "source": "mock-itsm",
    }
    text = format_tool_result("itsm_search_records", result)
    assert "INC-10255" in text
    assert "resolved" in text
    assert "Ingress certificate auto-renewal failure" in text


def test_search_records_no_matches():
    result = {"records": [], "count": 0, "source": "mock-itsm"}
    assert "No matching records found" in format_tool_result("itsm_search_records", result)


def test_create_request_surfaces_the_minted_record_id():
    result = {"record_id": "REQ-30100", "status": "submitted", "source": "mock-itsm"}
    text = format_tool_result("itsm_create_request", result)
    assert "REQ-30100" in text
    assert "submitted" in text


def test_placeholder_lookup_unchanged_legacy_shape():
    result = {"result": "PLACEHOLDER_TOOL_RESPONSE_MARKER", "source": "mock"}
    assert format_tool_result("placeholder_lookup", result) == "PLACEHOLDER_TOOL_RESPONSE_MARKER"


def test_non_dict_result_stringified():
    assert format_tool_result("itsm_search_records", None) == "None"
    assert format_tool_result("anything", "already a string") == "already a string"


def test_unknown_tool_without_result_key_stringified():
    result = {"some": "shape"}
    assert format_tool_result("some_future_tool", result) == str(result)
