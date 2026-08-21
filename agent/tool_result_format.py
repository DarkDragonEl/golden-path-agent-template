"""Deterministic tool-result -> final_output text formatting.

Not a second model call: SRS-AGT-F-03 keeps this agent to one model call
per turn, and the domain eval cases (result_contains-style assertions)
only need the relevant fact substrings present, not fluent prose. This is
the fix for the gap flagged in the Phase B2 report ("human_approval_node's
final_output formatting doesn't know itsm_create_request's output shape")
— it turns out the same gap also affects tool_invoke_node's own read
path for itsm_search_records, found while live-smoke-testing Phase B3.
"""


def format_tool_result(tool_name: str, result) -> str:
    if not isinstance(result, dict):
        return str(result)

    if tool_name == "itsm_search_records":
        records = result.get("records", [])
        if not records:
            return "No matching records found."
        return "\n".join(
            f"{r['record_id']} ({r['record_type']}, status: {r['status']}): {r['short_description']}"
            for r in records
        )

    if tool_name == "itsm_create_request":
        return f"Request {result.get('record_id')} has been submitted (status: {result.get('status')})."

    # placeholder_lookup and anything else not yet given a real format:
    # legacy {"result": ..., "source": ...} shape.
    if "result" in result:
        return result.get("result", "")
    return str(result)
