import pytest
from starlette.testclient import TestClient

from mcp_server import itsm_store
from mcp_server.server import build_app


@pytest.fixture(scope="session")
def rest_client():
    """Shared REST client for mcp_server's combined FastAPI+MCP app.

    Session-scoped, not per-module: `mcp_server.server.mcp` is a
    process-wide singleton that lazily creates and caches its own
    StreamableHTTPSessionManager on first `streamable_http_app()` call,
    and that session manager's `.run()` can only be entered once per
    *process*, not once per test module — confirmed empirically (a second
    `build_app()`/TestClient cycle in the same process raises `RuntimeError:
    ... can only be called once per instance`, even after the first one's
    context has fully exited). Every test needing REST access shares this
    one fixture instead of calling `build_app()` itself.
    """
    with TestClient(build_app()) as client:
        yield client


@pytest.fixture(autouse=True)
def _reset_itsm_store():
    """Every test starts and ends against the seed data, regardless of
    which tests ran before it or in what order."""
    itsm_store.store.reset()
    yield
    itsm_store.store.reset()
