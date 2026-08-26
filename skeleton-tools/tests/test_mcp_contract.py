import os

os.environ.setdefault("MCP_MODE", "mock")

from mcp_server.schemas import PlaceholderLookupInput, PlaceholderLookupOutput  # noqa: E402
from mcp_server.server import healthcheck, placeholder_lookup  # noqa: E402


def test_placeholder_lookup_mock_response():
    result = placeholder_lookup(query="anything")
    validated = PlaceholderLookupOutput(**result)
    assert validated.result == "PLACEHOLDER_TOOL_RESPONSE_MARKER"
    assert validated.source == "mock"


def test_input_schema_accepts_write_flag():
    parsed = PlaceholderLookupInput(query="x", write=True)
    assert parsed.write is True


def test_input_schema_defaults_write_false():
    parsed = PlaceholderLookupInput(query="x")
    assert parsed.write is False


def test_healthcheck():
    assert healthcheck() == {"status": "ok"}
