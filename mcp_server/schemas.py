"""Pydantic request/response schemas for the mock ITSM MCP tool contract
(srs/SRS-MIT.md) that mcp_server/server.py's tool handlers validate
against; agent/tool_schemas.py mirrors the input fields field-for-field for
the model-facing tool schema, so the two stay in lockstep without importing
one from the other.

ItsmSearchRecordsInput/Output implement SRS-MIT-IF-02 (read-only,
record_type constrained to itsm_store.RECORD_TYPES). ItsmCreateRequestInput/
Output implement SRS-MIT-IF-03 (write, category constrained to
itsm_store.REQUEST_CATEGORIES) — approval-gated by the agent's write-gating
restructure (SRS-MIT-SEC-01), not by this schema or by mcp_server/server.py.
PlaceholderLookupInput/Output are the not-yet-domain-specific placeholder
tool's schema (TODO(domain): replace once the real domain tools are
selected). PlaceholderWriteActionInput is the dedicated write-classified
placeholder tool (agent/policy.py, ADR-018) so a write is signaled by which
tool is called, never by an
argument flag — placeholder_lookup's own legacy `write` field is unchanged
and unused by this tool.
"""

from pydantic import BaseModel, Field

from .itsm_store import RECORD_TYPES, REQUEST_CATEGORIES


class ItsmSearchRecordsInput(BaseModel):
    """Field-for-field per srs/SRS-MIT.md SRS-MIT-IF-02. Read-only."""

    record_type: str = Field(description="incident | request | known_error")
    query: str | None = None
    record_id: str | None = None
    status: str | None = None
    limit: int = 10

    def model_post_init(self, __context) -> None:
        if self.record_type not in RECORD_TYPES:
            raise ValueError(f"record_type must be one of {RECORD_TYPES}, got {self.record_type!r}")


class ItsmSearchRecordsOutput(BaseModel):
    records: list[dict]
    count: int
    source: str = "mock-itsm"


class ItsmCreateRequestInput(BaseModel):
    """Field-for-field per srs/SRS-MIT.md SRS-MIT-IF-03. Write — approval-gated.

    Existence and callability of this tool does not itself
    grant it a bypass path (SRS-MIT-SEC-01): the approval gate is enforced
    by the agent's write-gating restructure, not by
    this schema or by mcp_server/server.py.
    """

    short_description: str
    description: str
    category: str = Field(description="access | provisioning | break_fix | information")
    requested_for: str
    related_record_id: str | None = None

    def model_post_init(self, __context) -> None:
        if self.category not in REQUEST_CATEGORIES:
            raise ValueError(f"category must be one of {REQUEST_CATEGORIES}, got {self.category!r}")


class ItsmCreateRequestOutput(BaseModel):
    record_id: str
    status: str = "submitted"
    source: str = "mock-itsm"


class PlaceholderLookupInput(BaseModel):
    query: str
    write: bool = False
    # TODO(domain): replace with the real domain tool's actual input fields
    # once the 1-2 domain tools are selected (e.g. record_id, filters).
    # `write` is a generic placeholder signal distinguishing a
    # consequential call from a read — keep an equivalent signal even
    # after the real schema replaces this one.


class PlaceholderLookupOutput(BaseModel):
    result: str
    source: str
    # TODO(domain): replace with the real domain tool's actual output shape
    # (structured record / citation metadata / status code).


class PlaceholderWriteActionInput(BaseModel):
    """ADR-018: write is signaled by which tool is called, never an
    argument (SRS-MIT-IF-03), same as every real domain tool.
    placeholder_lookup stays CONTRACT-FROZEN; this tool never sets or
    reads its write field."""

    query: str
