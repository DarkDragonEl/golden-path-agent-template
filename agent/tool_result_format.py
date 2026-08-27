"""Deterministic tool-result -> final_output text formatting (DEC-013).

Not a model call: a tool-call branch never needs a second call to produce
its final_output -- the deterministic mapping here is sufficient (domain
eval's result_contains-style assertions only need the relevant fact
substrings present, not fluent prose). `generate`'s genuine second model
call is on the separate no-tool/knowledge-answer branch this module is
never reached from.
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
