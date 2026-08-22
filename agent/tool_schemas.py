"""OpenAI-style tool schemas the agent passes to the model on every
reasoning call. Mirrors mcp_server/schemas.py's ItsmSearchRecordsInput/
ItsmCreateRequestInput field-for-field (srs/SRS-MIT.md SRS-MIT-IF-02/IF-03).
Same-PR sync obligation: any field change on either side lands in the
same PR — the pattern this repo's SRS documents already use for reader-
convenience schema reproductions (e.g. srs/SRS-AGT.md §2's note on
SRS-APR-IF-01/SRS-MIT-IF-02/03).

Gap noted honestly, not glossed over: `srs/SRS-AGT.md`'s SRS-AGT-IF-04
(resolved at Checkpoint B0-b, accepted as drafted) calls for treating
SRS-MIT-IF-01's tool-catalog metadata as the *runtime* source of truth for
tool identity, via a real MCP client session — `mcp_server/client.py`
does not implement the MCP protocol today (an in-process function call in
mock mode, an ad hoc REST POST in live mode), so a genuine MCP
`ClientSession`-based runtime lookup is out of Phase B3's scope. This
static, same-PR-synced mirror is the interim realization; closing the gap
for real is future work, not silently declared done.

Empirically verified against the live MaaS (both `granite-3-2-8b-instruct`
and `llama-scout-17b`) in the Phase B kickoff tool-calling spike —
`tools/phase_b_tool_calling_spike.py` / `reports/phase-b-tool-calling-spike.md`
— using this exact schema shape.
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "itsm_search_records",
            "description": (
                "Search or look up mock ITSM records (incidents, requests, known errors). "
                "Read-only; never creates, modifies, or deletes state."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "record_type": {
                        "type": "string",
                        "enum": ["incident", "request", "known_error"],
                        "description": "Which kind of record to search.",
                    },
                    "query": {"type": "string", "description": "Free-text search query."},
                    "record_id": {
                        "type": "string",
                        "description": "When present, return that one record instead of a list.",
                    },
                    "status": {"type": "string", "description": "Optional status filter."},
                    "limit": {"type": "integer", "description": "Max records to return (default 10)."},
                },
                "required": ["record_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "itsm_create_request",
            "description": (
                "Draft a new ITSM service request. Write — approval-gated; calling this only "
                "drafts the request, it does not execute until a human approves it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "short_description": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["access", "provisioning", "break_fix", "information"],
                    },
                    "requested_for": {"type": "string"},
                    "related_record_id": {"type": "string"},
                },
                "required": ["short_description", "description", "category", "requested_for"],
            },
        },
    },
]
