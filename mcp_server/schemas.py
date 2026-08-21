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

    Existence and callability of this tool in Phase B1 does not itself
    grant it a bypass path (SRS-MIT-SEC-01): the approval gate is enforced
    by the agent's write-gating restructure, landing in Phase B2, not by
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
